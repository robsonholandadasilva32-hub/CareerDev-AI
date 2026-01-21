from typing import Optional, Tuple
import openai
import json
import asyncio
from sqlalchemy.orm import Session
from app.core.config import settings
from app.ai.prompts import CAREER_ASSISTANT_SYSTEM_PROMPT, get_interviewer_system_prompt
from app.db.models.user import User

def _fetch_user_and_build_context(user_id: int, db: Session, mode: str) -> Tuple[str, str]:
    """
    Synchronously fetches user data and builds context to be run in a thread.
    Returns a tuple of (context_string, system_prompt).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "", CAREER_ASSISTANT_SYSTEM_PROMPT

    profile = user.career_profile
    plans = user.learning_plans
    skills = profile.skills_snapshot if profile else {}
    target_role = profile.target_role if profile else 'Software Engineer'
    active_plans = [p.title for p in plans if p.status != 'completed']

    if mode == "interview":
        system_prompt = get_interviewer_system_prompt(
            {"target_role": target_role, "skills": skills},
            user.name
        )
        context_str = ""
    else:
        system_prompt = CAREER_ASSISTANT_SYSTEM_PROMPT
        context_str = f"""
        **User Context:**
        - Name: {user.name}
        - Premium Status: {user.is_premium}
        - Current Skills: {json.dumps(skills)}
        - Active Learning Plan: {', '.join(active_plans)}
        - Focus: {target_role}

        Use this context to give personalized advice. If Premium is False and they ask for advanced resume checks, suggest upgrading.
        """
    return context_str, system_prompt

class ChatbotService:
    def __init__(self, simulated: bool = True):
        if settings.OPENAI_API_KEY:
            self.async_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.simulated = False
        else:
            self.async_client = None
            self.simulated = True

    async def get_response(self, message: str, lang: str = "pt", user_id: int = None, db: Session = None, mode: str = "standard") -> str:
        """
        Mode can be 'standard' or 'interview'.
        """
        context_str = ""
        system_prompt = CAREER_ASSISTANT_SYSTEM_PROMPT

        if user_id and db:
            context_str, system_prompt = await asyncio.to_thread(
                _fetch_user_and_build_context, user_id, db, mode
            )

        if self.simulated:
            return self._simulated_response(message, lang, context_str, mode)
        else:
            return await self._llm_response(message, lang, context_str, system_prompt)

    def _simulated_response(self, message: str, lang: str, context: str, mode: str) -> str:
        msg = message.lower()

        if mode == "interview":
             if "start" in msg or "iniciar" in msg:
                 return "Vamos começar. Explique a diferença entre TCP e UDP."
             return "Boa resposta (Simulada). Próxima: O que é Dependency Injection?"

        if "meu plano" in msg or "my plan" in msg:
            if "Active Learning Plan" in context:
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

        if lang == "pt":
            return "Estou em modo simulado. Pergunte sobre 'Rust', 'Go', 'Carreira' ou 'Meu Plano'. Tente o modo Entrevista!"
        return "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'My Plan'. Try Interview Mode!"

    async def _llm_response(self, message: str, lang: str, context: str, system_prompt: str) -> str:
        try:
            lang_instruction = f"Reply in {lang}."

            response = await self.async_client.chat.completions.create(
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
