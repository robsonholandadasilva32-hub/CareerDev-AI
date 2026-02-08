from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from app.db.models.governance import GovernanceLog
from app.db.models.audit import AuditLog

class AuditService:
    def check_system_integrity(self, db: Session):
        """
        Checks if the Governance System is active (heartbeat).
        Used by the Trust Engine to verify if logs are being written.
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Check if any system/governance logs exist in the last 24h
        # Using a count query is efficient and prevents loading full objects
        recent_count = db.query(GovernanceLog).filter(GovernanceLog.timestamp >= cutoff).count()

        if recent_count > 0:
            return {"status": "HEALTHY", "message": "System active."}
        else:
            return {"status": "WARNING", "message": "No governance logs in 24h."}

    def get_recent_activity(self, db: Session, user_id: int, limit: int = 50):
        """
        Retrieves recent audit logs for a user.
        Used by the Dashboard to show login history and user actions.
        """
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.login_timestamp)).limit(limit).all()

audit_service = AuditService()