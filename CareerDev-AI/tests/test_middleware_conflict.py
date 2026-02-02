import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_nextjs_routes_blocked():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test a standard Next.js static asset path
        response = await client.get("/_next/static/chunks/main-c916298e3b3c66a2.js")
        assert response.status_code == 404
        assert response.json() == {"detail": "Static Asset Not Found"}

        # Test another Next.js path
        response = await client.get("/_next/image?url=%2Flogo.png&w=640&q=75")
        assert response.status_code == 404
        assert response.json() == {"detail": "Static Asset Not Found"}

@pytest.mark.asyncio
async def test_git_routes_blocked():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test .git config
        response = await client.get("/.git/config")
        assert response.status_code == 404
        assert response.json() == {"detail": "Static Asset Not Found"}

        # Test .git HEAD
        response = await client.get("/.git/HEAD")
        assert response.status_code == 404
        assert response.json() == {"detail": "Static Asset Not Found"}

@pytest.mark.asyncio
async def test_normal_routes_allowed():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test health check (should be 200 OK)
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Test a non-existent route not starting with blocked prefixes (should be standard 404 HTML)
        # Note: The custom 404 handler returns HTML, so we check content type or text
        response = await client.get("/some/random/path")
        assert response.status_code == 404
        assert "Static Asset Not Found" not in response.text
        assert "text/html" in response.headers["content-type"]
