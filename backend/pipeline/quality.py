"""Missing-value and precision assessment of the processed observations.

One row per (indicator, level): how many values are present, missing (and why),
how many carry published standard errors, and how many are flagged imprecise.
Used by the pipeline (``data/processed/data_quality_summary.csv``) and the dashboard.
"""
from __future__ import annotations

from collections import defaultdict

QUALITY_FIELDS = ["indicator_id", "level", "n_observations", "n_present", "n_missing", "pct_missing",
                  "missing_reasons", "n_with_se", "n_cv_gt_15", "n_cv_gt_30", "statuses"]


def _flags(o: dict) -> list[str]:
    f = o.get("flags") or []
    return [x for x in (f.split(";") if isinstance(f, str) else f) if x]


def missingness_summary(observations: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o in observations:
        groups[(o["indicator_id"], o["level"])].append(o)
    rows = []
    for (ind, level), obs in sorted(groups.items()):
        miss = [o for o in obs if o["value"] is None]
        reasons = sorted({f for o in miss for f in _flags(o)})
        flags = [set(_flags(o)) for o in obs]
        rows.append({
            "indicator_id": ind, "level": level, "n_observations": len(obs), "n_present": len(obs) - len(miss),
            "n_missing": len(miss), "pct_missing": round(100 * len(miss) / len(obs), 1),
            "missing_reasons": ";".join(reasons),
            "n_with_se": sum(o.get("se") is not None for o in obs),
            "n_cv_gt_15": sum("cv_gt_15_use_with_caution" in f for f in flags),
            "n_cv_gt_30": sum("cv_gt_30_unreliable" in f for f in flags),
            "statuses": ";".join(sorted({o["status"] for o in obs})),
        })
    return rows
