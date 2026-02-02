from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

if settings.ENVIRONMENT == "production" and "sqlite" in DATABASE_URL:
    import logging
    logging.getLogger("app.db").warning("⚠️  PRODUCTION WARNING: Using SQLite in production is NOT recommended. Use PostgreSQL.")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ✅ DEPENDÊNCIA PADRÃO FASTAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

