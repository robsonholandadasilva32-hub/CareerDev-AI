from fastapi import Request
from fastapi.responses import RedirectResponse
from app.core.jwt import decode_token


def require_auth(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/login", status_code=302)

    payload = decode_token(token)

    if not payload:
        return RedirectResponse("/login", status_code=302)

    # opcional: anexar user_id ao request
    request.state.user_id = payload.get("sub")

    return None

