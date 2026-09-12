from backend.routes.weather import weather_bp
from flask import Flask, render_template

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


if __name__ == "__main__":
    app.run(debug=True)
