# Imboni — Rwanda's Data-to-Action Intelligence Platform

> **From Data to Development Action**
> Team **DataMinds** · NISR 2026 Big Data Hackathon · Track 2: *Financial Inclusion & Poverty Reduction*

Imboni turns Rwanda's official poverty and financial-inclusion statistics into explainable evidence: where
deprivation is concentrated, how certain the estimates are, and what a development budget could reach.

> **Independence statement.** Imboni is a student project. It is **not** an official NISR product and is not
> endorsed by NISR. All statistics are reproduced from cited public publications; values Imboni derives are
> labelled *calculated*, values transcribed from figures are labelled *official · transcribed*, and simulator
> outputs are labelled *illustrative*.

---

## 1. Problem and users

EICV7 (2023/24) measures poverty two ways — **monetary poverty** (27.4%) and **multidimensional poverty
incidence** (30.5%). Only 14.3% of people are poor on both, so programmes targeted on one lens miss many people
visible only in the other. District planners, MINECOFIN/MINALOC analysts, development partners and civil society
need to see *which* deprivations dominate *where*, *how reliable* district figures are, and *what a budget could
plausibly reach* — without over-reading uncertain numbers or confusing different concepts.

## 2. What makes it different

| | |
|---|---|
| **Uncertainty-aware geography** | 30 district estimates with NISR's own standard errors → 95% CIs, approximate significance tests vs national, and Monte-Carlo **rank intervals** so "worst district" claims are not over-read. |
| **Validated pipeline** | 189 automated checks: 17 published benchmarks, M0 = H × A, Σ w·CH ≈ M0, overlap margins, Census district sums, CI coherence, ranges, duplicates. It **found an inconsistency** in NISR's MPI contribution tables (B.7–B.9), which Imboni documents rather than silently "fixes". |
| **Need-anchored budget simulator** | Allocations reconcile to the franc (largest-remainder rounding); reach is capped by measured need (Census households × EICV7/FinScope deprivation rates); unit-cost sensitivity; save, compare, export CSV/PDF. Explicitly *not* a poverty-reduction forecast. |
| **Honest financial inclusion** | FinScope 2024 access strand for all 30 districts, EICV7 household savings/MoMo accounts by poverty status, VUP payment channels — and a table of variables that are collected but **not published** (credit, loan sources…), shown as unavailable rather than estimated. |
| **Source-grounded Q&A** | Deterministic natural-language explorer — no LLM or API key; every answer cites its table. |

## 3. Architecture

**Hybrid:** a Streamlit dashboard is the primary interface; it imports the same Python analytics as the
FastAPI backend, which still serves the React app. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the
assessment and decision.

```
 official NISR files ──► backend/pipeline (inventory → parse → validate → quality) ──► data/processed/*.json|csv
                                                                                          │ (committed)
                    backend/app: store · analytics · simulator · insights · nlq · reports ◄┘
                         │                                          │
   streamlit_app.py + dashboard/  (PRIMARY)          FastAPI main.py ──► React + Vite SPA (frontend/)
   no database, no secrets, no network at runtime    SQLAlchemy ──► MySQL or SQLite fallback (saved scenarios)
```

* Every statistic is computed once, in `backend/app`, from the validated processed files. Neither interface needs
  the database to show statistics; Streamlit does not use it at all.
* The Docker image (one container serving `/api/*` and the React build) remains available as an alternative.

**Stack:** Python 3.13 · Streamlit · Plotly · pandas · FastAPI · SQLAlchemy 2 · SciPy/NumPy · ReportLab · openpyxl ·
pdfplumber · React 19 · TypeScript · Vite 8 · Tailwind CSS 4 · Recharts · d3-geo.

## 4. Folder structure

