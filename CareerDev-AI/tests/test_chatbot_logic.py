import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.chatbot import ChatbotService
from app.core.config import settings

# Helper to setup chatbot with specific model settings
@pytest.fixture
def mock_openai_client():
    with patch("app.ai.chatbot.openai.AsyncOpenAI") as mock_class:
        mock_instance = AsyncMock()
        # Mock the create method's return value structure
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mocked Response"))]
        mock_instance.chat.completions.create.return_value = mock_response

        mock_class.return_value = mock_instance
        yield mock_instance

@pytest.mark.asyncio
async def test_gpt_5_mini_excludes_temperature(mock_openai_client):
    """Test that gpt-5-mini excludes temperature"""
    with patch("app.ai.chatbot.settings.OPENAI_MODEL", "gpt-5-mini"), \
         patch("app.ai.chatbot.settings.OPENAI_API_KEY", "fake-key"):

        # Re-init service to pick up API key and disable simulation
        service = ChatbotService()
        # Ensure it's not simulated
        service.simulated = False
        service.async_client = mock_openai_client

        await service._llm_response("hello", "en", "context", "system prompt")

        # Verify call args
        args, kwargs = mock_openai_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-5-mini"
        assert "temperature" not in kwargs, "Temperature should be excluded for gpt-5-mini"

@pytest.mark.asyncio
async def test_o1_model_excludes_temperature(mock_openai_client):
    """Test that o1-* models exclude temperature"""
    with patch("app.ai.chatbot.settings.OPENAI_MODEL", "o1-preview"), \
         patch("app.ai.chatbot.settings.OPENAI_API_KEY", "fake-key"):

        service = ChatbotService()
        service.simulated = False
        service.async_client = mock_openai_client

        await service._llm_response("hello", "en", "context", "system prompt")

        args, kwargs = mock_openai_client.chat.completions.create.call_args
        assert kwargs["model"] == "o1-preview"
        assert "temperature" not in kwargs, "Temperature should be excluded for o1 models"

@pytest.mark.asyncio
async def test_standard_model_includes_temperature(mock_openai_client):
    """Test that standard models include temperature"""
    with patch("app.ai.chatbot.settings.OPENAI_MODEL", "gpt-4o"), \
         patch("app.ai.chatbot.settings.OPENAI_API_KEY", "fake-key"):

        service = ChatbotService()
        service.simulated = False
        service.async_client = mock_openai_client

        await service._llm_response("hello", "en", "context", "system prompt")

        args, kwargs = mock_openai_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o"
        assert "temperature" in kwargs
        assert kwargs["temperature"] == 0.7

@pytest.mark.asyncio
async def test_fallback_includes_temperature(mock_openai_client):
    """Test that fallback always includes temperature, even if primary failed"""
    # Make the first call raise an error
    import openai
    mock_openai_client.chat.completions.create.side_effect = [
        openai.BadRequestError("Error", response=MagicMock(), body=None), # First call fails
        MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback Response"))]) # Second call succeeds
    ]

    with patch("app.ai.chatbot.settings.OPENAI_MODEL", "gpt-5-mini"), \
         patch("app.ai.chatbot.settings.OPENAI_FALLBACK_MODEL", "gpt-4o-mini"), \
         patch("app.ai.chatbot.settings.OPENAI_API_KEY", "fake-key"):

        service = ChatbotService()
        service.simulated = False
        service.async_client = mock_openai_client

        response = await service._llm_response("hello", "en", "context", "system prompt")

        assert response == "Fallback Response"

        # Check calls. Expect 2 calls.
        assert mock_openai_client.chat.completions.create.call_count == 2

        # First call (Primary) - should NOT have temperature (gpt-5-mini)
        call1 = mock_openai_client.chat.completions.create.call_args_list[0]
        assert call1[1]["model"] == "gpt-5-mini"
        assert "temperature" not in call1[1]

        # Second call (Fallback) - SHOULD have temperature (gpt-4o-mini)
        call2 = mock_openai_client.chat.completions.create.call_args_list[1]
        assert call2[1]["model"] == "gpt-4o-mini"
        assert call2[1]["temperature"] == 0.7
