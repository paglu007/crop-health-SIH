from flask import Blueprint, request
from backend.services.advisory import generate_advisory
from backend.models import Prediction

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/advisory", methods=["POST"])
def get_advisory():
    data = request.get_json()

    risk_level = data.get("risk_level")

    if not risk_level:
        return {"error": "risk_level is required"}, 400

    try:
        advisory = generate_advisory(risk_level.upper())
    except ValueError as e:
        return {"error": str(e)}, 400

    return advisory
@analyze_bp.route("/prediction/<int:prediction_id>/advisory", methods=["GET"])
def get_prediction_advisory(prediction_id):
    prediction = Prediction.query.get(prediction_id)

    if not prediction:
        return {"error": "Prediction not found"}, 404

    return generate_advisory(prediction.label)
