# Deployment

**Current status: not deployed.** Deployment needs the team's own hosting account. No live URL is claimed.

## Recommended: one container on Render (free plan)

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

## Alternative: separate frontend and backend

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
