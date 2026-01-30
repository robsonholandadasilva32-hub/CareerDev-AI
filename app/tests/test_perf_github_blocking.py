
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.jwt import create_access_token
from app.db.session import get_db
from app.routes.social import oauth

@pytest.fixture(scope="function")
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture(autouse=True)
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
def register_mock_oauth():
    """Register mock github client and cleanup after test."""
    added = False
    if 'github' not in oauth._registry:
        oauth.register(
            name='github',
            client_id='mock_gh_id',
            client_secret='mock_gh_secret',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )
        added = True
    yield
    if added and 'github' in oauth._registry:
        # OAuth registry is a dict or similar
        del oauth._registry['github']

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_github_callback_exception_blocking(client, mock_db_session, register_mock_oauth):
    """
    Demonstrates that the exception handler blocks the event loop
    by simulating a slow DB commit in log_audit.
    """
    # 1. Setup Mock User
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "perfuser@example.com"
    mock_user.is_active = True
    mock_user.is_banned = False

    # 2. Auth Setup
    token_data = {"sub": "1", "email": "perfuser@example.com"}
    access_token = create_access_token(token_data)
    client.cookies.set("access_token", access_token)

    # 3. Inject Blocking Behavior in db.commit
    def slow_commit():
        time.sleep(0.5) # BLOCKING SLEEP

    mock_db_session.commit.side_effect = slow_commit

    # Mock load user in middleware
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user

    # 4. Trigger Exception
    async def fast_background_task():
        delays = []
        for _ in range(5):
            start = time.perf_counter()
            await asyncio.sleep(0.1)
            end = time.perf_counter()
            delays.append(end - start)
        return delays

    with patch('app.routes.social.oauth.github.fetch_access_token', side_effect=Exception("Boom!")) as mock_fetch, \
         patch("app.middleware.auth.SessionLocal", return_value=mock_db_session):

        # Run concurrently
        task_req = asyncio.create_task(client.get("/auth/github/callback?code=gh_perf_code", follow_redirects=False))
        task_bg = asyncio.create_task(fast_background_task())

        response = await task_req
        delays = await task_bg

        max_delay = max(delays)
        print(f"DEBUG: Max loop delay: {max_delay:.4f}s")

        if max_delay > 0.4:
            print("PERF: DETECTED BLOCKING EVENT LOOP")
        else:
            print("PERF: NO BLOCKING DETECTED")

        # Expect redirect to login with error (accept 302, 303, 307)
        assert response.status_code in [302, 303, 307]
        assert "error=github_failed" in response.headers.get("location", "")
