import requests

def get_current_weather(lat: float, lon: float) -> dict:
    """
    Fetches real-time weather data from Open-Meteo for a given latitude and longitude.
    Returns a normalized dictionary with temperature, humidity, rainfall, and wind speed.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    }
    
    try:
        # 5-second timeout is good practice so our backend doesn't hang indefinitely
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status() 
        data = response.json()
        
        current = data.get("current", {})
        
        # Normalize into the structure the Risk Engine expects
        return {
            "temp_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "rainfall_mm": current.get("precipitation"),
            "wind_speed_kph": current.get("wind_speed_10m")
        }
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None

# --- Quick Local Test ---
if __name__ == "__main__":
    # Testing with Kolkata, India coordinates
    print("Testing Open-Meteo API integration...")
    weather = get_current_weather(22.5726, 88.3639)
    print("Result:", weather)
