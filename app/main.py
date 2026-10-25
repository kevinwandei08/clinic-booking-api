
from fastapi import FastAPI

app = FastAPI(
    title="Clinic Booking API",
    description="REST API for managing clinic appointments.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "clinic-booking-api",
    }


@app.get("/")
def root():
    return {
        "message": "Welcome to the Clinic Booking API",
        "docs": "/docs",
    }
