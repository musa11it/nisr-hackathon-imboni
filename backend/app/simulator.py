"""Intervention budget simulator (scenario arithmetic, NOT an impact model).

For each intervention line:
    amount_j          = budget × share_j  (integer RWF; largest-remainder rounding so Σ amounts == allocated)
    capacity_j        = floor(amount_j / unit_cost_j)                  households the money can pay for
    eligible_j        = households(geo) × need_rate_j / 100            households lacking the service (estimate)
    reached_j         = min(capacity_j, eligible_j)
    idle_j            = amount_j − reached_j × unit_cost_j            money not needed at this unit cost
    coverage_j        = reached_j / eligible_j
    people_j          = reached_j × mean household size (Census 2022)

What it does NOT do: predict poverty or MPI reduction, or establish programme effectiveness.
Reached counts are household-interventions; one household may receive several.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .store import DataStore

MAX_BUDGET = 10_000_000_000_000  # 10 trillion RWF hard ceiling for input validation

# need basis: ordered candidates (level, indicator, transform). If the target level is missing, the
# next coarser level is used and flagged.
INTERVENTIONS: dict[str, dict] = {
    "housing": {
        "label": "Housing improvement (roofing)", "icon": "home",
        "need": [("roof_metal", "complement")],
        "need_label": "Households without metal/iron-sheet roofing (EICV7 Table A5.13)",
        "default_unit_cost": 1_200_000, "default_share": 25,
        "proxy_note": "Roofing is a narrower proxy than the MPI housing-materials indicator (floor, walls, roof).",
    },
    "cooking": {
        "label": "Cleaner cooking", "icon": "flame",
        "need": [("mpi_ch_cooking_fuel", "direct")],
        "need_label": "People who are MPI-poor AND deprived in cooking fuel (censored headcount, EICV7 MPI Table B.3)",
        "default_unit_cost": 45_000, "default_share": 15,
        "proxy_note": "Censored headcount is person-based and published down to province only; applied to households as an approximation.",
    },
    "water": {
        "label": "Improved water access", "icon": "droplets",
        "need": [("improved_water", "complement")],
        "need_label": "Households without an improved drinking-water source (EICV7 Table A5.16)",
        "default_unit_cost": 250_000, "default_share": 20,
        "proxy_note": "Source type only; the MPI water indicator also applies a distance criterion.",
    },
    "electricity": {
        "label": "Electricity / solar access", "icon": "zap",
        "need": [("electricity_lighting", "complement")],
        "need_label": "Households not using electricity as main lighting source (EICV7 Table A5.14)",
        "default_unit_cost": 350_000, "default_share": 15,
        "proxy_note": None,
    },
    "sanitation": {
        "label": "Improved sanitation", "icon": "bath",
        "need": [("improved_sanitation", "complement")],
        "need_label": "Households without improved sanitation (EICV7 Table A5.17)",
        "default_unit_cost": 150_000, "default_share": 0,
        "proxy_note": None,
    },
    "health_insurance": {
        "label": "Health insurance premiums", "icon": "heart-pulse",
        "need": [("health_insurance_cov", "complement")],
        "need_label": "People without health insurance (EICV7 Table A3.7), applied to households",
        "default_unit_cost": 15_000, "default_share": 0,
        "proxy_note": "Person-based rate applied to households as an approximation.",
    },
    "financial_inclusion": {
        "label": "Financial inclusion support", "icon": "landmark",
        "need": [("fs_excluded", "direct"), ("fs_informal_only", "direct")],
        "need_label": "Adults financially excluded or informal-only (FinScope 2024 Access Strand), applied to households",
        "default_unit_cost": 100_000, "default_share": 15,
        "proxy_note": "Adult-level shares applied to households; reference: EICV7 VUP Financial Services average loan "
                      "≈ RWF 99,900 per participant (Table 4.13) — a loan size, not a programme delivery cost.",
    },
    "education": {
        "label": "School attendance support", "icon": "graduation-cap",
        "need": [("mpi_ch_school_attendance", "direct")],
        "need_label": "People who are MPI-poor AND live with a 6–11-year-old not attending school (EICV7 MPI)",
        "default_unit_cost": 80_000, "default_share": 10,
        "proxy_note": "Person-based censored headcount published to province only.",
    },
}

DEFAULT_SENSITIVITY = [0.5, 0.8, 1.0, 1.2, 1.5]


class InterventionInput(BaseModel):
    id: str
    share_pct: float = Field(ge=0, le=100)
    unit_cost_rwf: float = Field(ge=1, le=1_000_000_000)

    @field_validator("unit_cost_rwf")
    @classmethod
    def whole_rwf(cls, v: float) -> int:
        return int(round(v))  # whole RWF keeps all money arithmetic exact

    @field_validator("id")
    @classmethod
    def known(cls, v: str) -> str:
        if v not in INTERVENTIONS:
            raise ValueError(f"unknown intervention '{v}'")
        return v


class Geography(BaseModel):
    level: Literal["national", "province", "district"] = "national"
    geo_id: str = "rwanda"


class ScenarioInput(BaseModel):
    name: str = Field(default="Untitled scenario", min_length=1, max_length=120)
    total_budget_rwf: float = Field(gt=0, le=MAX_BUDGET)
    geography: Geography = Geography()
    interventions: list[InterventionInput] = Field(min_length=1, max_length=len(INTERVENTIONS))
    sensitivity: list[float] = Field(default_factory=lambda: list(DEFAULT_SENSITIVITY), max_length=9)

    @model_validator(mode="after")
    def check(self):
        ids = [i.id for i in self.interventions]
        if len(set(ids)) != len(ids):
            raise ValueError("each intervention may appear only once")
        total = sum(i.share_pct for i in self.interventions)
        if total > 100 + 1e-9:
            raise ValueError(f"allocation shares sum to {total:.2f}% — must not exceed 100%")
        if any(not (0.1 <= f <= 10) for f in self.sensitivity):
            raise ValueError("sensitivity multipliers must be between 0.1 and 10")
        return self


def allocate_amounts(budget: int, shares: list[float]) -> list[int]:
    """Largest-remainder rounding: integer amounts whose sum equals round(budget × Σshares/100)."""
    raw = [budget * s / 100 for s in shares]
    target = round(budget * sum(shares) / 100)
    floors = [math.floor(r) for r in raw]
    rem = target - sum(floors)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:max(rem, 0)]:
        floors[i] += 1
    return floors


def _need_rate(store: DataStore, spec: list[tuple[str, str]], level: str, gid: str) -> tuple[float | None, dict]:
    chain = [(level, gid)]
    if level == "district":
        chain.append(("province", store.province_of(gid)))
    if level != "national":
        chain.append(("national", "rwanda"))
    for lvl, g in chain:
        vals = [store.one(ind, lvl, g) for ind, _ in spec]
        if all(v is not None and v["value"] is not None for v in vals):
            rate = sum((100 - v["value"]) if tr == "complement" else v["value"] for v, (_, tr) in zip(vals, spec))
            return rate, {"level_used": lvl, "geo_used": store.geo_name(lvl, g), "fallback": (lvl, g) != (level, gid),
                          "inputs": [{"indicator_id": v["indicator_id"], "value": v["value"], "period": v["period"],
                                      "source_id": v["source_id"], "table_ref": v["table_ref"], "status": v["status"]}
                                     for v in vals]}
    return None, {"level_used": None, "fallback": True, "inputs": []}


def context(store: DataStore, level: str, gid: str) -> dict:
    name = store.geo_name(level, gid)
    if name is None:
        raise KeyError(f"{level}/{gid}")
    hh = store.one("households_census", level, gid)
    size = store.one("household_size_census", level, gid)
    needs = {}
    for k, spec in INTERVENTIONS.items():
        rate, info = _need_rate(store, spec["need"], level, gid)
        needs[k] = {"rate_pct": rate, "eligible_households": None if rate is None or not hh else round(hh["value"] * rate / 100),
                    **info}
    return {"level": level, "geo_id": gid, "name": name,
            "households": hh and hh["value"], "household_size": size and size["value"],
            "households_source": "Census 2022 (PHC5) Table 58", "household_size_source": "Census 2022 (PHC5) Table 60",
            "needs": needs}


def suggest_need_weighted(store: DataStore, level: str, gid: str, ids: list[str]) -> dict[str, float]:
    """Shares proportional to estimated eligible households × unit-cost-free need rate (transparent default)."""
    ctx = context(store, level, gid)
    w = {k: ctx["needs"][k]["rate_pct"] or 0 for k in ids}
    tot = sum(w.values())
    if tot <= 0:
        return {k: round(100 / len(ids), 2) for k in ids}
    shares = {k: round(v / tot * 100, 2) for k, v in w.items()}
    drift = round(100 - sum(shares.values()), 2)
    shares[max(shares, key=shares.get)] += drift
    return shares


def run_scenario(store: DataStore, inp: ScenarioInput) -> dict:
    geo = inp.geography
    ctx = context(store, geo.level, geo.geo_id)
    budget = int(round(inp.total_budget_rwf))
    amounts = allocate_amounts(budget, [i.share_pct for i in inp.interventions])
    hh_size = ctx["household_size"] or 0
    lines = []
    for item, amount in zip(inp.interventions, amounts):
        spec = INTERVENTIONS[item.id]
        need = ctx["needs"][item.id]
        eligible = need["eligible_households"]
        capacity = math.floor(amount / item.unit_cost_rwf)
        reached = capacity if eligible is None else min(capacity, eligible)
        used = reached * item.unit_cost_rwf
        sens = []
        for f in inp.sensitivity:
            cap = math.floor(amount / (item.unit_cost_rwf * f))
            r = cap if eligible is None else min(cap, eligible)
            sens.append({"multiplier": f, "unit_cost_rwf": item.unit_cost_rwf * f, "households_reached": r,
                         "coverage_pct": (r / eligible * 100) if eligible else None})
        lines.append({
            "id": item.id, "label": spec["label"], "share_pct": item.share_pct, "amount_rwf": amount,
            "unit_cost_rwf": item.unit_cost_rwf, "capacity_households": capacity,
            "eligible_households": eligible, "need_rate_pct": need["rate_pct"], "need_label": spec["need_label"],
            "need_basis": need, "households_reached": reached,
            "people_reached_est": round(reached * hh_size) if hh_size else None,
            "coverage_of_need_pct": (reached / eligible * 100) if eligible else None,
            "amount_used_rwf": used, "amount_idle_rwf": amount - used,
            "budget_exceeds_need": eligible is not None and capacity > eligible,
            "cost_per_person_rwf": item.unit_cost_rwf / hh_size if hh_size else None,
            "sensitivity": sens, "proxy_note": spec["proxy_note"],
            "unit_cost_is_default": item.unit_cost_rwf == spec["default_unit_cost"],
        })
    allocated = sum(amounts)
    summary = {
        "total_budget_rwf": budget, "allocated_rwf": allocated, "unallocated_rwf": budget - allocated,
        "allocated_pct": sum(i.share_pct for i in inp.interventions),
        "reconciles": (allocated == round(budget * sum(i.share_pct for i in inp.interventions) / 100)
                       and 0 <= budget - allocated <= budget
                       and all(l["amount_used_rwf"] + l["amount_idle_rwf"] == l["amount_rwf"] for l in lines)),
        "household_interventions": sum(l["households_reached"] for l in lines),
        "people_reached_est_sum": sum(l["people_reached_est"] or 0 for l in lines),
        "idle_rwf": sum(l["amount_idle_rwf"] for l in lines),
        "max_unique_households_bound": max((l["households_reached"] for l in lines), default=0),
    }
    return {
        "name": inp.name, "inputs": inp.model_dump(), "context": ctx, "lines": lines, "summary": summary,
        "labels": {
            "status": "illustrative scenario",
            "reach_definition": "Households reached = household-interventions; a household may benefit from several lines, "
                                "so unique households lie between the largest single line and the sum.",
            "not_measured": "This is budget arithmetic. It does not estimate change in monetary poverty or the MPI, "
                            "and it does not show that any intervention is effective.",
            "unit_costs": "Default unit costs are illustrative placeholders chosen by the DataMinds team, not costed "
                          "programme estimates. Replace them with programme costing before any use.",
        },
    }


def catalogue() -> list[dict]:
    return [{"id": k, "label": v["label"], "icon": v["icon"], "need_label": v["need_label"],
             "default_unit_cost": v["default_unit_cost"], "default_share": v["default_share"],
             "proxy_note": v["proxy_note"], "unit_cost_status": "illustrative placeholder"}
            for k, v in INTERVENTIONS.items()]
