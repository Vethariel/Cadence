# Cadence

Monorepo with a Python backend (FastAPI) and a React frontend.

## Backend

```bash
cp .env.example .env
uv sync
uv run uvicorn cadence.main:app --reload
```

Health check: http://localhost:8000/health

### Benchmark (corpus MIDI + prompts alineados)

Los prompts de ejemplo viven en `examples/benchmark_prompts.json` (uno por arquetipo de `examples/*.mid`). Tras generar en la UI o con la API, evalúa:

```bash
PYTHONPATH=. uv run --no-sync python -m cadence.analysis.midi_benchmark --suite
PYTHONPATH=. uv run --no-sync python -m cadence.analysis.test_benchmark_examples
```

Convención de export: `output/cadence_<id>_<timestamp>.rsong` donde `<id>` es `sparse_loop`, `dense_dance`, etc.

Plan de mejora (benchmark + textura/orquestación): [docs/IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md)

## Frontend

`cadence-ui/` — to be scaffolded with Vite.
