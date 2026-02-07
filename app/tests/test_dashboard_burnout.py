import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_user_with_profile
from app.db.session import get_db

client = TestClient(app)

class MockUser:
    id = 1
    email = "test@example.com"
    name = "Test User"
    badges = []
    is_premium = False
    subscription_status = "active"
    subscription_end_date = datetime(2030, 1, 1)
    is_recurring = True
    created_at = datetime.now()
    linkedin_id = "test_linkedin"
    linkedin_profile_url = "https://linkedin.com/in/test"
    github_id = "test_github"
    github_username = "test_github_user"
    is_profile_completed = True
    preferred_language = "pt"
    avatar_url = "http://example.com/avatar.jpg"
    streak_count = 5

    career_profile = MagicMock()
    career_profile.github_activity_metrics = {}
    career_profile.linkedin_alignment_data = {}
    career_profile.skills_graph_data = {}
    career_profile.market_relevance_score = 50

def mock_get_user_with_profile():
    return MockUser()

def mock_get_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_user_with_profile] = mock_get_user_with_profile
    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides = {}

@patch("app.routes.dashboard.career_engine")
def test_dashboard_render_burnout_panel(mock_career_engine):
    # Setup mocks for career_engine
    mock_career_engine.analyze.return_value = {
        "zone_a_holistic": {"score": 50},
        "zone_b_matrix": {},
        "weekly_plan": {"mode": "GROWTH", "tasks": []},
        "skill_confidence": {},
        "career_risks": [],
        "hidden_gems": [],
        "career_forecast": {"risk_level": "LOW"},
        "zone_a_radar": {},
        "missing_skills": [],
        "risk_timeline": SimpleNamespace(labels=["Jan", "Feb"], values=[10, 20]),
        "benchmark": {"message": "Contextual Benchmark Test Message"},
        "shap_visual": {"labels": ["Factor A"], "values": [10]},
        "counterfactual": None,
        "multi_week_plan": None,
        # Inject burnout data
        "team_burnout": {
            "burnout_score": 75,
            "level": "HIGH",
            "avg_risk": 80,
            "variance": 10
        },
        "team_health": {
             "health_score": 40,
             "label": "POOR",
             "member_count": 5
        }
    }
    mock_career_engine.get_weekly_history = AsyncMock(return_value=[])

    try:
        response = client.get("/dashboard")
        assert response.status_code == 200

        # Verify Burnout Panel content
        assert "TEAM BURNOUT RISK" in response.text
        assert "75%" in response.text
        assert "HIGH" in response.text
        assert "AVG: 80" in response.text
        assert "VAR: 10" in response.text

        # Verify Team Health Panel content (to ensure both exist)
        assert "TEAM HEALTH" in response.text
        assert "40%" in response.text

    except Exception as e:
        pytest.fail(f"Dashboard failed to render: {e}")
