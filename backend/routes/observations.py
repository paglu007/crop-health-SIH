from flask import Blueprint, request, jsonify
import os
import uuid
from backend.database import db
from backend.models import Field, Observation

observations_bp = Blueprint(
    "observations",
    __name__,
    url_prefix="/api/observations"
)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
@observations_bp.route("", methods=["POST"])
def create_observation():
    data = request.form
    image = request.files.get("image")

    if not image:
        return jsonify({
        "success": False,
        "message": "Image file is required"
    }), 400

    if not allowed_file(image.filename):
        return jsonify({
        "success": False,
        "message": "Only PNG, JPG, and JPEG images are allowed"
    }), 400
    extension = image.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4()}.{extension}"
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    image.save(image_path)
    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    field_id = data.get("field_id")

    if not field_id:
        return jsonify({
            "success": False,
            "message": "field_id is required"
        }), 400

    field = db.session.get(Field, field_id)

    if not field:
        return jsonify({
            "success": False,
            "message": "Field not found"
        }), 404

    observation = Observation(
    field_id=field_id,
    farmer_observation=data.get("farmer_observation"),
    image_path=image_path
)

    db.session.add(observation)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Observation created successfully",
        "observation": {
            "id": observation.id,
            "field_id": observation.field_id,
            "farmer_observation": observation.farmer_observation,
            "image_path": observation.image_path,
            "created_at": observation.created_at.isoformat()
        }
    }), 201
