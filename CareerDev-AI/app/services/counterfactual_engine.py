class CounterfactualEngine:
    """
    Generates actionable 'what-if' explanations based on
    current features used by the risk model.
    """

    def generate(self, features: dict, current_risk: int) -> dict:
        suggestions = []
        estimated_deltas = []

        # --- Commit velocity ---
        commit_velocity = features.get("commit_velocity", 0)
        if commit_velocity < 15:
            suggestions.append(
                "Increase coding activity to at least 15 commits/month."
            )
            estimated_deltas.append(-15)

        # --- Skill confidence trend ---
        skill_slope = features.get("skill_slope", 0)
        if skill_slope <= 0:
            suggestions.append(
                "Demonstrate skill growth by completing at least one verified weekly routine."
            )
            estimated_deltas.append(-10)

        # --- Market alignment ---
        market_gap = features.get("market_gap", [])
        if market_gap:
            suggestions.append(
                f"Reduce market gap by practicing {market_gap[0]}."
            )
            estimated_deltas.append(-20)

        projected_risk = max(
            0,
            current_risk + sum(estimated_deltas)
        )

        return {
            "current_risk": current_risk,
            "projected_risk": projected_risk,
            "actions": suggestions,
            "summary": (
                f"If you follow these steps, your estimated risk "
                f"could drop from {current_risk}% to {projected_risk}%."
            )
        }


counterfactual_engine = CounterfactualEngine()
