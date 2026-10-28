from datetime import datetime

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    patient_name: str = Field(min_length=2, max_length=120)
    patient_email: str = Field(min_length=5, max_length=255)
    start_at: datetime


class AppointmentCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AppointmentReschedule(BaseModel):
    start_at: datetime