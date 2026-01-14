from typing import Optional
import openai
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.ai.prompts import CAREER_ASSISTANT_SYSTEM_PROMPT, get_interviewer_system_prompt
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

    def get_response(self, message: str, lang: str = "pt", user_id: int = None, db: Session = None, mode: str = "standard") -> str:
        """
        Mode can be 'standard' or 'interview'.
        """
        context_str = ""
        system_prompt = CAREER_ASSISTANT_SYSTEM_PROMPT

        # 1. Fetch User Context if available
        if user_id and db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                profile = user.career_profile
                plans = user.learning_plans

                # Context Build
                skills = profile.skills_snapshot if profile else {}
                target_role = profile.target_role if profile else 'Software Engineer'
                active_plans = [p.title for p in plans if p.status != 'completed']

                # Check Mode
                if mode == "interview":
                     system_prompt = get_interviewer_system_prompt(
                         {"target_role": target_role, "skills": skills},
                         user.name
                     )
                else:
                    context_str = f"""
                    **User Context:**
                    - Name: {user.name}
                    - Premium Status: {user.is_premium}
                    - 2FA Method: {user.two_factor_method} (Enabled: {user.two_factor_enabled})
                    - Current Skills: {json.dumps(skills)}
                    - Active Learning Plan: {', '.join(active_plans)}
                    - Focus: {target_role}

                    Use this context to give personalized advice. If Premium is False and they ask for advanced resume checks, suggest upgrading.
                    """

        if self.simulated:
            return self._simulated_response(message, lang, context_str, mode)
        else:
            return self._llm_response(message, lang, context_str, system_prompt)

    def _simulated_response(self, message: str, lang: str, context: str, mode: str) -> str:
        msg = message.lower()

        if mode == "interview":
             if "start" in msg or "iniciar" in msg:
                 return "Vamos começar. Explique a diferença entre TCP e UDP."
             return "Boa resposta (Simulada). Próxima: O que é Dependency Injection?"

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
            return "Estou em modo simulado. Pergunte sobre 'Rust', 'Go', 'Carreira' ou 'Meu Plano'. Tente o modo Entrevista!"
        return "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'My Plan'. Try Interview Mode!"

    def _llm_response(self, message: str, lang: str, context: str, system_prompt: str) -> str:
        try:
            # Determine language prompt suffix
            lang_instruction = f"Reply in {lang}."

            response = openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt + "\n" + context},
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
