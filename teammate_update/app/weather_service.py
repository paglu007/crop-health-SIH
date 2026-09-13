"""
Weather Service Module for Crop Disease Risk Advisory.
Fetches real weather data from OpenWeather APIs, parses into WeatherSnapshot,
computes disease-specific microclimate risk, and caches results to honor rate limits.
"""

import math
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

from app.config import Config
from app.models import WeatherSnapshot, WeatherSummary

# In-memory location cache: key -> {"timestamp": float, "summary": WeatherSummary, "snapshots": list[WeatherSnapshot]}
_WEATHER_CACHE: Dict[str, Dict] = {}


def _get_cache_key(lat: float, lon: float) -> str:
    """Rounds coordinates to ~1km precision to maximize cache hits for local microclimates."""
    return f"{round(lat, 2)}:{round(lon, 2)}"


def _extract_temp_range(favorable_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extracts temperature ranges like '24-29C' or '15-20C' or 'above 35C' from favorable conditions text.
    """
    text = favorable_text.lower()
    
    # Pattern: 24-29c or 24-29 c or 24 - 29C
    range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*c", text)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
        
    # Pattern: above 35c
    above_match = re.search(r"above\s*(\d+)\s*c", text)
    if above_match:
        return float(above_match.group(1)), 45.0
        
    # Pattern: cool (< 22C) or warm (> 24C)
    if "cool" in text or "cold" in text:
        return 10.0, 22.0
    if "warm" in text or "hot" in text:
        return 23.0, 34.0
        
    return None, None


def compute_weather_risk(snapshots: List[WeatherSnapshot], favorable_conditions: str) -> float:
    """
    Computes disease weather risk score [0.0 - 1.0] by evaluating:
    1. Average and sustained high relative humidity (>80% or >85%)
    2. Temperature alignment with disease's favorable_conditions range
    3. Rainfall/wetness presence
    4. Consecutive days of high moisture favoring fungal/bacterial sporulation

    Args:
        snapshots: List of WeatherSnapshot instances (past and forecast)
        favorable_conditions: Text description from database (e.g., 'Warm humid weather 24-29C, extended leaf wetness')

    Returns:
        weather_risk_score: Float between 0.0 and 1.0
    """
    if not snapshots:
        return 0.5  # Neutral fallback if no snapshots available

    fav_text = favorable_conditions.lower()
    wants_high_humidity = any(term in fav_text for term in ["high humidity", "humid", "dew", "wet", "moist", "waterlog"])
    wants_dry = any(term in fav_text for term in ["dry", "drought", "moisture stress"])
    min_temp, max_temp = _extract_temp_range(favorable_conditions)

    # 1. Humidity Risk Component (Weight: 45%)
    # Count sustained high humidity snapshots (>80%)
    high_humidity_count = sum(1 for s in snapshots if s.humidity >= 80.0)
    avg_humidity = sum(s.humidity for s in snapshots) / len(snapshots)
    
    if wants_high_humidity:
        # Scale: humidity > 85% pushes humidity score toward 1.0
        humidity_score = min(1.0, max(0.0, (avg_humidity - 50.0) / 40.0))
        # Bonus for sustained continuous moisture
        sustained_factor = min(0.2, (high_humidity_count / max(1, len(snapshots))) * 0.25)
        humidity_score = min(1.0, humidity_score + sustained_factor)
    elif wants_dry:
        # Lower humidity is more risky for powdery mildews/dry rots
        humidity_score = min(1.0, max(0.0, (80.0 - avg_humidity) / 40.0))
    else:
        humidity_score = min(1.0, max(0.0, avg_humidity / 100.0))

    # 2. Temperature Fit Component (Weight: 35%)
    avg_temp = sum(s.temperature for s in snapshots) / len(snapshots)
    if min_temp is not None and max_temp is not None:
        if min_temp <= avg_temp <= max_temp:
            temp_score = 1.0
        else:
            # Distance penalty
            distance = min(abs(avg_temp - min_temp), abs(avg_temp - max_temp))
            temp_score = max(0.1, 1.0 - (distance / 12.0))
    else:
        # Default mild-to-warm conduciveness for plant pathogens (18C - 30C)
        if 18.0 <= avg_temp <= 30.0:
            temp_score = 0.85
        else:
            temp_score = 0.4

    # 3. Rainfall / Wetness Component (Weight: 20%)
    total_rain = sum(s.rainfall for s in snapshots)
    has_rain_demand = any(term in fav_text for term in ["rain", "splashing rain", "wetness", "waterlogging", "monsoon"])
    
    if has_rain_demand:
        rain_score = min(1.0, total_rain / 15.0)  # 15mm+ rainfall maximizes wetness index
    else:
        rain_score = min(0.6, total_rain / 20.0)

    # Composite Weather Conduciveness Calculation
    composite = (0.45 * humidity_score) + (0.35 * temp_score) + (0.20 * rain_score)
    return round(float(min(1.0, max(0.05, composite))), 3)


def _aggregate_daily_sustained_days(snapshots: List[WeatherSnapshot]) -> int:
    """Calculates how many unique days experienced high humidity (>75%)."""
    days_with_high_humidity = set()
    for s in snapshots:
        if s.humidity >= 75.0:
            # take date prefix YYYY-MM-DD
            day_key = s.date.split()[0] if " " in s.date else s.date.split("T")[0]
            days_with_high_humidity.add(day_key)
    return len(days_with_high_humidity)


def fetch_weather_snapshots(
    lat: float,
    lon: float,
    favorable_conditions: str = ""
) -> Tuple[List[WeatherSnapshot], WeatherSummary, float]:
    """
    Fetches weather data from OpenWeather API with intelligent caching & graceful fallback.
    
    Tries:
    1. Check in-memory cache for recent data (< TTL)
    2. Real OpenWeather 5-day / 3-hour forecast endpoint
    3. OpenWeather Timemachine / OneCall if historical available
    4. Fallback to cached entry or synthetic realistic microclimate based on lat/lon
    
    Returns:
        Tuple of (snapshots, weather_summary, weather_risk_score)
    """
    cache_key = _get_cache_key(lat, lon)
    now_ts = time.time()
    api_key = Config.OPENWEATHER_API_KEY.strip()

    # Check cache freshness
    cached = _WEATHER_CACHE.get(cache_key)
    if cached and (now_ts - cached["timestamp"] < Config.WEATHER_CACHE_TTL_SECONDS):
        snapshots = cached["snapshots"]
        summary = cached["summary"]
        risk_score = compute_weather_risk(snapshots, favorable_conditions)
        return snapshots, summary, risk_score

    snapshots: List[WeatherSnapshot] = []
    is_live = False
    data_note = ""

    # 1. Attempt Live OpenWeather API Calls
    if api_key and api_key != "YOUR_OPENWEATHER_API_KEY":
        try:
            # A. 5-day / 3-hour Forecast Endpoint
            forecast_resp = requests.get(
                Config.OPENWEATHER_FORECAST_URL,
                params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
                timeout=5.0
            )
            
            if forecast_resp.status_code == 200:
                data = forecast_resp.json()
                items = data.get("list", [])
                for item in items[:24]:  # Next 3 days in 3-hr blocks
                    main = item.get("main", {})
                    weather_desc = item.get("weather", [{}])[0].get("description", "")
                    wind = item.get("wind", {}).get("speed", 0.0)
                    rain_data = item.get("rain", {})
                    rain_vol = rain_data.get("3h", 0.0) if isinstance(rain_data, dict) else 0.0
                    
                    dt_txt = item.get("dt_txt", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
                    snapshots.append(WeatherSnapshot(
                        date=dt_txt,
                        humidity=float(main.get("humidity", 65.0)),
                        temperature=float(main.get("temp", 25.0)),
                        rainfall=float(rain_vol),
                        wind_speed=float(wind),
                        description=weather_desc
                    ))
                is_live = True
                data_note = "Live OpenWeather 5-Day Forecast API"

            # B. Attempt Historical Timemachine endpoint (past 7 days sample)
            # OpenWeather 3.0 OneCall Timemachine
            past_days = 3
            for day_offset in range(1, past_days + 1):
                past_time = int(now_ts - (day_offset * 86400))
                try:
                    hist_resp = requests.get(
                        Config.OPENWEATHER_TIMEMACHINE_URL,
                        params={"lat": lat, "lon": lon, "dt": past_time, "appid": api_key, "units": "metric"},
                        timeout=3.0
                    )
                    if hist_resp.status_code == 200:
                        hist_data = hist_resp.json().get("data", [])
                        if hist_data:
                            h_item = hist_data[0]
                            h_dt = datetime.fromtimestamp(past_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                            snapshots.insert(0, WeatherSnapshot(
                                date=h_dt,
                                humidity=float(h_item.get("humidity", 70.0)),
                                temperature=float(h_item.get("temp", 26.0)),
                                rainfall=float(h_item.get("rain", {}).get("1h", 0.0) if isinstance(h_item.get("rain"), dict) else 0.0),
                                wind_speed=float(h_item.get("wind_speed", 0.0)),
                                description=h_item.get("weather", [{}])[0].get("description", "historical")
                            ))
                except Exception:
                    # Non-fatal if timemachine is not covered by the user's free tier
                    break

        except Exception as e:
            print(f"[WeatherService] OpenWeather API call failed: {e}")

    # 2. Fallback to Stale Cache if available
    if not snapshots and cached:
        snapshots = cached["snapshots"]
        summary = cached["summary"]
        summary.data_source_note = f"Cached data (API fallback, cached {int((now_ts - cached['timestamp']) / 60)} mins ago)"
        risk_score = compute_weather_risk(snapshots, favorable_conditions)
        return snapshots, summary, risk_score

    # 3. Fallback: If no API key or API call failed, generate representative regional microclimate
    if not snapshots:
        # Realistic seasonal regional microclimate estimation for Indian agricultural coordinates
        is_live = False
        data_note = "Live OpenWeather key not configured or unreachable; using neutral fallback."
        
        # Base realistic 7-day pattern
        for day_offset in range(-3, 4):
            day_date = (datetime.now(timezone.utc) + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            # Simulating seasonal variation around typical tropical/subtropical conditions
            sim_humidity = 78.0 + (5.0 * math.sin(day_offset * 1.2))
            sim_temp = 27.5 + (2.0 * math.cos(day_offset * 0.9))
            sim_rain = 3.5 if day_offset >= 0 else 1.2
            snapshots.append(WeatherSnapshot(
                date=f"{day_date} 12:00",
                humidity=round(sim_humidity, 1),
                temperature=round(sim_temp, 1),
                rainfall=sim_rain,
                wind_speed=3.2,
                description="Humid / moderate cloud cover"
            ))

    # Compute risk and summary
    weather_risk_score = compute_weather_risk(snapshots, favorable_conditions)
    sustained_days = _aggregate_daily_sustained_days(snapshots)
    
    current_snapshot = snapshots[len(snapshots) // 2]
    avg_hum = round(sum(s.humidity for s in snapshots) / len(snapshots), 1)
    max_hum = round(max(s.humidity for s in snapshots), 1)
    tot_rain = round(sum(s.rainfall for s in snapshots), 1)

    trend = "High sustained moisture (>75% RH) conducive to fungal/bacterial spread" if avg_hum >= 75.0 else "Moderate humidity with low moisture accumulation"

    summary = WeatherSummary(
        location=f"Lat {lat:.2f}°, Lon {lon:.2f}°",
        current_temp_c=current_snapshot.temperature,
        current_humidity_pct=current_snapshot.humidity,
        avg_humidity_pct=avg_hum,
        max_humidity_pct=max_hum,
        total_rain_mm=tot_rain,
        sustained_high_humidity_days=sustained_days,
        forecast_trend=trend,
        is_live_data=is_live,
        data_source_note=data_note or ("OpenWeather API Verified" if is_live else None),
        snapshots=snapshots
    )

    # Store in cache
    _WEATHER_CACHE[cache_key] = {
        "timestamp": now_ts,
        "summary": summary,
        "snapshots": snapshots
    }

    return snapshots, summary, weather_risk_score
