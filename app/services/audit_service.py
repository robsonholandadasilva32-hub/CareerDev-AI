from sqlalchemy.orm import Session
from app.db.models.governance import GovernanceLog
from datetime import datetime, timedelta

class AuditService:
    def check_system_integrity(self, db: Session):
        """
        Checks if the Governance System is active (heartbeat).
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Check if any system/governance logs exist in the last 24h
        # Using a count query is efficient
        recent_count = db.query(GovernanceLog).filter(GovernanceLog.timestamp >= cutoff).count()

        if recent_count > 0:
            return {"status": "HEALTHY", "message": "System active."}
        else:
            return {"status": "WARNING", "message": "No governance logs in 24h."}

audit_service = AuditService()
