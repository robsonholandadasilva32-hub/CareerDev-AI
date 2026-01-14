from typing import Optional
import openai
from app.core.config import settings
from app.ai.prompts import CAREER_ASSISTANT_SYSTEM_PROMPT

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
        msg = message.lower()

        # Contextual Simulated Responses
        if "rust" in msg:
            return "Rust é uma linguagem focada em segurança e performance. Ótima para sistemas embarcados e serviços críticos."
        elif "go" in msg or "golang" in msg:
            return "Go é excelente para microsserviços e aplicações em nuvem devido à sua concorrência leve."
        elif "carreira" in msg or "career" in msg:
            return "Para avançar sua carreira, o CareerDev AI sugere focar em T-Shaped skills e conectar seu GitHub para análise de lacunas."
        elif "login" in msg or "entrar" in msg:
            return "Você pode entrar usando E-mail/Senha, GitHub ou LinkedIn para uma experiência completa."
        elif "segurança" in msg or "security" in msg:
            return "Nossa segurança inclui criptografia de ponta, sessões seguras e autenticação em dois fatores (2FA)."
        elif "objetivo" in msg or "goal" in msg:
            return "Nosso objetivo é automatizar seu upskilling com IA, identificando o que o mercado pede e o que você precisa aprender."

        # Default fallback
        if lang == "pt":
            return "Estou em modo simulado. Pergunte sobre 'Rust', 'Go', 'Carreira' ou 'Login'."
        return "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'Login'."

    def _llm_response(self, message: str, lang: str) -> str:
        try:
            # Determine language prompt suffix
            lang_instruction = f"Reply in {lang}."

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": CAREER_ASSISTANT_SYSTEM_PROMPT},
                    {"role": "system", "content": lang_instruction},
                    {"role": "user", "content": message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Erro ao comunicar com a IA (Verifique a API Key)."

# Global Instance
chatbot_service = ChatbotService()

def simple_ai_response(message: str) -> str:
    # In a real app, we would detect language from the request context
    # For now, we default to PT or try to infer from the message content in a robust implementation
    return chatbot_service.get_response(message)
