import os
from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.core.jwt import decode_token
from app.services.security_service import revoke_session

router = APIRouter()

@router.get("/setup/claim-admin-rights")
def claim_admin_rights(request: Request, db: Session = Depends(get_db)):
    # 1. Check if user is logged in (AuthMiddleware populates request.state.user)
    if not getattr(request.state, "user", None):
         return Response(content="Forbidden: You must be logged in.", status_code=403)

    user_state = request.state.user

    # 2. Hardcoded Security Check
    expected_email = os.getenv("ADMIN_EMAIL", "robsonholandasilva@yahoo.com.br")

    # Case-insensitive comparison
    if user_state.email.lower() != expected_email.lower():
        return Response(content="Forbidden: Invalid Account.", status_code=403)

    # 3. Fetch User from DB (state user is detached)
    user = db.query(User).filter(User.id == user_state.id).first()
    if not user:
        return Response(content="User not found in DB.", status_code=404)

    # 4. Set Admin Rights
    user.is_admin = True
    db.commit()

    # 5. Invalidate Session
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            sid = payload.get("sid")
            if sid:
                revoke_session(db, sid)

    # 6. Prepare Response
    final_response = Response(
        content=f"Admin rights granted for {user.email}. Please log in again to see the dashboard.",
        media_type="text/plain"
    )

    # 7. Clear Cookies
    final_response.delete_cookie("access_token")
    final_response.delete_cookie("careerdev_session")

    return final_response
