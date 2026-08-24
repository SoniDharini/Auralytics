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
│   │       │   ├── campaign_discovery.py # Campaign-scoped YouTube creator discovery
│   │       │   ├── influencers.py   # Creator reads & shortlisting
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

## Real Creator Discovery (YouTube Data API v3)

Creator discovery is campaign-scoped and reads exclusively from live platform data.
No influencer is ever seeded, mocked, or fabricated — fields the API does not return
are stored as `NULL` and rendered as `N/A`.

### Configuration

Add a YouTube Data API v3 key to `backend/.env` (backend only — it is never sent to
the browser and never appears in an API response or log line):

```env
YOUTUBE_API_KEY=your-key-here
YOUTUBE_DISCOVERY_MAX_CREATORS=30
YOUTUBE_MAX_SEARCH_QUERIES=4
YOUTUBE_RECENT_VIDEO_SAMPLE=8
INFLUENCER_CACHE_TTL_HOURS=6
```

### Endpoints

| Method | URL | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/campaigns/{id}/discover-creators` | Run the pipeline against YouTube (`?refresh=true` bypasses cached stats) |
| `GET` | `/api/v1/campaigns/{id}/influencers` | Read already-discovered creators from PostgreSQL |
| `GET` | `/api/v1/campaigns/{id}/influencers/{influencer_id}` | One creator plus its campaign match breakdown |
| `PATCH` | `/api/v1/campaigns/{id}/influencers/{influencer_id}` | Persist status: `DISCOVERED` / `SHORTLISTED` / `REJECTED` / `CONTACTED` |

All routes require a JWT and resolve the campaign through `campaign.owner_id == current_user.id`.

### Pipeline

```
campaign brief
  -> CampaignQueryBuilder            keywords + interests + location -> <= 4 queries
  -> search.list (type=channel)      100 quota units per query
  -> deduplicate by channel id
  -> channels.list (batched by 50)   snippet, statistics, contentDetails, brandingSettings
  -> subscriber min/max filter       applied BEFORE per-channel video calls
  -> playlistItems + videos.list     5-10 recent uploads per surviving channel
  -> derived metrics                 avg views/likes/comments, engagement rate
  -> CreatorScoringService           explainable weighted score (0-100)
  -> UPSERT influencers              unique on (platform, external_id)
  -> UPSERT campaign_influencers     per-campaign score, query and status
```

### Match scoring

Deterministic and fully explainable. Weights: keyword relevance 30, subscriber
suitability 25, engagement 20, publishing activity 15, location 10. When a signal is
unavailable (hidden subscriber count, no published country, no video statistics) the
factor is skipped and its weight is redistributed, so creators are never penalised for
data YouTube does not publish. Every factor is stored with its explanation in
`campaign_influencers.match_reasons` and surfaced in the UI.

### Quota behaviour

`search.list` costs 100 units against the default 10,000/day allowance; the other calls
cost 1 each. A full run with four queries and 25 creators costs roughly 450 units.
Opening the discovery page issues no YouTube requests at all — it reads PostgreSQL.
Statistics younger than `INFLUENCER_CACHE_TTL_HOURS` are reused unless `?refresh=true`.

---

## AI Agents (Groq)

Shared intelligence provider for all agents. PostgreSQL + YouTube remain the source of
truth; Groq only reasons over structured backend context.

### Environment

```env
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1
AI_REQUEST_TIMEOUT=60
AI_MAX_RETRIES=2
```

Never set `VITE_GROQ_API_KEY`. Keys stay backend-only.

### Milestone endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/ai/status` | Groq configured/reachable probe (auth required, no secrets) |
| `POST` | `/api/v1/campaigns/{id}/agents/start` | Supervisor advances workflow (Strategy first) |
| `POST` | `/api/v1/campaigns/{id}/agents/strategy` | Run Strategy Agent explicitly |
| `GET` | `/api/v1/campaigns/{id}/agents/strategy` | Latest persisted strategy JSON |
| `GET` | `/api/v1/campaigns/{id}/agents/runs` | Campaign-scoped agent runs |
| `GET` | `/api/v1/agent-runs` | Current user's agent runs |

### First milestone flow

```
Campaign (PostgreSQL)
  -> Supervisor (deterministic workflow_state)
  -> Strategy Agent
  -> Shared GrokProvider
  -> Pydantic + budget validation
  -> campaign_strategies + agent_runs
  -> Agent Center / Campaign AI Strategy tab
```

Discovery, Outreach, Contract, Performance, and Optimization agents are scaffolded in
the architecture but intentionally not auto-executed until Strategy is stable.

---


## Demo Credentials

- **Email**: `aaditya@glownaturals.com`
- **Password**: `password123`

---

## Running Tests

```bash
pytest -v
```
