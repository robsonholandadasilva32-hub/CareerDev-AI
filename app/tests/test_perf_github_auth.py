
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.jwt import create_access_token

# We don't need real DB or Models if we mock the Session
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
async def test_github_callback_blocking_behavior(client, mock_db_session):
    """
    Demonstrates that the current implementation blocks the event loop
    by simulating a slow DB operation.
    """
    # 1. Setup Mock User
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "perfuser@example.com"
    mock_user.linkedin_id = "linkedin-perf-123"
    mock_user.github_id = None
    mock_user.is_profile_completed = False
    mock_user.terms_accepted = False
    mock_user.is_active = True # FIX: Ensure middleware allows access
    mock_user.is_banned = False # FIX: AuthMiddleware checks this property (even if not in model?)

    # Mock DB Query returning this user
    # current_user = db.query(User).filter(...).first()
    # We mock the chain: db.query().filter().first()
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user

    # Also Mock get_user_by_github_id used in conflict check
    # But wait, we want to simulate blocking there or somewhere else.

    # 2. Auth Setup (Cookie)
    # The middleware needs to decode the token.
    token_data = {"sub": "1", "email": "perfuser@example.com"}
    access_token = create_access_token(token_data)
    client.cookies.set("access_token", access_token)

    # 3. Mock GitHub Response
    mock_token = {'access_token': 'fake_gh_token_perf', 'token_type': 'bearer', 'scope': 'user:email'}
    mock_user_info = {
        'id': 77777,
        'login': 'perfgh',
        'email': 'perfuser@example.com',
        'name': 'Perf GitHub User',
        'avatar_url': 'http://avatar.url/gh_perf.jpg'
    }

    # 4. Inject Blocking Behavior
    # We will patch `get_user_by_github_id` to sleep.
    # The route calls: existing_user = get_user_by_github_id(db, github_id)

    def slow_check(*args, **kwargs):
        time.sleep(0.5) # BLOCKING SLEEP
        return None

    # 5. Background Task
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
            client_id='mock_gh_id',
            client_secret='mock_gh_secret',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    # We also need to mock User loading in AuthMiddleware,
    # otherwise it tries to query DB with the real session logic which we mocked but
    # the middleware might use a new session or depends on get_db.
    # AuthMiddleware uses `get_db`? No, it usually instantiates SessionLocal.

    # Let's patch SessionLocal in middleware to return our mock session.

    with patch('app.routes.social.oauth.github.fetch_access_token', new_callable=AsyncMock) as mock_fetch, \
         patch('app.routes.social.oauth.github.get', new_callable=AsyncMock) as mock_get, \
         patch("app.middleware.auth.SessionLocal", return_value=mock_db_session), \
         patch("app.routes.social.get_user_by_github_id", side_effect=slow_check) as mock_slow:

        mock_fetch.return_value = mock_token
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_user_info
        mock_get.return_value = mock_resp

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

        # Basic assertion to ensure route finished successfully (redirect)
        assert response.status_code == 303 or response.status_code == 302
