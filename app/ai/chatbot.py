from typing import Optional
import openai
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.ai.prompts import CAREER_ASSISTANT_SYSTEM_PROMPT
from app.db.models.user import User

class ChatbotService:
    def __init__(self, simulated: bool = True):
        self.simulated = simulated
        # Check if real API key exists
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.simulated = False # Auto-switch to real mode if key exists
        else:
            self.simulated = True

    def get_response(self, message: str, lang: str = "pt", user_id: int = None, db: Session = None) -> str:
        context_str = ""

        # 1. Fetch User Context if available
        if user_id and db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                profile = user.career_profile
                plans = user.learning_plans

                skills = profile.skills_snapshot if profile else {}
                active_plans = [p.title for p in plans if p.status != 'completed']

                context_str = f"""
                **User Context:**
                - Name: {user.name}
                - Current Skills: {json.dumps(skills)}
                - Active Learning Plan: {', '.join(active_plans)}
                - Focus: {profile.target_role if profile else 'Not set'}

                Use this context to give personalized advice. If they ask about their plan, refer to the active items.
                """

        if self.simulated:
            return self._simulated_response(message, lang, context_str)
        else:
            return self._llm_response(message, lang, context_str)

    def _simulated_response(self, message: str, lang: str, context: str) -> str:
        msg = message.lower()

        # Enhanced Mock Responses using Context
        if "meu plano" in msg or "my plan" in msg:
            if "Active Learning Plan" in context:
                 # Extract plan mock
                 return "Baseado no seu perfil, você deve focar em: " + context.split("Active Learning Plan:")[1].split("- Focus")[0].strip()
            return "Você ainda não tem um plano ativo. Acesse o dashboard para gerar um."

        if "rust" in msg:
            return "Rust é uma linguagem focada em segurança e performance. Ótima para sistemas embarcados e serviços críticos."
        elif "go" in msg or "golang" in msg:
            return "Go é excelente para microsserviços e aplicações em nuvem devido à sua concorrência leve."
        elif "carreira" in msg or "career" in msg:
            return "Para avançar sua carreira, o CareerDev AI sugere focar em T-Shaped skills e conectar seu GitHub para análise de lacunas."
        elif "login" in msg or "entrar" in msg:
            return "Você pode entrar usando E-mail/Senha, GitHub ou LinkedIn para uma experiência completa."

        # Default fallback
        if lang == "pt":
            return "Estou em modo simulado. Pergunte sobre 'Rust', 'Go', 'Carreira' ou 'Meu Plano'."
        return "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'My Plan'."

    def _llm_response(self, message: str, lang: str, context: str) -> str:
        try:
            # Determine language prompt suffix
            lang_instruction = f"Reply in {lang}."

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": CAREER_ASSISTANT_SYSTEM_PROMPT + "\n" + context},
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
