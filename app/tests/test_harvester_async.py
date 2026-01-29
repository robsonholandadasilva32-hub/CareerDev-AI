import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.services.social_harvester import social_harvester

@pytest.mark.asyncio
async def test_harvest_linkedin_data_uses_to_thread():
    # Patch asyncio.to_thread
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        # Patch httpx
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {})

            # Setup mock return for _get_user_sync
            # First call to to_thread is _get_user_sync, returns True
            mock_to_thread.side_effect = [True, None]

            await social_harvester.harvest_linkedin_data(1, "token")

            # Verify to_thread called twice:
            # 1. _get_user_sync
            # 2. _save_linkedin_data_sync
            assert mock_to_thread.call_count == 2

            # Check arguments
            calls = mock_to_thread.call_args_list
            assert calls[0][0][0] == social_harvester._get_user_sync
            assert calls[1][0][0] == social_harvester._save_linkedin_data_sync

@pytest.mark.asyncio
async def test_harvest_github_data_uses_to_thread():
    # calls sync_profile
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        with patch.object(social_harvester, "_harvest_github_raw", new_callable=AsyncMock) as mock_harvest_raw:
            mock_harvest_raw.return_value = ({}, {}) # raw_langs, metrics

            # Setup mock returns
            # 1. _ensure_profile_exists_sync -> ("Senior Developer", None)
            # 2. _save_github_data_sync -> None
            mock_to_thread.side_effect = [("Senior Developer", None), None]

            await social_harvester.harvest_github_data(1, "token")

            assert mock_to_thread.call_count == 2
            calls = mock_to_thread.call_args_list
            assert calls[0][0][0] == social_harvester._ensure_profile_exists_sync
            assert calls[1][0][0] == social_harvester._save_github_data_sync
