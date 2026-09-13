"""
Configuration Module for Crop Disease Risk Advisory System (SIH 2026).
Loads environment variables using python-dotenv with safe fallbacks.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "sih2026-crop-advisory-secret-key")
    
    # API Keys (Never hardcoded)
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Database
    DATABASE_PATH = BASE_DIR / "crop_disease.db"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
    )
    
    # Weather cache TTL in seconds (1 to 3 hours, default 2 hours = 7200s)
    WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "7200"))
    
    # OpenWeather Endpoints
    OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
    OPENWEATHER_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
    OPENWEATHER_TIMEMACHINE_URL = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"

    # Claude LLM Model
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
