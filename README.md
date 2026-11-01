# FOOD HAS A DEADLINE (FHD)

> **Tagline:** *Move food before time runs out.*  
> **Mission:** An AI-powered, perishability-aware food redistribution engine that matches expiring surplus food from donors to recipient organizations before spoilage occurs.

---

## 1. Project Overview

Every year, millions of tons of nutritious food are discarded by farms, supermarkets, and restaurants simply because traditional donation logistics operate too slowly. When a supplier has 100 kg of dairy expiring in 6 hours, traditional batch matching fails: food spoils in transit, recipient facilities lack refrigerated storage, or donors lack visibility into local intake capacities.

**Food Has a Deadline (FHD)** redefines food rescue as a time-critical logistics problem:
* **Deterministic Perishability Intelligence:** Mathematically computes decay rates, remaining shelf-life, and urgency scores without relying on LLM arithmetic.
* **Constrained Operations Research Optimization (Google OR-Tools):** Solves multi-supplier, multi-receiver capacitated allocation problems subject to time horizons, volume constraints, dietary requirements, and cold-chain capabilities.
* **Agentic AI Orchestration (Google Gemini API):** Synthesizes multi-factor operational data, invokes deterministic tools, simulates disruption scenarios, and explains complex distribution proposals to human coordinators.
* **Geospatial Dispatch Engine (OSM / OSRM / Leaflet):** Evaluates transit time viability and routing feasibility across supplier-receiver networks.
* **Human-in-the-Loop Governance:** AI and optimization engines produce *Proposals*; authorized human coordinators retain exclusive authority to commit transactions.

---

## 2. Technology Stack

### Frontend
* **Core:** React 19, TypeScript, Vite
* **Styling & UI:** Tailwind CSS, shadcn/ui, Lucide React
* **Routing:** React Router DOM
* **Geospatial & Maps:** Leaflet, React Leaflet, OpenStreetMap
* **Networking & Forms:** Axios, React Hook Form, Zod, `@hookform/resolvers`, `clsx`, `tailwind-merge`

### Backend
* **Runtime:** Python 3.12
* **Framework:** FastAPI, Uvicorn
* **Database & ORM:** PostgreSQL 16+, SQLAlchemy 2.0, Alembic, `psycopg` (binary)
* **Configuration & Validation:** Pydantic v2, Pydantic Settings, `python-dotenv`
* **Security & Auth:** `pwdlib[argon2]` (Argon2id password hashing), PyJWT
* **Testing:** pytest, pytest-asyncio, httpx

### AI, Optimization & Geospatial
* **Mathematical Optimization:** Google OR-Tools (Mixed-Integer Linear Programming)
* **Generative AI:** Google Gen AI SDK (`google-genai`), Gemini 2.0 / 1.5
* **Geospatial Routing:** OpenStreetMap, OSRM (Open Source Routing Machine), Haversine fallback

---

## 3. Repository Structure

```
food-has-a-deadline/
│
├── frontend/                     # React + TypeScript + Vite Client
│   ├── public/                   # Static assets & icons
│   ├── src/
│   │   ├── assets/               # Frontend media & icons
│   │   ├── components/           # UI & functional components
│   │   │   └── ui/               # shadcn/ui component primitives
│   │   ├── layouts/              # Root & role-based page layouts
│   │   ├── pages/                # Application views (Home, etc.)
│   │   ├── services/             # Axios API client & services
│   │   ├── hooks/                # Custom React hooks
│   │   ├── context/              # React context providers
│   │   ├── types/                # TypeScript interface definitions
│   │   ├── utils/                # Utility helpers (cn, formatters)
│   │   ├── App.tsx               # Route declarations
│   │   ├── index.css             # Tailwind base & CSS variables
│   │   └── main.tsx              # Application entry point
│   ├── components.json           # shadcn/ui configuration
│   ├── tailwind.config.js        # Tailwind CSS theme configuration
│   ├── tsconfig.json             # TypeScript project references
│   └── vite.config.ts            # Vite bundler configuration
│
├── backend/                      # FastAPI Python Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI entry point & CORS
│   │   ├── core/                 # Config & settings (Pydantic Settings)
│   │   ├── api/                  # API routers & endpoint definitions
│   │   ├── models/               # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/              # Pydantic v2 validation schemas
│   │   ├── repositories/         # Database persistence queries
│   │   ├── services/             # Core business logic services
│   │   ├── intelligence/         # Perishability decay calculation engine
│   │   ├── agent/                # Gemini tool-calling agent orchestrator
│   │   ├── optimisation/         # Google OR-Tools allocation solver
│   │   ├── geospatial/           # OSRM & Haversine routing services
│   │   └── database/             # SQLAlchemy engine & session maker
│   ├── alembic/                  # Database migration scripts
│   ├── tests/                    # pytest test suite
│   ├── requirements.txt          # Python dependencies
│   ├── alembic.ini               # Alembic migration configuration
│   └── .env.example              # Backend environment template
│
├── docs/                         # Technical Design Documentation
│   ├── SYSTEM_ARCHITECTURE.md    # High-level architecture & component breakdown
│   ├── DATABASE_DESIGN.md        # Relational schema, ER diagrams & constraints
│   ├── AI_AGENT_ARCHITECTURE.md  # Agent workflow, tool contracts & resilience
│   ├── MATCHING_AND_OPTIMISATION.md # OR-Tools MILP math & perishability engine
│   ├── API_SPECIFICATION.md      # Complete RESTful OpenAPI contract
│   ├── SECURITY_AND_RELIABILITY.md # Auth, RBAC, anti-overselling & reliability
│   └── IMPLEMENTATION_ROADMAP.md # 12-phase execution plan & hackathon criteria
│
├── docker-compose.yml            # Local PostgreSQL container service
├── .gitignore                    # Environment & artifact exclusions
├── .env.example                  # Monorepo environment variable template
└── README.md                     # Project documentation (this file)
```

