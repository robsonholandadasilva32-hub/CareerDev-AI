from fastapi.testclient import TestClient
from app.main import app
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.routes.dashboard import get_current_user_secure
from app.db.session import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import pytest
from sqlalchemy.pool import StaticPool

# Setup In-Memory DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_passport_pdf_generation():
    # Create User
    db = TestingSessionLocal()
    # Check if user exists or recreate logic? In-memory DB is persistent across this module execution?
    # Yes, engine is global.

    user = User(name="Passport User", email="passport@example.com", hashed_password="pw")
    profile = CareerProfile(
        market_relevance_score=90,
        skills_graph_data={"labels": ["Rust"], "datasets": [{"data": [100]}]},
        pending_micro_projects=[{"title": "Test Task", "status": "pending"}]
    )
    user.career_profile = profile
    db.add(user)
    db.commit()
    db.refresh(user)

    # Override Auth
    app.dependency_overrides[get_current_user_secure] = lambda: user

    response = client.get("/api/export/passport")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

    db.close()
    # Clean override
    del app.dependency_overrides[get_current_user_secure]

def test_public_badge():
    # Create User
    db = TestingSessionLocal()
    user = User(name="Badge User", email="badge@example.com", hashed_password="pw")
    profile = CareerProfile(market_relevance_score=45) # Red Badge
    user.career_profile = profile
    db.add(user)
    db.commit()
    user_id = user.id

    response = client.get(f"/api/badge/{user_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "45/100" in response.text
    # Red color check for < 50
    assert "#ff0055" in response.text

    db.close()

def test_public_badge_not_found():
    response = client.get("/api/badge/999999")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "N/A" in response.text
