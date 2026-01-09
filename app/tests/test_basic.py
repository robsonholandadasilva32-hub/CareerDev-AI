import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.db.models.user import User

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.mark.asyncio
async def test_homepage(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "CareerDev AI" in response.text

@pytest.mark.asyncio
async def test_login_page(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "CareerDev AI" in response.text

@pytest.mark.asyncio
async def test_dashboard_redirect_without_auth(client):
    response = await client.get("/dashboard")
    # Should redirect to login
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/login"
