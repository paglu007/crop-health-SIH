"""
LLM Advisory Enrichment Service Module.
Uses Anthropic's Claude API (client.messages.create) to translate verified database facts
into encouraging, plain-language advisory explanations for farmers.

CRITICAL CONSTRAINT:
The LLM must ONLY rephrase/explain verified database fields. It must NEVER invent new
treatment steps, dosages, chemical names, or facts not present in the database record.
"""

from typing import Optional, Tuple
from backend.teammate_ai.config import Config
from backend.teammate_ai.models import DiseaseAdvisory, WeatherSummary

# System prompt with strict anti-hallucination constraint
CLAUDE_SYSTEM_PROMPT = (
    "You are an empathetic agricultural extension advisor communicating directly with a farmer.\n"
    "CRITICAL CONSTRAINT:\n"
    "Only explain and rephrase the provided verified facts in simple, farmer-friendly language.\n"
    "Do NOT add any treatment detail, dosage, chemical name, or recommendation that is not "
    "explicitly given to you in the database record below.\n"
    "Do NOT invent new steps or facts. Your role is strictly translation and clarification.\n"
    "Structure your response with clear, simple sections:\n"
    "1. Field Condition & Risk Assessment (reference the current weather & high-humidity trends)\n"
    "2. Symptoms to Check in the Field (rephrased clearly)\n"
    "3. Action Steps (only the verified low/medium/high advisory and preventive measures)\n"
    "4. Organic & Chemical Options (ONLY exact measures mentioned in the provided text, no invented chemicals or dosages)\n"
    "Keep the tone supportive, clear, and reassuring."
)


def generate_fallback_farmer_explanation(
    disease: DiseaseAdvisory,
    risk_level: str,
    weather: WeatherSummary
) -> str:
    """
    Deterministic fallback explanation constructed strictly from verified database fields
    when the Anthropic API is unavailable or unconfigured.
    """
    # Pick the appropriate level advisory
    if risk_level == "HIGH":
        level_advice = disease.high_risk_advisory or disease.medium_risk_advisory or "Inspect crop immediately."
    elif risk_level == "MEDIUM":
        level_advice = disease.medium_risk_advisory or disease.low_risk_advisory or "Monitor crop closely."
    else:
        level_advice = disease.low_risk_advisory or "Conditions are favorable; maintain routine monitoring."

    weather_note = (
        f"Right now in your area, temperature is around {weather.current_temp_c}°C with "
        f"{weather.current_humidity_pct}% humidity (averaging {weather.avg_humidity_pct}%). "
        f"We have noticed {weather.sustained_high_humidity_days} sustained high-moisture days. "
        f"{'These damp conditions strongly match the weather this disease thrives in.' if weather.avg_humidity_pct >= 75 else 'Keep a close eye on changes in humidity.'}"
    )

    explanation = (
        f"Namaste Farmer. Based on field observations for {disease.crop} ({disease.disease_name}), "
        f"here is your verified advisory:\n\n"
        f"🌿 CURRENT RISK LEVEL: {risk_level}\n"
        f"{weather_note}\n\n"
        f"🔍 SYMPTOMS TO LOOK FOR:\n{disease.symptoms}\n\n"
        f"🛡️ IMMEDIATE ADVISORY:\n{level_advice}\n\n"
        f"🌱 PREVENTIVE MEASURES:\n{disease.preventive_measures or 'Maintain clean field sanitation and healthy spacing.'}\n\n"
        f"🧪 TREATMENT OPTIONS (FROM VERIFIED EXTENSION DATABASE):\n"
        f"• Organic Treatment: {disease.organic_treatment or 'Consult local KVK for organic inputs.'}\n"
        f"• Chemical Treatment: {disease.chemical_treatment or 'Follow local agricultural department recommendations.'}\n\n"
        f"👨‍🌾 EXPERT ADVICE:\n{disease.expert_advisory or 'Reach out to your local Krishi Vigyan Kendra (KVK) if symptoms persist.'}"
    )
    return explanation


def enrich_advisory_with_llm(
    disease: DiseaseAdvisory,
    risk_level: str,
    final_risk_score: float,
    weather: WeatherSummary
) -> Tuple[str, str]:
    """
    Enriches verified database advisory using Anthropic Claude API (claude-3-5-sonnet).
    Guaranteed graceful fallback if API fails or key is missing.

    Returns:
        Tuple of (farmer_friendly_explanation, status_string)
    """
    api_key = Config.ANTHROPIC_API_KEY.strip()

    # If no valid API key, return deterministic fallback
    if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY":
        return generate_fallback_farmer_explanation(disease, risk_level, weather), "fallback_no_api_key"

    # Construct the strictly factual prompt payload
    advisory_for_level = (
        disease.high_risk_advisory if risk_level == "HIGH"
        else disease.medium_risk_advisory if risk_level == "MEDIUM"
        else disease.low_risk_advisory
    )

    user_prompt = f"""
Here are the verified agricultural facts for a crop disease assessment:

[CROP & DISEASE]
- Crop: {disease.crop}
- Disease: {disease.disease_name}
- Pathogen Type: {disease.pathogen_type}

[RISK ASSESSMENT]
- Calculated Risk Level: {risk_level} (Score: {final_risk_score:.2f} / 1.00)

[LIVE WEATHER CONTEXT]
- Current Temperature: {weather.current_temp_c} °C
- Current Humidity: {weather.current_humidity_pct} %
- Average Humidity: {weather.avg_humidity_pct} %
- Sustained High-Moisture Days: {weather.sustained_high_humidity_days} days
- Rain Volume: {weather.total_rain_mm} mm
- Forecast Trend: {weather.forecast_trend}

[VERIFIED DATABASE RECORD - DO NOT ADD ANY NEW FACTS BEYOND THESE]
- Symptoms: {disease.symptoms}
- Favorable Weather Conditions: {disease.favorable_conditions}
- Advisory for this Risk Level: {advisory_for_level}
- Preventive Measures: {disease.preventive_measures}
- Organic Treatment: {disease.organic_treatment}
- Chemical Treatment: {disease.chemical_treatment}
- Expert Advisory: {disease.expert_advisory}

Please generate a simple, reassuring, and clear explanation for the farmer.
Remember: Do NOT invent or add any new chemical dosages, brand names, or unverified treatments.
"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=Config.ANTHROPIC_MODEL,
            max_tokens=1000,
            temperature=0.2,  # Low temperature for strict factual fidelity
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract text blocks
        content_blocks = response.content
        explanation_text = ""
        for block in content_blocks:
            if hasattr(block, "text"):
                explanation_text += block.text

        if explanation_text.strip():
            return explanation_text.strip(), "success"
        else:
            return generate_fallback_farmer_explanation(disease, risk_level, weather), "fallback_empty_response"

    except Exception as err:
        print(f"[LLMAdvisoryService] Anthropic API call error: {err}")
        # Graceful fallback: never crash the core flow
        fallback = generate_fallback_farmer_explanation(disease, risk_level, weather)
        return fallback, f"fallback_error: {str(err)}"
