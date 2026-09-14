"""
Advisory Core Orchestration Module (SIH 2026).
Combines weather service, risk engine, database CRUD, and LLM enrichment into a single pipeline.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from backend.teammate_ai.database import find_advisory
from backend.teammate_ai.models import (
    AdvisoryRequest,
    AdvisoryResponse,
    RawDatabaseAdvisory,
    WeatherSummary,
    DiseaseAdvisory,
)
from backend.teammate_ai.risk import compute_final_risk
from backend.teammate_ai.weather_service import fetch_weather_snapshots
from backend.teammate_ai.llm_advisory_service import enrich_advisory_with_llm


def generate_advanced_advisory(req: AdvisoryRequest, db: Session) -> AdvisoryResponse:
    """
    Executes the full combined advisory workflow:
    
    1. Query Database for Disease Advisory:
       Retrieves verified symptoms, favorable conditions, and treatments.
       
    2. Fetch Weather & Calculate Weather Risk Score:
       Calls OpenWeather API (forecast + timemachine) with local caching.
       Computes microclimate conduciveness against favorable_conditions.
       If weather fails, falls back to neutral 0.5 score.
       
    3. Calculate Final Composite Risk:
       final_risk = 0.6 * cv_confidence + 0.4 * weather_risk_score
       LOW < 0.40, MEDIUM 0.40 - 0.70, HIGH > 0.70
       
    4. LLM Enrichment (Claude API):
       Rephrases verified database facts + live weather into farmer-friendly advice.
       Strict anti-hallucination prompt.
       If LLM fails, falls back safely to raw database text.
    """
    # -------------------------------------------------------------------------
    # Step A: Query Database for Disease Record
    # -------------------------------------------------------------------------
    disease_record = find_advisory(db, req.crop, req.disease_name)
    if not disease_record:
        # Create a safe fallback record so system never halts unexpectedly
        disease_record = DiseaseAdvisory(
            crop=req.crop,
            disease_name=req.disease_name,
            pathogen_type="Suspected Pathogen",
            symptoms=f"Suspected symptoms observed for {req.disease_name} on {req.crop}.",
            favorable_conditions="High relative humidity and warm temperatures.",
            low_risk_advisory=f"Maintain regular field monitoring for {req.crop}.",
            medium_risk_advisory=f"Inspect leaves and stems for early signs of {req.disease_name}.",
            high_risk_advisory=f"High risk of {req.disease_name} spreading. Isolate affected plants and consult agricultural officer.",
            expert_advisory="Contact nearest Krishi Vigyan Kendra (KVK) or extension officer.",
            preventive_measures="Ensure proper spacing, sanitation, and avoid excessive overhead irrigation.",
            organic_treatment="Neem oil spray or bio-fungicide formulations.",
            chemical_treatment="Consult local extension manual for approved fungicides/bactericides."
        )

    # -------------------------------------------------------------------------
    # Step B: Call Weather Service (with Try/Except and 0.5 Neutral Fallback)
    # -------------------------------------------------------------------------
    try:
        snapshots, weather_summary, weather_risk_score = fetch_weather_snapshots(
            lat=req.latitude,
            lon=req.longitude,
            favorable_conditions=disease_record.favorable_conditions or ""
        )
    except Exception as weather_err:
        print(f"[AdvisoryFlow] Weather service error: {weather_err}")
        # Error handling requirement: Neutral score 0.5 and explicit note
        weather_risk_score = 0.5
        weather_summary = WeatherSummary(
            location=f"Lat {req.latitude:.2f}°, Lon {req.longitude:.2f}°",
            current_temp_c=25.0,
            current_humidity_pct=60.0,
            avg_humidity_pct=60.0,
            max_humidity_pct=70.0,
            total_rain_mm=0.0,
            sustained_high_humidity_days=0,
            forecast_trend="Weather data service currently unreachable.",
            is_live_data=False,
            data_source_note="Weather API unavailable; evaluated with neutral baseline risk (0.50).",
            snapshots=[]
        )

    # -------------------------------------------------------------------------
    # Step C: Compute Composite Risk (CV: 60%, Weather: 40%)
    # -------------------------------------------------------------------------
    final_risk_score, risk_level = compute_final_risk(
        cv_confidence=req.cv_confidence,
        weather_risk_score=weather_risk_score
    )

    # Pick specific advisory for calculated level
    if risk_level == "HIGH":
        level_specific_text = disease_record.high_risk_advisory or ""
    elif risk_level == "MEDIUM":
        level_specific_text = disease_record.medium_risk_advisory or ""
    else:
        level_specific_text = disease_record.low_risk_advisory or ""

    # Structure raw database output
    raw_db_advisory = RawDatabaseAdvisory(
        crop=disease_record.crop,
        disease_name=disease_record.disease_name,
        pathogen_type=disease_record.pathogen_type,
        symptoms=disease_record.symptoms,
        favorable_conditions=disease_record.favorable_conditions,
        advisory_for_level=level_specific_text,
        low_risk_advisory=disease_record.low_risk_advisory,
        medium_risk_advisory=disease_record.medium_risk_advisory,
        high_risk_advisory=disease_record.high_risk_advisory,
        expert_advisory=disease_record.expert_advisory,
        preventive_measures=disease_record.preventive_measures,
        organic_treatment=disease_record.organic_treatment,
        chemical_treatment=disease_record.chemical_treatment
    )

    # -------------------------------------------------------------------------
    # Step D: Call LLM Advisory Service (Claude API with Graceful Fallback)
    # -------------------------------------------------------------------------
    try:
        farmer_explanation, llm_status = enrich_advisory_with_llm(
            disease=disease_record,
            risk_level=risk_level,
            final_risk_score=final_risk_score,
            weather=weather_summary
        )
    except Exception as llm_err:
        print(f"[AdvisoryFlow] LLM enrichment error: {llm_err}")
        farmer_explanation = (
            f"Advisory for {disease_record.crop} - {disease_record.disease_name} (Risk: {risk_level}).\n"
            f"{level_specific_text}\n"
            f"Preventive Measures: {disease_record.preventive_measures}\n"
            f"Treatments: Organic: {disease_record.organic_treatment} | Chemical: {disease_record.chemical_treatment}"
        )
        llm_status = f"fallback_raw_data: {str(llm_err)}"

    # -------------------------------------------------------------------------
    # Step E: Return Complete Pydantic Model
    # -------------------------------------------------------------------------
    return AdvisoryResponse(
        crop=disease_record.crop,
        disease_name=disease_record.disease_name,
        cv_confidence=req.cv_confidence,
        weather_risk_score=weather_risk_score,
        final_risk_score=final_risk_score,
        risk_level=risk_level,
        weather_summary=weather_summary,
        raw_database_advisory=raw_db_advisory,
        farmer_friendly_explanation=farmer_explanation,
        llm_generation_status=llm_status,
        created_at=datetime.now(timezone.utc).isoformat()
    )
