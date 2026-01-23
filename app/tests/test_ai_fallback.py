import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import openai
from app.ai.chatbot import ChatbotService
from app.core.config import settings

@pytest.mark.asyncio
async def test_ai_fallback_logic():
    # Patch settings to ensure we are not in simulated mode
    with patch("app.core.config.settings.OPENAI_API_KEY", "test-key"):
        # Initialize service
        service = ChatbotService()
        # Ensure simulated is False
        service.simulated = False

        # Mock the async client
        mock_client = AsyncMock()
        service.async_client = mock_client

        # Setup the mock response for success
        mock_success_response = MagicMock()
        mock_success_response.choices = [MagicMock(message=MagicMock(content="Fallback Success"))]

        # Configure side effects: First call raises NotFoundError, second succeeds
        # We need to construct a proper NotFoundError.
        # openai.NotFoundError requires response, body, message.

        mock_http_response = MagicMock()
        mock_http_response.status_code = 404

        error = openai.NotFoundError(
            message="Model not found",
            response=mock_http_response,
            body=None
        )

        mock_client.chat.completions.create.side_effect = [
            error,
            mock_success_response
        ]

        # Execute
        response = await service._llm_response(
            message="Test Message",
            lang="en",
            context="",
            system_prompt="System Prompt"
        )

        # Verify response
        assert response == "Fallback Success"

        # Verify calls
        assert mock_client.chat.completions.create.call_count == 2

        # Check first call used primary model
        first_call = mock_client.chat.completions.create.call_args_list[0]
        assert first_call.kwargs['model'] == settings.OPENAI_MODEL

        # Check second call used fallback model
        second_call = mock_client.chat.completions.create.call_args_list[1]
        assert second_call.kwargs['model'] == settings.OPENAI_FALLBACK_MODEL
