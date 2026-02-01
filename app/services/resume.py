import asyncio
import json
import logging
import openai
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models.career import CareerProfile, LearningPlan

logger = logging.getLogger(__name__)

def _mock_analyze(text: str, target_role: str):
    """
    Fallback/Mock logic when AI is unavailable.
    """
    text_lower = text.lower()
    keywords = {
        "python": 10, "rust": 15, "docker": 10, "kubernetes": 15,
        "aws": 10, "react": 5, "sql": 10, "fastapi": 10
    }

    found = []
    missing = []
    score = 20

    for kw, points in keywords.items():
        if kw in text_lower:
            found.append(kw.title())
            score += points
        else:
            missing.append(kw.title())

    score = min(score, 100)

    feedback = "Seu currículo é sólido, mas pode melhorar (Modo Offline/Mock)."
    if score > 80:
        feedback = "Excelente perfil! Você está muito bem posicionado."
    elif score < 40:
        feedback = "Precisa de mais palavras-chave técnicas relevantes."

    return {
        "score": score,
        "found_skills": found,
        "missing_skills": missing[:3],
        "feedback": feedback
    }

def analyze_resume_text(text: str, target_role: str):
    """
    Uses OpenAI to analyze the resume against the target role.
    Falls back to mock logic on error or missing key.
    """
    if not settings.OPENAI_API_KEY:
        return _mock_analyze(text, target_role)

    try:
        openai.api_key = settings.OPENAI_API_KEY

        system_prompt = """
        You are an expert Senior Technical Recruiter and Career Coach.
        Analyze the provided resume text for the specific Target Role.

        You must return a valid JSON object with the following structure:
        {
            "score": <integer 0-100>,
            "found_skills": [<list of strings (skills found)>],
            "missing_skills": [<list of strings (critical skills missing for the role)>],
            "feedback": "<string (brief, constructive feedback in Portuguese)>"
        }

        Be strict but encouraging. Prioritize hard skills for the score.
        """

        response = openai.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Target Role: {target_role}\n\nResume Text:\n{text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Ensure fallback for partial JSON
        return {
            "score": data.get("score", 50),
            "found_skills": data.get("found_skills", []),
            "missing_skills": data.get("missing_skills", []),
            "feedback": data.get("feedback", "Análise concluída.")
        }

    except Exception as e:
        logger.error(f"Error in AI Resume Analysis: {e}")
        return _mock_analyze(text, target_role)

def process_resume_upload(db: Session, user_id: int, resume_text: str):
    user_profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()
    target = user_profile.target_role if user_profile else "Developer"

    analysis = analyze_resume_text(resume_text, target)

    # Auto-link: Add missing skills to Learning Plan
    added_plans = []
    # Ensure missing_skills is a list
    missing = analysis.get("missing_skills", [])
    if not isinstance(missing, list):
        missing = []

    # N+1 fix: Fetch existing plans in one query
    existing_plans = db.query(LearningPlan.technology).filter(
        LearningPlan.user_id == user_id,
        LearningPlan.technology.in_(missing)
    ).all()
    existing_skills = {plan.technology for plan in existing_plans}

    for skill in missing:
        if skill not in existing_skills:
            new_plan = LearningPlan(
                user_id=user_id,
                title=f"Dominar {skill}",
                description=f"Identificado pela IA como gap para {target}.",
                technology=skill,
                status="pending"
            )
            db.add(new_plan)
            added_plans.append(skill)

    db.commit()

    analysis["added_plans"] = added_plans
    return analysis

async def process_resume_upload_async(db: Session, user_id: int, resume_text: str, github_evidence: Optional[Dict[str, List[str]]] = None):
    user_profile = await asyncio.to_thread(db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first)
    target = user_profile.target_role if user_profile else "Developer"

    analysis = await asyncio.to_thread(analyze_resume_text, resume_text, target)

    # --- Cross-Validation Logic ---
    verification_results = []
    github_evidence = github_evidence or {}

    # Create a case-insensitive lookup for GitHub evidence
    # Key: Lowercase Skill, Value: (Original Skill Name, List of Repos)
    gh_lookup = {k.lower(): (k, v) for k, v in github_evidence.items()}

    resume_skills = analysis.get("found_skills", [])
    # Track which GH skills were matched to avoid duplicates in Inferred
    matched_gh_skills = set()

    for skill in resume_skills:
        skill_lower = skill.lower()
        if skill_lower in gh_lookup:
            # VERIFIED
            original_gh_name, repos = gh_lookup[skill_lower]
            repo_str = ", ".join(repos[:3]) # Limit to 3
            if len(repos) > 3: repo_str += f" +{len(repos)-3} others"

            verification_results.append({
                "skill": skill,
                "status": "VERIFIED",
                "evidence": f"Found in: {repo_str}"
            })
            matched_gh_skills.add(skill_lower)
        else:
            # DECLARED
            verification_results.append({
                "skill": skill,
                "status": "DECLARED",
                "evidence": "Not found in public repositories"
            })

    # INFERRED (Bonus - skills in GitHub but not in Resume)
    for skill_lower, (original_name, repos) in gh_lookup.items():
        if skill_lower not in matched_gh_skills:
             repo_str = ", ".join(repos[:3])
             verification_results.append({
                "skill": original_name,
                "status": "INFERRED",
                "evidence": f"Found in: {repo_str}"
            })

    # Sort results: Verified first, then Declared, then Inferred
    status_order = {"VERIFIED": 0, "DECLARED": 1, "INFERRED": 2}
    verification_results.sort(key=lambda x: status_order.get(x["status"], 99))

    analysis["verification_results"] = verification_results
    # ------------------------------

    # Auto-link: Add missing skills to Learning Plan
    added_plans = []
    # Ensure missing_skills is a list
    missing = analysis.get("missing_skills", [])
    if not isinstance(missing, list):
        missing = []

    # N+1 fix: Fetch existing plans in one query
    existing_plans = await asyncio.to_thread(db.query(LearningPlan.technology).filter(
        LearningPlan.user_id == user_id,
        LearningPlan.technology.in_(missing)
    ).all)
    existing_skills = {plan.technology for plan in existing_plans}

    for skill in missing:
        if skill not in existing_skills:
            new_plan = LearningPlan(
                user_id=user_id,
                title=f"Dominar {skill}",
                description=f"Identificado pela IA como gap para {target}.",
                technology=skill,
                status="pending"
            )
            db.add(new_plan)
            added_plans.append(skill)

    await asyncio.to_thread(db.commit)

    analysis["added_plans"] = added_plans
    return analysis
