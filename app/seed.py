
from datetime import time

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Doctor, DoctorWorkingHours


def seed_database():
    with SessionLocal() as db:
        # Find the test doctor by name and specialty.
        doctor = db.scalar(
            select(Doctor).where(
                Doctor.full_name == "Dr. Jane Mwangi",
                Doctor.specialty == "General Practice",
            )
        )

        # Create the doctor only if they do not already exist.
        if doctor is None:
            doctor = Doctor(
                full_name="Dr. Jane Mwangi",
                specialty="General Practice",
                is_active=True,
            )
            db.add(doctor)
            db.flush()
            print("Test doctor created.")
        else:
            print(f"Test doctor already exists (ID: {doctor.id}).")

        # Monday-Friday, 09:00-17:00.
        # Monday = 0, Tuesday = 1, ..., Sunday = 6.
        for day in range(5):
            existing_hours = db.scalar(
                select(DoctorWorkingHours).where(
                    DoctorWorkingHours.doctor_id == doctor.id,
                    DoctorWorkingHours.day_of_week == day,
                )
            )

            if existing_hours is None:
                db.add(
                    DoctorWorkingHours(
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                    )
                )

        db.commit()
        print("Seed completed successfully.")


if __name__ == "__main__":
    seed_database()
