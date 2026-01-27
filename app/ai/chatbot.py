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

    # Safe attribute access within the synchronous thread to prevent DetachedInstanceError
    profile = user.career_profile
    plans = user.learning_plans or []  # SAFEGUARD: Ensure it's a list even if None

    skills = profile.skills_snapshot if profile else {}
    target_role = profile.target_role if profile else 'Software Engineer'
    
    # List active plans for context
    active_plans = [p.title for p in plans if p.status != 'completed']

    # --- Mode Selection ---
    if mode == "interview":
        # Generates the dynamic Interviewer Persona
        system_prompt = get_interviewer_system_prompt(
            {"target_role": target_role, "skills": skills},
            user.name
        )
        context_str = f"Candidate Name: {user.name}\nTarget Role: {target_role}"
    else:
        # Standard Career OS Persona
        system_prompt = CAREER_ASSISTANT_SYSTEM_PROMPT
        
        # Enhanced Context Structure for the "Gap Analysis Engine"
        context_str = f"""
        [USER DATA CONTEXT]
        Name: {user.name}
        Premium Status: {user.is_premium}
        Target Role: {target_role}
        
        [CURRENT SKILL SNAPSHOT]
        {json.dumps(skills, indent=2)}
        
        [ACTIVE PROJECTS/PLANS]
        {json.dumps(active_plans) if active_plans else "None (Suggest a micro-project)"}
        
        [INSTRUCTION]
        Use this data to perform Gap Analysis. If Premium is False and they ask for deep Resume parsing, suggest upgrading.
        """
        
    return context_str, system_prompt

class ChatbotService:
    def __init__(self, simulated: bool = True):
        # Fallback empty string if key is None to prevent crash on init logic
        api_key = settings.OPENAI_API_KEY
        if api_key:
            self.async_client = openai.AsyncOpenAI(api_key=api_key)
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

        # If we have a user and db, fetch context in a separate thread to avoid blocking the event loop
        if user_id and db:
            context_str, system_prompt = await asyncio.to_thread(
                _fetch_user_and_build_context, user_id, db, mode
            )

        if self.simulated:
            return self._simulated_response(message, lang, context_str, mode)
        else:
            return await self._llm_response(message, lang, context_str, system_prompt)

    def _simulated_response(self, message: str, lang: str, context: str, mode: str) -> str:
        """
        Offline fallback. STRICT ENGLISH ONLY as per new Prime Directive.
        """
        msg = message.lower()

        # --- Simulated Interview Mode ---
        if mode == "interview":
             if "start" in msg or "begin" in msg:
                 return "Let's begin the mock interview. Question 1: Explain the difference between TCP and UDP regarding packet reliability."
             return "[Simulated Evaluation] Grade: B+. Technical Accuracy: Good. \n\nNext Question: How would you handle a race condition in a multi-threaded Python application?"

        # --- Simulated Career OS Mode ---
        if "plan" in msg:
            if "Active Learning Plan" in context or "ACTIVE PROJECTS" in context:
                 return "Based on your profile, you should continue your active micro-project. Shall we review your GitHub commit history?"
            return "You don't have an active plan yet. Please go to the dashboard to generate a 'Gap Analysis' plan."

        if "rust" in msg:
            return "Rust ensures memory safety without a garbage collector. It is a high-value skill for Edge Computing. Would you like a micro-project to build a CLI tool in Rust?"
        
        elif "go" in msg or "golang" in msg:
            return "Go (Golang) is the standard for Cloud Native infrastructure. It offers excellent concurrency primitives (Goroutines). I recommend building a gRPC service to practice."
        
        elif "career" in msg:
            return "To advance your career, I recommend focusing on 'T-Shaped' skills. Let's analyze your GitHub repository to find your niche gaps."
        
        elif "login" in msg:
            return "You can login using Email, GitHub, or LinkedIn to unlock the full Career OS experience."

        # Default fallback (English Only)
        return "I am operating in Simulated Mode (Offline). I can discuss 'Rust', 'Go', 'Career Strategy', or check your 'Plan'. For live intelligence, please connect to the internet."

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
        primary_model = settings.OPENAI_MODEL or "gpt-4o-mini" # Fallback default
        params = {
            "model": primary_model,
            "messages": messages
        }

        # O1 models and gpt-5-mini do not support temperature
        if not (primary_model.startswith("o1-") or primary_model == "gpt-5-mini"):
            params["temperature"] = 0.7

        try:
            response = await self.async_client.chat.completions.create(**params)
            content = response.choices[0].message.content
            return content if content else "AI returned an empty response."
        
        except (openai.NotFoundError, openai.BadRequestError) as e:
            print(f"WARNING: Primary model {settings.OPENAI_MODEL} failed (Error: {e}). Switching to fallback: {settings.OPENAI_FALLBACK_MODEL}.")
            try:
                response = await self.async_client.chat.completions.create(
                    model=settings.OPENAI_FALLBACK_MODEL or "gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e_fallback:
                print(f"CRITICAL: Fallback model also failed: {e_fallback}")
                return "System Error: Unable to reach AI services. Please check your connection or API quotas."
        
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "Error communicating with AI. Please check the system logs."

# Global Instance
chatbot_service = ChatbotService()
