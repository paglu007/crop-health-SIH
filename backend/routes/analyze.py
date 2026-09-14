from flask import Blueprint, request
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid

from backend.services.advisory import generate_advisory
from backend.services.ai_model import rice_disease_model
from backend.models import Prediction


analyze_bp = Blueprint("analyze", __name__)


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# AI PREDICTION
# ============================================================

@analyze_bp.route("/predict", methods=["POST"])
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

    original_name = secure_filename(image.filename)

    extension = Path(original_name).suffix.lower()

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

    image.save(str(image_path))

    try:
        result = rice_disease_model.predict(str(image_path))

        return {
            "success": True,
            "prediction": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500


# ============================================================
# ADVISORY
# ============================================================

@analyze_bp.route("/advisory", methods=["POST"])
def get_advisory():

    data = request.get_json()

    if not data:
        return {
            "error": "JSON data is required"
        }, 400

    risk_level = data.get("risk_level")

    if not risk_level:
        return {
            "error": "risk_level is required"
        }, 400

    try:
        advisory = generate_advisory(
            risk_level.upper()
        )

    except ValueError as e:
        return {
            "error": str(e)
        }, 400

    return advisory


# ============================================================
# PREDICTION ADVISORY
# ============================================================

@analyze_bp.route(
    "/prediction/<int:prediction_id>/advisory",
    methods=["GET"]
)
def get_prediction_advisory(prediction_id):

    prediction = Prediction.query.get(prediction_id)

    if not prediction:
        return {
            "error": "Prediction not found"
        }, 404

    return generate_advisory(
        prediction.label
    )