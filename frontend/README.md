# Imboni — frontend

React 19 + TypeScript + Vite + Tailwind CSS 4 single-page app. See the root `README.md` for the full project.

```bash
npm ci
npm run dev      # http://localhost:5173 — proxies /api to http://127.0.0.1:8000
npm run lint     # oxlint
npm run build    # type-check (tsc -b) + production bundle in dist/ (served by the FastAPI backend)
```

Set `VITE_API_BASE_URL` only when the API is hosted on a different origin.
