import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.routes.dashboard import get_current_user_secure
from app.db.session import get_db

client = TestClient(app)

class MockUser:
    id = 1
    email = "test@example.com"
    name = "Test User"
    badges = []
    is_premium = False
    is_admin = False
    # Mock career_profile as an object, not just MagicMock because template accesses attributes
    career_profile = MagicMock()

def mock_get_current_user_secure():
    user = MockUser()
    user.career_profile.level = 1
    user.career_profile.focus = "Dev"
    return user

def mock_get_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[get_current_user_secure] = mock_get_current_user_secure
    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides = {}

@patch("app.routes.dashboard.career_engine")
@patch("app.routes.dashboard.validate_onboarding_access", return_value=None)
def test_dashboard_contains_pro_suite(mock_validate, mock_career_engine):
    mock_career_engine.analyze_profile.return_value = {"level": 1, "focus": "Dev", "skills": {}}
    mock_career_engine.generate_plan.return_value = []
    mock_career_engine.get_career_dashboard_data.return_value = {
        "zone_a_holistic": {"score": 80, "color": "green", "details": "Good"},
        "zone_b_matrix": [],
        "zone_c_ai": {"insights": "Good job"},
        "doughnut_data": {}
    }

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "PRO SUITE" in response.text
    assert "DOWNLOAD PASSPORT" in response.text
    assert "COPY BADGE MARKDOWN" in response.text
    assert "copyBadgeCode()" in response.text
