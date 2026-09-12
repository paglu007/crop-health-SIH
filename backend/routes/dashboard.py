from flask import Blueprint
from backend.models import Field, Observation, Prediction
from backend.database import db

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
    latest_prediction = Prediction.query.order_by(
    Prediction.created_at.desc()
).first()

    field_summaries = []

    for field in Field.query.all():
     observation_count = Observation.query.filter_by(
        field_id=field.id
    ).count()

    field_summaries.append({
        "id": field.id,
        "name": field.name,
        "crop_name": field.crop_name,
        "observation_count": observation_count
    })
    return {
        "latest_prediction": {
    "id": latest_prediction.id,
    "label": latest_prediction.label,
    "score": latest_prediction.score,
    "prediction_type": latest_prediction.prediction_type
} if latest_prediction else None,
    "fields": field_summaries,
    "total_fields": total_fields,
    "total_observations": total_observations,
    "total_predictions": total_predictions,
    "risk_counts": risk_counts
    
    
}
