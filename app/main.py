
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas import (
    AppointmentCreate,
    AppointmentCancel,
    AppointmentReschedule,
)
from app.database import get_db
from app.models import Appointment, Doctor, DoctorWorkingHours, Patient
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import test_database_connection

app = FastAPI(
    title="Clinic Booking API",
    description="REST API for managing clinic appointments.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to the Clinic Booking API",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "clinic-booking-api",
    }


@app.get("/health/db")
def database_health_check():
    try:
        result = test_database_connection()

        if result != 1:
            raise HTTPException(
                status_code=503,
                detail="Database health check failed",
            )

        return {
            "status": "ok",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )

CLINIC_TZ = ZoneInfo("Africa/Nairobi")


@app.get("/doctors/{doctor_id}/availability")
def get_doctor_availability(
    doctor_id: int,
    requested_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    # 1. Confirm that the doctor exists and is active.
    doctor = db.get(Doctor, doctor_id)

    if doctor is None or not doctor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or inactive",
        )

    # 2. Find working hours for the requested weekday.
    working_hours = db.scalar(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor_id,
            DoctorWorkingHours.day_of_week == requested_date.weekday(),
        )
    )

    if working_hours is None:
        return {
            "doctor_id": doctor_id,
            "date": requested_date.isoformat(),
            "available_slots": [],
        }

    # 3. Build the day's working-hours boundaries.
    day_start = datetime.combine(
        requested_date,
        working_hours.start_time,
        tzinfo=CLINIC_TZ,
    )
    day_end = datetime.combine(
        requested_date,
        working_hours.end_time,
        tzinfo=CLINIC_TZ,
    )

    # 4. Fetch booked appointments that overlap working hours.
    appointments = db.scalars(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == "booked",
            Appointment.start_at < day_end,
            Appointment.end_at > day_start,
        )
    ).all()

    # 5. Generate available 30-minute slots.
    now = datetime.now(CLINIC_TZ)
    minimum_booking_time = now + timedelta(hours=1)
    available_slots = []

    slot_start = day_start

    while slot_start + timedelta(minutes=30) <= day_end:
        slot_end = slot_start + timedelta(minutes=30)

        # Exclude past slots and slots within one hour of now.
        if slot_start >= minimum_booking_time:
            overlaps = any(
                appointment.start_at < slot_end
                and appointment.end_at > slot_start
                for appointment in appointments
            )

            if not overlaps:
                available_slots.append(
                    {
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                    }
                )

        slot_start = slot_end

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor.full_name,
        "date": requested_date.isoformat(),
        "timezone": "Africa/Nairobi",
        "slot_duration_minutes": 30,
        "available_slots": available_slots,
    }

@app.post("/appointments", status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
):
    # 1. Require a timezone-aware appointment start time.
    if (
        payload.start_at.tzinfo is None
        or payload.start_at.utcoffset() is None
    ):
        raise HTTPException(
            status_code=422,
            detail="start_at must include a timezone offset",
        )

    # Normalize the requested time to Kenya time.
    start_at = payload.start_at.astimezone(CLINIC_TZ)
    end_at = start_at + timedelta(minutes=30)

    # 2. Reject bookings in the past or within one hour.
    now = datetime.now(CLINIC_TZ)

    if start_at < now:
        raise HTTPException(
            status_code=400,
            detail="Cannot book an appointment in the past",
        )

    if start_at < now + timedelta(hours=1):
        raise HTTPException(
            status_code=400,
            detail="Appointments must be booked at least one hour ahead",
        )

    # 3. Check that the doctor exists and is active.
    doctor = db.get(Doctor, payload.doctor_id)

    if doctor is None or not doctor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or inactive",
        )

    # 4. Require the start time to align to a 30-minute slot.
    if start_at.minute not in (0, 30) or start_at.second != 0 or start_at.microsecond != 0:
        raise HTTPException(
            status_code=400,
            detail="Appointment must start on a 30-minute boundary",
        )

    # 5. Check the doctor's working hours for that weekday.
    working_hours = db.scalar(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor.id,
            DoctorWorkingHours.day_of_week == start_at.weekday(),
        )
    )

    if working_hours is None:
        raise HTTPException(
            status_code=400,
            detail="Doctor does not work on the requested day",
        )

    work_start = datetime.combine(
        start_at.date(),
        working_hours.start_time,
        tzinfo=CLINIC_TZ,
    )
    work_end = datetime.combine(
        start_at.date(),
        working_hours.end_time,
        tzinfo=CLINIC_TZ,
    )

    if start_at < work_start or end_at > work_end:
        raise HTTPException(
            status_code=400,
            detail="Appointment must fall within doctor's working hours",
        )

    # 6. Reject any overlap with an existing booked appointment.
    conflicting_appointment = db.scalar(
        select(Appointment).where(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "booked",
            Appointment.start_at < end_at,
            Appointment.end_at > start_at,
        )
    )

    if conflicting_appointment is not None:
        raise HTTPException(
            status_code=409,
            detail="This appointment slot is already booked",
        )


    # 7. Create or reuse the patient, then save the appointment.
    patient_name = payload.patient_name.strip()
    patient_email = payload.patient_email.strip().lower()

    try:
        # Insert the patient only if this email does not already exist.
        patient_insert = (
            pg_insert(Patient)
            .values(
                full_name=patient_name,
                email=patient_email,
            )
            .on_conflict_do_nothing(
                index_elements=[Patient.email]
            )
            .returning(Patient.id)
        )

        patient_id = db.scalar(patient_insert)

        # If the patient already exists, retrieve their existing ID.
        if patient_id is None:
            patient = db.scalar(
                select(Patient).where(
                    Patient.email == patient_email
                )
            )

            if patient is None:
                raise HTTPException(
                    status_code=500,
                    detail="Could not find or create patient",
                )

            patient_id = patient.id

        # Keep the legacy patient fields while linking the patient record.
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor.id,
            patient_name=patient_name,
            patient_email=patient_email,
            start_at=start_at,
            end_at=end_at,
            status="booked",
        )

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create appointment",
        )

    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "patient_name": appointment.patient_name,
        "patient_email": appointment.patient_email,
        "start_at": appointment.start_at.isoformat(),
        "end_at": appointment.end_at.isoformat(),
        "status": appointment.status,
    }


