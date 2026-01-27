import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.chatbot import ChatbotService
from app.ai.prompts import CAREER_ASSISTANT_SYSTEM_PROMPT, get_interviewer_system_prompt

# Helper to setup chatbot with specific model settings
@pytest.fixture
def mock_openai_client():
    with patch("app.ai.chatbot.openai.AsyncOpenAI") as mock_class:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mocked Response"))]
        mock_instance.chat.completions.create.return_value = mock_response

        mock_class.return_value = mock_instance
        yield mock_instance

def test_career_assistant_system_prompt_prime_directive():
    """Verify that CAREER_ASSISTANT_SYSTEM_PROMPT contains the Prime Directive."""
    assert "*** PRIME DIRECTIVE: STRICT ENGLISH ONLY ***" in CAREER_ASSISTANT_SYSTEM_PROMPT
    assert "You MUST communicate EXCLUSIVELY in English." in CAREER_ASSISTANT_SYSTEM_PROMPT
    assert "LANGUAGE BARRIER PROTOCOL:" in CAREER_ASSISTANT_SYSTEM_PROMPT

def test_interviewer_system_prompt_english_only():
    """Verify that get_interviewer_system_prompt enforces English-only communication."""
    prompt = get_interviewer_system_prompt({"target_role": "Dev", "skills": {}}, "Test User")
    assert "In a real scenario, we need to stick to English." in prompt

def test_simulated_response_english_only():
    """Verify that simulated responses are always in English regardless of input language."""
    service = ChatbotService()
    service.simulated = True

    # Test with Portuguese input and language
    response_pt = service._simulated_response("Como eu aprendo Rust?", "pt-BR", "", "standard")
    assert "Rust is a language focused on safety and performance" in response_pt
    assert "Rust é uma linguagem" not in response_pt

    # Test with Spanish input and language
    response_es = service._simulated_response("Como aprendo Rust?", "es", "", "standard")
    assert "Rust is a language focused on safety and performance" in response_es
    assert "Rust es un lenguaje" not in response_es

    # Test "start" command in interview mode (simulated)
    response_interview = service._simulated_response("Start", "pt-BR", "", "interview")
    assert "Let's start. Explain the difference between TCP and UDP." in response_interview
    assert "Vamos começar" not in response_interview

@pytest.mark.asyncio
async def test_llm_response_no_language_injection(mock_openai_client):
    """Verify that _llm_response does NOT inject 'Reply in [Language]' instruction."""
    with patch("app.ai.chatbot.settings.OPENAI_MODEL", "gpt-4o"), \
         patch("app.ai.chatbot.settings.OPENAI_API_KEY", "fake-key"):

        service = ChatbotService()
        service.simulated = False
        service.async_client = mock_openai_client

        await service._llm_response("hello", "pt-BR", "context", "system prompt")

        # Verify call args
        args, kwargs = mock_openai_client.chat.completions.create.call_args
        messages = kwargs["messages"]

        # Check that no message instructs to reply in Portuguese
        for msg in messages:
            if msg["role"] == "system":
                assert "Responda em Português do Brasil." not in msg["content"]
                assert "Reply in pt-BR." not in msg["content"]
