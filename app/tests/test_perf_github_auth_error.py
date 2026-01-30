
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.jwt import create_access_token
from app.db.session import get_db

@pytest.fixture(scope="function")
def mock_db_session():
    session = MagicMock()
    return session

@pytest.fixture(autouse=True)
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.mark.asyncio
async def test_github_callback_error_blocking(client, mock_db_session):
    """
    Verifies that error paths (e.g. no email) block the loop due to sync log_audit.
    """
    # 1. Setup Mock User (Session exists)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "perfuser@example.com"
    mock_user.is_active = True
    mock_user.is_banned = False

    # Mock DB Query for current user in onboarding check
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user

    # 2. Auth Setup
    token_data = {"sub": "1", "email": "perfuser@example.com"}
    access_token = create_access_token(token_data)
    client.cookies.set("access_token", access_token)

    # 3. Mock GitHub Response - NO EMAIL to trigger error path
    mock_token = {'access_token': 'fake_token', 'scope': 'user:email'}
    mock_user_info = {
        'id': 123,
        'email': None, # MISSING EMAIL
        'login': 'noemailuser'
    }

    # 4. Mock slow log_audit
    def slow_log_audit(*args, **kwargs):
        time.sleep(0.5) # BLOCKING SLEEP
        return None

    # 5. Background Task to measure blocking
    async def fast_background_task():
        delays = []
        for _ in range(5):
            start = time.perf_counter()
            await asyncio.sleep(0.1)
            end = time.perf_counter()
            delays.append(end - start)
        return delays

    # Mock OAuth
    from app.routes.social import oauth
    if 'github' not in oauth._registry:
         oauth.register(
            name='github',
            client_id='mock',
            client_secret='mock',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get, \
         patch("app.middleware.auth.SessionLocal", return_value=mock_db_session), \
         patch("app.routes.social.log_audit", side_effect=slow_log_audit) as mock_audit:

        mock_fetch.return_value = mock_token
        # First call gets user profile (no email)
        mock_resp_profile = MagicMock()
        mock_resp_profile.json.return_value = mock_user_info

        # Second call gets user emails (return empty list or None to fail)
        mock_resp_emails = MagicMock()
        mock_resp_emails.json.return_value = []

        mock_get.side_effect = [mock_resp_profile, mock_resp_emails]

        # Run concurrently
        task_req = asyncio.create_task(client.get("/auth/github/callback?code=123", follow_redirects=False))
        task_bg = asyncio.create_task(fast_background_task())

        response = await task_req
        delays = await task_bg

        max_delay = max(delays)
        print(f"DEBUG: Max loop delay: {max_delay:.4f}s")

        # We EXPECT NO blocking now.
        if max_delay > 0.4:
            pytest.fail(f"PERF: DETECTED BLOCKING EVENT LOOP (Max Delay: {max_delay:.4f}s)")
        else:
            print("PERF: NO BLOCKING DETECTED (SUCCESS)")

        # Verify that the request actually completed successfully (redirected)
        # Default RedirectResponse is 307
        assert response.status_code in [302, 303, 307], f"Unexpected status code: {response.status_code}"
        assert "error=github_no_email" in response.headers.get("location", ""), f"Unexpected location: {response.headers.get('location')}"
