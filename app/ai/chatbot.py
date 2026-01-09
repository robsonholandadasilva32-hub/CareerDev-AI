from typing import Optional

class ChatbotService:
    def __init__(self, simulated: bool = True, api_key: Optional[str] = None):
        self.simulated = simulated
        self.api_key = api_key

    def get_response(self, message: str, lang: str = "pt") -> str:
        if self.simulated:
            return self._simulated_response(message, lang)
        else:
            return self._llm_response(message, lang)

    def _simulated_response(self, message: str, lang: str) -> str:
        # Simple keywords detection for prototype
        msg = message.lower()

        if "rust" in msg:
            return "Rust é uma linguagem focada em segurança e performance. Ótima para sistemas embarcados e serviços críticos."
        elif "go" in msg or "golang" in msg:
            return "Go é excelente para microsserviços e aplicações em nuvem devido à sua concorrência leve."
        elif "carreira" in msg:
            return "Para avançar sua carreira, foque em T-Shaped skills: especialize-se em uma área (ex: Backend) mas conheça o todo."

        if lang == "pt":
            return "Interessante pergunta. Como uma IA em desenvolvimento, sugiro focar em fundamentos sólidos."
        return "Interesting question. As an AI in development, I suggest focusing on solid fundamentals."

    def _llm_response(self, message: str, lang: str) -> str:
        # TODO: Implement OpenAI/Gemini integration here
        # import openai
        # openai.api_key = self.api_key
        # ...
        return "LLM Integration Pending API Key"

# Global Instance (Singleton-ish)
chatbot_service = ChatbotService(simulated=True)

def simple_ai_response(message: str) -> str:
    return chatbot_service.get_response(message)
