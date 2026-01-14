from sqlalchemy.orm import Session
from app.services.career_engine import CareerEngine
from app.db.models.career import CareerProfile, LearningPlan

# Mock AI Service for Resume (will be replaced by real AI in next steps if API key exists)
def analyze_resume_text(text: str, target_role: str):
    """
    Simulates AI analysis of resume text.
    Returns structured data: Score, Key Gaps, Strengths.
    """
    # Simple keyword checking logic for prototype
    text_lower = text.lower()

    keywords = {
        "python": 10, "rust": 15, "docker": 10, "kubernetes": 15,
        "aws": 10, "react": 5, "sql": 10, "fastapi": 10
    }

    found = []
    missing = []
    score = 20 # Base score

    for kw, points in keywords.items():
        if kw in text_lower:
            found.append(kw.title())
            score += points
        else:
            missing.append(kw.title())

    score = min(score, 100)

    feedback = "Seu currículo é sólido, mas pode melhorar."
    if score > 80:
        feedback = "Excelente perfil! Você está muito bem posicionado."
    elif score < 40:
        feedback = "Precisa de mais palavras-chave técnicas relevantes."

    return {
        "score": score,
        "found_skills": found,
        "missing_skills": missing[:3], # Top 3 missing
        "feedback": feedback
    }

def process_resume_upload(db: Session, user_id: int, resume_text: str):
    user_profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()
    target = user_profile.target_role if user_profile else "Developer"

    analysis = analyze_resume_text(resume_text, target)

    # Auto-link: Add missing skills to Learning Plan
    added_plans = []
    for skill in analysis["missing_skills"]:
        # Check if plan already exists
        exists = db.query(LearningPlan).filter(
            LearningPlan.user_id == user_id,
            LearningPlan.technology == skill
        ).first()

        if not exists:
            new_plan = LearningPlan(
                user_id=user_id,
                title=f"Dominar {skill}",
                description=f"Identificado automaticamente pela Análise de Currículo como um gap para a vaga de {target}.",
                technology=skill,
                status="pending"
            )
            db.add(new_plan)
            added_plans.append(skill)

    db.commit()

    analysis["added_plans"] = added_plans
    return analysis
