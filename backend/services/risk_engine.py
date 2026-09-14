import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from backend.config import RISK_MODEL_PATH, SUPPORTED_DISEASES

class CropRiskEngine:
    """
    Scikit-Learn powered Risk Engine that calculates crop disease spread risk (0-100%)
    and categorizes threat level based on infection severity and micro-climate parameters.
    """
    def __init__(self):
        from pathlib import Path

        self.model_path = Path(RISK_MODEL_PATH)
        self.regressor = None
        self.classifier = None
        self._initialize_or_load_model()

    def _generate_synthetic_epidemiology_data(self, n_samples: int = 1500) -> pd.DataFrame:
        """
        Generates realistic agricultural epidemiology dataset based on plant pathology principles:
        - Fungal spores thrive in high humidity (>80%) and warm temperatures (20-30°C).
        - Bacterial blights spread rapidly with rain splash and high winds.
        - Higher infection severity increases baseline sporulation rate.
        """
        np.random.seed(42)
        
        # Features
        pathogen_type_num = np.random.choice([0, 1, 2, 3], size=n_samples) # 0: Healthy, 1: Fungal, 2: Bacterial, 3: Pest
        severity_pct = np.random.uniform(5.0, 95.0, size=n_samples)
        temp_c = np.random.uniform(10.0, 42.0, size=n_samples)
        humidity_pct = np.random.uniform(30.0, 99.0, size=n_samples)
        rainfall_mm = np.random.uniform(0.0, 50.0, size=n_samples)
        wind_speed_kph = np.random.uniform(0.0, 40.0, size=n_samples)

        risk_scores = []
        for i in range(n_samples):
            ptype = pathogen_type_num[i]
            sev = severity_pct[i]
            t = temp_c[i]
            h = humidity_pct[i]
            r = rainfall_mm[i]
            w = wind_speed_kph[i]

            if ptype == 0:  # Healthy
                base_risk = 5.0 + 0.1 * r + 0.05 * h
            elif ptype == 1: # Fungal (e.g., Late Blight, Rust, Scab)
                # Fungal index: Optimal temp 18-28C, Humidity > 75%
                temp_factor = 1.0 - (abs(t - 24.0) / 20.0)
                temp_factor = max(0.1, temp_factor)
                humidity_factor = (h / 100.0) ** 2
                rain_factor = 1.0 + (r / 25.0)
                base_risk = (sev * 0.4) + (humidity_factor * 35.0) + (temp_factor * 20.0) + (rain_factor * 5.0)
            elif ptype == 2: # Bacterial
                # Bacterial index: Rain splash & warmth
                temp_factor = 1.0 if (25.0 <= t <= 35.0) else 0.5
                rain_factor = (r / 50.0) * 30.0
                wind_factor = (w / 40.0) * 15.0
                base_risk = (sev * 0.35) + rain_factor + wind_factor + (temp_factor * 20.0)
            else: # Pest (e.g., Aphids, Armyworm)
                # Pests prefer moderate/warm dry to wet weather with wind dispersion
                wind_factor = (w / 40.0) * 20.0
                temp_factor = (t / 40.0) * 25.0
                base_risk = (sev * 0.4) + wind_factor + temp_factor + (h * 0.15)

            score = min(max(base_risk, 0.0), 100.0)
            risk_scores.append(score)

        df = pd.DataFrame({
            'pathogen_type': pathogen_type_num,
            'severity_pct': severity_pct,
            'temp_c': temp_c,
            'humidity_pct': humidity_pct,
            'rainfall_mm': rainfall_mm,
            'wind_speed_kph': wind_speed_kph,
            'risk_score': risk_scores
        })
        return df

    def train_model(self):
        """
        Trains Scikit-Learn Random Forest models on epidemiological dataset.
        """
        df = self._generate_synthetic_epidemiology_data()
        X = df[['pathogen_type', 'severity_pct', 'temp_c', 'humidity_pct', 'rainfall_mm', 'wind_speed_kph']]
        y = df['risk_score']

        self.regressor = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=12)
        self.regressor.fit(X, y)

        # Categorical risk classification
        risk_labels = pd.cut(y, bins=[-1, 25, 55, 80, 100], labels=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        self.classifier = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.classifier.fit(X, risk_labels)

        # Save model pipeline
        joblib.dump({
            'regressor': self.regressor,
            'classifier': self.classifier
        }, self.model_path)
        print(f"Scikit-Learn Risk Model trained & saved successfully to {self.model_path}")

    def _initialize_or_load_model(self):
        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.regressor = data.get('regressor')
                self.classifier = data.get('classifier')
            except Exception:
                self.train_model()
        else:
            self.train_model()

    def _encode_pathogen(self, pathogen_type: str) -> int:
        mapping = {
            "Healthy": 0,
            "Fungal": 1,
            "Fungal/Oomycete": 1,
            "Bacterial": 2,
            "Pest": 3
        }
        return mapping.get(pathogen_type, 1)

    def calculate_risk(
        self,
        pathogen_type: str,
        severity_pct: float,
        temp_c: float,
        humidity_pct: float,
        rainfall_mm: float,
        wind_speed_kph: float
    ) -> Dict[str, Any]:
        """
        Calculates 0-100% Risk Score and threat level using trained Scikit-Learn model.
        """
        ptype_num = self._encode_pathogen(pathogen_type)
        input_data = pd.DataFrame([{
            'pathogen_type': ptype_num,
            'severity_pct': severity_pct,
            'temp_c': temp_c,
            'humidity_pct': humidity_pct,
            'rainfall_mm': rainfall_mm,
            'wind_speed_kph': wind_speed_kph
        }])

        raw_score = float(self.regressor.predict(input_data)[0])
        score = round(min(max(raw_score, 2.0 if pathogen_type == "Healthy" else 15.0), 99.0), 1)

        # Categorize
        if score < 25.0:
            risk_level = "LOW"
            risk_category = "Minimal Outbreak Threat"
            spread_rate = "Slow / Contained (< 2% field expansion / week)"
        elif score < 55.0:
            risk_level = "MEDIUM"
            risk_category = "Moderate Spread Risk"
            spread_rate = "Moderate (5-15% field expansion / week)"
        elif score < 80.0:
            risk_level = "HIGH"
            risk_category = "Severe Propagation Risk"
            spread_rate = "Rapid Sporulation / Transmission (20-40% field expansion / week)"
        else:
            risk_level = "CRITICAL"
            risk_category = "Epidemic / Outbreak Alert"
            spread_rate = "Explosive Outbreak (> 50% field expansion within 72 hours)"

        # Analyze favorable environmental triggers
        favorable_factors = []
        if humidity_pct >= 80.0:
            favorable_factors.append(f"High relative humidity ({humidity_pct}%) creates optimal sporulation moisture.")
        if 20.0 <= temp_c <= 30.0:
            favorable_factors.append(f"Temperature of {temp_c}°C falls directly in the pathogen acceleration window.")
        if rainfall_mm >= 10.0:
            favorable_factors.append(f"Rainfall ({rainfall_mm} mm) facilitates foliar moisture and bacterial splash dispersal.")
        if wind_speed_kph >= 15.0:
            favorable_factors.append(f"Wind speed ({wind_speed_kph} km/h) accelerates airborne spore transport to adjacent plots.")
        if severity_pct >= 30.0:
            favorable_factors.append(f"High existing leaf lesion severity ({severity_pct}%) provides large inoculum reserve.")

        if not favorable_factors:
            favorable_factors.append("Current ambient environmental conditions are suppressing rapid pathogen expansion.")

        return {
            "risk_score": score,
            "risk_level": risk_level,
            "risk_category": risk_category,
            "spread_rate_estimate": spread_rate,
            "favorable_factors": favorable_factors
        }

# Global Instance
risk_engine = CropRiskEngine()
