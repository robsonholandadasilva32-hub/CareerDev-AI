from app.db.models.user import User
from fastapi.responses import RedirectResponse

def get_next_onboarding_step(user: User) -> str:
    """
    Determines the next step in the onboarding flow for a user.
    """
    if not user.linkedin_id:
        # If user somehow got here without LinkedIn (e.g. GitHub login first),
        # we might want to enforce LinkedIn.
        # The prompt says: "if not user.linkedin_id: Redirecionar para Login LinkedIn (fluxo existente)"
        return "/login/linkedin"

    if not user.github_id:
        return "/onboarding/connect-github"

    if not user.is_profile_completed:
        return "/onboarding/complete-profile"

    return "/dashboard"

def validate_onboarding_access(user: User):
    """
    Checks if the user has completed onboarding.
    Returns a RedirectResponse to the next step if not complete.
    Returns None if complete.
    """
    step = get_next_onboarding_step(user)
    if step != "/dashboard":
        return RedirectResponse(step, status_code=302)
    return None
