from app.db.models.user import User
from fastapi.responses import RedirectResponse

def get_next_onboarding_step(user: User) -> str:
    """
    Determines the next step in the onboarding flow for a user.
    """
    if not user.github_id:
        return "/onboarding/connect-github"
    # Zero Touch: Profile completion is automatic or skipped
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

    # Zero Touch: We no longer block access for profile completion

    return None
