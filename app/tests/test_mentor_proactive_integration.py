import pytest
from unittest.mock import MagicMock, patch
from app.services.mentor_engine import MentorEngine
from app.services.career_engine import CareerEngine
from app.db.models.user import User

def test_proactive_from_counterfactual_logic():
    """Test the logic of the new method in MentorEngine"""
    # Setup
    mentor = MentorEngine()
    mentor.store = MagicMock()
    db = MagicMock()
    user = MagicMock(spec=User)

    # Case 1: Valid counterfactual
    counterfactual = {
        "actions": [
            {"action": "Learn Rust", "impact": "High"}
        ]
    }

    mentor.proactive_from_counterfactual(db, user, counterfactual)

    # Verify
    mentor.store.assert_called_once()
    args, _ = mentor.store.call_args
    # args: (db, user, category, content)
    assert args[1] == user
    assert args[2] == "PROACTIVE"
    assert "Learn Rust" in args[3]
    assert "High" in args[3]

def test_proactive_from_counterfactual_empty():
    """Test that empty or invalid data does not trigger storage"""
    # Setup
    mentor = MentorEngine()
    mentor.store = MagicMock()
    db = MagicMock()
    user = MagicMock(spec=User)

    # Case 2: Empty/Invalid
    mentor.proactive_from_counterfactual(db, user, {})
    mentor.proactive_from_counterfactual(db, user, {"actions": []})

    # Verify no calls
    mentor.store.assert_not_called()

def test_generate_multi_week_plan_logic():
    """Test the logic of the generate_multi_week_plan method"""
    # Setup
    mentor = MentorEngine()
    mentor.store = MagicMock()
    db = MagicMock()
    user = MagicMock(spec=User)

    # Case 1: Valid counterfactual
    counterfactual = {
        "actions": [
            {"action": "Action 1", "impact": "High"},
            {"action": "Action 2", "impact": "Low"}
        ]
    }

    result = mentor.generate_multi_week_plan(db, user, counterfactual)

    # Verify
    assert len(result) == 4
    assert result[0]["week"] == "Week 1"
    assert len(result[0]["tasks"]) == 2
    assert result[0]["tasks"][0]["task"] == "Action 1"
    assert result[0]["tasks"][0]["status"] == "Pending"

    # Verify storage
    mentor.store.assert_called_once()
    args, _ = mentor.store.call_args
    assert args[2] == "MULTI_WEEK_PLAN"

def test_generate_weekly_plan_from_shap_logic():
    """Test the logic of the generate_weekly_plan_from_shap method"""
    # Setup
    mentor = MentorEngine()
    mentor.store = MagicMock()
    db = MagicMock()
    user = MagicMock(spec=User)

    # Case 1: Valid counterfactual
    counterfactual = {
        "actions": [
            {"action": "Action 1", "impact": "High"},
            {"action": "Action 2", "impact": "Low"},
            {"action": "Action 3", "impact": "Medium"},
            {"action": "Action 4", "impact": "High"}
        ]
    }

    result = mentor.generate_weekly_plan_from_shap(db, user, counterfactual)

    # Verify
    assert len(result) == 4
    # Check distribution logic: Mon, Wed, Fri, Mon
    assert result[0]["day"] == "Mon"
    assert result[0]["task"] == "Action 1"

    assert result[1]["day"] == "Wed"
    assert result[1]["task"] == "Action 2"

    assert result[2]["day"] == "Fri"
    assert result[2]["task"] == "Action 3"

    assert result[3]["day"] == "Mon"
    assert result[3]["task"] == "Action 4"

    # Verify storage
    mentor.store.assert_called_once()
    args, _ = mentor.store.call_args
    assert args[2] == "WEEKLY_PLAN"

def test_career_engine_integration():
    """Test that CareerEngine.analyze calls mentor_engine.proactive_from_counterfactual and generate_weekly_plan_from_shap"""
    # Mock dependencies
    with patch("app.services.career_engine.mentor_engine") as mock_mentor, \
         patch("app.services.career_engine.counterfactual_engine") as mock_cf_engine, \
         patch("app.services.career_engine.benchmark_engine") as mock_benchmark, \
         patch("app.services.career_engine.compute_features") as mock_compute, \
         patch("app.services.career_engine.CareerEngine.forecast_career_risk") as mock_forecast:

        # Setup return values
        mock_cf_data = {"actions": [{"action": "Test Action", "impact": "10"}]}
        mock_cf_engine.generate.return_value = mock_cf_data
        mock_forecast.return_value = {"risk_score": 50}

        # Initialize engine
        career = CareerEngine()
        # Mock internal methods to isolate analyze flow
        career._calculate_skill_confidence = MagicMock(return_value={})
        career._generate_weekly_routine = MagicMock(return_value={})
        career.should_enable_accelerator = MagicMock(return_value=False)

        # Call analyze
        db = MagicMock()
        user = MagicMock(spec=User)
        user.streak_count = 0
        user.id = 1

        # Configure career_profile and metrics to avoid MagicMock comparison errors
        user.career_profile = MagicMock()
        # Ensure dictionary access works for these attributes
        user.career_profile.github_activity_metrics = {"commits_last_30_days": 10, "raw_languages": {}}
        user.career_profile.linkedin_alignment_data = {}
        user.career_profile.market_relevance_score = 80
        user.career_profile.skills_snapshot = {}

        # We need to ensure db.query works if it's called
        # The analyze method queries RiskSnapshot
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_limit = mock_order.limit.return_value
        mock_limit.all.return_value = [] # No snapshots for this test

        result_dict = career.analyze(
            db=db,
            raw_languages={},
            linkedin_input={},
            metrics={},
            skill_audit={},
            user=user
        )

        # Verify mentor was called with the CF data
        mock_mentor.proactive_from_counterfactual.assert_called_once_with(db, user, mock_cf_data)

        # Verify multi-week plan generation
        mock_mentor.generate_multi_week_plan.assert_called_once_with(db, user, mock_cf_data)

        # Verify SHAP-based weekly plan generation
        mock_mentor.generate_weekly_plan_from_shap.assert_called_once_with(db, user, mock_cf_data)

        # Verify result contains the new key
        assert "auto_weekly_plan" in result_dict
