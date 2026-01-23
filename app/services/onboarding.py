from app.db.models.user import User
from fastapi.responses import RedirectResponse

def get_next_onboarding_step(user: User) -> str:
    """
    Determines the next step in the onboarding flow for a user.
    Strictly prioritizes Dashboard access if profile is marked as completed.
    """
    # 1. Absolute Priority: If profile is completed, go to Dashboard.
    # This prevents looping back to onboarding if a social ID is missing but the user is already "done".
    if user.is_profile_completed:
        return "/dashboard"

    # 2. LinkedIn Check (Primary Auth)
    if not user.linkedin_id:
        return "/login/linkedin"

    # 3. GitHub Check
    if not user.github_id:
        return "/onboarding/connect-github"

    # 4. Profile Completion
    return "/onboarding/complete-profile"

def validate_onboarding_access(user: User):
    """
    Checks if the user has completed onboarding.
    Returns a RedirectResponse to the next step if not complete.
    Returns None if complete.
    """
    # If the user is supposed to be on the dashboard, this returns "/dashboard"
    next_step = get_next_onboarding_step(user)

    # If the calculation says "/dashboard", it means the user is cleared.
    # If we are calling this function from a protected route (like /dashboard),
    # returning None means "Access Granted".
    if next_step == "/dashboard":
        return None

    # Otherwise, redirect to the required step.
    return RedirectResponse(next_step, status_code=303)
