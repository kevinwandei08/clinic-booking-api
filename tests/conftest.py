import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

_project_root = Path(__file__).resolve().parents[1]
_source_url = dotenv_values(_project_root / ".env").get("DATABASE_URL")

if not _source_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

_parsed = urlsplit(_source_url)
if _parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
    raise RuntimeError("Unexpected database driver; refusing test setup")
if _parsed.path.lstrip("/") != "clinic_booking":
    raise RuntimeError("Expected clinic_booking in .env; refusing test setup")

os.environ["DATABASE_URL"] = urlunsplit(
    (_parsed.scheme, _parsed.netloc, "/clinic_booking_test",
     _parsed.query, _parsed.fragment)
)

if make_url(os.environ["DATABASE_URL"]).database != "clinic_booking_test":
    raise RuntimeError("Test database safety check failed")

from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# Import only after the test DATABASE_URL has been configured.
from app.database import Base, engine, get_db
from app.main import app
from app.models import Appointment, Doctor, DoctorWorkingHours, Patient


@pytest.fixture(scope="session")
def test_engine():
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != "clinic_booking_test":
        raise RuntimeError(
            f"Refusing to test against unexpected database: {url.database}"
        )

    Base.metadata.create_all(bind=engine)
    yield engine
    # Deliberately leave the test database and its schema in place.


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    with TestingSessionLocal() as db:
        # Delete child rows before parent rows.
        db.execute(delete(Appointment))
        db.execute(delete(DoctorWorkingHours))
        db.execute(delete(Patient))
        db.execute(delete(Doctor))
        db.commit()

        doctor = Doctor(
            full_name="Dr. Test Doctor",
            specialty="General Practice",
            is_active=True,
        )
        db.add(doctor)
        db.flush()

        for weekday in range(5):
            db.add(
                DoctorWorkingHours(
                    doctor_id=doctor.id,
                    day_of_week=weekday,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            )
        db.commit()
        db.refresh(doctor)

        yield db


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
