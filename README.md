# Student Project Scheduling Tool

A specialized full-stack project scheduling and management platform designed specifically for college students working on academic capstone/final-year projects.

The system incorporates three core scheduling algorithms:
* **Priority Scheduling:** Dynamic academic weighting factoring in deadlines, milestone importance, critical path status, and dependency depth.
* **Critical Path Method (CPM):** Forward/backward pass calculations to determine Early Start (ES), Early Finish (EF), Late Start (LS), Late Finish (LF), Slack/Float, and project critical path.
* **PERT (Program Evaluation and Review Technique):** Three-point duration estimation ($o, m, p$), variance calculation, and normal distribution probability ($Z$-score) of meeting academic deadlines.

It also integrates:
* **Academic Milestones & Review Readiness Scorecard** (viva/presentation readiness)
* **Team Workload Balancing & Overload Detection**
* **Student & Faculty Guide Monitoring Dashboards**

---

## Tech Stack

* **Backend:** FastAPI, Python 3.14, SQLAlchemy 2.0 (Async), Alembic, asyncpg, psycopg
* **Frontend (Planned Phase 3):** React 19, Vite, TypeScript, Tailwind CSS, Lucide React
* **Database:** PostgreSQL 16+

---

## Project Structure

```text
Student Project scheduling tool/
├── backend/
│   ├── alembic/              # Database migration configurations & version scripts
│   ├── alembic.ini           # Alembic configuration
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   └── health.py    # Health check & DB diagnostics
│   │   │       └── router.py        # API router
│   │   ├── core/
│   │   │   ├── config.py            # App settings (Pydantic BaseSettings)
│   │   │   └── database.py          # Async SQLAlchemy engine & session factory
│   │   ├── models/                  # Declarative database models (Phase 2)
│   │   ├── schemas/                 # Pydantic validation schemas (Phase 2)
│   │   ├── algorithms/              # Scheduling algorithms (Phase 2)
│   │   └── main.py                  # FastAPI application entry point
│   ├── tests/
│   │   ├── conftest.py              # Pytest fixtures and AsyncClient setup
│   │   ├── test_health.py           # Health endpoint and CORS tests
│   │   └── test_database_config.py  # Database URL and config validation tests
│   ├── requirements.txt             # Backend dependencies
│   └── .env.example                 # Environment variables template
├── frontend/                        # React + TypeScript frontend (Phase 3)
├── README.md
└── .gitignore
```

---

## Backend Setup & Execution

### 1. Prerequisites
Ensure you have installed:
* Python 3.14 (or 3.11+)
* PostgreSQL 16 (Running on localhost:5432)

### 2. Environment Variables Configuration
In the `backend/` directory, copy `.env.example` to `.env`:
```powershell
cp backend/.env.example backend/.env
```
Open `backend/.env` in VS Code and set your PostgreSQL credentials:
```env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_actual_password
POSTGRES_DB=student_project_scheduler
```

### 3. Activating the Virtual Environment
The virtual environment has been pre-created in `backend/.venv`.
To activate it in PowerShell:
```powershell
.\backend\.venv\Scripts\Activate.ps1
```
*(Or in Command Prompt: `backend\.venv\Scripts\activate.bat`)*

### 4. Running the Test Suite
Run all unit and integration tests using pytest:
```powershell
& .\backend\.venv\Scripts\pytest.exe backend/tests -v
```

### 5. Starting the Development Server
To start the FastAPI development server with hot reload:
```powershell
& .\backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --port 8000
```
* **Interactive API Documentation (Swagger UI):** [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
* **ReDoc Documentation:** [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
* **System Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## Database Migrations (Alembic)
Once the PostgreSQL database is created and credentials are configured in `backend/.env`:
```powershell
# Create a new migration revision after defining models:
cd backend
..\backend\.venv\Scripts\alembic.exe revision --autogenerate -m "initial migration"

# Apply migrations to database:
..\backend\.venv\Scripts\alembic.exe upgrade head
```
