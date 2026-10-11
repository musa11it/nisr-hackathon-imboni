"""Imboni API — FastAPI application.

Run (dev):  uvicorn backend.app.main:app --reload --port 8000
Docs (dev): http://localhost:8000/api/docs
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from . import analytics, nlq, reports, simulator
from .config import get_settings
from .db import SessionLocal, db_status, init_engine
from .models import Indicator, Observation, Scenario, Source
from .store import DataStore, get_store

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper(),
                    format='{"t":"%(asctime)s","lvl":"%(levelname)s","log":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("imboni.api")
VERSION = "1.0.0"
MAX_SCENARIOS = 1000  # simple guard against unbounded growth on a public demo
LEVELS = Literal["national", "area", "province", "district", "quintile"]


def seed_database(store: DataStore) -> dict:
    """Mirror processed reference data into the database (our own tables only)."""
    with SessionLocal() as s:
        n = s.scalar(select(func.count()).select_from(Observation))
        if n == len(store.observations):
            return {"seeded": False, "observations": n}
        s.execute(delete(Observation))
        s.execute(delete(Indicator))
        s.execute(delete(Source))
        s.add_all(Source(id=x["id"], title=x["title"][:300], publisher=x["publisher"][:300], url=x["url"],
                         period=x.get("period"), access=(x.get("access") or "")[:200],
                         sha256=(x.get("retrieval") or {}).get("sha256"),
                         retrieved_at=(x.get("retrieval") or {}).get("retrieved_at"), citation=x.get("citation"))
                  for x in store.sources)
        s.add_all(Indicator(id=i["id"], name=i["name"], theme=i["theme"], unit=i["unit"], universe=i["universe"],
                            definition=i["definition"], period=i["period"], source_id=i["source_id"],
                            table_ref=i["table_ref"], status=i["status"]) for i in store.indicators)
        s.add_all(Observation(**{k: o[k] for k in ("indicator_id", "level", "geo_id", "geo_name", "period", "value",
                                                   "se", "ci_low", "ci_high", "cv", "deff", "status", "source_id",
                                                   "table_ref")},
                              breakdown=o.get("breakdown") or "", flags=(o.get("flags") or "")[:400])
                  for o in store.observations)
        s.commit()
        return {"seeded": True, "observations": len(store.observations)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = get_store()
    try:
        init_engine()
        info = seed_database(store)
        log.info("database ready: %s %s", db_status()["backend"], info)
    except Exception as exc:  # the API stays usable from processed files
        log.error("database initialisation failed: %s", str(exc)[:200])
    yield


app = FastAPI(title="Imboni API", version=VERSION, lifespan=lifespan,
              description="Rwanda's Data-to-Action Intelligence Platform — DataMinds (student team). "
                          "Not an official NISR service.",
              docs_url="/api/docs" if settings.is_dev else None, redoc_url=None,
              openapi_url="/api/openapi.json" if settings.is_dev else None)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "X-Scenario-Token"], allow_credentials=False)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - t0) * 1000)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


@app.exception_handler(KeyError)
async def not_found(_: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"error": "not_found", "detail": f"Unknown: {exc.args[0] if exc.args else ''}"})


@app.exception_handler(RequestValidationError)
async def invalid(_: Request, exc: RequestValidationError):
    errs = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": errs})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "Unexpected server error."})


def store_dep() -> DataStore:
    return get_store()


def _slug_ok(v: str) -> str:
    if not re.fullmatch(r"[a-z0-9_]{1,40}", v):
        raise HTTPException(422, "invalid identifier")
    return v


def _public_db_status() -> dict:
    st = db_status()
    if not settings.is_dev and st.get("fallback_reason"):
        st["fallback_reason"] = "primary database unavailable"
    return st


def _file(content: bytes | str, media: str, name: str) -> Response:
    data = content.encode("utf-8-sig") if isinstance(content, str) else content
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ------------------------------------------------------------------ meta
@app.get("/api/health", tags=["meta"])
def health(store: DataStore = Depends(store_dep)):
    return {"status": "ok", "version": VERSION, "data": {"observations": len(store.observations),
                                                          "generated_at": store.manifest.get("generated_at")},
            "database": _public_db_status()}


@app.get("/api/meta", tags=["meta"])
def meta(store: DataStore = Depends(store_dep)):
    return {"app": "Imboni", "team": "DataMinds", "version": VERSION, "manifest": store.manifest,
            "validation": store.validation["summary"], "database": _public_db_status(),
            "disclaimer": reports.DISCLAIMER}


@app.get("/api/sources", tags=["meta"])
def sources(store: DataStore = Depends(store_dep)):
    return store.sources


@app.get("/api/indicators", tags=["data"])
def indicators(theme: str | None = None, store: DataStore = Depends(store_dep)):
    return [i for i in store.indicators if theme is None or i["theme"] == theme]


@app.get("/api/indicators/{indicator_id}", tags=["data"])
def indicator(indicator_id: str, store: DataStore = Depends(store_dep)):
    meta_ = store.indicator_index.get(indicator_id)
    if not meta_:
        raise KeyError(indicator_id)
    return {**meta_, "source": store.source_ref(meta_["source_id"]),
            "observations": [analytics.enrich(store, o) for o in store.query(indicator_id)]}


@app.get("/api/observations", tags=["data"])
def observations(indicator: str | None = None, level: str | None = None, geo_id: str | None = None,
                 format: Literal["json", "csv"] = "json", store: DataStore = Depends(store_dep)):
    rows = store.observations if indicator is None else store.query(indicator)
    rows = [o for o in rows if (level is None or o["level"] == level) and (geo_id is None or o["geo_id"] == geo_id)]
    if format == "csv":
        return _file(reports.to_csv(rows, preamble=["Imboni (DataMinds) export of official NISR statistics. "
                                                    "status: official | official_transcribed | calculated."]),
                     "text/csv", f"imboni_observations{'_' + indicator if indicator else ''}.csv")
    return rows


@app.get("/api/geo/{level}", tags=["data"])
def geo(level: Literal["province", "district"], store: DataStore = Depends(store_dep)):
    return store.geo[level]


# ------------------------------------------------------------------ analytics
@app.get("/api/dashboard", tags=["analytics"])
def dashboard(store: DataStore = Depends(store_dep)):
    return analytics.dashboard(store)


@app.get("/api/map", tags=["analytics"])
def map_layer(indicator: str, level: Literal["province", "district"] = "district",
              format: Literal["json", "csv"] = "json", store: DataStore = Depends(store_dep)):
    layer = analytics.map_layer(store, indicator, level)
    if format == "csv":
        cols = ["geo_id", "geo_name", "value", "se", "ci_low", "ci_high", "cv", "rank", "rank_low", "rank_high",
                "period", "status", "table_ref", "flags"]
        return _file(reports.to_csv(layer["rows"], cols, [f"{layer['indicator']['name']} by {level}",
                                                          f"Source: {layer['indicator']['source_id']} {layer['indicator']['table_ref']}"]),
                     "text/csv", f"imboni_{indicator}_{level}.csv")
    return layer


@app.get("/api/profile/{level}/{geo_id}", tags=["analytics"])
def profile(level: Literal["national", "province", "district"], geo_id: str, store: DataStore = Depends(store_dep)):
    return analytics.profile(store, level, _slug_ok(geo_id))


@app.get("/api/mpi", tags=["analytics"])
def mpi(store: DataStore = Depends(store_dep)):
    return analytics.mpi_summary(store)


@app.get("/api/financial-inclusion", tags=["analytics"])
def financial_inclusion(store: DataStore = Depends(store_dep)):
    return analytics.financial_inclusion(store)


@app.get("/api/analysis/correlations", tags=["analytics"])
def correlations(level: Literal["district", "province"] = "district", indicators: str | None = None,
                 store: DataStore = Depends(store_dep)):
    inds = [i for i in indicators.split(",") if i in store.indicator_index] if indicators else None
    return analytics.correlations(store, inds, level)


@app.get("/api/analysis/composite", tags=["analytics"])
def composite(store: DataStore = Depends(store_dep)):
    return analytics.composite_index(store)


@app.get("/api/analysis/trends", tags=["analytics"])
def trends(store: DataStore = Depends(store_dep)):
    return analytics.trends(store)


@app.get("/api/analysis/data-quality", tags=["analytics"])
def data_quality(store: DataStore = Depends(store_dep)):
    return analytics.data_quality(store)


# ------------------------------------------------------------------ Q&A
class Question(BaseModel):
    question: str = Field(min_length=1, max_length=300)


@app.post("/api/ask", tags=["explorer"])
def ask(q: Question, store: DataStore = Depends(store_dep)):
    return nlq.ask(store, q.question)


@app.get("/api/ask/examples", tags=["explorer"])
def ask_examples():
    return nlq.EXAMPLES


# ------------------------------------------------------------------ simulator
@app.get("/api/simulator/catalogue", tags=["simulator"])
def sim_catalogue():
    return simulator.catalogue()


@app.get("/api/simulator/context/{level}/{geo_id}", tags=["simulator"])
def sim_context(level: Literal["national", "province", "district"], geo_id: str, store: DataStore = Depends(store_dep)):
    return simulator.context(store, level, _slug_ok(geo_id))


@app.get("/api/simulator/suggest/{level}/{geo_id}", tags=["simulator"])
def sim_suggest(level: Literal["national", "province", "district"], geo_id: str,
                ids: str = Query(..., description="comma-separated intervention ids"),
                store: DataStore = Depends(store_dep)):
    chosen = [i for i in ids.split(",") if i in simulator.INTERVENTIONS]
    if not chosen:
        raise HTTPException(422, "no valid intervention ids")
    return {"shares": simulator.suggest_need_weighted(store, level, _slug_ok(geo_id), chosen),
            "method": "Shares proportional to each intervention's estimated need rate in the target area "
                      "(a transparent default, not an optimisation)."}


@app.post("/api/simulator/run", tags=["simulator"])
def sim_run(inp: simulator.ScenarioInput, store: DataStore = Depends(store_dep)):
    return simulator.run_scenario(store, inp)


def _sim_sources(store):
    return [store.source_index[s] for s in ("rphc5_main", "eicv7_mi", "eicv7_mpi", "finscope_2024", "eicv7_vup")]


@app.post("/api/simulator/export", tags=["simulator"])
def sim_export(inp: simulator.ScenarioInput, format: Literal["csv", "pdf"] = "csv", store: DataStore = Depends(store_dep)):
    res = simulator.run_scenario(store, inp)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", inp.name)[:40] or "scenario"
    if format == "pdf":
        return _file(reports.scenario_pdf(res, _sim_sources(store)), "application/pdf", f"imboni_{safe}.pdf")
    return _file(reports.scenario_csv(res), "text/csv", f"imboni_{safe}.csv")


@app.get("/api/scenarios", tags=["simulator"])
def list_scenarios():
    try:
        with SessionLocal() as s:
            rows = s.scalars(select(Scenario).order_by(Scenario.created_at.desc()).limit(100)).all()
            return [{"id": r.id, "name": r.name, "created_at": r.created_at.isoformat() + "Z", "summary": r.summary,
                     "inputs": r.inputs} for r in rows]
    except Exception:
        raise HTTPException(503, "Scenario storage unavailable (database not initialised).")


@app.post("/api/scenarios", tags=["simulator"], status_code=201)
def save_scenario(inp: simulator.ScenarioInput, store: DataStore = Depends(store_dep)):
    res = simulator.run_scenario(store, inp)
    token = secrets.token_urlsafe(24)
    try:
        with SessionLocal() as s:
            if (s.scalar(select(func.count()).select_from(Scenario)) or 0) >= MAX_SCENARIOS:
                raise HTTPException(507, "Scenario storage is full on this demo instance.")
            row = Scenario(name=inp.name, inputs=inp.model_dump(),
                           summary={**res["summary"], "geography": res["context"]["name"]},
                           delete_token_hash=hashlib.sha256(token.encode()).hexdigest())
            s.add(row)
            s.commit()
            return {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat() + "Z",
                    "summary": row.summary, "delete_token": token}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Scenario storage unavailable (database not initialised).")


@app.get("/api/scenarios/{scenario_id}", tags=["simulator"])
def get_scenario(scenario_id: int, store: DataStore = Depends(store_dep)):
    with SessionLocal() as s:
        row = s.get(Scenario, scenario_id)
        if not row:
            raise HTTPException(404, "scenario not found")
        return {"id": row.id, **simulator.run_scenario(store, simulator.ScenarioInput(**row.inputs))}


@app.delete("/api/scenarios/{scenario_id}", tags=["simulator"], status_code=204)
def delete_scenario(scenario_id: int, x_scenario_token: str | None = Header(default=None, max_length=100)):
    """Only the creator (holder of the token returned at creation) may delete a scenario."""
    with SessionLocal() as s:
        row = s.get(Scenario, scenario_id)
        if not row:
            raise HTTPException(404, "scenario not found")
        given = hashlib.sha256((x_scenario_token or "").encode()).hexdigest()
        if not row.delete_token_hash or not hmac.compare_digest(given, row.delete_token_hash):
            raise HTTPException(403, "Only the browser that saved this scenario can delete it.")
        s.delete(row)
        s.commit()
    return Response(status_code=204)


# ------------------------------------------------------------------ reports
@app.get("/api/reports/profile/{level}/{geo_id}.pdf", tags=["reports"])
def profile_pdf(level: Literal["national", "province", "district"], geo_id: str, store: DataStore = Depends(store_dep)):
    p = analytics.profile(store, level, _slug_ok(geo_id))
    srcs = [store.source_index[s] for s in ("eicv7_mi", "eicv7_mpi", "finscope_2024", "rphc5_main")]
    return _file(reports.area_report_pdf(p, srcs), "application/pdf", f"imboni_profile_{geo_id}.pdf")


@app.get("/api/reports/profile/{level}/{geo_id}.csv", tags=["reports"])
def profile_csv(level: Literal["national", "province", "district"], geo_id: str, store: DataStore = Depends(store_dep)):
    p = analytics.profile(store, level, _slug_ok(geo_id))
    rows = [{**{k: e.get(k) for k in ("indicator_id", "name", "unit", "value", "se", "ci_low", "ci_high", "cv",
                                      "national", "province", "rank", "n_peers", "period", "status", "table_ref")},
             "source": e["source"]["short"], "vs_national": (e.get("vs_national") or {}).get("label")}
            for e in p["indicators"]]
    return _file(reports.to_csv(rows, preamble=[f"Imboni area profile: {p['name']} ({level})", reports.DISCLAIMER]),
                 "text/csv", f"imboni_profile_{geo_id}.csv")


# ------------------------------------------------------------------ frontend (production build)
dist = settings.frontend_dist
if dist.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (dist / full_path).resolve()
        if full_path and target.is_file() and dist.resolve() in target.parents:
            return FileResponse(target)
        if full_path.startswith("assets/") or "." in full_path.rsplit("/", 1)[-1]:
            raise HTTPException(404, "Not found")  # missing static file, not an app route
        return FileResponse(dist / "index.html")
