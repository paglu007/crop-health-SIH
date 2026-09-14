"""
Risk calculation engine for Crop Disease Advisory System (SIH 2026).
Combines Computer Vision (CV) model confidence with Weather Risk score.
"""

from typing import Tuple

def compute_final_risk(cv_confidence: float, weather_risk_score: float) -> Tuple[float, str]:
    """
    Combines computer vision confidence with microclimate weather risk score.
    
    Formula:
        final_risk = (0.6 * cv_confidence) + (0.4 * weather_risk_score)
        
    Classification Thresholds:
        - LOW:    final_risk < 0.40
        - MEDIUM: 0.40 <= final_risk <= 0.70
        - HIGH:   final_risk > 0.70

    Args:
        cv_confidence: Confidence score from image classification model [0.0 - 1.0]
        weather_risk_score: Environmental conduciveness score from weather service [0.0 - 1.0]

    Returns:
        Tuple containing:
            - final_risk_score: Normalized rounded float [0.0 - 1.0]
            - risk_level: Categorical risk level ('LOW', 'MEDIUM', 'HIGH')
    """
    # Clamp inputs between 0.0 and 1.0
    cv = max(0.0, min(1.0, float(cv_confidence)))
    weather = max(0.0, min(1.0, float(weather_risk_score)))

    # Weighted composite score
    raw_final_risk = (0.6 * cv) + (0.4 * weather)
    final_risk_score = round(raw_final_risk, 4)

    # Determine risk category
    if final_risk_score < 0.40:
        risk_level = "LOW"
    elif final_risk_score <= 0.70:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return final_risk_score, risk_level
