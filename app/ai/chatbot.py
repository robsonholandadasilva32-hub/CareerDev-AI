from typing import Optional, Tuple, Dict, Any
import openai
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.ai.prompts import (
    CAREER_ASSISTANT_SYSTEM_PROMPT,
    get_interviewer_system_prompt,
    CHALLENGE_GENERATOR_PROMPT,
    CHALLENGE_GRADER_PROMPT,
    LINKEDIN_POST_GENERATOR_PROMPT,
    PROJECT_SPEC_GENERATOR_PROMPT
)
from app.db.models.user import User
from app.db.models.career import CareerProfile

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

    async def get_response(self, message: str, lang: str = "en", user_id: int = None, db: Session = None, mode: str = "standard") -> Dict[str, Any]:
        """
        Mode can be 'standard', 'interview', or 'challenge'.
        Returns Dict with 'message' and 'meta'.
        """

        profile = None
        if user_id and db:
             user = db.query(User).filter(User.id == user_id).first()
             if user:
                 profile = user.career_profile

        # 1. TRIGGER CHALLENGE
        if message == "/trigger_challenge" and profile:
             return await self._handle_challenge_trigger(profile, db, lang)

        # 2. GRADE CHALLENGE
        if mode == "challenge" and profile:
             return await self._handle_challenge_grading(message, profile, db, lang)

        # 3. STANDARD / INTERVIEW
        context_str = ""
        system_prompt = CAREER_ASSISTANT_SYSTEM_PROMPT

        if user_id and db:
            context_str, system_prompt = await asyncio.to_thread(
                _fetch_user_and_build_context, user_id, db, mode
            )

        response_text = ""
        if self.simulated:
            response_text = self._simulated_response(message, lang, context_str, mode)
        else:
            response_text = await self._llm_response(message, lang, context_str, system_prompt)

        return {"message": response_text, "meta": {"mode": mode}}

    def _find_weakness(self, profile: CareerProfile) -> str:
        try:
            metrics = profile.github_activity_metrics or {}
            raw_langs = metrics.get("raw_languages", {})
            if not raw_langs:
                return "General Engineering"

            total = sum(raw_langs.values())
            if total == 0:
                return "General Engineering"

            lowest_skill = None
            lowest_pct = 100

            for skill, bytes_count in raw_langs.items():
                pct = (bytes_count / total) * 100
                if 0 < pct < lowest_pct:
                    lowest_pct = pct
                    lowest_skill = skill

            return lowest_skill or "General Engineering"
        except Exception:
            return "General Engineering"

    async def _handle_challenge_trigger(self, profile: CareerProfile, db: Session, lang: str) -> Dict[str, Any]:
        skill = self._find_weakness(profile)

        question = ""
        if self.simulated:
            question = f"Challenge Mode (Simulated): Explain the core concept of {skill} and why it matters."
        else:
            prompt = CHALLENGE_GENERATOR_PROMPT.format(skill=skill)
            # We call LLM directly
            question = await self._llm_response("", lang, "", prompt)

        # Save State
        profile.active_challenge = {
            "skill": skill,
            "question": question,
            "timestamp": datetime.utcnow().isoformat()
        }
        db.commit()

        return {"message": question, "meta": {"mode": "challenge"}}

    async def _handle_challenge_grading(self, answer: str, profile: CareerProfile, db: Session, lang: str) -> Dict[str, Any]:
        active = profile.active_challenge or {}
        question = active.get("question", "Unknown")

        grade = ""
        if self.simulated:
            grade = "Rating: ⭐⭐⭐\nCorrection: Good attempt (Simulated).\nFollow-up: Try diving deeper into the docs."
        else:
            prompt = CHALLENGE_GRADER_PROMPT.format(question=question, answer=answer)
            grade = await self._llm_response("", lang, "", prompt)

        # Clear State
        profile.active_challenge = None
        db.commit()

        return {"message": grade, "meta": {"mode": "standard"}}

    async def generate_linkedin_post(self, skill: str, lang: str) -> str:
        """
        Generates a viral LinkedIn post using the dedicated prompt.
        """
        clean_skill = skill.replace(" ", "").replace("/", "")

        if self.simulated:
            return f"Excited to share my progress in {skill}! Thanks to CareerDev AI for the structured learning path. 🚀 #{clean_skill} #TechJourney (Simulated)"

        prompt = LINKEDIN_POST_GENERATOR_PROMPT.format(skill=skill, skill_clean=clean_skill)
        return await self._llm_response("", lang, "", prompt)

    async def generate_project_spec(self, skill: str, lang: str) -> str:
        """
        Generates a Micro-Project Specification (Markdown) to fill a skill gap.
        """
        if self.simulated:
            return f"# Project: {skill} Accelerator (Simulated)\n\n**Objective:** Build a proof of concept.\n\n**Tasks:**\n1. Setup Environment.\n2. Implement core logic.\n3. Push to GitHub."

        prompt = PROJECT_SPEC_GENERATOR_PROMPT.format(skill=skill)
        return await self._llm_response("", lang, "", prompt)

    def _simulated_response(self, message: str, lang: str, context: str, mode: str) -> str:
        msg = message.lower()

        # Helper for simple multilingual return
        def reply(en, pt, es):
            if lang == 'pt-BR' or lang == 'pt': return pt
            if lang == 'es': return es
            return en

        if mode == "interview":
             if "start" in msg:
                 return reply(
                     "Let's start. Explain the difference between TCP and UDP.",
                     "Vamos começar. Explique a diferença entre TCP e UDP.",
                     "Empecemos. Explica la diferencia entre TCP y UDP."
                 )
             return reply(
                 "Good answer (Simulated). Next: What is Dependency Injection?",
                 "Boa resposta (Simulado). Próxima: O que é Injeção de Dependência?",
                 "Buena respuesta (Simulado). Siguiente: ¿Qué es la Inyección de Dependencias?"
             )

        if "my plan" in msg or "meu plano" in msg:
            if "Active Learning Plan" in context:
                 plan_name = context.split("Active Learning Plan:")[1].split("- Focus")[0].strip()
                 return reply(
                     "Based on your profile, you should focus on: " + plan_name,
                     "Com base no seu perfil, você deve focar em: " + plan_name,
                     "Basado en tu perfil, deberías enfocarte en: " + plan_name
                 )
            return reply(
                "You don't have an active plan yet. Go to the dashboard to generate one.",
                "Você ainda não tem um plano ativo. Vá ao dashboard para gerar um.",
                "Aún no tienes un plan activo. Ve al panel para generar uno."
            )

        if "rust" in msg:
            return reply(
                "Rust is a language focused on safety and performance. Great for embedded systems and critical services.",
                "Rust é uma linguagem focada em segurança e performance. Ótima para sistemas embarcados e serviços críticos.",
                "Rust es un lenguaje enfocado en seguridad y rendimiento. Genial para sistemas integrados y servicios críticos."
            )
        elif "go" in msg or "golang" in msg:
            return reply(
                "Go is excellent for microservices and cloud applications due to its lightweight concurrency.",
                "Go é excelente para microsserviços e aplicações em nuvem devido à sua concorrência leve.",
                "Go es excelente para microservicios y aplicaciones en la nube debido a su concurrencia ligera."
            )
        elif "career" in msg or "carreira" in msg:
            return reply(
                "To advance your career, CareerDev AI suggests focusing on T-Shaped skills and connecting your GitHub for gap analysis.",
                "Para avançar na carreira, o CareerDev AI sugere focar em habilidades T-Shaped e conectar seu GitHub para análise de lacunas.",
                "Para avanzar en tu carrera, CareerDev AI sugiere enfocarse en habilidades T-Shaped y conectar tu GitHub para análisis de brechas."
            )
        elif "login" in msg or "entrar" in msg:
            return reply(
                "You can login using Email/Password, GitHub or LinkedIn for a complete experience.",
                "Você pode entrar usando E-mail/Senha, GitHub ou LinkedIn para uma experiência completa.",
                "Puedes iniciar sesión usando Email/Contraseña, GitHub o LinkedIn para una experiencia completa."
            )

        return reply(
            "Operating in simulated mode. Ask about 'Rust', 'Go', 'Career' or 'My Plan'. Try Interview Mode!",
            "Operando em modo simulado. Pergunte sobre 'Rust', 'Go', 'Carreira' ou 'Meu Plano'. Tente o Modo Entrevista!",
            "Operando en modo simulado. Pregunta sobre 'Rust', 'Go', 'Carrera' o 'Mi Plan'. ¡Prueba el Modo Entrevista!"
        )

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
        lang_instruction = f"Reply in {lang}."
        if lang == 'pt-BR' or lang == 'pt':
             lang_instruction = "Responda em Português do Brasil."
        elif lang == 'es':
             lang_instruction = "Responda em Espanhol."

        messages = [
            {"role": "system", "content": system_prompt + "\n" + context},
            {"role": "system", "content": lang_instruction}
        ]
        if message:
            messages.append({"role": "user", "content": message})

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
