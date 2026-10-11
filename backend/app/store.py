"""Read-only access to the validated, processed datasets.

The app serves statistics from ``data/processed`` (output of the pipeline), so it
remains fully usable when the database is unavailable. The database stores user
scenarios and a mirrored copy of the observations for SQL users.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .config import get_settings


class DataStore:
    def __init__(self, data_dir: Path):
        if not (data_dir / "observations.json").exists():
            raise FileNotFoundError(
                f"Processed data not found in {data_dir}. Run: python -m backend.pipeline.build")
        load = lambda n: json.loads((data_dir / n).read_text("utf-8"))  # noqa: E731
        self.observations: list[dict] = load("observations.json")
        self.indicators: list[dict] = load("indicators.json")
        self.sources: list[dict] = load("sources.json")
        self.mpi_framework: dict = load("mpi_framework.json")
        self.unavailable_financial: list[dict] = load("unavailable_financial.json")
        self.validation: dict = load("validation_report.json")
        self.geo = {lvl: load(f"geo/{f}") for lvl, f in [("province", "provinces.geojson"), ("district", "districts.geojson")]}
        manifest = data_dir.parent / "metadata" / "processed_manifest.json"
        self.manifest = json.loads(manifest.read_text("utf-8")) if manifest.exists() else {}
        self.indicator_index = {i["id"]: i for i in self.indicators}
        self.source_index = {s["id"]: s for s in self.sources}
        self._by_ind: dict[str, list[dict]] = {}
        for o in self.observations:
            self._by_ind.setdefault(o["indicator_id"], []).append(o)

    # ------------------------------------------------------------------ queries
    def query(self, indicator: str, level: str | None = None, geo_id: str | None = None,
              breakdown: str | None = None, period: str | None = None) -> list[dict]:
        return [o for o in self._by_ind.get(indicator, [])
                if (level is None or o["level"] == level)
                and (geo_id is None or o["geo_id"] == geo_id)
                and (breakdown is None or (o.get("breakdown") or "") == breakdown)
                and (period is None or o["period"] == period)]

    def one(self, indicator: str, level: str, geo_id: str, breakdown: str = "", period: str | None = None) -> dict | None:
        rows = self.query(indicator, level, geo_id, breakdown, period)
        return rows[0] if rows else None

    def value(self, indicator: str, level: str, geo_id: str, breakdown: str = "") -> float | None:
        o = self.one(indicator, level, geo_id, breakdown)
        return None if o is None else o["value"]

    def geo_name(self, level: str, geo_id: str) -> str | None:
        if level == "national":
            return "Rwanda"
        for f in self.geo.get(level, {}).get("features", []):
            if f["properties"]["geo_id"] == geo_id:
                return f["properties"]["name"]
        if level == "area" and geo_id in {"urban", "rural"}:
            return geo_id.title()
        return None

    def province_of(self, district_id: str) -> str | None:
        for f in self.geo["district"]["features"]:
            if f["properties"]["geo_id"] == district_id:
                return f["properties"]["province_id"]
        return None

    def districts(self) -> list[dict]:
        return [f["properties"] for f in self.geo["district"]["features"]]

    def provinces(self) -> list[dict]:
        return [f["properties"] for f in self.geo["province"]["features"]]

    def source_ref(self, source_id: str) -> dict:
        s = self.source_index.get(source_id, {})
        return {"id": source_id, "title": s.get("title"), "short": s.get("short"), "url": s.get("url"),
                "landing_page": s.get("landing_page"), "publisher": s.get("publisher")}


@lru_cache
def get_store() -> DataStore:
    return DataStore(get_settings().data_dir)
