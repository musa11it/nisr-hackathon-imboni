# Imboni — one-shot local setup (Windows PowerShell).  Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example — edit DATABASE_URL." }
.\.venv\Scripts\python -m backend.pipeline.build --fetch
.\.venv\Scripts\python scripts/init_db.py
Push-Location frontend; npm ci; npm run build; Pop-Location
.\.venv\Scripts\python -m pytest -q
Write-Host "`nDone. Start with:  .\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000   (then open http://localhost:8000)"
