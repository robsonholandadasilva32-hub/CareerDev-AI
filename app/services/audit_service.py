from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models.governance import GovernanceLog
from datetime import datetime, timedelta

class AuditService:
    def log_event(self, db: Session, event_type: str, details: str = None, severity: str = "INFO", user_id: int = None):
        """
        Logs a system or user event to the GovernanceLog table.
        """
        try:
            log_entry = GovernanceLog(
                event_type=event_type,
                details=details,
                severity=severity,
                user_id=user_id,
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def get_compliance_summary(self, db: Session, user_id: int):
        """
        Returns summary metrics for the System Audit panel (User-specific + Global).
        """
        # Filter for user-specific events OR global events (user_id is NULL)
        query = db.query(GovernanceLog).filter(
            or_(GovernanceLog.user_id == user_id, GovernanceLog.user_id == None)
        )

        total_logs = query.count()
        last_entry = query.order_by(GovernanceLog.timestamp.desc()).first()

        return {
            "total_events": total_logs,
            "last_activity": last_entry.timestamp if last_entry else None,
            "status": "ACTIVE" if total_logs > 0 else "NO_LOGS"
        }

    def check_system_integrity(self, db: Session):
        """
        Checks if the Governance Subsystem is active (Health Check).
        Monitors ALL logs in the last 24h (User + Global).
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_count = db.query(GovernanceLog).filter(GovernanceLog.timestamp >= cutoff).count()

        return {
            "status": "HEALTHY" if recent_count > 0 else "WARNING",
            "message": f"{recent_count} governance events in last 24h",
            "last_check": datetime.utcnow()
        }

audit_service = AuditService()
