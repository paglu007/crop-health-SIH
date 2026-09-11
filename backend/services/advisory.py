def generate_advisory(risk_level):
    valid_levels = {"HIGH", "MEDIUM", "LOW"}

    if risk_level not in valid_levels:
      raise ValueError("Invalid risk level")
    if risk_level == "HIGH":
        return {
            "priority": "URGENT",
            "message": "Inspect affected plants and consider immediate disease management."
        }

    if risk_level == "MEDIUM":
        return {
            "priority": "WARNING",
            "message": "Monitor the crop closely and inspect for signs of disease."
        }

    return {
        "priority": "NORMAL",
        "message": "Continue regular crop monitoring."
    }