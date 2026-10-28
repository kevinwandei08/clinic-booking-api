from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Africa/Nairobi")


def next_weekday_at(hour=10, minute=0):
    """Return a future weekday appointment time in Nairobi time."""
    candidate = datetime.now(TZ).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ) + timedelta(days=2)

    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)

    # Ensure it is comfortably beyond the API's one-hour lead-time rule.
    if candidate <= datetime.now(TZ) + timedelta(hours=2):
        candidate += timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

    return candidate


def appointment_payload(start_at, doctor_id, email="patient.one@example.com"):
    return {
        "doctor_id": doctor_id,
        "patient_name": "Test Patient",
        "patient_email": email,
        "start_at": start_at.isoformat(),
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_doctor_id_is_rejected(client, db_session):
    from app.models import Doctor
    doctor_id = db_session.query(Doctor).first().id
    payload = appointment_payload(next_weekday_at(), doctor_id)
    payload["doctor_id"] = 0

    response = client.post("/appointments", json=payload)

    assert response.status_code == 422


def test_successful_booking(client, db_session):
    from app.models import Doctor
    doctor_id = db_session.query(Doctor).first().id
    start_at = next_weekday_at()

    response = client.post(
        "/appointments",
        json=appointment_payload(start_at, doctor_id),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == doctor_id
    assert data["patient_email"] == "patient.one@example.com"
    assert data["status"] == "booked"
    assert data["patient_id"] > 0


def test_overlapping_booking_is_rejected(client, db_session):
    from app.models import Doctor
    doctor_id = db_session.query(Doctor).first().id
    start_at = next_weekday_at()

    first = client.post(
        "/appointments",
        json=appointment_payload(start_at, doctor_id, "first@example.com"),
    )
    second = client.post(
        "/appointments",
        json=appointment_payload(start_at, doctor_id, "second@example.com"),
    )

    assert first.status_code == 201
    assert second.status_code == 409


def book_test_appointment(client, db_session, start_at, email):
    from app.models import Doctor

    doctor_id = db_session.query(Doctor).first().id
    response = client.post(
        "/appointments",
        json=appointment_payload(start_at, doctor_id, email),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cancel_appointment(client, db_session):
    appointment = book_test_appointment(
        client, db_session, next_weekday_at(), "cancel@example.com"
    )

    response = client.patch(
        f"/appointments/{appointment['id']}/cancel",
        json={"reason": "Patient requested cancellation"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"


def test_cannot_cancel_appointment_twice(client, db_session):
    appointment = book_test_appointment(
        client, db_session, next_weekday_at(), "twice@example.com"
    )
    url = f"/appointments/{appointment['id']}/cancel"

    first = client.patch(url, json={"reason": "Patient requested cancellation"})
    second = client.patch(url, json={"reason": "Patient requested cancellation"})

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text


def test_reschedule_appointment(client, db_session):
    appointment = book_test_appointment(
        client, db_session, next_weekday_at(), "reschedule@example.com"
    )
    new_start = next_weekday_at(hour=11)

    response = client.patch(
        f"/appointments/{appointment['id']}/reschedule",
        json={"start_at": new_start.isoformat()},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "booked"
    assert response.json()["start_at"].startswith(new_start.date().isoformat())


def test_reschedule_to_occupied_slot_is_rejected(client, db_session):
    first = book_test_appointment(
        client, db_session, next_weekday_at(), "first-reschedule@example.com"
    )
    occupied_start = next_weekday_at(hour=11)

    book_test_appointment(
        client, db_session, occupied_start, "occupied-slot@example.com"
    )

    response = client.patch(
        f"/appointments/{first['id']}/reschedule",
        json={"start_at": occupied_start.isoformat()},
    )

    assert response.status_code == 409, response.text


def test_patient_appointment_history(client, db_session):
    appointment = book_test_appointment(
        client, db_session, next_weekday_at(), "history@example.com"
    )

    response = client.get(
        f"/patients/{appointment['patient_id']}/appointments"
    )

    assert response.status_code == 200, response.text
    history = response.json()
    assert isinstance(history, list)
    assert len(history) == 1
    assert history[0]["id"] == appointment["id"]
    assert history[0]["status"] == "booked"


def test_missing_patient_history_returns_404(client):
    response = client.get("/patients/999999/appointments")

    assert response.status_code == 404


def test_doctor_availability_on_working_day(client, db_session):
    from app.models import Doctor

    doctor_id = db_session.query(Doctor).first().id
    requested_date = next_weekday_at().date()

    response = client.get(
        f"/doctors/{doctor_id}/availability",
        params={"date": requested_date.isoformat()},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["doctor_id"] == doctor_id
    assert data["date"] == requested_date.isoformat()
    assert isinstance(data["available_slots"], list)
    assert len(data["available_slots"]) > 0


def test_doctor_availability_on_weekend_is_empty(client, db_session):
    from app.models import Doctor

    doctor_id = db_session.query(Doctor).first().id
    requested_date = next_weekday_at().date()

    # Find the Saturday immediately following the selected weekday.
    saturday = requested_date + timedelta(
        days=(5 - requested_date.weekday()) % 7
    )
    if saturday.weekday() != 5:
        saturday += timedelta(days=7)

    response = client.get(
        f"/doctors/{doctor_id}/availability",
        params={"date": saturday.isoformat()},
    )

    assert response.status_code == 200, response.text
    assert response.json()["available_slots"] == []


def test_same_email_reuses_existing_patient(client, db_session):
    from app.models import Doctor

    doctor_id = db_session.query(Doctor).first().id
    first_start = next_weekday_at()
    second_start = first_start + timedelta(minutes=30)

    first = client.post(
        "/appointments",
        json=appointment_payload(
            first_start, doctor_id, "returning@example.com"
        ),
    )
    second = client.post(
        "/appointments",
        json=appointment_payload(
            second_start, doctor_id, "returning@example.com"
        ),
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["patient_id"] == second.json()["patient_id"]


def test_cancelled_appointment_releases_time_slot(client, db_session):
    appointment = book_test_appointment(
        client, db_session, next_weekday_at(), "release-slot@example.com"
    )

    cancel_response = client.patch(
        f"/appointments/{appointment['id']}/cancel",
        json={"reason": "Patient requested cancellation"},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    from app.models import Doctor

    doctor_id = db_session.query(Doctor).first().id
    replacement = client.post(
        "/appointments",
        json=appointment_payload(
            datetime.fromisoformat(appointment["start_at"]),
            doctor_id,
            "replacement@example.com",
        ),
    )

    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["status"] == "booked"
    assert replacement.json()["id"] != appointment["id"]
