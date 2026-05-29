# Cadence

Monorepo with a Python backend (FastAPI) and a React frontend.

## Backend

```bash
cp .env.example .env
uv sync
uv run uvicorn cadence.main:app --reload
```

Health check: http://localhost:8000/health

## Frontend

`cadence-ui/` — to be scaffolded with Vite.
