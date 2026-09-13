"""
Entry Point for Crop Disease Risk Advisory System (SIH 2026).
Run directly with: python main.py or flask run
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"🌾 SIH 2026 Crop Disease Risk Advisory (Flask) running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
