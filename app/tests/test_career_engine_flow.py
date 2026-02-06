import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.career_engine import career_engine
from app.db.models.user import User
from app.db.models.career import CareerProfile
from datetime import datetime

class MockRiskSnapshot:
    def __init__(self, risk_score, recorded_at):
        self.risk_score = risk_score
        self.recorded_at = recorded_at

@pytest.mark.asyncio
async def test_get_counterfactual_flow():
    # Mock dependencies
    db = MagicMock()
    user = MagicMock(spec=User)
    user.id = 1
    user.streak_count = 5

    # Mock Profile
    profile = MagicMock(spec=CareerProfile)
    profile.github_activity_metrics = {
        "commits_last_30_days": 20,
        "languages": {"Python": 50000}
    }
    profile.linkedin_alignment_data = {
        "skills": {"Python": "Expert"}
    }
    user.career_profile = profile

    # Mock DB Query for RiskSnapshot
    # db.query().filter().order_by().limit().all()
    mock_snapshots = [
        MockRiskSnapshot(risk_score=20, recorded_at=datetime.utcnow()),
        MockRiskSnapshot(risk_score=50, recorded_at=datetime.utcnow())
    ]

    # Setup chain
    query_mock = db.query.return_value
    filter_mock = query_mock.filter.return_value
    order_mock = filter_mock.order_by.return_value
    limit_mock = order_mock.limit.return_value
    limit_mock.all.return_value = mock_snapshots

    # Need to handle alert_engine which might be called inside forecast_career_risk
    # And specifically mock social_harvester.get_metrics which is now awaited
    with patch("app.services.career_engine.alert_engine") as mock_alert, \
         patch("app.services.career_engine.ml_forecaster") as mock_ml, \
         patch("app.services.career_engine.lstm_model") as mock_lstm, \
         patch("app.services.career_engine.social_harvester.get_metrics", new_callable=AsyncMock) as mock_get_metrics:

        mock_ml.predict.return_value = {"ml_risk": 25, "model_version": "v1"}
        mock_lstm.predict.return_value = 25

        # Mock what get_metrics returns
        mock_get_metrics.return_value = {
            "commits_last_30_days": 20,
            "languages": {"Python": 50000}
        }

        # Run (await the async method)
        result = await career_engine.get_counterfactual(db, user)

        # Verify structure
        assert "current_risk" in result
        assert "projected_risk" in result
        assert "actions" in result
        assert "summary" in result

        # Check values
        # Risk decreased (50->20), Slope = 30. Good.
        # Commits = 20. > 15. Good.
        # Market Gap: Python is in user. Rust is in Market. Gap = Rust, etc.
        # So expected action about Market Gap.

        actions = result["actions"]
        assert any("market gap" in a.lower() for a in actions)

# =========================================================
# REFACTORED LOGIC TESTS
# =========================================================

def create_mock_user(commits=0, market_score=0, skills_snapshot=None, languages=None):
    user = MagicMock(spec=User)
    profile = MagicMock(spec=CareerProfile)

    metrics = {}
    if commits is not None:
        metrics["commits_last_30_days"] = commits
    if languages is not None:
        metrics["languages"] = languages

    profile.github_activity_metrics = metrics
    profile.market_relevance_score = market_score
    profile.skills_snapshot = skills_snapshot or {}

    user.career_profile = profile
    return user

def test_explain_risk_priority_1_stagnation():
    # Commits < 5
    user = create_mock_user(commits=4, market_score=80)
    result = career_engine.explain_risk(user)
    assert result["summary"] == "High risk driven by low coding activity (stagnation)."

def test_explain_risk_priority_2_market_relevance():
    # Commits >= 5, Market < 50
    user = create_mock_user(commits=10, market_score=40)
    result = career_engine.explain_risk(user)
    assert result["summary"] == "Risk driven by low alignment with current market trends."

def test_explain_risk_priority_3_skill_gap():
    # Commits >= 5, Market >= 50
    user = create_mock_user(commits=10, market_score=60)
    result = career_engine.explain_risk(user)
    assert result["summary"] == "Moderate risk due to specific skill gaps in your target role."

def test_generate_weekly_routine_focus_selection():
    # Select highest byte count
    stats = {"languages": {"Python": 100, "Rust": 5000, "Go": 200}}
    routine = career_engine._generate_weekly_routine(stats, user_streak=5)
    assert routine["focus"] == "Rust"
    assert "Rust" in routine["tasks"][0]["task"]

def test_generate_weekly_routine_fallback():
    # No languages -> Python
    stats = {"languages": {}}
    routine = career_engine._generate_weekly_routine(stats, user_streak=5)
    assert routine["focus"] == "Python"
    assert "Python" in routine["tasks"][0]["task"]

def test_simulate_skill_path_with_existing_confidence():
    user = create_mock_user(skills_snapshot={"Rust": 50})
    result = career_engine.simulate_skill_path(user, "Rust", months=1)
    # base 50, months 1 * 7 = 57. min(90, 57) = 57.
    assert result["expected_confidence"] == 57

def test_simulate_skill_path_default_confidence():
    user = create_mock_user(skills_snapshot={})
    result = career_engine.simulate_skill_path(user, "Rust", months=1)
    # base 0, months 1 * 7 = 7.
    assert result["expected_confidence"] == 7

def test_simulate_skill_path_market_alignment():
    # Rust is in market_high_demand_skills
    user = create_mock_user()
    result = career_engine.simulate_skill_path(user, "Rust")
    assert result["market_alignment"] == "High"

    # Cobol is likely not
    result_cobol = career_engine.simulate_skill_path(user, "Cobol")
    assert result_cobol["market_alignment"] == "Medium"
