import pytest
from unittest.mock import MagicMock, patch
import asyncio
from app.services.career_engine import career_engine

@pytest.mark.asyncio
async def test_get_weekly_history_async_offloading():
    # Setup mocks
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 123

    expected_result = [{"week": 1, "focus": "Python"}]

    # We want to verify that _get_weekly_history_sync is called
    # and that it is called via asyncio.to_thread

    with patch.object(career_engine, '_get_weekly_history_sync', return_value=expected_result) as mock_sync:
        with patch('asyncio.to_thread', side_effect=asyncio.to_thread) as mock_to_thread:
            # Call the async method
            result = await career_engine.get_weekly_history(mock_db, mock_user)

            # Verify result
            assert result == expected_result

            # Verify to_thread was called with the sync method
            mock_to_thread.assert_called_once()
            args, _ = mock_to_thread.call_args
            assert args[0] == mock_sync
            assert args[1] == mock_db
            assert args[2] == mock_user.id

            # Verify sync method was called (implicitly by the real to_thread side_effect)
            mock_sync.assert_called_once_with(mock_db, mock_user.id)
