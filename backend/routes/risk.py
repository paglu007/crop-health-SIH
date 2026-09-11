from flask import Blueprint, request, jsonify

from database import db
from models import Observation, Prediction

from services.risk_engine import risk_engine

risk_bp = Blueprint(
    "risk",
    __name__,
    url_prefix="/api/risk"
)


@risk_bp.route("/calculate", methods=["POST"])
@risk_bp.route("/observation/<int:observation_id>", methods=["GET"])
def get_observation_predictions(observation_id):
    predictions = Prediction.query.filter_by(
        observation_id=observation_id
    ).all()

    return jsonify({
        "success": True,
        "predictions": [
            {
                "id": p.id,
                "prediction_type": p.prediction_type,
                "label": p.label,
                "score": p.score,
                "model_name": p.model_name,
                "model_version": p.model_version,
                "created_at": p.created_at.isoformat()
            }
            for p in predictions
        ]
    }), 200
def calculate_risk():
    

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    required_fields = [
    "observation_id",
    "pathogen_type",
    "severity_pct",
    "temp_c",
    "humidity_pct",
    "rainfall_mm",
    "wind_speed_kph"
]

    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"{field} is required"
            }), 400
    observation = db.session.get(Observation, data["observation_id"])

    if not observation:
        return jsonify({
            "success": False,
            "message": "Observation not found"
        }), 404
    
    result = risk_engine.calculate_risk(
        data["pathogen_type"],
        data["severity_pct"],
        data["temp_c"],
        data["humidity_pct"],
        data["rainfall_mm"],
        data["wind_speed_kph"]
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
    "prediction_id": prediction.id
}), 200