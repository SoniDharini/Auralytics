# InfluenceOS — Autonomous Influencer Marketing SaaS

InfluenceOS is a full-stack, AI-powered autonomous influencer marketing SaaS platform that connects brands to creators with automated strategy, discovery, outreach, contract risk review, and real-time ROAS performance tracking.

---

## Full-Stack Architecture

```
InfluenceOS/
├── frontend/             # React 19 + TypeScript + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/   # UI Design System & Auth Modals
│   │   ├── context/      # AuthContext & Session Management
│   │   ├── layouts/      # AppLayout, Sidebar, Header
│   │   ├── pages/        # Dashboard, Campaigns, Discovery, Approvals, etc.
│   │   ├── services/     # Typed API Client with 401 Silent Refresh
│   │   └── types/        # TypeScript Interfaces
│   └── package.json
│
├── backend/              # Python 3.14 + FastAPI + PostgreSQL (asyncpg)
│   ├── app/
│   │   ├── api/v1/       # REST Endpoints (Auth, Campaigns, Influencers, etc.)
│   │   ├── core/         # Config, Security (Argon2 + PyJWT), Exceptions
│   │   ├── db/           # Async Engine, DeclarativeBase, Seed Data
│   │   ├── dependencies/ # get_current_user JWT Auth Guard
│   │   ├── models/       # SQLAlchemy 2.0 ORM Models
│   │   └── schemas/      # Pydantic v2 Request/Response Schemas
│   ├── alembic/          # Database Migrations
│   ├── tests/            # Pytest Unit & Live Integration Suite
│   └── requirements.txt
│
└── pgsql/                # Standalone Native PostgreSQL 16 Binaries & Data
```

---

## Quickstart (No Docker Required)

### 1. Start Native PostgreSQL
```powershell
.\start_postgres.ps1
```

### 2. Start the FastAPI Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows (or source venv/bin/activate on Unix)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
API Documentation available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend Web App available at: [http://localhost:5173](http://localhost:5173)

---

## Default Demo Credentials

- **Email**: `aaditya@glownaturals.com`
- **Password**: `password123`

---

## Authentication & Security Highlights

1. **Password Hashing**: Uses modern **Argon2** via `pwdlib`. Plain passwords are never stored.
2. **Access Tokens**: Short-lived (15 min) signed JWT tokens kept in client application memory.
3. **Session Persistence**: Server-side hashed refresh sessions delivered via `HttpOnly`, `SameSite=Lax` cookies with automatic single-flight rotation.
4. **Browser Reload**: Transparent session restoration on browser refresh prevents flashing login screens.
5. **Route Protection**: Unauthenticated requests to `/app/*` are guarded and redirected to `/login`, preserving return destination.
6. **Graceful Logout**: Connected to the existing confirmation modal with instant server-side revocation.
