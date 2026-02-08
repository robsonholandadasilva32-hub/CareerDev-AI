from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models.audit import AuditLog

class AuditService:
    def get_recent_activity(self, db: Session, user_id: int, limit: int = 50):
        """Retrieves recent audit logs for a user."""
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.login_timestamp)).limit(limit).all()

audit_service = AuditService()
