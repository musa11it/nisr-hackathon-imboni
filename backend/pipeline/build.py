"""Run the full, reproducible Imboni data pipeline.

    python -m backend.pipeline.build                  # parse existing raw files
    python -m backend.pipeline.build --fetch          # download missing raw files first
    python -m backend.pipeline.build --allow-partial  # build without missing OPTIONAL sources (gaps recorded)

Before anything is written, a data inventory checks every required/optional raw file.
If one is missing the build stops and the existing processed outputs are left untouched.

Outputs (data/processed):
    observations.csv / observations.json   tidy long table, one row per value
    indicators.json                        catalogue + coverage per indicator
    sources.json                           source registry + checksums + retrieval dates
    mpi_framework.json                     official MPI dimensions, indicators, weights, cut-offs
    unavailable_financial.json             variables collected but not published
    validation_report.json                 automated checks (errors fail the build)
    data_quality_summary.csv               missing values, published SEs and CV flags per indicator x level
    geo/provinces.geojson, geo/districts.geojson
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import sys
from fractions import Fraction

from .fetch import LOG_PATH, fetch_all, sha256
from .geography import DISTRICT_IDS, DISTRICT_PROVINCE, PROVINCES, province_id
from .indicators import INDICATOR_INDEX, INDICATORS, MPI_INDICATORS, MPI_K, UNAVAILABLE_FINANCIAL
from .inventory import OPTIONAL, REQUIRED, inventory, missing, write_inventory
from .model import Obs
from .parse_eicv import parse_main_indicators, parse_mpi, parse_poverty_profile, parse_vup
from .parse_pdf import parse_census, parse_finscope
from .paths import METADATA_DIR, PROCESSED_DIR, RAW_DIR, write_text_lf
from .quality import QUALITY_FIELDS, missingness_summary
from .sources import SOURCES
from .validate import validate

log = logging.getLogger("imboni.pipeline")
PIPELINE_VERSION = "1.0.0"
FIELDS = ["indicator_id", "level", "geo_id", "geo_name", "value", "period", "source_id", "table_ref", "status",
          "se", "ci_low", "ci_high", "cv", "deff", "breakdown", "flags", "note"]


def recompute_mpi_contributions(obs: list[Obs]) -> list[Obs]:
    """contribution_j = w_j·CH_j / Σ_i w_i·CH_i  (Alkire–Foster decomposition)."""
    weights = {i[0]: i[3] for i in MPI_INDICATORS}
    by_geo: dict[tuple, dict] = {}
    for o in obs:
        if o.indicator_id.startswith("mpi_ch_") and o.value is not None:
            by_geo.setdefault((o.level, o.geo_id, o.geo_name), {})[o.indicator_id[7:]] = o.value
    out = []
    for (lvl, gid, gname), ch in by_geo.items():
        if set(ch) != set(weights):
            continue
        total = sum(Fraction(str(ch[w])) * weights[w] for w in weights)
        for w in weights:
            share = float(Fraction(str(ch[w])) * weights[w] / total * 100)
            out.append(Obs(f"mpi_contrib_calc_{w}", lvl, gid, gname, round(share, 2), "2023/24", "eicv7_mpi",
                           "Derived: w·CH / Σ w·CH", status="calculated",
                           note=f"weight {weights[w]} × CH {ch[w]}% / {float(total):.3f}"))
    return out


def _round_coords(geom, nd=4):
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
    geom["coordinates"] = r(geom["coordinates"])
    return geom


def build_geo() -> dict:
    out_dir = PROCESSED_DIR / "geo"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for level, fname, outname in [("province", "geoBoundaries-RWA-ADM1_simplified.geojson", "provinces.geojson"),
                                  ("district", "geoBoundaries-RWA-ADM2_simplified.geojson", "districts.geojson")]:
        src = json.loads((RAW_DIR / "boundaries" / fname).read_text("utf-8"))
        feats = []
        for f in src["features"]:
            name = f["properties"]["shapeName"]
            if level == "province":
                pid = province_id(name)
                props = {"geo_id": pid, "name": PROVINCES[pid], "level": "province"}
            else:
                props = {"geo_id": DISTRICT_IDS[name], "name": name, "level": "district",
                         "province_id": DISTRICT_PROVINCE[name], "province": PROVINCES[DISTRICT_PROVINCE[name]]}
            feats.append({"type": "Feature", "properties": props, "geometry": _round_coords(f["geometry"])})
        fc = {"type": "FeatureCollection", "features": feats,
              "attribution": "Boundaries: geoBoundaries (CC BY 4.0), www.geoboundaries.org"}
        write_text_lf((out_dir / outname), json.dumps(fc, separators=(",", ":")), "utf-8")
        res[level] = len(feats)
    return res


class MissingSourcesError(RuntimeError):
    def __init__(self, gaps: list[dict], optional_only: bool):
        self.gaps, self.optional_only = gaps, optional_only
        hint = ("Re-run with --fetch to download them, or with --allow-partial to build without them."
                if optional_only else "Re-run with --fetch to download them.")
        super().__init__("Missing source files: " + ", ".join(g["source_id"] for g in gaps) + ". " + hint)


def run(fetch: bool = False, allow_partial: bool = False) -> dict:
    if fetch:
        fetch_all()
    elif not LOG_PATH.exists():
        fetch_all()  # records checksums of already-present files; downloads only if missing

    inv = inventory()
    write_inventory(inv)
    gaps_required, gaps_optional = missing(inv, REQUIRED), missing(inv, OPTIONAL)
    if gaps_required:
        raise MissingSourcesError(gaps_required, optional_only=False)
    if gaps_optional and not allow_partial:
        raise MissingSourcesError(gaps_optional, optional_only=True)
    skipped = {g["source_id"] for g in gaps_optional}

    obs: list[Obs] = []
    extra_checks: list[dict] = []
    obs += parse_main_indicators(RAW_DIR / "EICV7_Tables_MainIndicatorReport.xlsx")
    obs += parse_mpi(RAW_DIR / "Tables_and_Figures_EICV7_Multidimensional_Poverty_MPI.xlsx")
    obs += parse_poverty_profile(RAW_DIR / "EICV7_Tables_Rwanda_Poverty_Profile.xlsx")
    if "eicv7_vup" not in skipped:
        obs += parse_vup(RAW_DIR / "EICV7_VUP_Thematic_Report_Tables.xlsx")
    if "finscope_2024" not in skipped:
        fin, fin_checks = parse_finscope(RAW_DIR / "Rwanda_FinScope_2024_Report.pdf")
        obs += fin
        extra_checks += fin_checks
    if "rphc5_main" not in skipped:
        cen, cen_checks = parse_census(RAW_DIR / "RPHC5_MainIndicatorsReport_Final.pdf")
        obs += cen
        extra_checks += cen_checks
    obs += recompute_mpi_contributions(obs)

    for o in obs:  # catalogue-level status for transcribed sources
        meta = INDICATOR_INDEX.get(o.indicator_id)
        if meta and meta["status"] == "official_transcribed" and o.status == "official":
            o.status = "official_transcribed"

    records = [o.to_dict() for o in obs]
    report = validate([{**r, "flags": r["flags"]} for r in records], extra_checks, missing_sources=skipped)
    report["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report["pipeline_version"] = PIPELINE_VERSION

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with (PROCESSED_DIR / "observations.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(records)
    write_text_lf((PROCESSED_DIR / "observations.json"), json.dumps(records, separators=(",", ":")), "utf-8")

    coverage: dict[str, set] = {}
    for r in records:
        coverage.setdefault(r["indicator_id"], set()).add(r["level"])
    catalogue = [{**i, "levels": sorted(coverage.get(i["id"], []))} for i in INDICATORS]
    write_text_lf((PROCESSED_DIR / "indicators.json"), json.dumps(catalogue, indent=1), "utf-8")

    retrieval = json.loads(LOG_PATH.read_text("utf-8")) if LOG_PATH.exists() else {}
    write_text_lf((PROCESSED_DIR / "sources.json"), json.dumps(
        [{**s, "retrieval": retrieval.get(s["id"])} for s in SOURCES], indent=1), "utf-8")

    framework = {
        "name": "Rwanda National Multidimensional Poverty Index (EICV7)",
        "method": "Alkire–Foster adjusted headcount ratio (M0), dual cut-off",
        "unit_of_identification": "Household (all members share the household's deprivation score)",
        "unit_of_analysis": "Individual",
        "poverty_cutoff_k": float(MPI_K),
        "poverty_cutoff_label": "Deprived in at least 1/3 (33.3%) of weighted indicators",
        "source": "NISR, EICV7 Thematic Report: Multidimensional Poverty, pp. 22–23",
        "changes_vs_eicv5": [
            "13 indicators instead of 14: bank-account indicator removed (future EICV rounds will not capture it)",
            "Charcoal no longer counted as cooking-fuel deprivation",
            "Assets indicator broadened to mobility assets",
            "School attendance age 6–11 (was 7–15); years of schooling eligible age 12+ (was 15–60)",
            "Housing materials considers floor, walls and roof (was floor only)",
            "Overcrowding threshold >3 persons per sleeping room (was >4)",
            "Poverty cut-off k = 33.3% (was 40%)",
        ],
        "indicators": [{"id": i, "label": l, "dimension": d, "weight": float(w), "weight_label": str(w),
                        "deprived_if": c} for i, l, d, w, c in MPI_INDICATORS],
    }
    write_text_lf((PROCESSED_DIR / "mpi_framework.json"), json.dumps(framework, indent=1), "utf-8")
    write_text_lf((PROCESSED_DIR / "unavailable_financial.json"), json.dumps(UNAVAILABLE_FINANCIAL, indent=1), "utf-8")
    write_text_lf((PROCESSED_DIR / "validation_report.json"), json.dumps(report, indent=1), "utf-8")
    with (PROCESSED_DIR / "data_quality_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=QUALITY_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(missingness_summary(records))
    geo = build_geo()

    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": report["generated_at"],
        "observations": len(records),
        "indicators_with_data": len(coverage),
        "geo_features": geo,
        "partial_build": bool(skipped),
        "missing_sources": sorted(skipped),
        "outputs": {p.name: sha256(p) for p in sorted(PROCESSED_DIR.glob("*.*"))},
    }
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    write_text_lf((METADATA_DIR / "processed_manifest.json"), json.dumps(manifest, indent=1), "utf-8")
    return {"manifest": manifest, "validation": report["summary"],
            "errors": [c for c in report["checks"] if c["severity"] == "error"],
            "warnings": [c for c in report["checks"] if c["severity"] == "warning"]}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Run the Imboni data pipeline")
    ap.add_argument("--fetch", action="store_true", help="download missing raw files before parsing")
    ap.add_argument("--allow-partial", action="store_true",
                    help="build even if OPTIONAL sources (VUP, FinScope, Census) are missing; gaps are recorded")
    args = ap.parse_args()
    try:
        res = run(fetch=args.fetch, allow_partial=args.allow_partial)
    except MissingSourcesError as exc:
        print(f"BUILD STOPPED - processed outputs were not modified.\n{exc}")
        for g in exc.gaps:
            print(f"  - {g['source_id']}: {g['action']}")
        return 2
    m = res["manifest"]
    if m["partial_build"]:
        print(f"PARTIAL BUILD - skipped missing optional sources: {', '.join(m['missing_sources'])}")
    print(f"Observations: {m['observations']}  indicators with data: {m['indicators_with_data']}  geo: {m['geo_features']}")
    s = res["validation"]
    print(f"Validation: {s['passed']}/{s['total']} passed, {s['errors']} errors, {s['warnings']} source warnings")
    for c in res["warnings"]:
        print(f"  WARNING {c['check']}: {c['detail']}")
    for c in res["errors"]:
        print(f"  ERROR   {c['check']}: {c['detail']}")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
