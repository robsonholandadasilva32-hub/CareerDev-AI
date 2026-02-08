from typing import Dict, List

class TrustEngine:
    def calculate_trust(self, audit_integrity: Dict, model_health: Dict) -> Dict:
        """
        Calculates a 0-100 score representing how much the user should trust the current insights.
        """
        score = 100
        penalties = []

        # 1. Check Data Freshness (Audit)
        if audit_integrity.get("status") != "HEALTHY":
            score -= 30
            penalties.append(f"System Integrity: {audit_integrity.get('message')}")

        # 2. Check Model Health (Variance/Drift)
        if model_health.get("status") != "HEALTHY":
            score -= 40
            penalties.append(f"Model Health: {model_health.get('message')}")

        # 3. Cap Score
        score = max(0, score)

        level = "HIGH"
        if score <= 50:
            level = "LOW"
        elif score <= 80:
            level = "MEDIUM"

        return {
            "trust_score": score,
            "level": level,
            "penalties": penalties
        }

trust_engine = TrustEngine()
