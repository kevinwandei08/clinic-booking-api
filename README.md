# Clinic Booking API

A REST API for doctor appointment booking built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features
- API and database health checks
- Doctor availability by date
- Appointment booking with validation and conflict prevention
- Patient records associated with appointments by email
- Appointment cancellation and rescheduling
- Patient appointment history
- Automated regression tests using pytest

## Technology Stack
- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL and Psycopg 3
- Pytest and FastAPI TestClient

## Prerequisites
- Python 3.12 or compatible version
- PostgreSQL
- Git

## Local Setup
Clone the repository and enter the project directory:
```bash
git clone https://github.com/kevinwandei08/clinic-booking-api.git
cd clinic-booking-api
```

Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Environment Configuration
Create a `.env` file in the project root with your PostgreSQL connection string:
```env
DATABASE_URL=postgresql+psycopg://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5432/clinic_booking
```
Replace the placeholders with your local credentials. Never commit `.env` or expose database passwords.

## Database Initialization
Create the tables and seed the example doctor and weekday working hours:
```bash
python -m app.create_tables
python -m app.seed
```

## Run the API
```bash
uvicorn app.main:app --reload
```
Useful endpoints:
- API root: `http://127.0.0.1:8000/`
- API health: `http://127.0.0.1:8000/health`
- Database health: `http://127.0.0.1:8000/health/db`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

## Run Automated Tests
The tests use a dedicated PostgreSQL database named `clinic_booking_test`. Ensure it exists and that your database user has the required permissions.
```bash
python -m compileall -q app tests
python -m pytest -v
```
**Important:** Tests clear and recreate fixture data in the test database. Never configure the test suite to use your main development or production database.

## API Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API root |
| GET | `/health` | API health check |
| GET | `/health/db` | Database connectivity check |
| GET | `/doctors/{doctor_id}/availability?date=YYYY-MM-DD` | Doctor availability |
| POST | `/appointments` | Book an appointment |
| PATCH | `/appointments/{appointment_id}/cancel` | Cancel an appointment |
| PATCH | `/appointments/{appointment_id}/reschedule` | Reschedule an appointment |
| GET | `/patients/{patient_id}/appointments` | Retrieve patient appointment history |

For request schemas and response details, run the API and visit `/docs`.

## Test Coverage
Tests cover health checks, validation, booking, conflicting bookings, cancellation, rescheduling, patient history, doctor availability, patient reuse by email, and release of cancelled appointment slots.
