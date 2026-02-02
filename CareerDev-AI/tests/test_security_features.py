import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# 1. Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_security.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Patching BEFORE importing app might be tricky if imports happen at top level
# But we can patch where it is used.

# Import app
from app.main import app
from app.db.base import Base
from app.db.models.user import User
from app.core.security import create_access_token
from app.db.session import get_db

@pytest.fixture(scope="module")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Patch get_db
    app.dependency_overrides[get_db] = lambda: session

    # Patch SessionLocal in AuthMiddleware
    # AuthMiddleware imports SessionLocal from app.db.session
    # PROBLEM: AuthMiddleware closes the session. We must prevent that.

    # Create a proxy or mock that does nothing on close
    original_close = session.close
    session.close = lambda: None

    with patch("app.middleware.auth.SessionLocal", lambda: session):
         # Also need to patch it in app.routes.security or whereever else?
         # But usually dependency overrides handle routes.
         # AuthMiddleware uses it directly.
         yield session

    # Restore close and close it
    session.close = original_close
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db): # Depend on db to ensure patch is active
    # We need to recreate TestClient inside the patch context?
    # No, TestClient calls the app. The app uses the patched class/function.
    with TestClient(app) as c:
        yield c

def test_rate_limiting_social(client):
    # TestClient doesn't easily support mocking IP for slowapi without more work.
    # slowapi uses request.client.host.
    # TestClient sets client=("testclient", 50000).
    # So all requests come from "testclient".

    for _ in range(5):
        client.get("/login/github", follow_redirects=False)

    response = client.get("/login/github", follow_redirects=False)
    assert response.status_code == 429

def test_admin_ban_flow(client, db):
    # Create Admin
    admin = User(name="Admin", email="admin@example.com", hashed_password="x", is_admin=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Create Victim
    victim = User(name="Victim", email="victim@example.com", hashed_password="x")
    db.add(victim)
    db.commit()
    db.refresh(victim)

    # Login as Admin
    token = create_access_token({"sub": str(admin.id)})
    client.cookies.set("access_token", token)

    # Ban Victim
    response = client.post(f"/admin/users/{victim.id}/ban")
    assert response.status_code == 200
    assert response.json()["is_banned"] is True

    # Verify in DB
    db.expire(victim)
    db.refresh(victim)
    assert victim.is_banned is True

    # Unban
    response = client.post(f"/admin/users/{victim.id}/ban")
    assert response.status_code == 200
    assert response.json()["is_banned"] is False

def test_kill_switch(client, db):
    # Create Banned User
    banned = User(name="Banned", email="banned@example.com", hashed_password="x", is_banned=True)
    db.add(banned)
    db.commit()
    db.refresh(banned)

    # Generate Token
    token = create_access_token({"sub": str(banned.id)})

    # 1. HTML Access (follow_redirects=False to catch 403 vs 302)
    client.cookies.set("access_token", token)
    response = client.get("/dashboard", follow_redirects=False)

    # If not banned, it would be 200. If banned, 403.
    # If redirects to login, 302.
    assert response.status_code == 403
    assert "Access Suspended" in response.text

    # 2. JSON Access (simulate API)
    response = client.get("/dashboard", headers={"Accept": "application/json"}, follow_redirects=False)
    assert response.status_code == 403
    assert response.json() == {"detail": "Access Revoked"}

def test_watchdog_monitoring(client):
    # Trigger 401s
    # We use a POST request to an endpoint that requires auth (and doesn't have token).
    # But wait, without token, AuthMiddleware sets user=None.
    # Most endpoints redirect to login if user=None.
    # We need an endpoint that returns 401.
    # We can rely on the fact that TestClient can send invalid token?
    # If token is invalid, AuthMiddleware catches exception and user=None.

    # Is there any endpoint that raises HTTPException(401)?
    # app/routes/career.py: analyze_resume checks user. If not user -> JSON 401.

    # Let's verify `analyze_resume`.
    # It calls `get_current_user_from_request`.
    # If None -> JSONResponse({"error": "Unauthorized"}, status_code=401)

    for _ in range(12):
        response = client.post("/career/analyze-resume", data={"resume_text": "foo"})
        assert response.status_code == 401

    # Passing implies Watchdog didn't crash.
