from fastapi import Request
from fastapi.responses import RedirectResponse

def require_auth(request: Request):
    """
    Guards a route by checking if request.state.user is populated.
    This relies on AuthMiddleware having run and validated the session.
    """
    if getattr(request.state, "user", None):
        return None

    return RedirectResponse("/login", status_code=302)

def get_current_user_from_request(request: Request):
    """
    Helper to extract user_id from request.state.user.
    Returns None if invalid.
    """
    user = getattr(request.state, "user", None)
    if user:
        return user.id
    return None
