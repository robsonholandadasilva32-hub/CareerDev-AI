import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.declarative import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.gamification import UserBadge
from app.db.crud.users import get_user_by_linkedin_id

# Setup In-Memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_get_user_by_linkedin_id_none_matches_existing_user(db_session):
    # 1. Create a user who signed up via Email (no LinkedIn ID)
    user = User(
        name="Email User",
        email="email@example.com",
        hashed_password="hash",
        linkedin_id=None
    )
    db_session.add(user)
    db_session.commit()

    # 2. Simulate logic: linkedin_id is None (because 'sub' was missing in OIDC response)
    missing_linkedin_id = None

    # 3. Call the function
    # NOTE: The current implementation of get_user_by_linkedin_id just does filter(User.linkedin_id == linkedin_id).
    # If linkedin_id is None, it generates WHERE linkedin_id IS NULL.
    found_user = get_user_by_linkedin_id(db_session, missing_linkedin_id)

    # 4. Assert that it CORRECTLY returns None (fix applied)
    assert found_user is None
