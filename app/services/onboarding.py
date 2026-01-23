from app.db.models.user import User
from fastapi.responses import RedirectResponse

def get_next_onboarding_step(user: User) -> str:
    """
    Determines the next step in the onboarding flow for a user.
    NOW: Strictly prioritizes Dashboard access. Onboarding is removed.
    """
    return "/dashboard"

def validate_onboarding_access(user: User):
    """
    Checks if the user has completed onboarding.
    NOW: Always returns None (Access Granted).
    """
    return None
