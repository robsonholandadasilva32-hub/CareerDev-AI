from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.security import AuditLog
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_current_admin(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    if not user.is_admin:
        logger.warning(f"Unauthorized Admin Access Attempt by User {user.id}")
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    # Calculate offset
    offset = (page - 1) * limit

    # Fetch total users
    total_users = db.query(User).count()

    # Calculate total pages
    total_pages = (total_users + limit - 1) // limit

    # Fetch users with pagination
    users = db.query(User).offset(offset).limit(limit).all()

    # Fetch recent watchdog logs
    logs = db.query(AuditLog)\
        .filter(AuditLog.action == "WARNING")\
        .order_by(AuditLog.created_at.desc())\
        .limit(50)\
        .all()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": admin,
            "users": users,
            "logs": logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_users": total_users,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }
    )

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
