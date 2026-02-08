from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.db.models.governance import GovernanceLog

logger = logging.getLogger(__name__)

def cleanup_governance_logs(db: Session, retention_days: int = 90) -> int:
    """
    Purges GovernanceLogs older than the retention period.
    Returns the number of deleted records.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    try:
        deleted_count = db.query(GovernanceLog).filter(
            GovernanceLog.timestamp < cutoff_date
        ).delete()

        db.commit()
        logger.info(f"✅ Governance Log Cleanup: {deleted_count} records purged (older than {retention_days} days).")
        return deleted_count

    except Exception as e:
        logger.error(f"❌ Governance Log Cleanup Failed: {e}")
        db.rollback()
        return 0
