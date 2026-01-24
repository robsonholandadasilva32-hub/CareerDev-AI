from app.db.models.user import User
from fastapi.responses import RedirectResponse

def get_next_onboarding_step(user: User) -> str:
    """
    Determines the next step in the onboarding flow for a user.
    """
    if not user.github_id:
        return "/onboarding/connect-github"
    if not user.is_profile_completed:
        return "/onboarding/complete-profile"
    return "/dashboard"

def validate_onboarding_access(user: User):
    """
    Enforces strict sequential onboarding flow.
    Returns a RedirectResponse if requirements are not met, else None.
    """
    if not user:
        return RedirectResponse("/login")

    if not user.linkedin_id:
         return RedirectResponse("/logout")

    if not user.github_id:
         return RedirectResponse("/onboarding/connect-github", status_code=303)

    if not user.is_profile_completed:
         return RedirectResponse("/onboarding/complete-profile", status_code=303)

    return None
