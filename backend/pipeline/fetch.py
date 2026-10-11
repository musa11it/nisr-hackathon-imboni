"""Download public source files into ``data/raw`` and log checksums.

Raw files are never modified. Existing files are kept unless ``--force`` is given,
so the pipeline is reproducible offline once the raw files exist. Restricted
sources (e.g. EICV7 microdata) are never downloaded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import urllib.request
from pathlib import Path

from .paths import METADATA_DIR, RAW_DIR
from .sources import SOURCES

log = logging.getLogger("imboni.pipeline.fetch")
USER_AGENT = "Imboni-DataMinds/1.0 (NISR Hackathon 2026 student project)"
LOG_PATH = METADATA_DIR / "retrieval_log.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        out.write(resp.read())
    tmp.replace(dest)


def fetch_all(force: bool = False) -> dict:
    previous = json.loads(LOG_PATH.read_text("utf-8")) if LOG_PATH.exists() else {}
    entries: dict[str, dict] = {}
    for src in SOURCES:
        if not src.get("file") or src["access"].startswith("registration"):
            continue
        dest = RAW_DIR / src["file"]
        status = "present"
        if force or not dest.exists():
            try:
                _download(src["url"], dest)
                status = "downloaded"
            except Exception as exc:  # network failure -> keep going, report it
                log.warning("Could not download %s: %s", src["id"], exc)
                status = "missing" if not dest.exists() else "present (refresh failed)"
        entry = {"source_id": src["id"], "url": src["url"], "file": src["file"], "status": status}
        if dest.exists():
            digest = sha256(dest)
            prev = previous.get(src["id"], {})
            same = prev.get("sha256") == digest
            if prev.get("sha256") and not same:
                log.warning("%s: checksum changed since %s — the publisher may have revised the file; "
                            "re-run validation and review differences", src["id"], prev.get("retrieved_at"))
                entry["previous_sha256"] = prev["sha256"]
            entry.update(
                sha256=digest,
                bytes=dest.stat().st_size,
                retrieved_at=prev.get("retrieved_at") if same and prev.get("retrieved_at")
                else dt.date.today().isoformat(),
            )
        entries[src["id"]] = entry
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(entries, indent=2), "utf-8")
    return entries


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    for sid, e in fetch_all(force=ap.parse_args().force).items():
        print(f"{e['status']:>10}  {sid:<22} {e.get('sha256', '')[:16]}")
