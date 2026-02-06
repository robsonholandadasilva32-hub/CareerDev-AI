import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.analytics import RiskSnapshot
from app.services.career_engine import career_engine
from datetime import datetime, timedelta

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

def test_get_counterfactual_implementation(db_session):
    # 1. Setup
    # Create a user
    test_user = User(
        full_name="Counterfactual User",
        email="cf_user@example.com",
        hashed_password="testpassword",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Create a career profile with metrics
    # Case: Low commit velocity (< 15) to trigger counterfactual suggestion
    career_profile = CareerProfile(
        user_id=test_user.id,
        github_activity_metrics={
            "commits_last_30_days": 5,
            "languages": {"Python": 5000}
        },
        linkedin_alignment_data={"skills": {"Python": "Expert"}}
    )
    db_session.add(career_profile)

    # Add some risk snapshots to simulate history
    # Newest risk higher than oldest => negative slope (bad)
    snapshot_old = RiskSnapshot(
        user_id=test_user.id,
        risk_score=20,
        recorded_at=datetime.utcnow() - timedelta(days=10)
    )
    snapshot_new = RiskSnapshot(
        user_id=test_user.id,
        risk_score=30,
        recorded_at=datetime.utcnow()
    )
    db_session.add(snapshot_old)
    db_session.add(snapshot_new)
    db_session.commit()

    # 2. Action
    # Call the method under test
    result = career_engine.get_counterfactual(db_session, test_user)

    # 3. Assertion
    # Verify structure
    assert "current_risk" in result
    assert "projected_risk" in result
    assert "actions" in result
    assert "summary" in result

    # Verify logic
    # Commit velocity is 5 (< 15), so we expect a suggestion
    actions = result["actions"]
    assert any("Increase coding activity" in a for a in actions)

    # Check that projected risk is different (likely lower) than current risk
    # if actions are suggested and valid
    # Note: Logic in counterfactual_engine subtracts from current_risk based on actions.
    # Current risk comes from forecast_career_risk.
    # With low commits (5 < 10), forecast adds +30 risk.
    # So current risk should be high-ish.

    assert isinstance(result["current_risk"], (int, float))
    assert isinstance(result["projected_risk"], (int, float))

    # The projected risk should be less than current risk if we have improvement actions
    if len(actions) > 0:
        assert result["projected_risk"] < result["current_risk"]
