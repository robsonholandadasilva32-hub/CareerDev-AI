from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.db.models.mentor_memory import MentorMemory

def cleanup_old_memories(days=180):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)

    db.query(MentorMemory)\
      .filter(MentorMemory.created_at < cutoff)\
      .delete()

    db.commit()
