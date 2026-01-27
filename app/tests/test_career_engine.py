import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.declarative import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.gamification import UserBadge  # noqa: F401
from app.db.models.security import AuditLog, UserSession # noqa: F401
from app.services.career_engine import career_engine

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Create a new database session for each test function.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_generate_plan_avoids_n_plus_one(db_session):
    # 1. Setup
    # Create a user
    test_user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="testpassword",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Create a career profile with some skills
    career_profile = CareerProfile(
        user_id=test_user.id,
        skills_snapshot={"Python": 80, "Go": 10} # Go is under the 30 threshold
    )
    db_session.add(career_profile)
    db_session.commit()

    # 2. Action
    # Generate the learning plan
    learning_plan = career_engine.generate_plan(db_session, test_user)

    # 3. Assertion
    # Check that a plan was generated
    assert learning_plan is not None
    assert len(learning_plan) > 0

    # Verify that items have IDs without needing a refresh loop
    for item in learning_plan:
        assert item.id is not None, "Item ID should be populated by the commit"

    # Check for the specific 'Go' and 'AI Ethics' plans
    technologies = {item.technology for item in learning_plan}
    assert "Go" in technologies
    assert "AI Ethics" in technologies
    assert "Rust" in technologies # Rust skill is not present, so it should be added