---

## 4. Architecture Overview

```mermaid
flowchart LR
    Client["Frontend Client\n(React + TS + Leaflet)"] --> Gateway["API Gateway\n(FastAPI + JWT RBAC)"]
    Gateway --> Services["Business Services\n(Surplus, Demand, Proposal)"]
    Services --> Perish["Perishability Engine\n(Deterministic Decay)"]
    Services --> Geo["Geospatial Engine\n(OSRM + Haversine)"]
    Services --> OR["Google OR-Tools\n(MILP Solver)"]
    Services --> Agent["AI Redistribution Agent\n(Gemini Tool Calling)"]
    Services --> DB[(PostgreSQL 16+\nSQLAlchemy 2.0)]
```

### Detailed Architecture Specifications:
* [System Architecture Specification](file:///docs/SYSTEM_ARCHITECTURE.md)
* [Database Design & Relational Schema](file:///docs/DATABASE_DESIGN.md)
* [AI Agent Architecture & Tool Contracts (Module 9 Verified)](file:///docs/AI_AGENT_ARCHITECTURE.md)
* [Matching & OR-Tools Optimization Architecture (Module 8 Verified)](file:///docs/MATCHING_AND_OPTIMISATION.md)
* [API Specification & REST Contracts](file:///docs/API_SPECIFICATION.md)
* [Security, RBAC & Reliability Architecture](file:///docs/SECURITY_AND_RELIABILITY.md)
* [Implementation Roadmap & Evaluation Alignment](file:///docs/IMPLEMENTATION_ROADMAP.md)

---

## 5. Prerequisites

Before running the application on Windows, verify that the following are installed:
* **Python:** Python 3.12 (`py -3.12 --version`)
* **Node.js:** Node.js v20+ or v24+ (`node --version`)
* **npm:** npm v10+ or v11+ (`npm --version`)
* **Database:** Local PostgreSQL 16+ running on port 5432, or Docker Desktop (`docker --version`)

---

## 6. Environment Variable Setup

The repository includes `.env.example` templates.

### 1. Root & Backend Environment
Create `backend/.env` (or copy from `backend/.env.example`):
```powershell
Copy-Item backend\.env.example backend\.env
```
Ensure `backend/.env` contains:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/food_has_a_deadline
SECRET_KEY=dev-secret-key-food-has-a-deadline-hackathon-2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GEMINI_API_KEY=
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development
```
*(Note: A `GEMINI_API_KEY` is optional for startup; the system automatically falls back to deterministic rule-based coordination if absent).*

### 2. Frontend Environment
Create `frontend/.env` (or copy from `frontend/.env.example`):
```powershell
Copy-Item frontend\.env.example frontend\.env
```
Ensure `frontend/.env` contains:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 7. PostgreSQL Database Setup

### Option A: Using Docker Compose
If Docker Desktop is running, launch the PostgreSQL database container with persistent volume:
```powershell
docker compose up -d
```

### Option B: Using Local PostgreSQL Installation
If using a locally installed PostgreSQL server on port 5432, create the database using `psql` or `createdb`:
```powershell
createdb -U postgres -h localhost food_has_a_deadline
```
Update the password in `backend/.env` to match your local PostgreSQL credentials:
```env
DATABASE_URL=postgresql+psycopg://postgres:<your_password>@localhost:5432/food_has_a_deadline
```

---

## 8. Backend Installation & Startup

Open a Windows PowerShell terminal:

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment (created in Module 0)
.\.venv\Scripts\Activate.ps1

# 3. Verify dependencies are installed
python -m pip install -r requirements.txt

# 4. Run test suite
python -m pytest

# 5. Start Uvicorn development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be live at:
* API Root: `http://127.0.0.1:8000/`
* Interactive API Documentation (Swagger / OpenAPI): `http://127.0.0.1:8000/docs`
* Health Check Endpoint: `http://127.0.0.1:8000/health`

---

## 9. Frontend Installation & Startup

Open a second Windows PowerShell terminal:

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Verify TypeScript build
npm run build

# 4. Start Vite development server
npm run dev
```

The frontend web application will be live at:
* Local URL: `http://localhost:5173/`

---

## 10. Health Check & Diagnostics

Query the backend health-check endpoint:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" | ConvertTo-Json
```

Expected response payload:
```json
{
  "status": "healthy",
  "app_name": "Food Has a Deadline",
  "version": "0.1.0",
  "environment": "development",
  "ai_configured": false,
  "database": {
    "status": "connected",
    "connected": true,
    "details": "PostgreSQL database connection verified"
  }
}
```
*(If PostgreSQL is not yet running or configured, `"database"` will report `"disconnected"` while the API remains healthy and functional).*
