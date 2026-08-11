# InfluenceOS Backend API

Production-ready asynchronous Python / FastAPI REST API for **InfluenceOS** — the autonomous AI-powered influencer marketing SaaS platform.

---

## Tech Stack & Architecture

- **Framework**: FastAPI (Python 3.10+)
- **ORM**: SQLAlchemy 2.0 (AsyncIO with `async_sessionmaker`)
- **Database**: Native PostgreSQL 16 (Driver: `asyncpg`) — **No Docker Required**
- **Migrations**: Alembic
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Authentication**: JWT Access Token (15 min) + Server-side Argon2 Password Hashing (`pwdlib`) + Rotated `HttpOnly` Refresh Sessions (7 days)

---

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py          # Register, Login, Refresh, Me, Logout
│   │       │   ├── users.py         # Profile & Settings
│   │       │   ├── campaigns.py     # Campaign CRUD & filtering
│   │       │   ├── influencers.py   # Discovery & shortlisting
│   │       │   ├── outreach.py      # Outreach messages & workflows
│   │       │   ├── contracts.py     # Contracts & AI risk analysis
│   │       │   ├── approvals.py     # Agent action approvals
│   │       │   ├── agents.py        # AI Agent status & timeline
│   │       │   └── analytics.py     # ROAS, spend, revenue aggregations
│   │       └── router.py            # API v1 router aggregator
│   ├── core/
│   │   ├── config.py                # Pydantic Settings
│   │   ├── exceptions.py            # Centralized HTTP exception classes
│   │   └── security.py              # Argon2 hashing & JWT utilities
│   ├── db/
│   │   ├── base.py                  # DeclarativeBase
│   │   ├── custom_types.py          # GUID & JSONB types
│   │   ├── seed.py                  # Initial demo data seeder
│   │   ├── session.py               # Async engine & get_db dependency
│   │   └── create_db.py             # Database creation utility
│   ├── dependencies/
│   │   └── auth.py                  # JWT Bearer get_current_user
│   ├── models/                      # SQLAlchemy ORM models
│   ├── schemas/                     # Pydantic request/response schemas
│   └── main.py                      # FastAPI app entry point & lifespan
├── alembic/                         # Database migration scripts
├── tests/                           # Pytest integration & E2E test suite
├── .env.example                     # Environment template
└── requirements.txt                 # Backend dependencies
```

---

## Quickstart & Local Setup (Native PostgreSQL — No Docker)

### 1. Start Native PostgreSQL
Run the included standalone PowerShell script from the repository root:
```powershell
.\start_postgres.ps1
```
*(To stop PostgreSQL at any time: `.\stop_postgres.ps1`)*

### 2. Configure Environment
```bash
cd backend
cp .env.example .env
```
Ensure `backend/.env` points to your PostgreSQL instance:
```env
DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/influenceos
```

### 3. Install Python Dependencies
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Apply Migrations
```bash
alembic upgrade head
```

### 5. Start the FastAPI Backend
```bash
uvicorn app.main:app --reload --port 8000
```
- **API Base URL**: `http://localhost:8000/api/v1`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## Demo Credentials

- **Email**: `aaditya@glownaturals.com`
- **Password**: `password123`

---

## Running Tests

```bash
pytest -v
```
