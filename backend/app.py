from flask import Flask

from config import Config
from database import db, init_db
from routes.fields import fields_bp
from routes.observations import observations_bp
from routes.risk import risk_bp
from routes.dashboard import dashboard_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
init_db(app)
app.register_blueprint(fields_bp)
app.register_blueprint(observations_bp)
app.register_blueprint(risk_bp)
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
@app.route("/")
def home():
    
    return "Crop Health Backend Running"


@app.route("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Crop Health API is running"
    }


if __name__ == "__main__":
    app.run(debug=True)