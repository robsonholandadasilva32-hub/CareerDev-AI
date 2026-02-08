from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.db.models.governance import GovernanceLog
from app.db.models.audit import AuditLog

class AuditService:
    # --- Governance & System Integrity (New) ---
    def log(self, db: Session, user_id: Optional[int], event: str, details: str, severity: str = "INFO"):
        """
        Logs a governance event (e.g., Risk Spike, System Check).
        Writes to the governance_logs table.
        """
        try:
            entry = GovernanceLog(
                user_id=user_id,
                event_type=event,
                details=details,
                severity=severity
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
        except Exception as e:
            print(f"Failed to audit log: {e}")
            db.rollback()
            return None

    def get_recent_logs(self, db: Session, limit: int = 50) -> List[GovernanceLog]:
        """
        Retrieves recent governance logs for system auditing.
        """
        # Note: Ensure your GovernanceLog model has 'created_at' or 'timestamp' consistent with this query.
        return db.query(GovernanceLog).order_by(desc(GovernanceLog.created_at)).limit(limit).all()

    # --- User Activity & Auth (Legacy) ---
    def get_recent_activity(self, db: Session, user_id: int, limit: int = 50):
        """
        Retrieves recent audit logs (logins/actions) for a specific user.
        Reads from the audit_logs table.
        """
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.login_timestamp)).limit(limit).all()

audit_service = AuditService()