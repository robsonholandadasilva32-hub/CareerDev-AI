import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.db.models.user import User
from app.core.security import create_access_token

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def free_user(db):
    email = f"free_{uuid.uuid4()}@example.com"
    user = User(
        email=email,
        name="Free User",
        hashed_password="hash",
        is_premium=False,
        is_profile_completed=True,
        terms_accepted=True,
        linkedin_id=f"li_free_{uuid.uuid4()}",
        github_id=f"gh_free_{uuid.uuid4()}"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def premium_user(db):
    email = f"premium_{uuid.uuid4()}@example.com"
    user = User(
        email=email,
        name="Premium User",
        hashed_password="hash",
        is_premium=True,
        is_profile_completed=True,
        terms_accepted=True,
        linkedin_id=f"li_premium_{uuid.uuid4()}",
        github_id=f"gh_premium_{uuid.uuid4()}"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_auth_headers(user):
    token = create_access_token(data={"sub": str(user.id)})
    return {"Cookie": f"access_token={token}"}

@pytest.mark.asyncio
async def test_analytics_gating_free_user(client, free_user):
    headers = get_auth_headers(free_user)
    # follow_redirects=False to verify the 303 redirect
    response = await client.get("/career/analytics", headers=headers, follow_redirects=False)

    # Expect redirect to upgrade page with error param
    assert response.status_code == 303
    assert response.headers["location"] == "/subscription/upgrade?error=premium_required"

@pytest.mark.asyncio
async def test_analytics_access_premium_user(client, premium_user):
    headers = get_auth_headers(premium_user)
    response = await client.get("/career/analytics", headers=headers)

    assert response.status_code == 200
    assert "Advanced Analytics" in response.text
    # Verify content loaded
    assert "Market Fit (Você vs Mercado)" in response.text

@pytest.mark.asyncio
async def test_dashboard_upgrade_link(client, free_user):
    headers = get_auth_headers(free_user)
    response = await client.get("/dashboard", headers=headers)

    assert response.status_code == 200
    # Check for the link
    assert '/subscription/upgrade' in response.text
    # Check for Assinar Premium text associated with the link
    assert 'Assinar Premium' in response.text

@pytest.mark.asyncio
async def test_dashboard_premium_content(client, premium_user):
    headers = get_auth_headers(premium_user)
    response = await client.get("/dashboard", headers=headers)

    assert response.status_code == 200
    # Check for VIP Support
    assert 'VIP' in response.text
    assert '∞ Ilimitado' in response.text
    # Assinar Premium should NOT be there
    assert 'Assinar Premium' not in response.text

@pytest.mark.asyncio
async def test_upgrade_page_content(client):
    response = await client.get("/subscription/upgrade")
    assert response.status_code == 200
    assert "Desbloqueie Seu Potencial Máximo" in response.text
    assert "Advanced Analytics Dashboard" in response.text
    assert "Proceed to Checkout" in response.text
    assert 'href="/billing/checkout"' in response.text
