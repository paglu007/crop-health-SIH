from flask import Blueprint, request, jsonify
from backend.database import db
from backend.models import Observation, Prediction, Field
from backend.services.risk_engine import risk_engine
from backend.services.weather import get_current_weather
from backend.services.advisory import generate_advisory  # <-- NEW IMPORT

risk_bp = Blueprint("risk", __name__, url_prefix="/api/risk")

# ... (keep get_observation_predictions exactly as it is) ...

@risk_bp.route("/calculate", methods=["POST"])
def calculate_risk():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Request body is required"}), 400

    required_fields = ["observation_id", "pathogen_type", "severity_pct"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"{field} is required"}), 400
            
    observation = db.session.get(Observation, data["observation_id"])
    if not observation:
        return jsonify({"success": False, "message": "Observation not found"}), 404

    # We need the Field to get the crop name and coordinates
    field = db.session.get(Field, observation.field_id)
    if not field:
        return jsonify({"success": False, "message": "Associated field not found"}), 404

    temp_c = data.get("temp_c")
    humidity_pct = data.get("humidity_pct")
    rainfall_mm = data.get("rainfall_mm")
    wind_speed_kph = data.get("wind_speed_kph")

    if None in [temp_c, humidity_pct, rainfall_mm, wind_speed_kph]:
        if field.latitude is None or field.longitude is None:
            return jsonify({"success": False, "message": "Weather data missing and Field coordinates unavailable"}), 400
            
        live_weather = get_current_weather(field.latitude, field.longitude)
        if not live_weather:
            return jsonify({"success": False, "message": "Failed to fetch live weather data"}), 502
            
        temp_c = temp_c if temp_c is not None else live_weather["temp_c"]
        humidity_pct = humidity_pct if humidity_pct is not None else live_weather["humidity_pct"]
        rainfall_mm = rainfall_mm if rainfall_mm is not None else live_weather["rainfall_mm"]
        wind_speed_kph = wind_speed_kph if wind_speed_kph is not None else live_weather["wind_speed_kph"]

    # 1. Calculate Risk
    result = risk_engine.calculate_risk(
        data["pathogen_type"],
        data["severity_pct"],
        temp_c,
        humidity_pct,
        rainfall_mm,
        wind_speed_kph
    )
    
    # 2. Save Prediction to DB
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

    weather_used = {
        "temp_c": temp_c,
        "humidity_pct": humidity_pct,
        "rainfall_mm": rainfall_mm,
        "wind_speed_kph": wind_speed_kph
    }

    # 3. Generate Advisory
    advisory = generate_advisory(
        crop=field.crop_name,
        growth_stage=field.growth_stage or "Vegetative",
        issue=data["pathogen_type"],
        severity=data["severity_pct"],
        weather=weather_used,
        risk_level=result["risk_level"]
    )

    # 4. Return everything to the frontend
    return jsonify({
        "success": True,
        "risk": result,
        "advisory": advisory,
        "prediction_id": prediction.id,
        "weather_used": weather_used
    }), 200
