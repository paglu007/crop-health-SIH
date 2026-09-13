"""
Models and Schemas for Crop Disease Risk Advisory System.
Contains:
1. SQLAlchemy DiseaseAdvisory model (database persistence)
2. Pydantic schemas for request/response serialization and validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ============================================================================
# SQLAlchemy ORM Models
# ============================================================================

class DiseaseAdvisory(Base):
    """
    SQLAlchemy model representing the verified disease advisory records
    loaded from plant_disease_advisory_dataset.csv.
    """
    __tablename__ = "disease_advisories"

    disease_id = Column(Integer, primary_key=True, autoincrement=True)
    crop = Column(String(100), nullable=False, index=True)
    disease_name = Column(String(150), nullable=False, index=True)
    pathogen_type = Column(String(100), nullable=True)
    symptoms = Column(Text, nullable=True)
    favorable_conditions = Column(Text, nullable=True)
    low_risk_advisory = Column(Text, nullable=True)
    medium_risk_advisory = Column(Text, nullable=True)
    high_risk_advisory = Column(Text, nullable=True)
    expert_advisory = Column(Text, nullable=True)
    preventive_measures = Column(Text, nullable=True)
    organic_treatment = Column(Text, nullable=True)
    chemical_treatment = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM instance to dictionary."""
        return {
            "disease_id": self.disease_id,
            "crop": self.crop,
            "disease_name": self.disease_name,
            "pathogen_type": self.pathogen_type,
            "symptoms": self.symptoms,
            "favorable_conditions": self.favorable_conditions,
            "low_risk_advisory": self.low_risk_advisory,
            "medium_risk_advisory": self.medium_risk_advisory,
            "high_risk_advisory": self.high_risk_advisory,
            "expert_advisory": self.expert_advisory,
            "preventive_measures": self.preventive_measures,
            "organic_treatment": self.organic_treatment,
            "chemical_treatment": self.chemical_treatment,
        }


# ============================================================================
# Pydantic Validation Schemas
# ============================================================================

class WeatherSnapshot(BaseModel):
    """
    Standardized snapshot of weather for a specific timestamp/day.
    Parsed from OpenWeather forecast or historical endpoints.
    """
    date: str = Field(description="ISO Date string or formatted day (e.g. 2026-09-12 or 2026-09-12 12:00)")
    humidity: float = Field(description="Relative humidity in percentage (0-100)")
    temperature: float = Field(description="Temperature in Celsius")
    rainfall: float = Field(default=0.0, description="Precipitation / rain volume in mm")
    wind_speed: float = Field(default=0.0, description="Wind speed in m/s")
    description: Optional[str] = Field(default="", description="Weather condition description")


class WeatherSummary(BaseModel):
    """Aggregated summary of live & forecast weather conditions."""
    location: str = Field(default="Lat/Lon Coordinates")
    current_temp_c: float
    current_humidity_pct: float
    avg_humidity_pct: float
    max_humidity_pct: float
    total_rain_mm: float
    sustained_high_humidity_days: int
    forecast_trend: str
    is_live_data: bool
    data_source_note: Optional[str] = None
    snapshots: List[WeatherSnapshot] = Field(default_factory=list)


class AdvisoryRequest(BaseModel):
    """Request payload for POST /api/advisory/advanced."""
    crop: str = Field(..., min_length=2, example="Tomato")
    disease_name: str = Field(..., min_length=2, example="Early Blight")
    cv_confidence: float = Field(..., ge=0.0, le=1.0, example=0.82)
    latitude: float = Field(..., ge=-90.0, le=90.0, example=22.57)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=88.36)


class RawDatabaseAdvisory(BaseModel):
    """The verified raw database fields matching the disease record."""
    crop: str
    disease_name: str
    pathogen_type: Optional[str] = None
    symptoms: Optional[str] = None
    favorable_conditions: Optional[str] = None
    advisory_for_level: str
    low_risk_advisory: Optional[str] = None
    medium_risk_advisory: Optional[str] = None
    high_risk_advisory: Optional[str] = None
    expert_advisory: Optional[str] = None
    preventive_measures: Optional[str] = None
    organic_treatment: Optional[str] = None
    chemical_treatment: Optional[str] = None


class AdvisoryResponse(BaseModel):
    """
    Combined response for the advanced crop disease risk advisory system.
    Provides both verified raw database facts and LLM-enriched natural language.
    """
    crop: str
    disease_name: str
    cv_confidence: float
    weather_risk_score: float
    final_risk_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    weather_summary: WeatherSummary
    raw_database_advisory: RawDatabaseAdvisory
    farmer_friendly_explanation: str
    llm_generation_status: str  # "success" or "fallback_raw_data"
    created_at: str
