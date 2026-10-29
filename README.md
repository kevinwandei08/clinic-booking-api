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

## System Design

### Architecture

The application uses a modular REST API architecture:

- **API layer:** FastAPI exposes HTTP endpoints, validates requests, and returns JSON responses.
- **Schema layer:** Pydantic schemas validate incoming data and define API request and response structures.
- **Persistence layer:** SQLAlchemy manages database connections, sessions, ORM models, and SQL operations.
- **Database layer:** PostgreSQL stores doctors, working hours, patients, and appointments.
- **Testing layer:** Pytest and FastAPI TestClient verify API behavior using a dedicated PostgreSQL test database.
- **Deployment layer:** Render hosts the API and PostgreSQL database. GitHub Actions runs automated checks and triggers deployment after successful tests on `main`.

### Data Model

The database uses relational models:

- **Doctor:** Stores doctor information, specialty, and active status.
- **DoctorWorkingHours:** Stores a doctor's working day and start/end times.
- **Patient:** Stores patient details, including email, for association with appointments.
- **Appointment:** Stores appointment details, including the doctor, patient, scheduled time, status, and cancellation or rescheduling information where applicable.

Appointments reference doctors and patients through foreign keys. Working hours reference doctors. These relationships maintain data integrity and support availability queries and patient appointment history.

### Request Flow

1. FastAPI receives an HTTP request.
2. Pydantic validates the request payload and data types.
3. The endpoint applies business rules, such as checking doctor availability and appointment conflicts.
4. SQLAlchemy queries or updates PostgreSQL using parameterized database operations.
5. The API returns a suitable JSON response and HTTP status code.

### Design Decisions and Trade-offs

- **FastAPI:** Provides request validation, automatic OpenAPI documentation, and a straightforward testing interface. The trade-off is that database sessions and business rules still require explicit implementation.
- **PostgreSQL:** Provides relational integrity and transactions for related appointment data. It requires a database service rather than a purely in-memory deployment.
- **SQLAlchemy:** Separates database operations from HTTP handling and supports maintainable ORM-based queries. It introduces an additional abstraction compared with writing raw SQL throughout the application.
- **30-minute availability slots:** Provide a simple, consistent appointment scheduling interval. Fixed slots are straightforward to calculate, but do not support arbitrary appointment durations without further design changes.
- **Dedicated test database:** Prevents automated tests from clearing development or production records. It requires a separate database and explicit test configuration.
- **Idempotent seed script:** Allows the initial doctor and working hours to be created without duplicating existing records. Production systems would normally use controlled database migrations and managed reference-data processes.

## Deployment

### Production Hosting

The application is deployed on Render, with PostgreSQL used for persistent storage.

Public API URL: `https://clinic-booking-api-q7iq.onrender.com`

Interactive API documentation: `https://clinic-booking-api-q7iq.onrender.com/docs`

Replace these placeholders with the actual public service URL before submission.

### Environment Variables

Configure the following variable in the Render service's environment settings:

- `DATABASE_URL`: The PostgreSQL connection URL supplied by the hosted database.

The application normalizes supported PostgreSQL URL prefixes to use the installed Psycopg 3 driver. Database credentials must be stored in environment variables and must never be committed to source control.

### Build and Start Commands

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python -m app.create_tables && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The startup command ensures that the required tables exist, runs the seed script, and launches the API on the port provided by Render.

For a larger production system, use versioned database migrations and a dedicated deployment initialization process rather than relying on table creation at application startup.

### Deployment Verification

After deployment, verify these endpoints using the public service URL:

- `/health` — application health.
- `/health/db` — database connectivity.
- `/docs` — interactive API documentation.

## Continuous Integration and Deployment

The GitHub Actions workflow is located at `.github/workflows/ci-cd.yml`.

It runs on:
- Pull requests targeting `main`.
- Pushes to `main`.

The test job checks out the repository, sets up Python 3.12, installs dependencies, starts a PostgreSQL service, creates an isolated `clinic_booking_test` database, compiles the application and tests, and runs the regression suite.

The deployment job runs after the test job succeeds on a push to `main`. It triggers a Render deployment using the GitHub repository secret `RENDER_DEPLOY_HOOK_URL`.

The deploy hook is stored in GitHub Actions secrets rather than in the source code. Failed tests prevent the deployment job from running.

## AI Usage Reflection

This section records how AI assistance was used during development. It should be reviewed and edited to reflect the developer's actual experience.

### 1. How AI Was Used

AI assistance was used to help plan the implementation sequence, explain FastAPI and SQLAlchemy concepts, troubleshoot Python import issues, structure automated tests, improve PostgreSQL connection configuration, and prepare deployment and documentation steps. Commands and code were run and verified locally before proceeding.

### 2. An AI Suggestion That Improved the Work

One useful recommendation was to isolate automated tests from the development database. The test configuration uses a dedicated `clinic_booking_test` database and resets fixture data between tests. This reduces the risk of test operations affecting development records.

A representative prompt was:

> Help me implement a FastAPI appointment booking API with PostgreSQL and pytest, using a separate test database so automated tests do not modify development data.

The resulting approach made regression testing safer and repeatable.

### 3. An AI Output That Was Incomplete or Needed Verification

AI-assisted terminal instructions and configuration changes required verification rather than blind execution. For example, invoking `pytest -v` initially failed because Python could not resolve the `app` package when loading the test configuration. Running `python -m pytest -v` through the active virtual environment resolved the issue, and all 14 tests passed.

This reinforced the importance of checking actual terminal output and validating proposed commands against the project's environment.

### 4. Two Decisions Made Independently

**Decision 1 — Use PostgreSQL for appointment data.** I chose a relational database because doctors, patients, working hours, and appointments have relationships that benefit from foreign keys, structured queries, and transaction support.

**Decision 2 — Keep automated tests isolated from development data.** I retained a dedicated test database because appointment tests create, update, and delete records. Isolation reduces the risk of accidental data loss and makes test results more reliable.

These decisions were based on the application's data relationships and the need for repeatable, safe testing.
