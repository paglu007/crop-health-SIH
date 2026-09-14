"""
Database connection and initial seeding module.
Manages SQLAlchemy session and populates SQLite database from the CSV dataset.
"""

import csv
import os
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.teammate_ai.config import Config
from backend.teammate_ai.models import Base, DiseaseAdvisory

# Initialize SQLAlchemy Engine
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False} if "sqlite" in Config.SQLALCHEMY_DATABASE_URI else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency helper to get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_database_from_csv(csv_path: Optional[Path] = None) -> int:
    """
    Populates the database with records from plant_disease_advisory_dataset.csv.
    Idempotent: skips if records already exist.
    
    Returns:
        Number of records inserted.
    """
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        existing_count = session.query(DiseaseAdvisory).count()
        if existing_count > 0:
            return existing_count

        if csv_path is None:
            # Look in data/ or root directory
            possible_paths = [
                Path(__file__).resolve().parent.parent / "data" / "plant_disease_advisory_dataset.csv",
                Path(__file__).resolve().parent.parent / "plant_disease_advisory_dataset.csv",
            ]
            for p in possible_paths:
                if p.exists():
                    csv_path = p
                    break

        if not csv_path or not csv_path.exists():
            print(f"[Database] Warning: CSV dataset file not found at {csv_path}")
            return 0

        records_to_insert = []
        with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                advisory = DiseaseAdvisory(
                    crop=row.get("crop", "").strip(),
                    disease_name=row.get("disease_name", "").strip(),
                    pathogen_type=row.get("pathogen_type", "").strip(),
                    symptoms=row.get("symptoms", "").strip(),
                    favorable_conditions=row.get("favorable_conditions", "").strip(),
                    low_risk_advisory=row.get("low_risk_advisory", "").strip(),
                    medium_risk_advisory=row.get("medium_risk_advisory", "").strip(),
                    high_risk_advisory=row.get("high_risk_advisory", "").strip(),
                    expert_advisory=row.get("expert_advisory", "").strip(),
                    preventive_measures=row.get("preventive_measures", "").strip(),
                    organic_treatment=row.get("organic_treatment", "").strip(),
                    chemical_treatment=row.get("chemical_treatment", "").strip(),
                )
                records_to_insert.append(advisory)

        if records_to_insert:
            session.bulk_save_objects(records_to_insert)
            session.commit()
            print(f"[Database] Successfully seeded {len(records_to_insert)} disease advisories from {csv_path.name}")
            return len(records_to_insert)
        return 0
    except Exception as e:
        session.rollback()
        print(f"[Database] Error seeding database: {e}")
        return 0
    finally:
        session.close()


def find_advisory(db: Session, crop: str, disease_name: str) -> Optional[DiseaseAdvisory]:
    """
    CRUD lookup by crop + disease_name (case-insensitive fuzzy/exact match).
    """
    crop_clean = crop.strip().lower()
    disease_clean = disease_name.strip().lower()

    # Exact case-insensitive match first
    result = db.query(DiseaseAdvisory).filter(
        DiseaseAdvisory.crop.ilike(crop_clean),
        DiseaseAdvisory.disease_name.ilike(disease_clean)
    ).first()

    if result:
        return result

    # Fallback to partial match within crop
    crop_matches = db.query(DiseaseAdvisory).filter(DiseaseAdvisory.crop.ilike(crop_clean)).all()
    for item in crop_matches:
        if disease_clean in item.disease_name.lower() or item.disease_name.lower() in disease_clean:
            return item

    return None
