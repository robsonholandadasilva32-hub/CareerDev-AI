import httpx
import math
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan

class CareerEngine:
    def __init__(self):
        # In a real app, these would come from an external API or LLM analysis
        self.market_trends = {
            "Rust": "High",
            "Go": "Very High",
            "Python": "Stable",
            "Ethical AI": "Emerging"
        }

    def calculate_verified_score(self, skill: str, github_bytes: int, linkedin_claims: List[str]) -> float:
        """
        Formula: V_score = (GitHub_Weight * Volume_Factor) + (LinkedIn_Weight * Social_Proof)
        """
        GH_WEIGHT = 0.7  # Code proves ability
        LI_WEIGHT = 0.3  # Profile proves marketability

        # Normalize GitHub bytes (Logarithmic scale to avoid skew by massive repos)
        # log(1) = 0. log(22000) ~ 10. So /10 scales it nicely to 0-1.
        volume_factor = min(math.log(github_bytes + 1) / 10, 1.0) # Cap at 1.0

        # Check case-insensitive
        social_proof = 1.0 if skill.lower() in [s.lower() for s in linkedin_claims] else 0.0

        return (GH_WEIGHT * volume_factor) + (LI_WEIGHT * social_proof)

    def analyze_profile(self, db: Session, user: User) -> Dict:
        """
        Analyzes the user profile, fetching external data if available,
        and updates/creates the CareerProfile in the DB.
        """
        if not user:
            return {}

        profile = user.career_profile
        if not profile:
            profile = CareerProfile(user_id=user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # 1. Sync External Data (Simulation)
        if user.github_id and not profile.github_stats:
            # Simulate GitHub fetching
            # Real implementation would use: httpx.get(f"https://api.github.com/user/{user.github_id}")
            profile.github_stats = {
                "repos": 12,
                "top_languages": {"Python": 60, "JavaScript": 30, "Rust": 10},
                "last_commit": datetime.utcnow().isoformat()
            }
            # Update skills based on GH
            current_skills = profile.skills_snapshot or {}
            current_skills.update({"Rust": 20, "Python": 80}) # Mocked inference
            profile.skills_snapshot = current_skills
            db.commit()

        # 2. Return Structured Data
        return {
            "skills": profile.skills_snapshot or {"General": 10},
            "level": profile.experience_level,
            "focus": profile.target_role,
            "trends": self.market_trends
        }

    def generate_plan(self, db: Session, user: User) -> List[LearningPlan]:
        """
        Generates or retrieves the current learning plan.
        """
        # Check existing incomplete items
        existing_plan = db.query(LearningPlan).filter(
            LearningPlan.user_id == user.id,
            LearningPlan.status != "completed"
        ).all()

        if existing_plan:
            return existing_plan

        # Generate new items based on gaps
        new_items = []
        profile = user.career_profile
        skills = profile.skills_snapshot if profile else {}

        # Gaps Analysis (Heuristic)
        if skills.get("Rust", 0) < 30:
            new_items.append(LearningPlan(
                user_id=user.id,
                title="Fundamentos de Rust",
                description="Domine Ownership e Borrowing com o Rust Book.",
                technology="Rust",
                resources=["https://doc.rust-lang.org/book/"],
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        if skills.get("Go", 0) < 30:
             new_items.append(LearningPlan(
                user_id=user.id,
                title="Microsserviços com Go",
                description="Crie uma API RESTful usando Gin ou Echo.",
                technology="Go",
                due_date=datetime.utcnow() + timedelta(days=7)
            ))

        # Always add an AI Ethics item
        # Ensure user_id is passed explicitly from user.id
        new_items.append(LearningPlan(
            user_id=user.id,
            title="Introdução à IA Ética",
            description="Entenda os princípios de explicabilidade e viés algorítmico.",
            technology="AI Ethics",
            due_date=datetime.utcnow() + timedelta(days=14)
        ))

        db.add_all(new_items)
        db.commit()

        return new_items

    def analyze_alignment(self, linkedin_data: Dict, github_metrics: Dict) -> List[Dict]:
        """
        The 'Imposter vs. Hidden Gem' Matrix Logic.
        Compares LinkedIn Claims vs. GitHub Reality (Languages + Frameworks).
        """
        audit_results = []

        # 1. Normalize Data
        raw_langs = github_metrics.get("raw_languages", {})
        detected_frameworks = set(github_metrics.get("detected_frameworks", []))
        claimed_skills = set([s.lower() for s in linkedin_data.get("claimed_skills", [])])

        # Combined evidence (Lang > 1KB OR Framework present)
        proven_skills = set()
        for lang, bytes_count in raw_langs.items():
            if bytes_count > 1000:
                proven_skills.add(lang.lower())

        # Map frameworks to languages for broader proof
        # e.g. using React proves JS/TS competence
        framework_map = {
            "react": ["javascript", "typescript", "react"],
            "fastapi": ["python", "fastapi"],
            "django": ["python", "django"],
            "tokio": ["rust"],
            "serde": ["rust"],
            "express": ["javascript", "node.js"]
        }

        for fw in detected_frameworks:
            if fw in framework_map:
                for s in framework_map[fw]:
                    proven_skills.add(s)
            proven_skills.add(fw) # Add the framework itself

        # 2. Analyze Alignment (Top 5 Claims + Top 5 Code)
        # We look at the Union of significant skills
        significant_skills = list(claimed_skills | proven_skills)[:8] # Analyze top 8 relevant

        for skill in significant_skills:
            is_claimed = skill in claimed_skills
            is_proven = skill in proven_skills

            status = "Neutral"
            action = "None"
            badge = "ok"

            if is_claimed and not is_proven:
                status = "Imposter Detected"
                action = "HOTFIX"
                badge = "critical"
            elif is_proven and not is_claimed:
                status = "Hidden Gem"
                action = "ADD_TO_LINKEDIN"
                badge = "opportunity"
            elif is_proven and is_claimed:
                status = "Verified Expert"
                badge = "success"

            audit_results.append({
                "skill": skill.title(),
                "status": status,
                "action": action,
                "badge": badge
            })

        return audit_results

    def get_career_dashboard_data(self, db: Session, user: User) -> Dict:
        """
        Returns the structured JSON object for the new Dashboard AI brain.
        Now includes 'radar_data' and 'missing_skills'.
        """
        # Ensure profile analysis runs first to populate data
        self.analyze_profile(db, user)
        profile = user.career_profile

        # --- DATA PREP ---
        metrics = profile.github_activity_metrics or {}
        raw_languages = metrics.get("raw_languages", {})
        detected_frameworks = metrics.get("detected_frameworks", [])

        li_data = profile.linkedin_alignment_data or {}
        claimed_skills = li_data.get("claimed_skills", [])

        # ZONE A: HOLISTIC SCANNER (Professional Health Bar)
        # Logic: (Profile Completeness + GitHub Activity + Skill Verification Score) / 3
        p_completeness = 80 if li_data.get("connected") else 40
        velocity_score = 85 if metrics.get("velocity_score") == "High" else 50

        # Skill Verification
        skill_ver_sum = 0
        top_skills = sorted(raw_languages.items(), key=lambda x: x[1], reverse=True)[:3]
        for skill, bytes_count in top_skills:
            skill_ver_sum += self.calculate_verified_score(skill, bytes_count, claimed_skills)
        avg_skill_ver = (skill_ver_sum / 3) * 100 if top_skills else 0

        holistic_score = int((p_completeness + velocity_score + avg_skill_ver) / 3)
        health_color = "green" if holistic_score > 80 else ("orange" if holistic_score > 50 else "red")

        # ZONE B: CROSS-VERIFICATION ENGINE
        skill_audit = self.analyze_alignment(li_data, metrics)

        # Extract 'missing_skills' for Chatbot (Imposter Detected)
        missing_skills = [item['skill'] for item in skill_audit if item['badge'] == 'critical']

        # ZONE C: STRENGTHS & WEAKNESSES (AI Insight)
        ai_insight_card = profile.ai_insights_summary or "System Analysis: Initializing Neural Link... Please wait for next scan."

        # MARKET RADAR DATA
        # We map top 5 skills to 3 axes: Github (Reality), LinkedIn (Claims), Market (Demand)
        # Normalize to 1-100
        radar_labels = []
        d_github = []
        d_linkedin = []
        d_market = []

        # Use top 5 languages/frameworks from GitHub as base + any high market demand ones missing
        base_skills = list(raw_languages.keys())[:5]
        if not base_skills: base_skills = ["Python", "JavaScript", "Rust"]

        for skill in base_skills:
            radar_labels.append(skill)

            # GitHub Score (Log Volume)
            vol = raw_languages.get(skill, 0)
            d_github.append(min(int(math.log(vol + 1) * 8), 100))

            # LinkedIn Score (Binary-ish)
            d_linkedin.append(90 if skill in claimed_skills else 20)

            # Market Score (Lookup or Random High for Demo)
            market_val = 80
            if skill in self.market_trends:
                trend = self.market_trends[skill]
                market_val = 95 if trend == "Very High" else (85 if trend == "High" else 60)
            d_market.append(market_val)

        return {
            "zone_a_holistic": {
                "score": holistic_score,
                "color": health_color,
                "details": f"Profile: {p_completeness}% | Code Velocity: {metrics.get('velocity_score', 'N/A')}"
            },
            "zone_b_matrix": skill_audit,
            "zone_c_ai": {
                "insights": ai_insight_card
            },
            "radar_data": {
                "labels": radar_labels,
                "datasets": [
                    {"label": "Code Reality", "data": d_github, "color": "#3b82f6"},
                    {"label": "Profile Claims", "data": d_linkedin, "color": "#10b981"},
                    {"label": "Market Demand", "data": d_market, "color": "#ef4444", "borderDash": [5, 5]}
                ]
            },
            "missing_skills": missing_skills,
            # Legacy
            "doughnut_data": profile.skills_graph_data
        }

career_engine = CareerEngine()
