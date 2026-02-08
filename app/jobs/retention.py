from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models.governance import GovernanceLog
from app.db.session import SessionLocal

def cleanup_governance_logs(days: int = 90):
    """
    Deletes governance logs older than the specified number of days.
    """
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted_count = db.query(GovernanceLog).filter(GovernanceLog.created_at < cutoff).delete()
        db.commit()
        print(f"Cleaned up {deleted_count} governance logs older than {days} days.")
    except Exception as e:
        print(f"Failed to cleanup governance logs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_governance_logs()
