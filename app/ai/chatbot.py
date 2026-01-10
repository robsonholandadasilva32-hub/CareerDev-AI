from typing import Optional
import openai
from app.core.config import settings

class ChatbotService:
    def __init__(self, simulated: bool = True):
        self.simulated = simulated
        # Check if real API key exists
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.simulated = False # Auto-switch to real mode if key exists
        else:
            self.simulated = True

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
            return "Estou operando em modo simulado (sem chave OpenAI). Pergunte sobre Rust ou Go."
        return "Operating in simulated mode (no OpenAI key). Ask about Rust or Go."

    def _llm_response(self, message: str, lang: str) -> str:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a helpful career assistant for developers. Language: {lang}. Be concise and futuristic."},
                    {"role": "user", "content": message}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Erro ao comunicar com a IA (Verifique a API Key)."

# Global Instance (Singleton-ish)
chatbot_service = ChatbotService()

def simple_ai_response(message: str) -> str:
    return chatbot_service.get_response(message)
