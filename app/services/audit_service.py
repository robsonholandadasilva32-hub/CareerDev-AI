from sqlalchemy.orm import Session
from app.db.models.governance import GovernanceLog
from datetime import datetime, timedelta

class AuditService:
    def get_compliance_summary(self, db: Session, user_id: int):
        """
        Returns a summary of audit activity for the governance dashboard.
        Counts GovernanceLog entries in the last 24h to prove the system is active.
        """
        # Check if GovernanceLog table exists/has data, handle gracefully
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            count = db.query(GovernanceLog).filter(GovernanceLog.timestamp >= cutoff).count()

            last_event = db.query(GovernanceLog).order_by(GovernanceLog.timestamp.desc()).first()
            last_active = last_event.timestamp if last_event else None
        except Exception:
            # Fallback if table doesn't exist yet or query fails
            count = 0
            last_active = None

        return {
            "total_events_logged": count,
            "last_activity": last_active,
            "status": "ACTIVE" if count > 0 else "IDLE"
        }

    def cleanup_governance_logs(self, db: Session, retention_days: int = 90):
        """
        Deletes governance logs older than the retention period (default 90 days).
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = db.query(GovernanceLog).filter(GovernanceLog.timestamp < cutoff).delete()
            db.commit()
            return deleted_count
        except Exception as e:
            db.rollback()
            # In a real app, we would log this error
            return 0

audit_service = AuditService()
