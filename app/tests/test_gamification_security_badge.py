import pytest
import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.models.user import User
from app.db.models.gamification import Badge, UserBadge
from app.db.models.career import CareerProfile, LearningPlan
from app.db.models.security import AuditLog, UserSession
from app.services.gamification import check_and_award_security_badge, init_badges
from app.db.declarative import Base

# Ensure tables exist (important for in-memory DBs)
# Importing models above ensures they are registered in Base
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db():
    session = SessionLocal()
    init_badges(session) # Ensure badges exist
    yield session
    session.close()

def create_test_user(db, github_id=None, linkedin_id=None):
    unique_email = f"test_{uuid.uuid4()}@example.com"
    user = User(
        name="Test User",
        email=unique_email,
        hashed_password="hash",
        github_id=github_id,
        linkedin_id=linkedin_id,
        email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def has_badge(db, user_id, badge_slug):
    badge = db.query(Badge).filter(Badge.slug == badge_slug).first()
    if not badge:
        return False
    user_badge = db.query(UserBadge).filter(
        UserBadge.user_id == user_id,
        UserBadge.badge_id == badge.id
    ).first()
    return user_badge is not None

def test_security_badge_requirements(db):
    # 1. User with neither
    user1 = create_test_user(db)
    awarded = check_and_award_security_badge(db, user1)
    assert not awarded
    assert not has_badge(db, user1.id, "guardian")

    # 2. User with only GitHub
    user2 = create_test_user(db, github_id=f"gh_{uuid.uuid4()}")
    awarded = check_and_award_security_badge(db, user2)
    assert not awarded
    assert not has_badge(db, user2.id, "guardian")

    # 3. User with only LinkedIn
    user3 = create_test_user(db, linkedin_id=f"li_{uuid.uuid4()}")
    awarded = check_and_award_security_badge(db, user3)
    assert not awarded
    assert not has_badge(db, user3.id, "guardian")

    # 4. User with BOTH
    user4 = create_test_user(db, github_id=f"gh_{uuid.uuid4()}", linkedin_id=f"li_{uuid.uuid4()}")
    awarded = check_and_award_security_badge(db, user4)
    assert awarded
    assert has_badge(db, user4.id, "guardian")

    # 5. Idempotency (Check again)
    awarded_again = check_and_award_security_badge(db, user4)
    assert not awarded_again # Should return False as already has badge
    assert has_badge(db, user4.id, "guardian")
