# 🌾 Crop Disease Risk Advisory System (SIH 2026)

Advanced backend built with **Python (Flask)**, combining:
1. **Computer Vision Model Confidence** ($cv\_confidence$)
2. **Real-time & Historical Weather Risk Service** (OpenWeather API with sustained humidity pattern matching and caching)
3. **Verified Disease Knowledge Base** (SQLite / SQLAlchemy loaded from `plant_disease_advisory_dataset.csv`)
4. **Farmer-Friendly LLM Advisory Enrichment** (Anthropic Claude 3.5 Sonnet with strict anti-hallucination constraints)

---

## 🏗️ Architecture & Flow Overview

```
[Client / Drone / App]
       │
       ▼ POST /api/advisory/advanced { crop, disease_name, cv_confidence, lat, lon }
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Weather Service (OpenWeather Forecast + Timemachine)               │
│    - Checks local memory cache (TTL: 2 hours)                         │
│    - Computes weather_risk_score (0.0 to 1.0) using sustained         │
│      humidity (RH > 80%), temperature match, and rainfall             │
│    - Fallback: neutral 0.50 risk if API is unreachable                │
└────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Risk Calculation Engine                                             │
│    - final_risk = (0.6 * cv_confidence) + (0.4 * weather_risk_score)   │
│    - Categorization:                                                  │
│        * LOW:    final_risk < 0.40                                     │
│        * MEDIUM: 0.40 <= final_risk <= 0.70                           │
│        * HIGH:   final_risk > 0.70                                     │
└────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. Database Lookup (SQLAlchemy / SQLite)                               │
│    - Queries DiseaseAdvisory model by crop + disease_name             │
│    - Retrieves verified symptoms, favorable conditions,               │
│      organic treatment, chemical treatment, and preventive measures    │
└────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. LLM Enrichment Service (Anthropic Claude API)                       │
│    - Translates verified database facts into warm, farmer-friendly    │
│      vernacular explanation                                            │
│    - STRICT SYSTEM PROMPT: Never invents new treatments, dosages, or  │
│      unverified chemicals. Strictly explains provided facts.          │
│    - Fallback: returns formatted raw database text if API fails       │
└────────────────────────────────────────────────────────────────────────┘
       │
       ▼
[Response JSON: risk_level, final_risk_score, weather_summary, raw_database_advisory, farmer_friendly_explanation]
```

---

## 📁 Project Structure

```
crop_advisory_backend/
├── app/
│   ├── __init__.py               # Flask app factory, CORS, database auto-seeding
│   ├── config.py                 # python-dotenv configuration and env loaders
│   ├── models.py                 # SQLAlchemy ORM and Pydantic request/response schemas
│   ├── database.py               # SQLite/PostgreSQL engine, sessionmaker, CSV seeder
│   ├── weather_service.py        # OpenWeather API integration, microclimate risk, caching
│   ├── llm_advisory_service.py   # Anthropic Claude client with strict anti-hallucination prompt
│   ├── risk.py                   # 60/40 composite risk calculation & LOW/MED/HIGH logic
│   ├── advisory.py               # Pipeline orchestrator combining all steps with error handling
│   └── routes.py                 # Flask endpoints (POST /api/advisory/advanced, etc.)
├── data/
│   └── plant_disease_advisory_dataset.csv  # 143 verified crop disease records
├── crop_disease.db               # Populated SQLite database
├── main.py                       # Application execution entry point
├── requirements.txt              # Production pip dependencies
├── .env.example                  # Environment variable reference
└── README.md                     # System documentation
```

---

## 🚀 Quickstart Guide

### 1. Clone or Extract the Project
```bash
unzip crop_disease_advisory_sih2026.zip
cd crop_advisory_backend
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and add your API keys:
```env
OPENWEATHER_API_KEY="your_openweather_api_key_here"
ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

### 4. Run the Flask Server
```bash
python main.py
```
The server will start at `http://localhost:5000`.

---

## 📡 API Reference

### POST `/api/advisory/advanced`
Computes the full integrated advisory flow.

#### Request Body:
```json
{
  "crop": "Tomato",
  "disease_name": "Early Blight",
  "cv_confidence": 0.82,
  "latitude": 22.57,
  "longitude": 88.36
}
```

#### Example Response:
```json
{
  "crop": "Tomato",
  "disease_name": "Early Blight",
  "cv_confidence": 0.82,
  "weather_risk_score": 0.845,
  "final_risk_score": 0.83,
  "risk_level": "HIGH",
  "weather_summary": {
    "location": "Lat 22.57°, Lon 88.36°",
    "current_temp_c": 27.5,
    "current_humidity_pct": 84.0,
    "avg_humidity_pct": 82.5,
    "max_humidity_pct": 91.0,
    "total_rain_mm": 14.2,
    "sustained_high_humidity_days": 4,
    "forecast_trend": "High sustained moisture (>75% RH) conducive to fungal/bacterial spread",
    "is_live_data": true,
    "data_source_note": "OpenWeather API Verified"
  },
  "raw_database_advisory": {
    "crop": "Tomato",
    "disease_name": "Early Blight",
    "pathogen_type": "fungal_blight",
    "symptoms": "Concentric dark spots with yellow halo on lower leaves",
    "favorable_conditions": "Warm humid weather 24-29C, extended leaf wetness",
    "advisory_for_level": "Conditions are strongly favorable for rapid spread of Early Blight in Tomato...",
    "preventive_measures": "Use certified disease-free planting material, maintain field sanitation...",
    "organic_treatment": "Neem-based sprays, Trichoderma-based bio-fungicides...",
    "chemical_treatment": "A recommended contact or systemic fungicide applied at first sign of symptoms...",
    "expert_advisory": "Persistent or worsening Early Blight symptoms should be reported..."
  },
  "farmer_friendly_explanation": "Namaste Farmer! In your field right now, the humidity has stayed high (above 82%) for 4 consecutive days with warm temperatures around 27°C. These exact conditions create high risk for Early Blight to spread rapidly...",
  "llm_generation_status": "success",
  "created_at": "2026-09-12T12:00:00Z"
}
```

---

## 🛡️ Error Handling Guarantees
- **Weather API Down**: If OpenWeather is unreachable or rate-limited, the system falls back to a neutral `0.50` risk score and flags `data_source_note`.
- **LLM API Down**: If Claude API encounters an outage, the system gracefully generates a clear, deterministic explanation directly from the verified database fields so farmer advisories never fail.