```
nisr-hachathon/
├── streamlit_app.py    Streamlit entrypoint (navigation, theme, sidebar)
├── dashboard/          Streamlit pages (views/), charts.py, theme.py, ui.py, data.py (cached access), logic.py (pure helpers)
├── backend/
│   ├── app/            analytics.py, simulator.py, insights.py, nlq.py, reports.py, store.py; FastAPI main.py, db.py, models.py
│   └── pipeline/       sources.py (registry), fetch.py, inventory.py, parse_eicv.py, parse_pdf.py, validate.py, quality.py, build.py
├── frontend/           React SPA (src/pages, src/components, src/lib), public/images (CC0 photos + credits)
├── data/
│   ├── raw/            original files, unchanged (downloaded, not committed)
│   ├── processed/      observations.csv/json, indicators.json, sources.json, validation_report.json, data_quality_summary.csv, geo/
│   └── metadata/       retrieval_log.json (URLs, dates, SHA-256), data_inventory.json, processed_manifest.json
├── docs/               architecture, methodology, data sources & dictionary, deployment, demo guide, limitations, AI disclosure
├── scripts/            setup.ps1 / setup.sh, init_db.py
├── tests/              pytest suite (pipeline, analytics, simulator, API, dashboard pages, charts)
├── .github/workflows/  ci.yml — lint, data checks, tests, Streamlit + React smoke builds
├── .streamlit/         config.toml (theme; no secrets)
├── Dockerfile · render.yaml · requirements*.txt · ruff.toml · .env.example
```

## 5. Run it locally

**Prerequisites:** Python 3.13 (tested; 3.11+ likely works but is untested). Node.js 20+ (tested with Node 24)
and MySQL 8 are needed only for the React/FastAPI variant.

**Streamlit dashboard (primary, no database or `.env` needed):**
```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt          # macOS/Linux: .venv/bin/pip
.venv/Scripts/streamlit run streamlit_app.py                # http://localhost:8501
```
The committed `data/processed/` is enough to run it. To rebuild the data, see §7.

**React + FastAPI variant:**
```bash
# one-shot (Windows):   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
# one-shot (macOS/Linux/Git Bash):  bash scripts/setup.sh

# or step by step
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt          # macOS/Linux: .venv/bin/pip
cp .env.example .env                                        # then edit DATABASE_URL (see §6)
.venv/Scripts/python -m backend.pipeline.build --fetch      # download official files + build + validate
.venv/Scripts/python scripts/init_db.py                     # create tables, mirror reference data
cd frontend && npm ci && cd ..
```

**Development (two terminals):**
```bash
.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000   # API + docs at /api/docs
cd frontend && npm run dev                                                  # http://localhost:5173 (proxies /api)
```
**Production-like (single server):** `cd frontend && npm run build`, then
`APP_ENV=production .venv/Scripts/python -m uvicorn backend.app.main:app --port 8000` → http://localhost:8000.

**Tests and checks:**
```bash
.venv/Scripts/python -m pytest -q          # 101 tests, incl. Streamlit page smoke tests (streamlit.testing)
.venv/Scripts/ruff check .                 # lint (ruff.toml)
cd frontend && npx tsc -b && npm run lint && npm run build
```
GitHub Actions (`.github/workflows/ci.yml`) runs the same checks on every push and pull request, plus a check that
the committed processed files match `processed_manifest.json` and a live `streamlit run` health check. CI never
downloads NISR data and needs no secrets.

## 6. Configuration and database

