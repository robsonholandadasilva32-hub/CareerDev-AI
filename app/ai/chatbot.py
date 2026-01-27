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

    async def get_response(self, message: str, lang: str = "en", user_id: int = None, db: Session = None, mode: str = "standard") -> str:
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
             if "start" in msg:
                 return "Let's start. Explain the difference between TCP and UDP."
             return "Good answer (Simulated). Next: What is Dependency Injection?"

        if "my plan" in msg or "meu plano" in msg:
            if "Active Learning Plan" in context:
                 plan_name = context.split("Active Learning Plan:")[1].split("- Focus")[0].strip()
                 return "Based on your profile, you should focus on: " + plan_name
            return "You don't have an active plan yet. Go to the dashboard to generate one."

        if "rust" in msg:
            return "Rust is a language focused on safety and performance. Great for embedded systems and critical services."
        elif "go" in msg or "golang" in msg:
            return "Go is excellent for microservices and cloud applications due to its lightweight concurrency."
        elif "career" in msg or "carreira" in msg:
            return "To advance your career, CareerDev AI suggests focusing on T-Shaped skills and connecting your GitHub for gap analysis."
        elif "login" in msg or "entrar" in msg:
            return "You can login using Email/Password, GitHub or LinkedIn for a complete experience."

        return "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'My Plan'. Try Interview Mode!"

    async def verify_connection(self):
        """
        Forces a test call to OpenAI to verify the API Key.
        Raises an exception if verification fails.
        """
        if self.simulated:
             print("WARNING: Chatbot is in simulated mode (No API Key).")
             return

        try:
            # Simple list models call to verify auth
            await self.async_client.models.list()
            print("SUCCESS: OpenAI Connection Verified.")
        except Exception as e:
            # Re-raise to let caller handle critical alert
            raise Exception(f"OpenAI Connection Failed: {e}")

    async def _llm_response(self, message: str, lang: str, context: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt + "\n" + context},
            {"role": "user", "content": message}
        ]

        # Determine params based on model name
        primary_model = settings.OPENAI_MODEL
        params = {
            "model": primary_model,
            "messages": messages
        }

        # O1 models and gpt-5-mini do not support temperature
        if not (primary_model.startswith("o1-") or primary_model == "gpt-5-mini"):
            params["temperature"] = 0.7

        try:
            response = await self.async_client.chat.completions.create(**params)
            return response.choices[0].message.content
        except (openai.NotFoundError, openai.BadRequestError) as e:
            print(f"WARNING: Primary model {settings.OPENAI_MODEL} failed (Error: {e}). Switching to fallback: {settings.OPENAI_FALLBACK_MODEL}.")
            try:
                response = await self.async_client.chat.completions.create(
                    model=settings.OPENAI_FALLBACK_MODEL,
                    messages=messages,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e_fallback:
                print(f"CRITICAL: Fallback model {settings.OPENAI_FALLBACK_MODEL} also failed: {e_fallback}")
                return "Error communicating with AI (Fallback failed)."
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Error communicating with AI (Check API Key)."

# Global Instance
chatbot_service = ChatbotService()
