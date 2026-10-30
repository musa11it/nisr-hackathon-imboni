# Architecture assessment and decision

*Assessment made on 2026-10-30, before the Streamlit transformation, by inspecting the repository's source,
data and configuration (not just file names).*

## 1. What existed

| Component | Location | State found |
|---|---|---|
| Reproducible data pipeline | `backend/pipeline/` | Working. Downloads public NISR/FinScope/Census/geoBoundaries files, records SHA-256, parses tables by printed labels, runs 189 validation checks (0 errors, 9 documented source inconsistencies), writes tidy outputs to `data/processed/`. |
| Validated processed data | `data/processed/`, `data/metadata/` | Committed. 1,746 observations, 104 indicators, 30-district/5-province GeoJSON. Raw files are git-ignored (publisher terms not stated). |
| Analytics | `backend/app/analytics.py` | Working. CIs from published SEs, z-tests vs national, Monte-Carlo rank intervals, MPI decomposition, Spearman correlations with Fisher-z CIs and BH q-values, experimental service-gap index. |
| Budget simulator | `backend/app/simulator.py` | Working. Pydantic-validated inputs, largest-remainder money allocation, reach capped by Census households × measured need, unit-cost sensitivity. |
| Q&A, reports | `backend/app/nlq.py`, `reports.py` | Working. Deterministic keyword Q&A (no LLM); ReportLab PDFs and CSV exports. |
| API | `backend/app/main.py` (FastAPI) | Working. Serves analytics from the processed files; the DB is used only for saved scenarios and a SQL mirror. |
| Database | `backend/app/db.py`, `models.py` | MySQL (XAMPP-style local) with automatic SQLite fallback. Not needed to view statistics. |
| Frontend | `frontend/` (React 19 + Vite + Tailwind, d3-geo, Recharts) | Working; builds and lints. |
| Tests | `tests/` | 57 pytest tests passing. |
| Deployment | `Dockerfile`, `render.yaml` | Prepared for Render; not deployed. |
| CI | — | **Missing.** |
| Streamlit | — | **Missing.** |

**Incomplete or weak points found**

* No automated CI; tests only ran on a developer machine.
* No Streamlit interface (the competition target), and hosting the React+FastAPI stack needs a paid/sleeping container.
* The pipeline crashed with a raw traceback if any source file was missing; there was no data inventory.
* Generated files were written with the OS line ending, so the checksums in `processed_manifest.json` matched only
  on Windows (git normalises to LF).
* Policy insights existed only as prose in the demo guide, not as data-driven, sourced output.
* EICV7 VUP microdata (catalog 121) and the NISR GIS portal were not in the source registry.

## 2. Decision: hybrid — Streamlit as the primary dashboard over the existing Python core

```
 NISR / FinScope / Census / geoBoundaries (public files)
        │  python -m backend.pipeline.build [--fetch] [--allow-partial]
        ▼
 backend/pipeline  ── inventory → parse → validate → quality summary ──►  data/processed/*.json|csv  (committed)
                                                                          data/metadata/*.json
        ┌──────────────────────────────────────────────────────────────────────┘
        ▼
 backend/app  (pure Python, no web framework needed)
   store.py · analytics.py · simulator.py · insights.py · nlq.py · reports.py
        │                                   │
        ▼                                   ▼
 streamlit_app.py + dashboard/        FastAPI main.py ──► React SPA (frontend/)
 (PRIMARY: Streamlit Community Cloud)  (preserved: Docker/Render; optional MySQL/SQLite for saved scenarios)
```

**Why hybrid rather than a full migration**

* All calculations already live in framework-independent Python modules. Streamlit imports them directly, so
  every number has exactly one implementation; nothing is duplicated in the dashboard.
* The React/FastAPI app works and is tested; deleting it would destroy functionality for no gain. It stays as an
  alternative deployment, and CI keeps it building.
* Streamlit needs **no database, secrets or network** at runtime: it reads the committed processed files. MySQL
  (local XAMPP) is not required for public deployment; scenarios in Streamlit are kept per browser session.
* No new infrastructure was introduced.

## 3. What was added or changed

| Area | Change |
|---|---|
| `streamlit_app.py`, `dashboard/` | New Streamlit dashboard: 9 pages (National, Geographic, MPI, Financial Inclusion, Simulator, Policy Insights, Data Explorer, Reports, Sources & Methods). `dashboard/logic.py` holds pure, unit-tested helpers; `charts.py` one visual grammar; `theme.py` the navy/teal identity shared with the React app. |
| `backend/app/insights.py` | Evidence-backed policy insights computed from the data (also exposed at `/api/insights`). |
| `backend/pipeline/inventory.py`, `quality.py` | Data inventory (`data/metadata/data_inventory.json`) and missing-value/precision summary (`data/processed/data_quality_summary.csv`). |
| `backend/pipeline/build.py`, `validate.py` | Pre-flight inventory; stops cleanly (no outputs touched) if sources are missing; `--allow-partial` builds without optional sources and records the gap as a validation warning; LF line endings for OS-independent checksums. |
| `backend/pipeline/sources.py` | Registered EICV7 VUP microdata (restricted) and the NISR GIS portal (reference only). |
| `backend/app/reports.py`, `main.py` | Profile CSV builder shared by API and dashboard; `/api/insights`. |
| `.github/workflows/ci.yml`, `ruff.toml` | CI: lint, processed-data checksum + validation check, import check, full test suite (including Streamlit page smoke tests), live Streamlit server smoke test, React lint/build. |
| `.streamlit/config.toml` | Theme and server settings (no secrets). |
| `tests/` | +44 tests (dashboard logic, pages, simulator interaction, charts, insights, pipeline pre-flight, manifest integrity). |
