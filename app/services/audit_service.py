from sqlalchemy.orm import Session
from app.db.models.governance import GovernanceLog
from datetime import datetime, timedelta

class AuditService:
    def check_system_integrity(self, db: Session):
        """Checks if system logs are being written (Heartbeat)."""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        try:
            # We assume the table exists. In a real scenario without migration, this might fail if run against a real DB.
            # But we are designing for the structure.
            count = db.query(GovernanceLog).filter(GovernanceLog.timestamp >= cutoff).count()

            # If no logs in 24h, system might be down or stale
            status = "HEALTHY" if count > 0 else "WARNING"
            message = f"{count} events in 24h"

            if count == 0:
                message = "System logs are stale or inactive."

            return {"status": status, "message": message}
        except Exception as e:
            # Fallback for when table doesn't exist or DB error
            return {"status": "WARNING", "message": "Audit log inaccessible."}

audit_service = AuditService()
