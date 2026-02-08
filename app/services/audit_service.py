from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.models.governance import GovernanceLog
from typing import List, Optional

class AuditService:
    def log(self, db: Session, user_id: Optional[int], event: str, details: str, severity: str = "INFO"):
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
        return db.query(GovernanceLog).order_by(desc(GovernanceLog.created_at)).limit(limit).all()

audit_service = AuditService()
