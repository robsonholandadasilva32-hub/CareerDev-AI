from fastapi import APIRouter, Response, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.jwt import decode_token
from app.services.security_service import revoke_session, log_audit

router = APIRouter()

@router.get("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # 1. Get Token/Session
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            sid = payload.get("sid")
            user_id = payload.get("sub")

            if sid:
                revoke_session(db, sid)

            try:
                uid = int(user_id) if user_id else None
                log_audit(db, uid, "LOGOUT", request.client.host, f"Session {sid} revoked", session_id=sid)
            except:
                pass

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("careerdev_session")
    return response