@app.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="Appointment is already cancelled",
        )

    reason = payload.reason.strip()

    if len(reason) < 3:
        raise HTTPException(
            status_code=422,
            detail="Cancellation reason must contain at least 3 characters",
        )

    appointment.status = "cancelled"
    appointment.cancellation_reason = reason

    try:
        db.commit()
        db.refresh(appointment)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not cancel appointment",
        )

    return {
        "id": appointment.id,
        "status": appointment.status,
        "cancellation_reason": appointment.cancellation_reason,
        "message": "Appointment cancelled successfully",
    }

@app.patch("/appointments/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    db: Session = Depends(get_db),
):
    # 1. Find the existing appointment.
    appointment = db.get(Appointment, appointment_id)

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found",
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="Cannot reschedule a cancelled appointment",
        )

    # 2. Require a timezone-aware timestamp.
    requested_start = payload.start_at

    if (
        requested_start.tzinfo is None
        or requested_start.utcoffset() is None
    ):
        raise HTTPException(
            status_code=422,
            detail="start_at must include a timezone offset",
        )

    new_start = requested_start.astimezone(CLINIC_TZ)
    new_end = new_start + timedelta(minutes=30)

    # 3. Enforce the advance-booking restriction.
    now = datetime.now(CLINIC_TZ)

    if new_start < now:
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule to a time in the past",
        )

    if new_start < now + timedelta(hours=1):
        raise HTTPException(
            status_code=400,
            detail="Appointments must be booked at least one hour ahead",
        )

    # 4. Validate the 30-minute boundary.
    if (
        new_start.minute not in (0, 30)
        or new_start.second != 0
        or new_start.microsecond != 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Appointment must start on a 30-minute boundary",
        )

    # 5. Check that the doctor is still active.
    doctor = db.get(Doctor, appointment.doctor_id)

    if doctor is None or not doctor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or inactive",
        )

    # 6. Validate working hours for the new date.
    working_hours = db.scalar(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor.id,
            DoctorWorkingHours.day_of_week == new_start.weekday(),
        )
    )

    if working_hours is None:
        raise HTTPException(
            status_code=400,
            detail="Doctor does not work on the requested day",
        )

    work_start = datetime.combine(
        new_start.date(),
        working_hours.start_time,
        tzinfo=CLINIC_TZ,
    )
    work_end = datetime.combine(
        new_start.date(),
        working_hours.end_time,
        tzinfo=CLINIC_TZ,
    )

    if new_start < work_start or new_end > work_end:
        raise HTTPException(
            status_code=400,
            detail="Appointment must fall within doctor's working hours",
        )

    # 7. Check conflicts, excluding this appointment itself.
    conflict = db.scalar(
        select(Appointment).where(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.id != appointment.id,
            Appointment.status == "booked",
            Appointment.start_at < new_end,
            Appointment.end_at > new_start,
        )
    )

    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail="The requested appointment slot is already booked",
        )

    # 8. Update the existing appointment in one transaction.
    # Do not cancel first or create a separate appointment.
    appointment.start_at = new_start
    appointment.end_at = new_end

    try:
        db.commit()
        db.refresh(appointment)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not reschedule appointment",
        )

    return {
        "id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "patient_name": appointment.patient_name,
        "patient_email": appointment.patient_email,
        "start_at": appointment.start_at.isoformat(),
        "end_at": appointment.end_at.isoformat(),
        "status": appointment.status,
        "message": "Appointment rescheduled successfully",
    }

@app.get("/patients/{patient_id}/appointments")
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
):
    # 1. Verify that the patient exists.
    patient = db.get(Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    # 2. Retrieve the patient's appointments in chronological order.
    appointments = db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(
            Appointment.start_at.asc(),
            Appointment.id.asc(),
        )
    ).all()

    # 3. Return the appointment history.
    return [
        {
            "id": appointment.id,
            "patient_id": appointment.patient_id,
            "doctor_id": appointment.doctor_id,
            "patient_name": appointment.patient_name,
            "patient_email": appointment.patient_email,
            "start_at": appointment.start_at.isoformat(),
            "end_at": appointment.end_at.isoformat(),
            "status": appointment.status,
            "cancellation_reason": appointment.cancellation_reason,
        }
        for appointment in appointments
    ]
