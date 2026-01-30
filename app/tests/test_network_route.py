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
    linkedin_profile_url = "https://linkedin.com/in/test"
    github_id = "test_github"
    github_username = "test_user"
    is_profile_completed = True
    preferred_language = "pt"
    avatar_url = "http://example.com/avatar.jpg"
    streak_count = 5
    # Add attributes checked by templates or other middlewares if necessary
    is_admin = False

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

def test_network_dashboard_render():
    response = client.get("/dashboard/network")
    assert response.status_code == 200
    assert "NETWORK NODE" in response.text
