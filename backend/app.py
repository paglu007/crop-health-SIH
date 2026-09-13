from backend.routes.weather import weather_bp
from flask import Flask, render_template, request

from backend.config import Config
from backend.database import db, init_db
from backend.routes.fields import fields_bp
from backend.routes.observations import observations_bp
from backend.routes.risk import risk_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.analyze import analyze_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
init_db(app)
app.register_blueprint(fields_bp)
app.register_blueprint(observations_bp)
app.register_blueprint(risk_bp)
app.register_blueprint(analyze_bp, url_prefix="/api/analyze")
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
app.register_blueprint(weather_bp)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Crop Health API is running"
    }


import random

# Hackathon in-memory storage (Phone -> OTP)
otp_storage = {}

@app.route("/api/login/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json() or {}
    phone = data.get("phone")
    
    if not phone:
        return {"status": "error", "message": "Phone number required"}, 400
    
    # Generate real 6-digit OTP
    otp = str(random.randint(100000, 999999))
    otp_storage[phone] = otp
    
    # SIMULATE SMS (Prints to your Flask terminal)
    print(f"\n" + "="*50)
    print(f"📱 SMS TO {phone}: Your KrishiRakshak OTP is {otp}")
    print("="*50 + "\n")
    
    return {"status": "success", "message": "OTP sent successfully!"}

@app.route("/api/login/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    phone = data.get("phone")
    user_otp = data.get("otp")
    
    # Check if OTP matches
    if otp_storage.get(phone) == user_otp:
        del otp_storage[phone] # Clear after use
        return {"status": "success", "role": "farmer", "message": "Farmer login successful!"}
    
    return {"status": "error", "message": "Invalid or expired OTP"}, 401
    # Hackathon shortcut: Accept any credentials and return a mock success
    return {"status": "success", "role": role, "message": f"Logged in as {role}"}
if __name__ == "__main__":
    app.run(debug=True)