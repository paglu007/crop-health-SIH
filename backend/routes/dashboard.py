from flask import Blueprint
from models import Field, Observation, Prediction

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def get_dashboard():
    total_fields = Field.query.count()
    total_observations = Observation.query.count()
    total_predictions = Prediction.query.count()
    risk_counts = {
    "HIGH": Prediction.query.filter_by(label="HIGH").count(),
    "MEDIUM": Prediction.query.filter_by(label="MEDIUM").count(),
    "LOW": Prediction.query.filter_by(label="LOW").count()
}

    return {
    "total_fields": total_fields,
    "total_observations": total_observations,
    "total_predictions": total_predictions,
    "risk_counts": risk_counts
}