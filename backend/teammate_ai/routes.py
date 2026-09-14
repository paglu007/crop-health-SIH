"""
Flask Routes and Endpoints for Crop Disease Risk Advisory.
Defines POST /api/advisory/advanced and auxiliary lookup/inspection endpoints.
"""

from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from pydantic import ValidationError

from backend.teammate_ai.database import SessionLocal, find_advisory
from backend.teammate_ai.models import AdvisoryRequest, DiseaseAdvisory
from backend.teammate_ai.advisory import generate_advanced_advisory

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    """Health status and database connectivity check."""
    session = SessionLocal()
    try:
        count = session.query(DiseaseAdvisory).count()
        return jsonify({
            "status": "healthy",
            "service": "Crop Disease Risk Advisory (SIH 2026)",
            "database_records_loaded": count,
            "framework": "Flask 3.x"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        session.close()


@bp.route("/crops", methods=["GET"])
def get_crops():
    """Returns unique list of crops available in the verified database."""
    session = SessionLocal()
    try:
        records = session.query(DiseaseAdvisory.crop).distinct().order_by(DiseaseAdvisory.crop).all()
        crops = [r[0] for r in records if r[0]]
        return jsonify({"crops": crops, "total": len(crops)}), 200
    finally:
        session.close()


@bp.route("/diseases", methods=["GET"])
def get_diseases():
    """Returns diseases matching a given crop query param."""
    crop_name = request.args.get("crop", "").strip()
    session = SessionLocal()
    try:
        query = session.query(DiseaseAdvisory)
        if crop_name:
            query = query.filter(DiseaseAdvisory.crop.ilike(crop_name))
        records = query.order_by(DiseaseAdvisory.disease_name).all()
        return jsonify({
            "crop": crop_name,
            "diseases": [
                {
                    "disease_id": r.disease_id,
                    "crop": r.crop,
                    "disease_name": r.disease_name,
                    "pathogen_type": r.pathogen_type,
                    "favorable_conditions": r.favorable_conditions
                }
                for r in records
            ],
            "total": len(records)
        }), 200
    finally:
        session.close()


@bp.route("/advisory/advanced", methods=["POST"])
def post_advanced_advisory():
    """
    Main advanced pipeline endpoint.
    
    Expected JSON Body:
    {
        "crop": "Tomato",
        "disease_name": "Early Blight",
        "cv_confidence": 0.82,
        "latitude": 22.57,
        "longitude": 88.36
    }
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    body = request.get_json()
    try:
        req_model = AdvisoryRequest(**body)
    except ValidationError as val_err:
        return jsonify({"error": "Validation Error", "details": val_err.errors()}), 422

    session = SessionLocal()
    try:
        response_model = generate_advanced_advisory(req_model, session)
        return jsonify(response_model.model_dump()), 200
    except Exception as err:
        current_app.logger.error(f"Error in /advisory/advanced: {err}")
        return jsonify({
            "error": "Failed to process advisory request",
            "message": str(err)
        }), 500
    finally:
        session.close()


@bp.route("/download-zip", methods=["GET"])
def download_zip():
    """Serves the generated zip file containing the entire backend project."""
    base_dir = Path(__file__).resolve().parent.parent
    zip_path = base_dir / "crop_disease_advisory_sih2026.zip"
    
    if not zip_path.exists():
        # Build it on the fly if needed
        from generate_zip import create_project_zip
        create_project_zip()

    if zip_path.exists():
        return send_file(
            zip_path,
            as_attachment=True,
            download_name="crop_disease_advisory_sih2026.zip",
            mimetype="application/zip"
        )
    return jsonify({"error": "Zip file could not be found or created."}), 404
