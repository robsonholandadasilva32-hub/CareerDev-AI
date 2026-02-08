from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.audit_service import audit_service
from app.services.pdf_engine import pdf_engine
from app.db.models.user import User
from datetime import datetime

router = APIRouter()

def get_current_user_secure(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@router.get("/audit/export")
def export_audit_log(
    user: User = Depends(get_current_user_secure),
    db: Session = Depends(get_db)
):
    # Fetch logs
    logs = audit_service.get_recent_activity(db, user.id, limit=50)

    # Generate PDF
    user_name = user.email if user.email else f"User {user.id}"

    pdf_buffer = pdf_engine.generate_audit_report(user_name, logs)

    # Generate filename with timestamp as requested
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_report_{user.id}_{timestamp}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
