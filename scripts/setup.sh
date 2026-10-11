#!/usr/bin/env bash
# Imboni — one-shot local setup (macOS/Linux/Git Bash). Run from the repository root: bash scripts/setup.sh
set -euo pipefail
PY=${PYTHON:-python3}
[ -d .venv ] || "$PY" -m venv .venv
if [ -f .venv/bin/python ]; then VPY=.venv/bin/python; else VPY=.venv/Scripts/python; fi
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install -r requirements-dev.txt
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example — edit DATABASE_URL."; }
"$VPY" -m backend.pipeline.build --fetch
"$VPY" scripts/init_db.py || echo "Database not initialised (see docs/DATABASE.md); the app still runs."
(cd frontend && npm ci && npm run build)
"$VPY" -m pytest -q
echo "Done. Start with: $VPY -m uvicorn backend.app.main:app --port 8000  (then open http://localhost:8000)"
