from flask import Blueprint, request, jsonify

from backend.database import db
from backend.models import Observation, Prediction, Field
from backend.services.risk_engine import risk_engine
from backend.services.weather import get_current_weather

# ADD THIS BACK:
risk_bp = Blueprint(
    "risk",
    __name__,
    url_prefix="/api/risk"
)

# ... your get_observation_predictions route ...
# ... your calculate_risk route ...
# ... (keep get_observation_predictions exactly as it is) ...

@risk_bp.route("/calculate", methods=["POST"])
def calculate_risk():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request body is required"}), 400

    # Only observation_id, pathogen_type, and severity_pct are strictly required now
    required_fields = ["observation_id", "pathogen_type", "severity_pct"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"{field} is required"}), 400
            
    observation = db.session.get(Observation, data["observation_id"])
    if not observation:
        return jsonify({"success": False, "message": "Observation not found"}), 404

    # Extract weather from request, OR fallback to live weather API
    temp_c = data.get("temp_c")
    humidity_pct = data.get("humidity_pct")
    rainfall_mm = data.get("rainfall_mm")
    wind_speed_kph = data.get("wind_speed_kph")

    # If ANY weather data is missing, fetch it live
    if None in [temp_c, humidity_pct, rainfall_mm, wind_speed_kph]:
        field = db.session.get(Field, observation.field_id)
        if not field or field.latitude is None or field.longitude is None:
            return jsonify({"success": False, "message": "Weather data missing and Field coordinates unavailable"}), 400
            
        live_weather = get_current_weather(field.latitude, field.longitude)
        if not live_weather:
            return jsonify({"success": False, "message": "Failed to fetch live weather data"}), 502
            
        # Use live data if request data was missing
        temp_c = temp_c if temp_c is not None else live_weather["temp_c"]
        humidity_pct = humidity_pct if humidity_pct is not None else live_weather["humidity_pct"]
        rainfall_mm = rainfall_mm if rainfall_mm is not None else live_weather["rainfall_mm"]
        wind_speed_kph = wind_speed_kph if wind_speed_kph is not None else live_weather["wind_speed_kph"]

    # Calculate Risk
    result = risk_engine.calculate_risk(
        data["pathogen_type"],
        data["severity_pct"],
        temp_c,
        humidity_pct,
        rainfall_mm,
        wind_speed_kph
    )
    
    prediction = Prediction(
        observation_id=observation.id,
        prediction_type="disease_risk",
        label=result["risk_level"],
        score=result["risk_score"],
        model_name="CropRiskEngine",
        model_version="v1"
    )

    db.session.add(prediction)
    db.session.commit()

    return jsonify({
        "success": True,
        "risk": result,
        "prediction_id": prediction.id,
        "weather_used": {
            "temp_c": temp_c,
            "humidity_pct": humidity_pct,
            "rainfall_mm": rainfall_mm,
            "wind_speed_kph": wind_speed_kph
        }
    }), 200
