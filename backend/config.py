import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

RISK_MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "risk_model.joblib"
)

SUPPORTED_DISEASES = [
    "Healthy",
    "Fungal",
    "Fungal/Oomycete",
    "Bacterial",
    "Pest"
]
class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR, "crop_health.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
