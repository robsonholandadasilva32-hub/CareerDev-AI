import pytest
from unittest.mock import MagicMock
from app.services.onboarding import get_next_onboarding_step

class MockUser:
    def __init__(self, linkedin_id=None, github_id=None, is_profile_completed=False):
        self.linkedin_id = linkedin_id
        self.github_id = github_id
        self.is_profile_completed = is_profile_completed

def test_onboarding_flow_logic():
    # Case 1: No LinkedIn
    user = MockUser(linkedin_id=None, github_id="gh123", is_profile_completed=False)
    assert get_next_onboarding_step(user) == "/login/linkedin"

    # Case 2: LinkedIn but no GitHub
    user = MockUser(linkedin_id="li123", github_id=None, is_profile_completed=False)
    assert get_next_onboarding_step(user) == "/onboarding/connect-github"

    # Case 3: LinkedIn and GitHub, but profile incomplete
    user = MockUser(linkedin_id="li123", github_id="gh123", is_profile_completed=False)
    assert get_next_onboarding_step(user) == "/onboarding/complete-profile"

    # Case 4: All done
    user = MockUser(linkedin_id="li123", github_id="gh123", is_profile_completed=True)
    assert get_next_onboarding_step(user) == "/dashboard"

def test_user_model_file_content():
    # Verify the User model file contains the new fields
    with open("app/db/models/user.py", "r") as f:
        content = f.read()

    assert "address_street = Column(String" in content
    assert "billing_address_street = Column(String" in content
    assert "is_profile_completed = Column(Boolean" in content
    assert "terms_accepted = Column(Boolean" in content
