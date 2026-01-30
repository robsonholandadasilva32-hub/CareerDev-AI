
import pytest
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.middleware.auth import AuthMiddleware
from app.core.jwt import create_access_token

# Define a simple app for testing the middleware
test_app = FastAPI()
test_app.add_middleware(AuthMiddleware)

@test_app.get("/test_auth")
def protected_route(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return {"user_id": user.id, "is_banned": user.is_banned}
    return {"user_id": None}

client = TestClient(test_app)

def test_auth_middleware_success():
    # Setup mocks
    mock_session_obj = MagicMock()
    mock_user_session = MagicMock()
    mock_user_session.is_active = True
    mock_user_session.last_active_at = datetime.utcnow()

    mock_user = MagicMock()
    mock_user.id = 123
    mock_user.is_banned = False

    # Mock DB Query results
    # First query is UserSession, Second is User
    # We can use side_effect or just configure the mock behavior specifically

    # We need to handle the chain: db.query(Model).filter(...).first()
    # It's easier if we mock the models or the query calls.

    with patch("app.middleware.auth.SessionLocal") as MockSessionLocal:
        session_instance = MockSessionLocal.return_value

        # When querying UserSession
        # db.query(UserSession) -> mock_query_session
        # .filter(...) -> mock_filter_session
        # .first() -> mock_user_session

        # When querying User
        # db.query(User) -> mock_query_user
        # ... -> mock_user

        # Implementation detail: The code calls db.query(UserSession) then db.query(User)
        # We can inspect the arguments to return different things

        def query_side_effect(model):
            query_mock = MagicMock()
            filter_mock = MagicMock()
            query_mock.filter.return_value = filter_mock

            if "UserSession" in str(model):
                filter_mock.first.return_value = mock_user_session
            elif "User" in str(model):
                filter_mock.first.return_value = mock_user
            return query_mock

        session_instance.query.side_effect = query_side_effect

        # Create token
        token = create_access_token({"sub": "123", "sid": "session_abc"})
        client.cookies.set("access_token", token)

        response = client.get("/test_auth")

        assert response.status_code == 200
        assert response.json() == {"user_id": 123, "is_banned": False}

        # Verify db was closed
        session_instance.close.assert_called_once()

def test_auth_middleware_banned_user():
    with patch("app.middleware.auth.SessionLocal") as MockSessionLocal:
        session_instance = MockSessionLocal.return_value

        mock_user_session = MagicMock()
        mock_user_session.is_active = True
        mock_user_session.last_active_at = datetime.utcnow()

        mock_user = MagicMock()
        mock_user.id = 456
        mock_user.is_banned = True # BANNED!

        def query_side_effect(model):
            query_mock = MagicMock()
            filter_mock = MagicMock()
            query_mock.filter.return_value = filter_mock

            if "UserSession" in str(model):
                filter_mock.first.return_value = mock_user_session
            elif "User" in str(model):
                filter_mock.first.return_value = mock_user
            return query_mock

        session_instance.query.side_effect = query_side_effect

        token = create_access_token({"sub": "456", "sid": "session_xyz"})
        client.cookies.set("access_token", token)

        # Should return 403 because user is banned
        # Code checks if accept application/json or path starts with /api
        # Our path is /test_auth, so it might return HTML if accept header not set?
        # The code:
        # if "application/json" in request.headers.get("accept", "") or request.url.path.startswith("/api"):
        #      return JSONResponse(status_code=403, content={"detail": "Access Revoked"})
        # return templates.TemplateResponse(...)

        response = client.get("/test_auth", headers={"Accept": "application/json"})

        assert response.status_code == 403
        assert response.json() == {"detail": "Access Revoked"}
