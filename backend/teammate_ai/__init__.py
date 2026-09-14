"""
Flask Application Factory for Crop Disease Risk Advisory.
"""

from flask import Flask
from flask_cors import CORS
from backend.teammate_ai.config import Config
from backend.teammate_ai.database import seed_database_from_csv
from backend.teammate_ai.routes import bp as api_bp

def create_app(config_class=Config) -> Flask:
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register Blueprints
    app.register_blueprint(api_bp)

    # Auto-seed database from CSV dataset on startup
    with app.app_context():
        try:
            count = seed_database_from_csv()
            app.logger.info(f"Database ready with {count} disease advisory records.")
        except Exception as e:
            app.logger.error(f"Database seed initialization warning: {e}")

    return app
