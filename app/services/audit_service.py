from sqlalchemy.orm import Session
from app.db.models.governance import GovernanceLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    def log_event(self, db: Session, event_type: str, severity: str, details: str, user_id: int = None):
        """
        Logs a system or governance event.
        Does NOT require IP address or request context.
        """
        try:
            log = GovernanceLog(
                event_type=event_type,
                severity=severity,
                details=details,
                user_id=user_id
            )
            db.add(log)
            db.commit()
            logger.info(f"✅ GOVERNANCE LOG: {event_type} [{severity}] - User: {user_id}")
        except Exception as e:
            logger.error(f"❌ GOVERNANCE LOG FAILED: {e}")
            db.rollback()

audit_service = AuditService()
