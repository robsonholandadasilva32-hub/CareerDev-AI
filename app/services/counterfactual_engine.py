from typing import Dict, List, Any

class CounterfactualEngine:
    """
    Generates quantitative counterfactual explanations.
    Output is explicit, numeric and action-oriented.
    
    Logic: Uses linear approximation to estimate risk reduction based on 
    key feature improvements (Commit Velocity, Skill Slope, Market Gaps).
    """

    def generate(self, features: Dict[str, Any], current_risk: int) -> Dict[str, Any]:
        actions = []
        deltas = []

        # --- 1. Commit Velocity Analysis ---
        # Hypothesis: Increasing activity reduces stagnation risk.
        commit_velocity = features.get("commit_velocity", 0)
        
        # Threshold calibrado (versão mais recente: 20 commits/mês)
        if commit_velocity < 20:
            increase = 20 - commit_velocity
            # Multiplier 2.4 calibrated empirically based on risk model weights
            risk_delta = int(increase * 2.4)  
            
            # Formatamos como string para compatibilidade direta com o template HTML
            actions.append(f"Increase activity by +{increase} commits/month (-{risk_delta}% risk)")
            deltas.append(risk_delta)

        # --- 2. Skill Growth Slope Analysis ---
        # Hypothesis: Positive learning trend buffers against market shifts.
        skill_slope = features.get("skill_slope", 0)
        if skill_slope <= 0:
            risk_delta = 10
            actions.append(f"Complete 1 verified weekly routine (-{risk_delta}% risk)")
            deltas.append(risk_delta)

        # --- 3. Market Gap Analysis ---
        # Hypothesis: Addressing missing market skills improves relevance.
        market_gap = features.get("market_gap", [])
        if market_gap:
            # Suggest the first missing skill
            top_gap = market_gap[0]
            risk_delta = 15
            actions.append(f"Practice {top_gap} for 4 weeks (-{risk_delta}% risk)")
            deltas.append(risk_delta)

        # Calculate total projected risk (clamped at 0)
        projected_risk = max(0, current_risk - sum(deltas))

        return {
            "current_risk": current_risk,
            "projected_risk": projected_risk,
            "actions": actions, # Retorna lista de strings formatadas
            "summary": (
                f"Executing the actions above could reduce your risk "
                f"from {current_risk}% to approximately {projected_risk}%."
            )
        }

# ---------------------------------------------------------
# SERVICE INSTANCE
# ---------------------------------------------------------
counterfactual_engine = CounterfactualEngine()
