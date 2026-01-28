import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.db.models.user import User
from app.db.models.career import CareerProfile
from app.db.models.gamification import UserBadge
from app.db.models.security import AuditLog, UserSession
from app.services.career_engine import career_engine

@pytest.mark.asyncio
async def test_analyze_profile_uses_social_harvester():
    # Setup
    user = User(id=1, email="test@test.com", github_token="fake_token")
    user.career_profile = CareerProfile(user_id=1)

    mock_db = MagicMock()

    # Mock social_harvester
    with patch("app.services.career_engine.social_harvester.sync_profile", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = True

        # Action
        result = await career_engine.analyze_profile(mock_db, user)

        # Assert
        mock_sync.assert_called_once()
        # db.commit should be called if sync succeeds (to update updated_at)
        mock_db.commit.assert_called()

@pytest.mark.asyncio
async def test_analyze_profile_fallback_if_no_token():
    # Setup
    user = User(id=1, email="test@test.com", github_token=None)
    user.career_profile = CareerProfile(user_id=1)
    mock_db = MagicMock()

    # Action
    result = await career_engine.analyze_profile(mock_db, user)

    # Assert
    # Should fallback to simulation
    assert user.career_profile.github_stats is not None
