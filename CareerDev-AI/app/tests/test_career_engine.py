import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
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
        full_name="Test User",
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
    # Generate the learning plan via analyze
    # emulate raw input based on user profile logic
    result = career_engine.analyze(
        db=db_session,
        raw_languages={"Python": 80000, "Go": 1000},
        linkedin_input={},
        metrics={"languages": {"Python": 80000, "Go": 1000}, "commits_last_30_days": 10},
        skill_audit={},
        user=test_user
    )
    weekly_plan = result.get("weekly_plan")

    # 3. Assertion
    # Check that a plan was generated
    assert weekly_plan is not None
    assert weekly_plan.get("mode") in ["GROWTH", "ACCELERATOR"]

    tasks = weekly_plan.get("tasks", [])
    assert len(tasks) > 0

    # Check content of tasks
    task_descriptions = [t["task"] for t in tasks]
    # Logic in _generate_weekly_routine: focus is Rust if Python > 100k and Rust < 5k.
    # Here Python is 80k, so focus should be Python.
    # Tasks: "Learn: Python fundamentals", "Build a CLI tool in Python"

    assert any("Python" in t for t in task_descriptions)
