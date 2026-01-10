from typing import List, Dict

class CareerEngine:
    def analyze_profile(self, user_id: int) -> Dict:
        # MOCK: In a real scenario, this would scrape GitHub/LinkedIn
        return {
            "skills": {
                "Python": 85,
                "JavaScript": 70,
                "Rust": 10,
                "Go": 25
            },
            "level": "Iniciante",
            "focus": "Full Stack"
        }

    def generate_plan(self, user_id: int) -> List[Dict]:
        return [
            {
                "title": "Aprofundamento em Rust",
                "description": "Crie uma CLI simples para manipulação de arquivos.",
                "status": "pending",
                "tech": "Rust"
            },
            {
                "title": "Microsserviços com Go",
                "description": "Implemente um servidor HTTP básico com autenticação JWT.",
                "status": "pending",
                "tech": "Go"
            },
            {
                "title": "IA Ética: Estudo de Caso",
                "description": "Leia o paper sobre viés em modelos de linguagem.",
                "status": "completed",
                "tech": "AI"
            }
        ]

career_engine = CareerEngine()
