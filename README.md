# Intervu

A production-quality portfolio project: practice interviews with AI-driven
questions and feedback.

## Stack

- **Frontend:** React + Vite + Tailwind CSS (v4) + React Router
- **Backend:** FastAPI + SQLAlchemy + SQLite

## Project status

Step 1 complete: project scaffolding, navigation between pages, and a
verified frontend/backend/database wiring. No AI, auth, or scoring logic
yet.

## Running locally

### Backend

```bash
cd backend
./venv/Scripts/activate      # Windows (PowerShell: venv\Scripts\Activate.ps1)
uvicorn app.main:app --reload --port 8000
```


### Frontend

```bash
cd frontend
npm run dev
```

