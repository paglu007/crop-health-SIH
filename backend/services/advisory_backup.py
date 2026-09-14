
def generate_advisory(crop, growth_stage, issue, severity, weather, risk_level):

    advisory = {
        "priority": "NORMAL",
        "risk_level": risk_level,
        "issue": issue,
        "recommendations": [],
        "weather_context": [],
        "monitoring": []
    }

    # Risk-based priority
    if risk_level == "HIGH":
        advisory["priority"] = "URGENT"
        advisory["recommendations"].append(
            "Inspect affected plants immediately and isolate severely affected areas."
        )
    elif risk_level == "MEDIUM":
        advisory["priority"] = "WARNING"
        advisory["recommendations"].append(
            "Increase field monitoring and inspect affected plants closely."
        )
    else:
        advisory["recommendations"].append(
            "Continue regular crop monitoring."
        )

    # Disease severity
    if severity >= 50:
        advisory["recommendations"].append(
            "High disease severity detected; prioritize affected plants for management."
        )
    elif severity >= 25:
        advisory["recommendations"].append(
            "Moderate disease severity detected; remove or manage visibly affected plant material where appropriate."
        )

    # Weather conditions
    humidity = weather.get("humidity_pct")
    temp = weather.get("temp_c")
    rainfall = weather.get("rainfall_mm")

    if humidity is not None and humidity >= 80:
        advisory["weather_context"].append(
            "High humidity may favor fungal disease development."
        )

    if rainfall is not None and rainfall > 0:
        advisory["weather_context"].append(
            "Recent rainfall may increase leaf wetness and disease spread risk."
        )

    if temp is not None:
        advisory["weather_context"].append(
            f"Current temperature is {temp}°C."
        )

    # Growth-stage monitoring
    advisory["monitoring"].append(
        f"Monitor {crop} during the {growth_stage} stage for changes in disease symptoms."
    )

    return advisory
