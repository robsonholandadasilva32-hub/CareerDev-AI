from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from app.db.declarative import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.db.models.security import AuditLog, UserSession
import pytest
from sqlalchemy.orm.exc import DetachedInstanceError

# Setup In-Memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_detached_error_reproduction(db):
    # 1. Create User
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="hash"
    )
    db.add(user)
    db.commit()
    user_id = user.id

    # Ensure creation session is closed so we start fresh
    db.close()

    # 2. Fetch User in a new session (Standard Query)
    session2 = SessionLocal()
    user_fetched = session2.query(User).filter(User.id == user_id).first()

    # 3. Close session (simulating request end before background task)
    session2.close()

    # 4. Access lazy loaded property -> Should Fail
    with pytest.raises(DetachedInstanceError):
        _ = user_fetched.career_profile

def test_eager_load_fix(db):
    # 1. Create User
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="hash"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    # 2. Fetch User WITH joinedload (The Fix)
    session2 = SessionLocal()
    user_fetched = session2.query(User).options(joinedload(User.career_profile)).filter(User.id == user_id).first()

    # 3. Close session
    session2.close()

    # 4. Access property -> Should Succeed (return None as it is empty)
    # This confirms that joinedload loads the relationship (even if None) and prevents DetachedInstanceError
    assert user_fetched.career_profile is None
