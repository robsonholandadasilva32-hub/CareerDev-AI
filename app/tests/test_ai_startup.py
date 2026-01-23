import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.chatbot import ChatbotService
from app.core.config import settings

@pytest.mark.asyncio
async def test_verify_connection_success():
    service = ChatbotService()
    service.simulated = False
    service.async_client = AsyncMock()
    service.async_client.models.list.return_value = {"data": []}

    # Should not raise
    await service.verify_connection()

@pytest.mark.asyncio
async def test_verify_connection_failure():
    service = ChatbotService()
    service.simulated = False
    service.async_client = AsyncMock()
    service.async_client.models.list.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="OpenAI Connection Failed: API Error"):
        await service.verify_connection()

@pytest.mark.asyncio
async def test_verify_connection_simulated():
    service = ChatbotService()
    service.simulated = True

    # Should not raise, just log warning
    await service.verify_connection()
