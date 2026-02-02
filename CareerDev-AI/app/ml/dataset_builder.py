import pandas as pd
from app.db.session import SessionLocal
from app.db.models.skill_snapshot import SkillSnapshot
from app.db.models.analytics import RiskSnapshot

def build_dataset():
    db = SessionLocal()

    skills = db.query(SkillSnapshot).all()
    risks = db.query(RiskSnapshot).all()

    df_skills = pd.DataFrame([{
        "user_id": s.user_id,
        "skill": s.skill,
        "confidence": s.confidence_score,
        "date": s.recorded_at
    } for s in skills])

    df_risks = pd.DataFrame([{
        "user_id": r.user_id,
        "risk": r.risk_score,
        "date": r.recorded_at
    } for r in risks])

    dataset = pd.merge(df_skills, df_risks, on=["user_id", "date"], how="left")
    dataset.to_csv("career_training_dataset.csv", index=False)
