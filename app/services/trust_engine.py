from datetime import datetime, timedelta
from typing import Dict, Optional

class TrustEngine:
    def calculate_trust(self, last_snapshot_date: Optional[datetime], audit_status: Dict) -> Dict:
        """
        Calculates System Trust based on Data Freshness and Governance Integrity.
        """
        score = 100
        penalties = []

        # 1. Data Freshness Check
        if not last_snapshot_date:
            score -= 50
            penalties.append("No historical data available.")
        elif last_snapshot_date < datetime.utcnow() - timedelta(days=7):
            score -= 30
            penalties.append("Risk data is stale (> 7 days old).")

        # 2. Audit Integrity Check
        if audit_status.get("status") != "HEALTHY":
            score -= 20
            penalties.append(f"Audit System Issue: {audit_status.get('message', 'Unknown issue')}")

        return {
            "trust_score": max(0, score),
            "level": "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW",
            "penalties": penalties
        }

trust_engine = TrustEngine()