All configuration is via environment variables (`.env`, never committed; template in `.env.example`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | e.g. `mysql+pymysql://<user>:<password>@localhost:3306/nisr-hachathon` (URL-encode special characters) |
| `DB_FALLBACK_ENABLED` / `DB_FALLBACK_URL` | Use SQLite if the primary DB is unreachable (logged, visible at `/api/health`) |
| `DB_CREATE_DATABASE` | Run `CREATE DATABASE IF NOT EXISTS` with a validated, backtick-quoted name (hyphen-safe) |
| `CORS_ORIGINS`, `APP_ENV`, `LOG_LEVEL` | CORS allow-list; `development` enables `/api/docs`; log level |
| `VITE_API_BASE_URL` (frontend) | Only needed if the frontend is hosted separately from the API |

The app never creates MySQL users, changes passwords or drops data. Tables are created with
`Base.metadata.create_all` (additive). See **[docs/DATABASE.md](docs/DATABASE.md)** for the one-time DBA SQL.

### Security model

* **No user accounts or personal data.** Imboni stores only aggregate statistics and saved scenarios
  (name, budget, shares, unit costs).
* **Saved scenarios are visible to everyone using the same instance** (useful for side-by-side comparison in a
  demo). Deleting one requires a random token returned only to the browser that saved it (stored hashed
  server-side); the instance stores at most 1,000 scenarios.
* All inputs are validated with Pydantic (budget ceiling, share bounds, unique interventions, identifier
  patterns); SQL goes through the SQLAlchemy ORM; errors return JSON without stack traces.
* `APP_ENV=production` disables the interactive API docs and redacts database error details from `/api/health`.
* CORS is an explicit allow-list (`CORS_ORIGINS`); secrets live only in `.env` / the host's environment.

## 7. Data acquisition and processing

```bash
python -m backend.pipeline.inventory               # which source files are present / missing / restricted
python -m backend.pipeline.build --fetch           # download missing public files, then build + validate
python -m backend.pipeline.build                   # rebuild offline from data/raw
python -m backend.pipeline.build --allow-partial   # build without missing OPTIONAL sources (VUP, FinScope, Census)
```

The build downloads public files listed in [`backend/pipeline/sources.py`](backend/pipeline/sources.py), records
URL / date / SHA-256, keeps raw files unchanged, parses tables by their printed labels, validates, and writes
`data/processed/` (plus `data_quality_summary.csv`: missing values, published SEs and CV flags per indicator).
It first runs a data inventory: if a source is missing it **stops before writing anything** and lists what to
download. `--allow-partial` records skipped sources as validation warnings and in the manifest — they are never
filled with substitute values. The build **fails** on any pipeline error; documented *source* inconsistencies are
reported as warnings. Restricted EICV7 microdata are never downloaded — see
[docs/MICRODATA_IMPORT.md](docs/MICRODATA_IMPORT.md).

| Source (public) | Used for |
|---|---|
| EICV7 Main Indicators 2023/24 tables (NISR) | Poverty & 11 service indicators for 30 districts with SE/CI/CV/deff; households; transfers |
| EICV7 Multidimensional Poverty tables + report (NISR) | MPI H/A/M0, censored/uncensored headcounts, k-sensitivity, MPI×monetary overlap, framework & weights |
| EICV7 Poverty Profile tables (NISR) | 2017 (modelled) vs 2024 poverty, poverty gap, consumption, Gini/Theil, savings & MoMo accounts, shocks |
| EICV7 VUP thematic tables (NISR) | VUP coverage, payment channels (SACCO/MoMo), timeliness, FS loans |
| FinScope Rwanda 2024 (NISR/AFR/BNR/MINECOFIN) | Financial access strand — national, area, sex, province, 30 districts (transcribed from figures) |
| Census 2022 (PHC5) main indicators (NISR) | Private households and household size by district (simulator denominators) |
| geoBoundaries ADM1/ADM2 (CC BY 4.0) | Map geometry |

Full registry with checksums: in-app **Sources & methods** page and [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## 8. Methodology, validation, limitations

* [docs/METHODOLOGY.md](docs/METHODOLOGY.md) — every formula, the official MPI framework, statistical tests,
  simulator arithmetic, experimental index, visual-encoding choices.
* [docs/LIMITATIONS.md](docs/LIMITATIONS.md) — known limitations and future improvements.
* Reproduce any chart: each chart's numbers come from an API endpoint (e.g. `/api/map?indicator=poverty_rate&level=district&format=csv`)
  which in turn reads `data/processed/observations.csv`; calculated values are derived in `backend/app/analytics.py`.

## 9. Deployment

**Recommended: Streamlit Community Cloud** — repository `musa11it/nisr-hackathon-imboni`, main file
`streamlit_app.py`, Python 3.13, no secrets required. Step-by-step instructions are in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). A `Dockerfile` and Render Blueprint (`render.yaml`) remain for the
React/FastAPI variant. **Status: not yet deployed** — deploying requires the team's own account; no live URL is
claimed.

## 10. AI-assistance disclosure

The hackathon requires disclosure of AI use. A completed draft is in [docs/AI_DISCLOSURE.md](docs/AI_DISCLOSURE.md);
the team must review and finalise it before submission. The application itself calls no external AI service.

## 11. Rights

See [LICENSE.md](LICENSE.md). Data remain the property of their publishers; photographs are CC0 (credits in
`frontend/public/images/CREDITS.md`); boundaries are CC BY 4.0 (geoBoundaries).
