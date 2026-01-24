from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_admin(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    if not user.is_admin:
        logger.warning(f"Unauthorized Admin Access Attempt by User {user.id}")
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.post("/admin/users/{user_id}/ban")
def ban_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle ban status
    target_user.is_banned = not target_user.is_banned
    db.commit()

    status = "banned" if target_user.is_banned else "unbanned"
    logger.info(f"Admin {admin.id} {status} user {user_id}")

    return {"message": f"User {user_id} has been {status}", "is_banned": target_user.is_banned}
