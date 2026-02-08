from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from app.db.models.governance import GovernanceLog

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for handling Governance and Compliance logging.
    Separated from Authentication/Security logs to ensure
    clean audit trails for system health and risk assessments.
    """

    def log_event(
        self,
        db: Session,
        user_id: int,
        event_type: str,
        severity: str = "INFO",
        details: Optional[str] = None
    ) -> GovernanceLog:
        """
        Logs a governance event (e.g., Risk Check, Policy Update).
        """
        try:
            log_entry = GovernanceLog(
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
        except Exception as e:
            logger.error(f"Failed to log governance event: {e}")
            db.rollback()
            return None

    def get_recent_activity(
        self,
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[GovernanceLog]:
        """
        Fetches the recent governance trail for transparency.
        """
        return (
            db.query(GovernanceLog)
            .filter(GovernanceLog.user_id == user_id)
            .order_by(GovernanceLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_compliance_summary(self, db: Session, user_id: int) -> Dict:
        """
        Generates a summary for the 'System Audit & Governance' panel.
        """
        try:
            # Total events count
            count = db.query(GovernanceLog).filter(GovernanceLog.user_id == user_id).count()

            # Last activity timestamp
            last_event = (
                db.query(GovernanceLog)
                .filter(GovernanceLog.user_id == user_id)
                .order_by(GovernanceLog.timestamp.desc())
                .first()
            )

            return {
                "total_events_logged": count,
                "last_activity": last_event.timestamp if last_event else None,
                "data_status": "SECURE",
                "retention_policy": "90 Days"
            }
        except Exception as e:
            logger.error(f"Failed to fetch compliance summary: {e}")
            return {
                "total_events_logged": 0,
                "last_activity": None,
                "data_status": "ERROR",
                "retention_policy": "Unknown"
            }

# Singleton instance
audit_service = AuditService()
