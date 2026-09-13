"""
Database Seeder and Zip Package Generator for Crop Disease Advisory System (SIH 2026).
"""

import os
import csv
import sqlite3
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crop_disease.db"
CSV_PATH = BASE_DIR / "data" / "plant_disease_advisory_dataset.csv"
ZIP_PATH = BASE_DIR / "crop_disease_advisory_sih2026.zip"
PUBLIC_ZIP = BASE_DIR / "public" / "crop_disease_advisory_sih2026.zip"


def create_sqlite_db():
    """Populates crop_disease.db with all 143 records using sqlite3."""
    print(f"[DB] Initializing SQLite database at {DB_PATH}...")
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE disease_advisories (
        disease_id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop TEXT NOT NULL,
        disease_name TEXT NOT NULL,
        pathogen_type TEXT,
        symptoms TEXT,
        favorable_conditions TEXT,
        low_risk_advisory TEXT,
        medium_risk_advisory TEXT,
        high_risk_advisory TEXT,
        expert_advisory TEXT,
        preventive_measures TEXT,
        organic_treatment TEXT,
        chemical_treatment TEXT
    );
    """)

    cursor.execute("CREATE INDEX idx_crop ON disease_advisories(crop);")
    cursor.execute("CREATE INDEX idx_disease_name ON disease_advisories(disease_name);")

    count = 0
    with open(CSV_PATH, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
            INSERT INTO disease_advisories (
                crop, disease_name, pathogen_type, symptoms, favorable_conditions,
                low_risk_advisory, medium_risk_advisory, high_risk_advisory,
                expert_advisory, preventive_measures, organic_treatment, chemical_treatment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("crop", "").strip(),
                row.get("disease_name", "").strip(),
                row.get("pathogen_type", "").strip(),
                row.get("symptoms", "").strip(),
                row.get("favorable_conditions", "").strip(),
                row.get("low_risk_advisory", "").strip(),
                row.get("medium_risk_advisory", "").strip(),
                row.get("high_risk_advisory", "").strip(),
                row.get("expert_advisory", "").strip(),
                row.get("preventive_measures", "").strip(),
                row.get("organic_treatment", "").strip(),
                row.get("chemical_treatment", "").strip(),
            ))
            count += 1

    conn.commit()
    conn.close()
    print(f"[DB] Successfully inserted {count} records into {DB_PATH.name}")


def create_project_zip():
    """Packages all files into a standalone production-ready zip archive."""
    print(f"[ZIP] Creating archive at {ZIP_PATH}...")
    files_to_pack = [
        "main.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "crop_disease.db",
        "plant_disease_advisory_dataset.csv",
        "data/plant_disease_advisory_dataset.csv",
        "app/__init__.py",
        "app/config.py",
        "app/models.py",
        "app/database.py",
        "app/weather_service.py",
        "app/llm_advisory_service.py",
        "app/risk.py",
        "app/advisory.py",
        "app/routes.py",
    ]

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in files_to_pack:
            file_path = BASE_DIR / rel_path
            if file_path.exists():
                arcname = f"crop_advisory_backend/{rel_path}"
                zf.write(file_path, arcname=arcname)
                print(f"  + Added {rel_path}")

    # Copy to public folder for direct browser download
    PUBLIC_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with open(ZIP_PATH, "rb") as src, open(PUBLIC_ZIP, "wb") as dst:
        dst.write(src.read())

    print(f"[ZIP] Complete! File size: {ZIP_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    create_sqlite_db()
    create_project_zip()
