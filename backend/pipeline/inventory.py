"""Data inventory: which source files are present, verified, missing or restricted.

    python -m backend.pipeline.inventory          # print the inventory, write data/metadata/data_inventory.json

Roles
  required   parsed by the pipeline; the build cannot run without it
  optional   parsed when present; ``build --allow-partial`` skips it and records the gap
  reference  documentation kept for provenance (reports, questionnaire); not parsed
  restricted microdata or portals that need registration/approval; never downloaded
"""
from __future__ import annotations

import json
import sys

from .fetch import LOG_PATH, sha256
from .paths import METADATA_DIR, RAW_DIR, write_text_lf
from .sources import SOURCES

REQUIRED = ("eicv7_mi", "eicv7_mpi", "eicv7_pp", "geoboundaries_adm1", "geoboundaries_adm2")
OPTIONAL = ("eicv7_vup", "finscope_2024", "rphc5_main")
INVENTORY_PATH = METADATA_DIR / "data_inventory.json"


def role(src: dict) -> str:
    if src["id"] in REQUIRED:
        return "required"
    if src["id"] in OPTIONAL:
        return "optional"
    if not src.get("file"):
        return "restricted"
    return "reference"


def _action(src: dict, r: str, present: bool) -> str:
    if r == "restricted":
        return f"Request access / review terms at {src['landing_page']}; not needed for the public build."
    if present:
        return "None."
    return f"Run `python -m backend.pipeline.build --fetch`, or download manually from {src['url']} into data/raw/{src['file']}."


def inventory(verify: bool = True) -> list[dict]:
    log = json.loads(LOG_PATH.read_text("utf-8")) if LOG_PATH.exists() else {}
    rows = []
    for src in SOURCES:
        r = role(src)
        path = RAW_DIR / src["file"] if src.get("file") else None
        present = bool(path and path.exists())
        logged = (log.get(src["id"]) or {}).get("sha256")
        digest = sha256(path) if present and verify else None
        rows.append({
            "source_id": src["id"], "short": src["short"], "role": r, "access": src["access"],
            "period": src["period"], "format": src["format"], "url": src["url"], "landing_page": src["landing_page"],
            "file": src.get("file"), "present": present, "bytes": path.stat().st_size if present else None,
            "sha256": digest, "logged_sha256": logged,
            "checksum_matches_log": None if digest is None or logged is None else digest == logged,
            "retrieved_at": (log.get(src["id"]) or {}).get("retrieved_at"),
            "action": _action(src, r, present),
        })
    return rows


def missing(rows: list[dict], which: tuple[str, ...]) -> list[dict]:
    return [r for r in rows if r["source_id"] in which and not r["present"]]


def write_inventory(rows: list[dict]) -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    write_text_lf(INVENTORY_PATH, json.dumps(rows, indent=1), "utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = inventory()
    write_inventory(rows)
    for r in rows:
        state = "restricted" if r["role"] == "restricted" else ("present" if r["present"] else "MISSING")
        check = {True: "checksum ok", False: "CHECKSUM CHANGED", None: ""}[r["checksum_matches_log"]]
        print(f"{r['role']:<10} {state:<10} {r['source_id']:<22} {check}")
    gaps = missing(rows, REQUIRED + OPTIONAL)
    for r in gaps:
        print(f"  -> {r['source_id']}: {r['action']}")
    print(f"Inventory written to {INVENTORY_PATH.relative_to(METADATA_DIR.parent.parent)}")
    return 1 if missing(rows, REQUIRED) else 0


if __name__ == "__main__":
    sys.exit(main())
