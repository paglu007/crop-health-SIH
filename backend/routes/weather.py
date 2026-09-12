from flask import Blueprint, request, jsonify
from backend.services.weather import get_current_weather

weather_bp = Blueprint('weather', __name__)

@weather_bp.route('/api/weather', methods=['GET'])
def get_weather():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is None or lon is None:
        return jsonify({"error": "Missing lat or lon parameters"}), 400

    weather_data = get_current_weather(lat, lon)
    
    if not weather_data:
        return jsonify({"error": "Failed to fetch weather data"}), 502

    return jsonify(weather_data), 200
