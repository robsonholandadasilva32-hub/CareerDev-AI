import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app

# Mock dependencies to avoid DB connection issues during import if not already handled
# However, app.main imports app.db.session which creates engine.
# We assume environment is set up or we mock before import (too late now).
# We will rely on the fact that existing tests run.

@pytest.mark.asyncio
async def test_analyze_posture_poor_posture():
    # Mock Auth Dependency
    async def mock_check_auth():
        user = MagicMock()
        user.id = 123
        return user

    # Override the dependency
    # Note: We need to import the function to override it in the app's routing table if it was used as Depends
    # But usually app.dependency_overrides works with the function object.
    from app.routes.monitoring import check_auth
    app.dependency_overrides[check_auth] = mock_check_auth

    # Mock OpenAI Client
    with patch("app.routes.monitoring.client") as mock_client:
        # If client is None (no API key in env), we mock the module variable
        if mock_client is None:
             # If it was None, patch might not work as expected if it was imported as None.
             # But patch target is string "app.routes.monitoring.client".
             pass

        # Setup the mock return value
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="YES"))
        ]

        # Ensure create is async
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Mock Sentry
        with patch("app.routes.monitoring.sentry_sdk") as mock_sentry:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/monitoring/analyze-posture",
                    json={"image": "dGVzdF9pbWFnZQ=="} # dummy base64
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "poor_posture"
            assert "Time to straighten up" in data["message"]

            # Verify Sentry was called
            mock_sentry.capture_message.assert_called_with("Poor Posture Detected for User 123", level="warning")

    # Clean up
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_analyze_posture_good_posture():
    async def mock_check_auth():
        user = MagicMock()
        user.id = 123
        return user

    from app.routes.monitoring import check_auth
    app.dependency_overrides[check_auth] = mock_check_auth

    with patch("app.routes.monitoring.client") as mock_client:
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="NO"))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.routes.monitoring.sentry_sdk") as mock_sentry:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/monitoring/analyze-posture",
                    json={"image": "dGVzdF9pbWFnZQ=="}
                )

            assert response.status_code == 200
            assert response.json()["status"] == "good_posture"
            mock_sentry.capture_message.assert_not_called()

    app.dependency_overrides = {}
