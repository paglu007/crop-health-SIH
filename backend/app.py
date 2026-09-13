from flask import Flask, render_template, request
from backend.routes.weather import weather_bp
from backend.teammate_ai.routes import bp as teammate_ai_bp
from backend.config import Config
from backend.database import db, init_db
from backend.routes.fields import fields_bp
from backend.routes.observations import observations_bp
from backend.routes.risk import risk_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.analyze import analyze_bp

import random


app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
init_db(app)


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(fields_bp)

app.register_blueprint(observations_bp)

app.register_blueprint(risk_bp)

app.register_blueprint(
    analyze_bp,
    url_prefix="/api/analyze"
)

app.register_blueprint(
    dashboard_bp,
    url_prefix="/api/dashboard"
)

app.register_blueprint(weather_bp)

app.register_blueprint(teammate_ai_bp)


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Crop Health API is running"
    }


# ============================================================
# DEVELOPMENT OTP LOGIN
# ============================================================

# Hackathon in-memory storage
# Phone number -> OTP
otp_storage = {}


# ------------------------------------------------------------
# SEND OTP
# ------------------------------------------------------------

@app.route("/api/login/send-otp", methods=["POST"])
def send_otp():

    data = request.get_json() or {}

    phone = data.get("phone")

    if not phone:
        return {
            "status": "error",
            "message": "Phone number required"
        }, 400

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Store OTP
    otp_storage[phone] = otp

    # Development SMS simulation
    print("\n" + "=" * 50)
    print(f"📱 SMS TO {phone}: Your KrishiRakshak OTP is {otp}")
    print("=" * 50 + "\n")

    return {
        "status": "success",
        "message": "OTP sent successfully!"
    }, 200


# ------------------------------------------------------------
# VERIFY OTP
# ------------------------------------------------------------

@app.route("/api/login/verify-otp", methods=["POST"])
def verify_otp():

    data = request.get_json() or {}

    phone = data.get("phone")

    user_otp = data.get("otp")

    # Get stored OTP
    stored_otp = otp_storage.get(phone)

    # Phone has no OTP
    if not stored_otp:
        return {
            "status": "error",
            "message": "OTP not found. Please request a new OTP."
        }, 400

    # Check OTP
    if stored_otp == str(user_otp):

        # Delete OTP after successful login
        del otp_storage[phone]

        return {
            "status": "success",
            "role": "farmer",
            "message": "Farmer login successful!"
        }, 200

    # Wrong OTP
    return {
        "status": "error",
        "message": "Invalid OTP"
    }, 401


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)