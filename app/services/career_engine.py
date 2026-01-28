import httpx
import math
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import logging

from app.db.models.user import User
from app.db.models.career import CareerProfile, LearningPlan
from app.services.social_harvester import social_harvester

logger = logging.getLogger(__name__)

class CareerEngine:
    def __init__(self):
        # Definição de tendências de mercado (Mock ou via API externa)
        self.market_trends = {
            "Rust": "High",
            "Go": "Very High",
            "Python": "Stable",
            "Ethical AI": "Emerging"
        }

    # --- LÓGICA AUXILIAR (Mantida) ---
    def calculate_verified_score(self, skill: str, github_bytes: int, linkedin_claims: List[str]) -> float:
        """
        Fórmula: V_score = (GitHub_Weight * Volume_Factor) + (LinkedIn_Weight * Social_Proof)
        """
        GH_WEIGHT = 0.7  
        LI_WEIGHT = 0.3  

        # Normaliza bytes do GitHub (Escala logarítmica)
        volume_factor = min(math.log(github_bytes + 1) / 10, 1.0) 

        # Prova Social (Case-insensitive)
        social_proof = 1.0 if skill.lower() in [s.lower() for s in linkedin_claims] else 0.0

        return (GH_WEIGHT * volume_factor) + (LI_WEIGHT * social_proof)

    # --- INTEGRAÇÃO DA LÓGICA "CAREER ARCHITECT" (Solicitação 7 e 8) ---
    
    def _generate_gap_insights(self, github_stats: Dict, linkedin_profile: Dict) -> List[Dict]:
        """
        Analisa a discrepância entre a Realidade (GitHub) e a Percepção (LinkedIn).
        Substitui a antiga analyze_skill_alignment.
        """
        insights = []
        raw_langs = github_stats.get('languages', {})
        claimed_skills = linkedin_profile.get('skills', {}) # Ex: {'Python': 'Expert'}

        # Lógica 1: O Impostor (Diz que sabe, mas não coda)
        for skill, claimed_level in claimed_skills.items():
            bytes_count = raw_langs.get(skill, 0)
            # Se diz Expert mas tem menos de 10k bytes (aprox. 300 linhas de código)
            if claimed_level == 'Expert' and bytes_count < 10000:
                insights.append({
                    "type": "CRITICAL",
                    "skill": skill,
                    "msg": f"⚠️ Discrepancy: Claims Expert in {skill} but low code volume.",
                    "action": "GENERATE_MICRO_PROJECT"
                })

        # Lógica 2: Hidden Gem (Coda muito, mas não "vende" no perfil)
        for lang, bytes_count in raw_langs.items():
            if lang not in claimed_skills and bytes_count > 50000:
                insights.append({
                    "type": "OPPORTUNITY",
                    "skill": lang,
                    "msg": f"💎 Hidden Gem: High volume in {lang}. Add to LinkedIn.",
                    "action": "UPDATE_PROFILE"
                })
        
        return insights

    def _generate_weekly_routine(self, github_stats: Dict, user_streak: int) -> Dict:
        """
        Gera o plano semanal (Growth Engine).
        Implementa a lógica de Hardcore Mode e priorização de Linguagem.
        """
        # Hardcore Mode (Se streak >= 4 semanas)
        if user_streak >= 4:
            return {
                "mode": "HARDCORE",
                "focus": "System Design",
                "tasks": [
                    {"day": "Week 4", "task": "Design a Distributed Rate Limiter in Rust", "type": "Architect", "action": "DESIGN_DOC"}
                ]
            }

        # Normal Mode: Define o Foco
        raw_langs = github_stats.get('languages', {})
        python_score = raw_langs.get('Python', 0)
        rust_score = raw_langs.get('Rust', 0)
        
        # Se é expert em Python mas novato em Rust -> Foco em Rust
        focus = "Rust" if (python_score > 100000 and rust_score < 5000) else "Python Advanced"
        
        task_code = f"CLI Tool: Parse JSON in {focus}"
        
        return {
            "mode": "GROWTH",
            "focus": focus,
            "tasks": [
                {
                    "day": "Mon", 
                    "task": f"Learn: {focus} Memory Model & Ownership", 
                    "type": "Learn", 
                    "done": False
                },
                {
                    "day": "Wed", 
                    "task": task_code, 
                    "type": "Code", 
                    "action": "VERIFY_REPO",
                    "verify_keyword": f"{focus.lower()}-cli" 
                }
            ]
        }

    # --- ORQUESTRAÇÃO DE DADOS (DB + API) ---

    async def analyze_profile(self, db: Session, user: User) -> Dict:
        """
        Garante que os dados do perfil existam no DB. Se não, cria mocks ou busca.
        """
        if not user: return {}
        
        profile = user.career_profile
        if not profile:
            profile = CareerProfile(user_id=user.id)
            db.add(profile)
            db.commit()

        # Simulação de Sync (Em prod, chamaria o social_harvester real)
        if not profile.github_activity_metrics:
            # Popula dados iniciais para a demo funcionar
            raw_langs = {"Python": 120000, "JavaScript": 30000, "Rust": 2000} # Rust baixo para ativar a engine
            profile.github_activity_metrics = {
                "raw_languages": raw_langs,
                "velocity_score": "High",
                "commits_last_30_days": 45
            }
            # Mock LinkedIn
            profile.linkedin_alignment_data = {
                "claimed_skills": ["Python", "JavaScript"], # Rust faltando -> Hidden Gem potencial se codasse mais
                "skills_map": {"Python": "Expert", "JavaScript": "Intermediate"}
            }
            db.commit()

        return {}

    async def get_career_dashboard_data(self, db: Session, user: User) -> Dict:
        """
        Retorna o JSON estruturado final para o Dashboard, unindo todas as lógicas.
        """
        # 1. Garante dados
        await self.analyze_profile(db, user)
        profile = user.career_profile

        # 2. Extrai dados brutos
        metrics = profile.github_activity_metrics or {}
        raw_languages = metrics.get("raw_languages", {})
        li_data = profile.linkedin_alignment_data or {}
        
        # Normaliza estrutura para as funções lógicas
        github_input = {"languages": raw_languages}
        linkedin_input = {"skills": li_data.get("skills_map", {})} 
        if not linkedin_input["skills"]:
            # Fallback se vier lista antiga
            linkedin_input["skills"] = {s: "Expert" for s in li_data.get("claimed_skills", [])}

        # 3. Executa a Lógica do "CareerArchitect"
        insights = self._generate_gap_insights(github_input, linkedin_input)
        
        # Simula Streak (Idealmente viria de user.streak_count no DB)
        current_streak = getattr(user, "streak_count", 0) 
        weekly_plan = self._generate_weekly_routine(github_input, current_streak)

        # 4. Formata Zone B (Matrix)
        skill_audit = []
        processed_skills = set()
        
        # Adiciona Insights (Críticos e Oportunidades)
        for item in insights:
            processed_skills.add(item["skill"])
            skill_audit.append({
                "skill": item["skill"],
                "verdict": "CRITICAL GAP" if item["type"] == "CRITICAL" else "HIDDEN GEM",
                "color": "#ef4444" if item["type"] == "CRITICAL" else "#10b981", # Red / Green
                "percentage": 10 if item["type"] == "CRITICAL" else 90,
                "msg": item["msg"]
            })

        # Adiciona Matches (O que está bom)
        for skill in linkedin_input["skills"]:
            if skill in raw_languages and skill not in processed_skills:
                bytes_count = raw_languages[skill]
                if bytes_count > 10000:
                    skill_audit.append({
                        "skill": skill,
                        "verdict": "MATCH",
                        "color": "#3b82f6", # Blue
                        "percentage": 100,
                        "msg": "Verified Expert"
                    })

        # 5. Formata Radar Chart (Zone A)
        radar_labels = []
        d_github = []
        d_linkedin = []
        d_market = []
        
        base_skills = list(raw_languages.keys())[:5]
        if not base_skills: base_skills = ["Python", "Rust", "Go"]

        for skill in base_skills:
            radar_labels.append(skill)
            # Valor GitHub (Realidade)
            vol = raw_languages.get(skill, 0)
            d_github.append(min(int(math.log(vol + 1) * 8), 100))
            # Valor LinkedIn (Percepção)
            d_linkedin.append(90 if skill in linkedin_input["skills"] else 20)
            # Valor Mercado
            d_market.append(95 if self.market_trends.get(skill) == "High" else 60)

        # Cálculo Holístico Simples
        holistic_score = int((sum(d_github) + sum(d_linkedin)) / (len(d_github)*2))

        return {
            "zone_a_holistic": {
                "score": holistic_score,
                "color": "green" if holistic_score > 70 else "orange",
                "details": f"Velocity: {metrics.get('velocity_score', 'N/A')}"
            },
            "zone_b_matrix": skill_audit,
            "weekly_plan": weekly_plan, # O novo Motor de Crescimento
            "zone_a_radar": {
                 "labels": radar_labels,
                 "datasets": [
                     {"label": "Code Reality (GH)", "data": d_github},
                     {"label": "Profile Claims (LI)", "data": d_linkedin},
                     {"label": "Market Demand", "data": d_market}
                 ]
            },
            "missing_skills": [i["skill"] for i in insights if i["type"] == "CRITICAL"]
        }

# Instância global para ser importada
career_engine = CareerEngine()
