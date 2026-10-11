"""Shared helpers for building tidy observation records."""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

SUPPRESSED_TOKENS = {"-", "–", "—", "..", "n/a", "na", "x"}


@dataclass
class Obs:
    indicator_id: str
    level: str            # national | area | province | district | quintile | sex | poverty_status | vup_component | ...
    geo_id: str           # stable id within level (e.g. 'gasabo', 'q1', 'urban')
    geo_name: str         # display label
    value: float | None
    period: str
    source_id: str
    table_ref: str
    status: str = "official"
    se: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    cv: float | None = None
    deff: float | None = None
    breakdown: str | None = None  # secondary dimension, e.g. 'k=40' or 'component=Direct Support'
    flags: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flags"] = ";".join(self.flags)
        return d


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def num(v) -> tuple[float | None, list[str]]:
    """Parse a numeric cell. Returns (value, flags). Never turns missing into zero."""
    if v is None:
        return None, ["missing"]
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None, ["missing"]
        return round(float(v), 6), []  # strip binary float noise (e.g. 100.00000000000031)
    s = str(v).strip().replace(",", "")
    if s.lower() in SUPPRESSED_TOKENS:
        return None, ["suppressed_or_no_observations_in_source"]
    if s == "":
        return None, ["missing"]
    try:
        return float(s), []
    except ValueError:
        return None, [f"unparseable:{s[:20]}"]


def precision_flags(o: Obs) -> None:
    """Attach reliability flags derived from the published precision measures."""
    if o.cv is not None:
        if o.cv > 30:
            o.flags.append("cv_gt_30_unreliable")
        elif o.cv > 15:
            o.flags.append("cv_gt_15_use_with_caution")
    if o.ci_high is not None and o.ci_high > 100 and o.ci_high < 200:
        o.flags.append("ci_upper_above_100_normal_approx")
    if o.ci_low is not None and o.ci_low < 0:
        o.flags.append("ci_lower_below_0_normal_approx")
    if o.se is not None and o.se < 1e-9:
        o.flags.append("se_zero_no_sampling_variation")
