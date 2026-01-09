from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./careerdev.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

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

