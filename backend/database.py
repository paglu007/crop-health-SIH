from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    with app.app_context():
        from models import CropReport, Field, Observation, Prediction
        db.create_all()