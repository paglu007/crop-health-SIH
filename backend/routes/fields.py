from flask import Blueprint, request, jsonify

from backend.database import db
from backend.models import Field

fields_bp = Blueprint("fields", __name__, url_prefix="/api/fields")


@fields_bp.route("", methods=["POST"])
def create_field():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    name = data.get("name")
    crop_name = data.get("crop_name")

    if not name or not crop_name:
        return jsonify({
            "success": False,
            "message": "name and crop_name are required"
        }), 400

    field = Field(
        name=name,
        crop_name=crop_name,
        growth_stage=data.get("growth_stage"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude")
    )

    db.session.add(field)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Field created successfully",
        "field": {
            "id": field.id,
            "name": field.name,
            "crop_name": field.crop_name,
            "growth_stage": field.growth_stage,
            "latitude": field.latitude,
            "longitude": field.longitude,
            "created_at": field.created_at.isoformat()
        }
    }), 201


@fields_bp.route("", methods=["GET"])
def get_all_fields():
    return {
        "status": "success",
        "fields": [
            {
                "id": 1,
                "name": "Wheat Plot A",
                "area_acres": 2.4,
                "crop_type": "Wheat",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "zone": "Western Plateau & Hills (Zone IX)",
                "soil_type": "Medium Black"
            }
        ]
    }

    return jsonify({
        "success": True,
        "field": {
            "id": field.id,
            "name": field.name,
            "crop_name": field.crop_name,
            "growth_stage": field.growth_stage,
            "latitude": field.latitude,
            "longitude": field.longitude,
            "created_at": field.created_at.isoformat()
        }
    }), 200
