def forecast_career_risk(
    self,
    skill_confidence: Dict[str, int],
    metrics: Dict,
    db: Optional[Session] = None,
    user: Optional[User] = None
) -> Dict:
    """
    Hybrid career risk forecast:
    - Rule-based signals
    - ML regression adjustment
    - Persistent ML audit log
    """

    # -------------------------------
    # RULE-BASED RISK
    # -------------------------------
    risk_score = 0
    reasons: List[str] = []

    avg_conf = sum(skill_confidence.values()) / max(len(skill_confidence), 1)
    velocity = metrics.get("commits_last_30_days", 0)

    if avg_conf < 60:
        risk_score += 30
        reasons.append("Overall skill confidence trending low.")

    if velocity < 10:
        risk_score += 30
        reasons.append("Low coding activity detected.")

    if metrics.get("velocity_score") == "Low":
        risk_score += 20
        reasons.append("Development velocity decreasing.")

    rule_risk = risk_score

    # -------------------------------
    # ML ADJUSTMENT (SAFE + LOGGED)
    # -------------------------------
    try:
        ml_result = ml_forecaster.predict(avg_conf, velocity)
        ml_risk = ml_result["ml_risk"]

        # Hybrid risk (balanced)
        risk_score = int((rule_risk + ml_risk) / 2)

        # Persist ML audit log (if context available)
        if db and user:
            db.add(MLRiskLog(
                user_id=user.id,
                ml_risk=ml_risk,
                rule_risk=rule_risk,
                model_version=ml_result["model_version"]
            ))
            db.commit()

    except Exception:
        # Fail-safe: rule-only risk
        risk_score = rule_risk

    # -------------------------------
    # FINAL CLASSIFICATION
    # -------------------------------
    if risk_score >= 60:
        level = "HIGH"
        summary = "High probability of stagnation or rejection within 6 months."
    elif risk_score >= 30:
        level = "MEDIUM"
        summary = "Moderate career risk detected within next 6 months."
    else:
        level = "LOW"
        summary = "Career trajectory stable."

    return {
        "risk_level": level,
        "risk_score": risk_score,
        "summary": summary,
        "reasons": reasons
    }
