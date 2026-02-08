from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models.governance import GovernanceLog
import logging

logger = logging.getLogger(__name__)

def cleanup_governance_logs(db: Session, retention_days: int = 90):
    """
    Deletes GovernanceLog entries older than retention_days.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    try:
        deleted_count = (
            db.query(GovernanceLog)
            .filter(GovernanceLog.timestamp < cutoff_date)
            .delete()
        )
        db.commit()
        if deleted_count > 0:
            logger.info(f"🧹 CLEANUP: Deleted {deleted_count} old GovernanceLog entries.")
    except Exception as e:
        logger.error(f"❌ CLEANUP FAILED: {e}")
        db.rollback()
