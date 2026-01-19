import pytest
from fastapi import Request
from httpx import AsyncClient, ASGITransport
from app.main import app

# Add a temporary route for testing scheme
# This route is added dynamically to the app instance for testing purposes
@app.get("/debug_scheme_check")
async def debug_scheme_check(request: Request):
    return {"scheme": request.url.scheme}

@pytest.mark.asyncio
async def test_proxy_headers_behavior():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Simulate request coming from a proxy with HTTPS
        headers = {"X-Forwarded-Proto": "https"}
        response = await client.get("/debug_scheme_check", headers=headers)

        assert response.status_code == 200
        # Expect 'http' initially because middleware is not added yet
        assert response.json()["scheme"] == "https"
