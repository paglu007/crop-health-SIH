from flask import Blueprint, request
from services.advisory import generate_advisory

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/advisory", methods=["POST"])
def get_advisory():
    data = request.get_json()

    risk_level = data.get("risk_level")

    if not risk_level:
        return {"error": "risk_level is required"}, 400

    advisory = generate_advisory(risk_level.upper())

    return advisory