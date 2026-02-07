from typing import Dict, List, Any
from app.ml.shap_explainer import shap_explainer

class CounterfactualEngine:
    """
    Generates quantitative counterfactual explanations.
    Output is explicit, numeric and action-oriented.
    
    Logic: Uses linear approximation to estimate risk reduction based on 
    key feature improvements (Commit Velocity, Skill Slope, Market Gaps).
    """

    def generate(self, features: Dict[str, Any], current_risk: int) -> Dict[str, Any]:
        """
        Facade method that now delegates to SHAP-based generation.
        Maintains backward compatibility for the call signature.
        """
        return self.generate_from_shap(features, current_risk)

    def generate_from_shap(self, features: dict, current_risk: int):
        # 1. Get mathematical explanation
        # features should now contain "avg_confidence" and "commit_velocity"
        explanation = shap_explainer.explain(
            features.get("avg_confidence", 0),
            features.get("commit_velocity", 0)
        )
        actions = []
        
        # 2. Translate SHAP positive contributions (risk drivers) into actions
        for feature, contribution in explanation["features"].items():
            # If contribution > 0, it increases risk. We want to reduce it.
            if contribution > 0:
                impact_val = int(contribution * 10) # Scale for readability if needed

                if feature == "commit_velocity":
                    actions.append({
                        "action": "Increase commit velocity",
                        "impact": f"-{impact_val}% risk",
                        "type": "behavior"
                    })
                elif feature == "avg_confidence":
                    actions.append({
                        "action": "Improve verified skill confidence",
                        "impact": f"-{impact_val}% risk",
                        "type": "skill"
                    })

        # Also keep Market Gap Analysis from legacy logic as it's not in the SHAP model yet
        # but provides valuable specific advice.
        # --- 3. Market Gap Analysis (Hybrid approach) ---
        market_gap = features.get("market_gap", [])
        if market_gap:
            top_gap = market_gap[0]
            # Assign a heuristic impact for market gap since it's not in SHAP model
            gap_impact = 15
            actions.append({
                "action": f"Practice {top_gap} for 4 weeks",
                "impact": f"-{gap_impact}% risk",
                "type": "skill"
            })

        # 3. Calculate projection
        # Parse numeric impact from string (e.g., "-15% risk" -> 15)
        total_reduction = 0
        final_actions = []

        for a in actions:
            try:
                impact_str = a["impact"].replace("% risk", "").replace("-", "")
                reduction = int(impact_str)
                total_reduction += reduction
                # Return structured object instead of formatted string
                final_actions.append(a)
            except ValueError:
                continue

        projected_risk = max(0, current_risk - total_reduction)

        return {
            "current_risk": current_risk,
            "projected_risk": projected_risk,
            "actions": final_actions,
            "summary": (
                f"Executing the actions above could reduce your risk "
                f"from {current_risk}% to approximately {projected_risk}%."
            )
        }

# ---------------------------------------------------------
# SERVICE INSTANCE
# ---------------------------------------------------------
counterfactual_engine = CounterfactualEngine()
