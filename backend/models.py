from datetime import datetime

from database import db


class CropReport(db.Model):
    __tablename__ = "crop_reports"

    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100), nullable=False)
    growth_stage = db.Column(db.String(100), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    prediction = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    observation = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Field(db.Model):
    __tablename__ = "fields"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    crop_name = db.Column(db.String(100), nullable=False)
    growth_stage = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
class Observation(db.Model):
    __tablename__ = "observations"

    id = db.Column(db.Integer, primary_key=True)

    field_id = db.Column(
        db.Integer,
        db.ForeignKey("fields.id"),
        nullable=False
    )

    image_path = db.Column(db.String(255), nullable=True)
    farmer_observation = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )    
class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)

    observation_id = db.Column(
        db.Integer,
        db.ForeignKey("observations.id"),
        nullable=False
    )

    prediction_type = db.Column(
        db.String(50),
        nullable=False
    )

    label = db.Column(db.String(100), nullable=True)

    confidence = db.Column(db.Float, nullable=True)

    score = db.Column(db.Float, nullable=True)

    model_name = db.Column(db.String(100), nullable=True)

    model_version = db.Column(db.String(50), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )    