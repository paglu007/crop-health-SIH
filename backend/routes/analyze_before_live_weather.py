from flask import Blueprint, request

from werkzeug.utils import secure_filename

from pathlib import Path

import uuid

from backend.services.advisory import generate_advisory
from backend.services.ai_model import rice_disease_model
from backend.services.risk_engine import risk_engine
from backend.models import Prediction


analyze_bp = Blueprint("analyze", __name__)


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DISEASE -> PATHOGEN TYPE
# ============================================================

def _get_pathogen_type(disease: str) -> str:
    """
    Maps EfficientNet disease classes to the pathogen categories
    expected by the existing risk engine.
    """

    disease_lower = disease.strip().lower()

    if disease_lower == "healthy rice leaf":
        return "Healthy"

    if disease_lower in {
        "bacterial leaf blight"
    }:
        return "Bacterial"

    if disease_lower in {
        "brown spot",
        "leaf blast",
        "leaf scald",
        "sheath blight"
    }:
        return "Fungal"

    return "Fungal"


# ============================================================
# WEATHER NORMALIZATION
# ============================================================

def _normalize_weather(weather: dict) -> dict:
    """
    Normalizes optional weather data into the exact fields
    expected by the existing risk engine.
    """

    return {
        "temp_c": float(weather.get("temp_c", 25.0)),
        "humidity_pct": float(weather.get("humidity_pct", 70.0)),
        "rainfall_mm": float(weather.get("rainfall_mm", 0.0)),
        "wind_speed_kph": float(weather.get("wind_speed_kph", 0.0)),
    }


# ============================================================
# SEVERITY PROXY
# ============================================================

def _severity_proxy_from_confidence(confidence: float) -> float:
    """
    The EfficientNet model does not measure lesion severity.

    Therefore this is only a provisional proxy used to satisfy
    the current risk-engine interface.

    It MUST NOT be interpreted as actual lesion-area measurement.
    """

    return round(
        min(max(float(confidence), 5.0), 95.0),
        1
    )


# ============================================================
# AI + RISK + ADVISORY PIPELINE
# ============================================================

def _run_diagnosis_pipeline(image_path: str, weather: dict | None = None):
    """
    Runs:

        EfficientNet diagnosis
        ->
        existing risk engine
        ->
        structured advisory knowledge base
    """

    diagnosis = rice_disease_model.predict(image_path)

    disease = diagnosis["disease"]
    confidence = float(diagnosis["confidence"])

    pathogen_type = _get_pathogen_type(disease)

    normalized_weather = _normalize_weather(
        weather or {}
    )

    severity_pct = _severity_proxy_from_confidence(
        confidence
    )

    risk = risk_engine.calculate_risk(
        pathogen_type=pathogen_type,
        severity_pct=severity_pct,
        temp_c=normalized_weather["temp_c"],
        humidity_pct=normalized_weather["humidity_pct"],
        rainfall_mm=normalized_weather["rainfall_mm"],
        wind_speed_kph=normalized_weather["wind_speed_kph"],
    )

    advisory = generate_advisory(
        crop="Rice",
        disease=disease,
        confidence=confidence,
        risk_level=risk["risk_level"],
        risk_score=risk["risk_score"],
        weather=normalized_weather,
    )

    return {
        "diagnosis": diagnosis,

        "risk": {
            **risk,

            "pathogen_type": pathogen_type,

            "severity_pct": severity_pct,

            "severity_source": "confidence_proxy",

            "severity_note": (
                "Severity is not directly measured by the current "
                "image model. The value shown is a provisional "
                "confidence-based proxy for the risk engine."
            )
        },

        "advisory": advisory
    }


# ============================================================
# AI PREDICTION
# ============================================================

@analyze_bp.route(
    "/predict",
    methods=["POST"]
)
def predict_disease():

    if "image" not in request.files:
        return {
            "error": "No image uploaded. Use field name 'image'."
        }, 400

    image = request.files["image"]

    if image.filename == "":
        return {
            "error": "No image selected."
        }, 400

    original_name = secure_filename(
        image.filename
    )

    extension = Path(
        original_name
    ).suffix.lower()

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    if extension not in allowed_extensions:
        return {
            "error": "Unsupported image format."
        }, 400

    filename = f"{uuid.uuid4()}{extension}"

    image_path = UPLOAD_DIR / filename

    image.save(
        str(image_path)
    )

    try:

        weather = request.form.get(
            "weather"
        )

        if weather:
            import json
            weather = json.loads(weather)
        else:
            weather = {}

        pipeline = _run_diagnosis_pipeline(
            str(image_path),
            weather=weather
        )

        return {
            "success": True,

            "prediction": pipeline["diagnosis"],

            "risk": pipeline["risk"],

            "advisory": pipeline["advisory"]
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }, 500


# ============================================================
# ADVISORY
# ============================================================

@analyze_bp.route(
    "/advisory",
    methods=["POST"]
)
def get_advisory():

    data = request.get_json()

    if not data:
        return {
            "error": "JSON data is required"
        }, 400

    crop = data.get("crop")

    disease = data.get("disease")

    confidence = data.get("confidence")

    risk_level = data.get("risk_level")

    risk_score = data.get("risk_score")

    weather = data.get("weather") or {}

    if not crop:
        return {
            "error": "crop is required"
        }, 400

    if not disease:
        return {
            "error": "disease is required"
        }, 400

    if confidence is None:
        return {
            "error": "confidence is required"
        }, 400

    if not risk_level:
        return {
            "error": "risk_level is required from the risk engine"
        }, 400

    try:

        confidence = float(
            confidence
        )

    except (TypeError, ValueError):

        return {
            "error": "confidence must be a number"
        }, 400

    try:

        advisory = generate_advisory(
            crop=crop,
            disease=disease,
            confidence=confidence,
            risk_level=str(
                risk_level
            ).upper(),
            risk_score=risk_score,
            weather=weather,
        )

        return {
            "success": True,
            "advisory": advisory
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }, 500


# ============================================================
# PREDICTION ADVISORY
# ============================================================

@analyze_bp.route(
    "/prediction/<int:prediction_id>/advisory",
    methods=["GET"]
)
def get_prediction_advisory(prediction_id):

    prediction = Prediction.query.get(
        prediction_id
    )

    if not prediction:

        return {
            "error": "Prediction not found"
        }, 404

    return {

        "success": True,

        "prediction": {

            "id": prediction.id,

            "prediction_type":
                prediction.prediction_type,

            "disease":
                prediction.label,

            "confidence":
                prediction.confidence,

            "score":
                prediction.score,

            "model_name":
                prediction.model_name,

            "model_version":
                prediction.model_version,
        },

        "message": (
            "Risk-engine output is required before generating "
            "the final advisory."
        )

    }, 400
