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
