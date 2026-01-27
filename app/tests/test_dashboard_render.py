import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.routes.dashboard import get_current_user_secure
from app.db.session import get_db

client = TestClient(app)

# Mock User
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
    github_id = "test_github"
    is_profile_completed = True
    preferred_language = "pt"
    avatar_url = "http://example.com/avatar.jpg"

def mock_get_current_user_secure():
    return MockUser()

def mock_get_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_current_user_secure] = mock_get_current_user_secure
    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides = {}

@patch("app.routes.dashboard.career_engine")
def test_dashboard_render_user_context(mock_career_engine):
    # Setup mocks for career_engine
    mock_career_engine.analyze_profile.return_value = {"level": "Junior", "focus": "Backend", "trends": {}}
    mock_career_engine.generate_plan.return_value = []
    mock_career_engine.get_career_dashboard_data.return_value = {
        "market_trends": {},
        "skill_gap": [],
        "weekly_plan": [],
        "radar_data": {"labels": [], "datasets": []},
        "doughnut_data": {"labels": [], "datasets": []},
        "market_alignment_score": 50
    }

    # Make request
    # Note: TestClient raises exceptions from the app by default.
    # The Jinja2 UndefinedError will propagate here.
    try:
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Template prefers name over email
        assert "Test User" in response.text
    except Exception as e:
        # If we catch the specific Jinja error, we know we reproduced it.
        # Failing the test with the error message is what we want for "reproduction".
        pytest.fail(f"Dashboard failed to render: {e}")
