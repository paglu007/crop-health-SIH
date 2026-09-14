"""Risk calculation engine adapted from the team's SIH risk engine.

This module calculates epidemiological risk from:
- computer-vision confidence
- environmental/weather risk
- temperature suitability
- humidity suitability
- moisture/leaf-wetness suitability

It does NOT perform image classification and does NOT generate treatment advice.
"""

from typing import Any, Dict, Optional


def calculate_combined_risk(
    cv_confidence: float,
    weather_risk_score: float,
    cv_weight: float = 0.55,
    weather_weight: float = 0.45,
    temp_score: Optional[float] = None,
    humidity_score: Optional[float] = None,
    moisture_score: Optional[float] = None,
    pathogen_aggressiveness: float = 1.0,
) -> Dict[str, Any]:

    total_w = max(0.01, cv_weight + weather_weight)
    w_cv = cv_weight / total_w
    w_weather = weather_weight / total_w

    c_cv = max(0.0, min(1.0, float(cv_confidence)))
    s_w = max(0.0, min(1.0, float(weather_risk_score)))

    linear_base = (w_cv * c_cv) + (w_weather * s_w)

    synergy_lambda = 0.08 * pathogen_aggressiveness
    synergy_bonus = 0.0

    if c_cv >= 0.35 and s_w >= 0.60:
        synergy_bonus = synergy_lambda * (c_cv * s_w)

    raw_combined = (linear_base + synergy_bonus) * pathogen_aggressiveness

    final_score = round(
        float(min(1.0, max(0.0, raw_combined))),
        3
    )

    if final_score >= 0.65:
        risk_level = "HIGH"
        action_window_hours = 24 if s_w >= 0.85 else 36
        action_urgency = (
            "High priority: inspect and manage affected areas promptly."
        )

    elif final_score >= 0.40:
        risk_level = "MEDIUM"
        action_window_hours = 72
        action_urgency = (
            "Moderate priority: increase monitoring and apply "
            "appropriate preventive management."
        )

    else:
        risk_level = "LOW"
        action_window_hours = 120
        action_urgency = (
            "Low environmental risk: continue routine monitoring."
        )

    if s_w >= 0.80 and c_cv >= 0.40:
        sporulation_potential = "High / Epidemic Surge"
    elif s_w >= 0.60:
        sporulation_potential = "Active Sporulation"
    elif s_w >= 0.35:
        sporulation_potential = "Moderate / Latent"
    else:
        sporulation_potential = "Inhibited / Dormant"

    trajectory_delta = round(
        0.10 * s_w * (1.0 - final_score),
        3
    )

    projected_24h = round(
        min(1.0, final_score + trajectory_delta),
        3
    )

    projected_72h = round(
        min(1.0, final_score + (trajectory_delta * 1.8)),
        3
    )

    formula_str = (
        f"({w_cv:.2f} × {c_cv:.2f} CV) + "
        f"({w_weather:.2f} × {s_w:.2f} Weather)"
    )

    if synergy_bonus > 0.005:
        formula_str += f" + {synergy_bonus:.3f} Synergy"

    formula_str += f" = {final_score:.3f} ({risk_level})"

    t_score = (
        round(float(temp_score), 2)
        if temp_score is not None
        else round(s_w, 2)
    )

    h_score = (
        round(float(humidity_score), 2)
        if humidity_score is not None
        else round(s_w, 2)
    )

    m_score = (
        round(float(moisture_score), 2)
        if moisture_score is not None
        else round(max(0.1, s_w * 0.9), 2)
    )

    return {
        "cv_confidence": round(c_cv, 3),
        "weather_risk_score": round(s_w, 3),
        "final_risk_score": final_score,
        "risk_level": risk_level,
        "synergy_bonus": round(synergy_bonus, 3),
        "thermal_suitability": t_score,
        "humidity_pressure": h_score,
        "moisture_pressure": m_score,
        "sporulation_potential": sporulation_potential,
        "action_window_hours": action_window_hours,
        "action_urgency": action_urgency,
        "projected_trajectory_24h": projected_24h,
        "projected_trajectory_72h": projected_72h,
        "formula_breakdown": formula_str,
    }
