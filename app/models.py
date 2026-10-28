from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    full_name: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient",
    )

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    full_name: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    specialty: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    working_hours: Mapped[list["DoctorWorkingHours"]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="doctor",
    )


class DoctorWorkingHours(Base):
    __tablename__ = "doctor_working_hours"

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "day_of_week",
            name="uq_doctor_working_hours_day",
        ),
        CheckConstraint(
            "day_of_week BETWEEN 0 AND 6",
            name="ck_working_hours_day_of_week",
        ),
        CheckConstraint(
            "end_time > start_time",
            name="ck_working_hours_valid_time_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Monday = 0, Tuesday = 1, ..., Sunday = 6
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    start_time: Mapped[time] = mapped_column(
        Time, nullable=False
    )
    end_time: Mapped[time] = mapped_column(
        Time, nullable=False
    )

    doctor: Mapped["Doctor"] = relationship(
        back_populates="working_hours"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
        CheckConstraint(
            "end_at > start_at",
            name="ck_appointment_valid_time_range",
        ),
        CheckConstraint(
            "status IN ('booked', 'cancelled')",
            name="ck_appointment_valid_status",
        ),
        Index(
            "ix_appointments_doctor_start",
            "doctor_id",
            "start_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    patient_name: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    patient_email: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="booked"
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    doctor: Mapped["Doctor"] = relationship(
        back_populates="appointments"
    )
    patient: Mapped["Patient"] = relationship(
        back_populates="appointments",
    )