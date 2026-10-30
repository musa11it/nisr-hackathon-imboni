# Deployment

**Current status: not deployed.** Deployment needs the team's own hosting account. No live URL is claimed.

## Recommended: Streamlit Community Cloud (Streamlit dashboard)

**Entrypoint:** `streamlit_app.py` (repository root). **Dependencies:** `requirements.txt` (root).
**Secrets:** none — the dashboard reads the committed `data/processed/` and `data/metadata/` files and needs no
database, API key or network access at runtime.

Pre-flight (all verified locally on 2026-10-30):

* No absolute paths: all file access goes through `pathlib` relative to the repository
  (`backend/pipeline/paths.py`, `streamlit_app.py`).
* No MySQL/XAMPP dependency: the dashboard never imports the database layer.
* `.env` and `.streamlit/secrets.toml` are git-ignored; `.streamlit/config.toml` contains only theme/server settings.
* Cold start renders the first page in ≈ 2 s locally; datasets are cached with `st.cache_resource`/`st.cache_data`.

Steps (per https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy):

1. Make sure the branch you deploy contains `streamlit_app.py`, `dashboard/`, `backend/`, `data/processed/`,
   `data/metadata/`, `.streamlit/config.toml` and `requirements.txt`, and that it is pushed to
   `https://github.com/musa11it/nisr-hackathon-imboni`.
2. Sign in at **https://share.streamlit.io** with the GitHub account that owns the repository, and authorise access.
3. Click **Create app** → **Yup, I have an app**.
4. Repository: `musa11it/nisr-hackathon-imboni` · Branch: the branch you pushed (e.g. `main`) ·
   Main file path: `streamlit_app.py` · App URL: optional custom subdomain (e.g. `imboni`).
5. **Advanced settings** → Python version **3.13** (the version the pinned requirements were tested with; the
   default is 3.12). Leave **Secrets** empty. Save.
6. Click **Deploy** and watch the build log; installing the scientific stack takes a few minutes.
7. Verify: all nine pages open from the sidebar, the district map renders, the simulator's allocation meter
   reaches 100%, and CSV/PDF downloads work.

Updating data: run the pipeline locally (`python -m backend.pipeline.build --fetch`), run the tests, commit
`data/processed/` and `data/metadata/`, and push — Community Cloud redeploys automatically.

## Alternative: one container on Render (React + FastAPI)

The `Dockerfile` builds the React app (Node 24) and runs FastAPI (Python 3.13), which serves both `/api/*` and
the SPA, so there is a single URL and no CORS configuration for the browser.

1. Push the repository to GitHub (public, as required by the hackathon). Make sure `.env` is not committed
   (`git check-ignore .env` should print `.env`).
2. Commit `data/processed/` and `data/metadata/` (the build uses them; raw files are not needed at runtime).
3. Render → **New → Blueprint** → select the repo. `render.yaml` defines the service, health check `/api/health`
   and `APP_ENV=production`.
4. Optional persistence: set `DATABASE_URL` to a managed MySQL instance (e.g. Aiven, PlanetScale-compatible MySQL,
   Railway). Without it, scenarios are stored in SQLite inside the container and are lost on redeploy.
5. After deploy, set `CORS_ORIGINS` to the service URL and verify:
   * `https://<service>.onrender.com/api/health` → `{"status":"ok", ...}`
   * the dashboard, explorer, simulator export (CSV/PDF) and a profile PDF.

Free Render services sleep when idle; the first request can take ~1 minute.

## Alternative: separate frontend and backend (React + FastAPI)

* Backend: any Python host (Render/Railway/Fly.io) with
  `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
* Frontend: Netlify/Vercel/GitHub Pages — build with `VITE_API_BASE_URL=https://<api-host>` and add an SPA
  fallback rule (all paths → `index.html`). Set the backend's `CORS_ORIGINS` to the frontend origin.

## Local Docker

```bash
docker build -t imboni .
docker run -p 8000:8000 imboni        # http://localhost:8000
```

(On the development machine the Docker daemon was not running, so the image build was not tested there; the same
steps — frontend build and production-mode API serving the SPA — were verified without Docker.)

## Production checklist

* `APP_ENV=production` (disables `/api/docs`, redacts DB errors).
* Secrets only in the host's environment settings — never in the repo, frontend bundle or logs.
* Re-run `python -m backend.pipeline.build --fetch` and the tests before each data refresh, then redeploy.
* CI (`.github/workflows/ci.yml`) must be green; it checks that committed processed files match the manifest.
* The Docker image also installs the Streamlit packages (one shared `requirements.txt`); this adds size but no
  runtime behaviour to the FastAPI container.
