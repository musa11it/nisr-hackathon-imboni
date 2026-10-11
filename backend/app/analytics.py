"""Derived statistics computed from validated official values.

Nothing here invents data: every function reads official observations from the
store and returns calculated values labelled ``status='calculated'`` together with
the formula used. Statistical caveats are returned alongside results.
"""
from __future__ import annotations

import math
from statistics import median

import numpy as np
from scipy import stats

from .store import DataStore

Z95 = 1.959964

# District-level indicators (EICV7 annex with SE, FinScope transcribed, Census)
DISTRICT_INDICATORS = [
    "poverty_rate", "health_insurance_cov", "electricity_lighting", "improved_water", "improved_sanitation",
    "roof_metal", "internet_home", "mobile_phone", "smartphone", "umudugudu", "workforce_ratio",
    "sending_transfers", "fs_banked", "fs_formally_served", "fs_informal_only", "fs_excluded",
]

# Deprivation view used for fingerprints: (indicator, transform, label)
FINGERPRINT = [
    ("poverty_rate", "direct", "Monetary poverty"),
    ("electricity_lighting", "complement", "No electricity for lighting"),
    ("improved_water", "complement", "No improved water source"),
    ("improved_sanitation", "complement", "No improved sanitation"),
    ("health_insurance_cov", "complement", "No health insurance"),
    ("roof_metal", "complement", "No metal/iron-sheet roof"),
    ("internet_home", "complement", "No internet at home"),
    ("fs_excluded", "direct", "Financially excluded (adults)"),
]

COMPOSITE_COMPONENTS = [
    ("electricity_lighting", "complement"), ("improved_water", "complement"), ("improved_sanitation", "complement"),
    ("health_insurance_cov", "complement"), ("roof_metal", "complement"), ("fs_formally_served", "complement"),
]


# ---------------------------------------------------------------- primitives
def enrich(store: DataStore, o: dict | None) -> dict | None:
    if o is None:
        return None
    meta = store.indicator_index.get(o["indicator_id"], {})
    flags = [f for f in (o.get("flags") or "").split(";") if f]
    return {
        "indicator_id": o["indicator_id"], "name": meta.get("name"), "short_name": meta.get("short_name"),
        "unit": meta.get("unit"), "universe": meta.get("universe"), "definition": meta.get("definition"),
        "polarity": meta.get("polarity"), "decimals": meta.get("decimals", 1), "theme": meta.get("theme"),
        "level": o["level"], "geo_id": o["geo_id"], "geo_name": o["geo_name"], "breakdown": o.get("breakdown") or "",
        "value": o["value"], "se": o["se"], "ci_low": o["ci_low"], "ci_high": o["ci_high"], "cv": o["cv"],
        "deff": o["deff"], "period": o["period"], "status": o["status"], "table_ref": o["table_ref"],
        "flags": flags, "note": o.get("note"), "source": store.source_ref(o["source_id"]),
        "indicator_notes": meta.get("notes"),
    }


def metric(store: DataStore, ind: str, level: str = "national", gid: str = "rwanda", breakdown: str = "") -> dict | None:
    return enrich(store, store.one(ind, level, gid, breakdown))


def deprivation(value: float | None, transform: str) -> float | None:
    if value is None:
        return None
    return 100.0 - value if transform == "complement" else value


def compare_to_reference(o: dict, ref: dict | None) -> dict:
    """Approximate two-sample z-test vs a reference estimate (independence assumed)."""
    if not ref or o.get("se") is None or ref.get("se") is None or o["value"] is None or ref["value"] is None:
        return {"available": False, "label": "No standard errors available"}
    diff = o["value"] - ref["value"]
    se = math.sqrt(o["se"] ** 2 + ref["se"] ** 2)
    if se == 0:
        return {"available": False, "label": "Zero standard error"}
    z = diff / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    label = "higher than" if z > Z95 else "lower than" if z < -Z95 else "not statistically different from"
    return {"available": True, "diff": diff, "se_diff": se, "z": z, "p_value": p, "label": label,
            "method": "z = (x̂₁ − x̂₂) / √(SE₁² + SE₂²); assumes independent estimates (conservative for a "
                      "district vs the national estimate that contains it)."}


def rank_intervals(values: dict[str, float], ses: dict[str, float], higher_is_rank1: bool,
                   draws: int = 4000, seed: int = 2026) -> dict[str, tuple[int, int, int]]:
    """Point rank and 90% rank interval by Monte Carlo from Normal(x̂, SE)."""
    keys = [k for k in values if values[k] is not None and ses.get(k) is not None]
    if len(keys) < 3:
        return {}
    rng = np.random.default_rng(seed)
    mu = np.array([values[k] for k in keys])
    sd = np.array([ses[k] for k in keys])
    sims = rng.normal(mu, sd, size=(draws, len(keys)))
    order = -sims if higher_is_rank1 else sims
    ranks = order.argsort(axis=1).argsort(axis=1) + 1
    point_order = (-mu if higher_is_rank1 else mu).argsort().argsort() + 1
    return {k: (int(point_order[i]), int(np.percentile(ranks[:, i], 5)), int(np.percentile(ranks[:, i], 95)))
            for i, k in enumerate(keys)}


# ---------------------------------------------------------------- map
def map_layer(store: DataStore, indicator: str, level: str) -> dict:
    meta = store.indicator_index.get(indicator)
    if not meta:
        raise KeyError(indicator)
    rows = [enrich(store, o) for o in store.query(indicator, level) if not o.get("breakdown")]
    nat = metric(store, indicator)
    polarity = meta["polarity"]
    worse_high = polarity != "higher_better"
    vals = {r["geo_id"]: r["value"] for r in rows}
    ses = {r["geo_id"]: r["se"] for r in rows if r["se"] is not None}
    rk = rank_intervals(vals, ses, higher_is_rank1=worse_high) if ses else {}
    present = [v for v in vals.values() if v is not None]
    order = sorted([r for r in rows if r["value"] is not None], key=lambda r: r["value"], reverse=worse_high)
    for i, r in enumerate(order, 1):
        r["rank"] = i
    for r in rows:
        r["vs_national"] = compare_to_reference(r, nat)
        if r["geo_id"] in rk:
            r["rank"], r["rank_low"], r["rank_high"] = rk[r["geo_id"]]
    return {
        "indicator": meta, "level": level, "national": nat, "rows": rows,
        "summary": {"n": len(present), "min": min(present) if present else None,
                    "max": max(present) if present else None,
                    "median": median(present) if present else None,
                    "range_ratio": (max(present) / min(present)) if present and min(present) > 0 else None},
        "rank_note": ("Rank 1 = most deprived. " if polarity != "neutral" else "Rank 1 = highest value. ")
                     + ("90% rank intervals from 4,000 Monte-Carlo draws using published standard errors."
                        if rk else "No standard errors published, so ranks carry unquantified uncertainty."),
    }


# ---------------------------------------------------------------- profile / fingerprint
def profile(store: DataStore, level: str, gid: str) -> dict:
    name = store.geo_name(level, gid)
    if name is None:
        raise KeyError(f"{level}/{gid}")
    province_id = store.province_of(gid) if level == "district" else (gid if level == "province" else None)
    indicators = []
    candidate = DISTRICT_INDICATORS + ["extreme_poverty_rate", "households_census", "household_size_census"]
    for ind in candidate:
        o = metric(store, ind, level, gid)
        if o is None:
            continue
        nat = metric(store, ind)
        prov = metric(store, ind, "province", province_id) if level == "district" and province_id else None
        peers = [r for r in store.query(ind, level) if not r.get("breakdown") and r["value"] is not None]
        meta = store.indicator_index[ind]
        entry = {**o, "national": nat and nat["value"], "national_ci": nat and [nat["ci_low"], nat["ci_high"]],
                 "province": prov and prov["value"], "vs_national": compare_to_reference(o, nat)}
        if len(peers) >= 3 and meta["polarity"] != "neutral":
            layer = map_layer(store, ind, level)
            me = next(r for r in layer["rows"] if r["geo_id"] == gid)
            entry.update(rank=me.get("rank"), rank_low=me.get("rank_low"), rank_high=me.get("rank_high"),
                         n_peers=len(peers), peer_min=min(p["value"] for p in peers),
                         peer_median=median(p["value"] for p in peers), peer_max=max(p["value"] for p in peers))
        indicators.append(entry)

    fingerprint = []
    for ind, tr, label in FINGERPRINT:
        o = store.one(ind, level, gid)
        n = store.one(ind, "national", "rwanda")
        if o is None or o["value"] is None:
            continue
        p = store.one(ind, "province", province_id) if level == "district" and province_id else None
        fingerprint.append({"indicator_id": ind, "label": label, "transform": tr,
                            "value": deprivation(o["value"], tr), "national": deprivation(n and n["value"], tr),
                            "province": deprivation(p and p["value"], tr) if p else None,
                            "status": o["status"], "source": store.source_ref(o["source_id"])})

    mpi_level, mpi_gid = (("province", province_id) if level in {"district", "province"} else (level, gid))
    mpi = None
    if mpi_gid:
        ch = []
        for i in store.mpi_framework["indicators"]:
            v = store.value(f"mpi_ch_{i['id']}", mpi_level, mpi_gid)
            nv = store.value(f"mpi_ch_{i['id']}", "national", "rwanda")
            ch.append({**i, "censored_headcount": v, "national": nv})
        mpi = {"level": mpi_level, "geo_id": mpi_gid, "geo_name": store.geo_name(mpi_level, mpi_gid),
               "is_parent_province": level == "district",
               "incidence": metric(store, "mpi_incidence", mpi_level, mpi_gid),
               "intensity": metric(store, "mpi_intensity", mpi_level, mpi_gid),
               "mpi": metric(store, "mpi", mpi_level, mpi_gid),
               "censored_headcounts": ch,
               "note": ("The official MPI is published only for national, urban/rural, province and quintile levels. "
                        "For a district, the parent province's MPI is shown for context and must not be read as the "
                        "district's own MPI.") if level == "district" else None}

    findings = _findings(name, indicators)
    return {"level": level, "geo_id": gid, "name": name, "province_id": province_id,
            "province_name": store.geo_name("province", province_id) if province_id and level == "district" else None,
            "indicators": indicators, "fingerprint": fingerprint, "mpi": mpi, "findings": findings}


def _fmt(v, d=1):
    return "n/a" if v is None else f"{v:.{d}f}"


def _findings(name: str, indicators: list[dict]) -> list[str]:
    out = []
    for e in indicators:
        vs = e.get("vs_national") or {}
        if not vs.get("available") or e["polarity"] == "neutral":
            continue
        if vs["label"] == "not statistically different from":
            continue
        worse = (vs["label"] == "higher than") == (e["polarity"] == "higher_worse")
        out.append({
            "indicator_id": e["indicator_id"], "kind": "concern" if worse else "strength",
            "text": f"{e['short_name']}: {_fmt(e['value'])}% in {name} vs {_fmt(e['national'])}% nationally — "
                    f"{vs['label']} the national estimate at the 95% level (approximate test, p = {vs['p_value']:.3f}).",
        })
    out.sort(key=lambda f: f["kind"] != "concern")
    return out


# ---------------------------------------------------------------- dashboard
def dashboard(store: DataStore) -> dict:
    m = lambda *a, **k: metric(store, *a, **k)  # noqa: E731
    h_r, h_u = store.value("mpi_incidence", "area", "rural"), store.value("mpi_incidence", "area", "urban")
    gap = {"value": h_r - h_u, "ratio": h_r / h_u, "rural": h_r, "urban": h_u, "unit": "percentage points",
           "status": "calculated", "formula": "H_rural − H_urban (Table B.5)", "period": "2023/24",
           "source": store.source_ref("eicv7_mpi"),
           "definition": "Difference between rural and urban MPI incidence; the ratio is H_rural / H_urban."}

    ch = []
    for i in store.mpi_framework["indicators"]:
        v = store.value(f"mpi_ch_{i['id']}", "national", "rwanda")
        u = store.value(f"mpi_uh_{i['id']}", "national", "rwanda")
        c = store.value(f"mpi_contrib_calc_{i['id']}", "national", "rwanda")
        ch.append({"id": i["id"], "label": i["label"], "dimension": i["dimension"], "weight": i["weight"],
                   "weight_label": i["weight_label"], "censored": v, "uncensored": u, "contribution_calc": c,
                   "deprived_if": i["deprived_if"]})
    ch.sort(key=lambda x: -(x["censored"] or 0))

    ov = {b: store.value("mpi_monetary_overlap", "national", "rwanda", b) for b in [
        "mpi_poor__monetary_poor", "mpi_poor__monetary_nonpoor", "mpi_nonpoor__monetary_poor", "mpi_nonpoor__monetary_nonpoor"]}
    overlap = {"cells": ov, "status": "official", "source": store.source_ref("eicv7_mpi"), "table": "Table 3.1",
               "either": ov["mpi_poor__monetary_poor"] + ov["mpi_poor__monetary_nonpoor"] + ov["mpi_nonpoor__monetary_poor"],
               "formula_either": "both + MPI-only + monetary-only (calculated)",
               "share_of_monetary_poor_also_mpi_poor": ov["mpi_poor__monetary_poor"] / (ov["mpi_poor__monetary_poor"] + ov["mpi_nonpoor__monetary_poor"]) * 100}

    pov24, pov17 = store.value("poverty_rate_pp", "national", "rwanda"), store.value("poverty_rate_2017_modelled", "national", "rwanda")
    provinces = []
    for p in store.provinces():
        pid = p["geo_id"]
        provinces.append({"geo_id": pid, "name": p["name"],
                          "poverty_rate": store.value("poverty_rate", "province", pid),
                          "mpi_incidence": store.value("mpi_incidence", "province", pid),
                          "mpi": store.value("mpi", "province", pid),
                          "extreme_poverty_rate": store.value("extreme_poverty_rate", "province", pid)})

    return {
        "kpis": {
            "poverty_rate": m("poverty_rate"), "extreme_poverty_rate": m("extreme_poverty_rate"),
            "mpi_incidence": m("mpi_incidence"), "mpi_intensity": m("mpi_intensity"), "mpi": m("mpi"),
            "rural_urban_gap": gap, "gini": m("gini"), "poverty_gap": m("poverty_gap"),
            "hh_savings_account": m("hh_savings_account"), "hh_momo_account": m("hh_momo_account"),
            "fs_excluded": m("fs_excluded"), "fs_banked": m("fs_banked"),
            "poverty_change": {"value": pov24 - pov17, "from": pov17, "to": pov24, "unit": "percentage points",
                               "status": "calculated", "period": "2016/17 (modelled) → 2024",
                               "formula": "P(2024) − P(2017, modelled on EICV7 methodology) — Poverty Profile Table 0.1",
                               "source": store.source_ref("eicv7_pp")},
        },
        "deprivations": ch, "overlap": overlap, "provinces": provinces,
        "validation": store.validation["summary"],
    }


# ---------------------------------------------------------------- MPI summary
def mpi_summary(store: DataStore) -> dict:
    groups = [("national", "rwanda"), ("area", "urban"), ("area", "rural")] + \
             [("province", p["geo_id"]) for p in store.provinces()] + [("quintile", f"q{i}") for i in range(1, 6)]
    table = []
    for lvl, gid in groups:
        row = {"level": lvl, "geo_id": gid, "name": store.geo_name(lvl, gid) or gid.upper()}
        for k in ["population_share", "mpi_incidence", "mpi_intensity", "mpi"]:
            row[k] = store.value(k, lvl, gid)
        row["mpi_check_HxA"] = (row["mpi_incidence"] or 0) * (row["mpi_intensity"] or 0) / 1e4
        row["censored"] = {i["id"]: store.value(f"mpi_ch_{i['id']}", lvl, gid) for i in store.mpi_framework["indicators"]}
        row["contrib_published"] = {i["id"]: store.value(f"mpi_contrib_{i['id']}", lvl, gid) for i in store.mpi_framework["indicators"]}
        row["contrib_calc"] = {i["id"]: store.value(f"mpi_contrib_calc_{i['id']}", lvl, gid) for i in store.mpi_framework["indicators"]}
        w = {i["id"]: i["weight"] for i in store.mpi_framework["indicators"]}
        row["sum_w_ch"] = sum(w[k] * v / 100 for k, v in row["censored"].items() if v is not None)
        table.append(row)
    k_curve = []
    for o in store.query("mpi_k_incidence"):
        k = int(o["geo_id"][1:])
        k_curve.append({"k": k, "incidence": o["value"], "intensity": store.value("mpi_k_intensity", "k_value", o["geo_id"]),
                        "mpi": store.value("mpi_k_mpi", "k_value", o["geo_id"])})
    k_curve.sort(key=lambda r: r["k"])
    overlap = []
    for lvl, gid in [("national", "rwanda"), ("area", "urban"), ("area", "rural")] + [("province", p["geo_id"]) for p in store.provinces()]:
        cells = {o["breakdown"]: o["value"] for o in store.query("mpi_monetary_overlap", lvl, gid)}
        overlap.append({"level": lvl, "geo_id": gid, "name": store.geo_name(lvl, gid), **cells})
    return {"framework": store.mpi_framework, "table": table, "k_curve": k_curve, "overlap": overlap,
            "source": store.source_ref("eicv7_mpi"),
            "contribution_note": ("NISR Tables B.7–B.9 print indicator contributions that cannot be reproduced from the "
                                  "published censored headcounts and the official weights (max gap ≈ 9–13 pp). Imboni "
                                  "shows both, labelling the recomputed version 'calculated' (w·CH / Σ w·CH).")}


# ---------------------------------------------------------------- correlations
def correlations(store: DataStore, indicators: list[str] | None = None, level: str = "district") -> dict:
    inds = indicators or DISTRICT_INDICATORS
    data = {}
    for ind in inds:
        rows = {o["geo_id"]: o["value"] for o in store.query(ind, level) if not o.get("breakdown")}
        if sum(v is not None for v in rows.values()) >= 8:
            data[ind] = rows
    keys = list(data)
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            common = [g for g in data[a] if g in data[b] and data[a][g] is not None and data[b][g] is not None]
            n = len(common)
            if n < 8:
                continue
            x = [data[a][g] for g in common]
            y = [data[b][g] for g in common]
            rho, p = stats.spearmanr(x, y)
            rho = float(rho)
            se = 1.06 / math.sqrt(n - 3)
            z = math.atanh(max(min(rho, 0.999999), -0.999999))
            pairs.append({"a": a, "b": b, "n": n, "rho": rho, "p_value": float(p),
                          "ci_low": math.tanh(z - Z95 * se), "ci_high": math.tanh(z + Z95 * se)})
    # Benjamini–Hochberg FDR
    m = len(pairs)
    for rank, pr in enumerate(sorted(pairs, key=lambda r: r["p_value"]), 1):
        pr["_bh"] = pr["p_value"] * m / rank
    running = 1.0
    for pr in sorted(pairs, key=lambda r: r["p_value"], reverse=True):
        running = min(running, pr.pop("_bh"))
        pr["q_value"] = running
    return {
        "level": level, "method": "Spearman rank correlation across geographic units; 95% CI via Fisher z with "
                                  "SE = 1.06/√(n−3); p-values adjusted for multiple testing (Benjamini–Hochberg q).",
        "indicators": [store.indicator_index[k] | {"n": sum(v is not None for v in data[k].values())} for k in keys],
        "pairs": pairs,
        "caveats": [
            "Ecological correlation: associations between district averages do not describe households and must not be "
            "read as causal effects (ecological fallacy).",
            "n ≤ 30 districts: confidence intervals are wide; many indicators share common drivers (urbanisation, Kigali).",
            "Indicators come from different surveys/periods (EICV7 2023/24, FinScope 2024) and universes (households, "
            "population, adults 16+).",
            "Sampling error in each district estimate is not propagated into the correlation.",
        ],
        "data": data,
    }


# ---------------------------------------------------------------- composite (experimental)
def composite_index(store: DataStore) -> dict:
    dists = store.districts()
    comp_vals = {}
    for ind, tr in COMPOSITE_COMPONENTS:
        comp_vals[ind] = {d["geo_id"]: deprivation(store.value(ind, "district", d["geo_id"]), tr) for d in dists}
    ids = [d["geo_id"] for d in dists if all(comp_vals[i][d["geo_id"]] is not None for i, _ in COMPOSITE_COMPONENTS)]
    z = {}
    for ind, _ in COMPOSITE_COMPONENTS:
        arr = np.array([comp_vals[ind][g] for g in ids])
        mu, sd = arr.mean(), arr.std(ddof=1)
        z[ind] = {g: (comp_vals[ind][g] - mu) / sd for g in ids}

    def score(exclude=None):
        use = [i for i, _ in COMPOSITE_COMPONENTS if i != exclude]
        return {g: sum(z[i][g] for i in use) / len(use) for g in ids}

    full = score()
    lo, hi = min(full.values()), max(full.values())
    poverty = {g: store.value("poverty_rate", "district", g) for g in ids}
    rho, p = stats.spearmanr([full[g] for g in ids], [poverty[g] for g in ids])
    n = len(ids)
    se = 1.06 / math.sqrt(n - 3)
    zr = math.atanh(float(rho))
    loo = []
    for ind, _ in COMPOSITE_COMPONENTS:
        s = score(exclude=ind)
        r2, _ = stats.spearmanr([full[g] for g in ids], [s[g] for g in ids])
        loo.append({"dropped": ind, "rank_correlation_with_full": float(r2)})
    rows = sorted(({"geo_id": g, "name": store.geo_name("district", g), "score": (full[g] - lo) / (hi - lo) * 100,
                    "z_mean": full[g], "poverty_rate": poverty[g],
                    "components": {i: comp_vals[i][g] for i, _ in COMPOSITE_COMPONENTS}} for g in ids),
                  key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {
        "name": "Imboni Service-Gap Index (experimental)", "status": "experimental",
        "formula": "SGI_d = mean_j z_dj, where z_dj = (x_dj − mean_j) / sd_j across the 30 districts and x_dj is the "
                   "share of households/people/adults lacking service j. Displayed score rescales SGI to 0–100 (min–max).",
        "components": [{"indicator_id": i, "transform": t, "weight": 1 / len(COMPOSITE_COMPONENTS),
                        "name": store.indicator_index[i]["name"]} for i, t in COMPOSITE_COMPONENTS],
        "validation": {"against": "poverty_rate (EICV7 district monetary poverty, NOT an input)", "n": n,
                       "spearman_rho": float(rho), "p_value": float(p),
                       "ci_low": math.tanh(zr - Z95 * se), "ci_high": math.tanh(zr + Z95 * se)},
        "sensitivity_leave_one_out": loo, "rows": rows,
        "warnings": [
            "Experimental and NOT the official MPI. It is a relative ranking of service gaps across districts only.",
            "Equal weights are a transparent default, not a normative judgement; leave-one-out results show sensitivity.",
            "Mixes universes (households, population, adults 16+) and sources (EICV7 2023/24, FinScope 2024).",
            "Z-scores make the score relative: a low score means 'better than other districts', not 'no deprivation'.",
        ],
    }


# ---------------------------------------------------------------- trends
def trends(store: DataStore) -> dict:
    rows = []
    for lvl, gid in [("national", "rwanda")] + [("province", p["geo_id"]) for p in store.provinces()] + [("area", "urban"), ("area", "rural")]:
        v24 = store.one("poverty_rate_pp", lvl, gid)
        v17 = store.one("poverty_rate_2017_modelled", lvl, gid)
        if not v24 or not v17:
            continue
        rows.append({"level": lvl, "geo_id": gid, "name": store.geo_name(lvl, gid), "p2017": v17["value"],
                     "p2024": v24["value"], "change_pp": v24["value"] - v17["value"],
                     "change_pct": (v24["value"] - v17["value"]) / v17["value"] * 100,
                     "ci2024": [v24["ci_low"], v24["ci_high"]],
                     "flags": [f for f in (v24["flags"] or "").split(";") if f]})
    cons = []
    for lvl, gid in [("national", "rwanda")] + [("province", p["geo_id"]) for p in store.provinces()] + \
                    [("area", "urban"), ("area", "rural")] + [("quintile", f"q{i}") for i in range(1, 6)]:
        a, b = store.value("median_consumption_ae_2017", lvl, gid), store.value("median_consumption_ae", lvl, gid)
        if a and b:
            cons.append({"level": lvl, "geo_id": gid, "name": store.geo_name(lvl, gid) or gid.upper(), "c2017": a,
                         "c2024": b, "change_pct": (b - a) / a * 100})
    fin = []
    for lvl, gid in [("national", "rwanda"), ("area", "urban"), ("area", "rural"), ("sex", "male"), ("sex", "female")]:
        for period in ("2020", "2024"):
            vals = {}
            for k in ["fs_banked", "fs_other_formal", "fs_informal_only", "fs_excluded"]:
                o = store.one(k, lvl, gid, period=period)
                vals[k] = o["value"] if o else None
            fin.append({"level": lvl, "geo_id": gid, "name": gid.title() if lvl != "national" else "Rwanda",
                        "period": period, **vals})
    return {"poverty": rows, "consumption": cons, "finscope": fin,
            "notes": ["2017 values are NISR's modelled re-estimates on the EICV7 methodology (comparable), not the "
                      "originally published EICV5 rates.",
                      "Urban/rural rows in Poverty Profile Tables 5.1–5.2 use 2012 urban definitions and differ from "
                      "EICV7 Table 9.1 (urban 16.7%, rural 31.6%).",
                      "Consumption is in thousand RWF per adult equivalent per year, January 2024 prices.",
                      "FinScope 2020 → 2024 comparison uses the FinScope Access Strand as published (adults 16+)."]}


# ---------------------------------------------------------------- data quality
def data_quality(store: DataStore) -> dict:
    by_level: dict[str, dict[str, int]] = {}
    missing, cv_flags, status_counts = [], {"cv_gt_15_use_with_caution": 0, "cv_gt_30_unreliable": 0}, {}
    for o in store.observations:
        by_level.setdefault(o["indicator_id"], {}).setdefault(o["level"], 0)
        by_level[o["indicator_id"]][o["level"]] += 1
        status_counts[o["status"]] = status_counts.get(o["status"], 0) + 1
        fl = (o.get("flags") or "").split(";")
        if o["value"] is None:
            missing.append({"indicator_id": o["indicator_id"], "geo_name": o["geo_name"], "level": o["level"],
                            "breakdown": o.get("breakdown"), "flags": [f for f in fl if f]})
        for f in cv_flags:
            if f in fl:
                cv_flags[f] += 1
    caution = [enrich(store, o) for o in store.observations
               if any(f in (o.get("flags") or "") for f in ("cv_gt_15", "cv_gt_30", "ci_upper_above_100", "se_zero"))]
    return {"n_observations": len(store.observations), "status_counts": status_counts,
            "coverage": by_level, "missing": missing, "precision_flags": cv_flags,
            "flagged_observations": caution, "validation": store.validation,
            "cv_rule": "Imboni convention: CV > 15% = use with caution; CV > 30% = unreliable (CV as published by NISR)."}


# ---------------------------------------------------------------- financial inclusion
def financial_inclusion(store: DataStore) -> dict:
    strand_keys = ["fs_banked", "fs_other_formal", "fs_informal_only", "fs_excluded"]

    def strand(level, gid, period="2024"):
        out = {}
        for k in strand_keys:
            o = store.one(k, level, gid, period=period)
            out[k] = None if o is None else o["value"]
        return out

    districts = []
    for d in store.districts():
        g = d["geo_id"]
        districts.append({"geo_id": g, "name": d["name"], "province_id": d["province_id"], **strand("district", g),
                          "formally_served": store.value("fs_formally_served", "district", g),
                          "poverty_rate": store.value("poverty_rate", "district", g),
                          "mobile_phone": store.value("mobile_phone", "district", g),
                          "smartphone": store.value("smartphone", "district", g),
                          "internet_home": store.value("internet_home", "district", g)})
    provinces = [{"geo_id": p["geo_id"], "name": p["name"], **strand("province", p["geo_id"])} for p in store.provinces()]
    headline = [{"key": o["breakdown"], "label": o["note"], "value": o["value"], "status": o["status"]}
                for o in store.query("fs_headline")]
    eicv = {k: {"all": store.value(k, "national", "rwanda"), "poor": store.value(k, "poverty_status", "poor"),
                "non_poor": store.value(k, "poverty_status", "non_poor"),
                "gap_pp": store.value(k, "poverty_status", "non_poor") - store.value(k, "poverty_status", "poor"),
                "meta": store.indicator_index[k]} for k in ["hh_savings_account", "hh_momo_account"]}
    vup = []
    for comp in ["direct_support", "classic_public_works", "expanded_public_works", "nsds"]:
        o = store.one("vup_payment_sacco", "vup_component", comp)
        vup.append({"component": o["geo_name"], "sacco": o["value"],
                    "momo": store.value("vup_payment_momo", "vup_component", comp),
                    "on_time": store.value("vup_payment_on_time", "vup_component", comp),
                    "households": store.value("vup_component_households", "vup_component", comp),
                    "poverty_rate": store.value("vup_poverty_rate", "vup_component", comp)})
    fs = {"loan_approved": store.value("vup_fs_loan_approved", "vup_component", "financial_services"),
          "avg_loan": store.value("vup_fs_avg_loan", "vup_component", "financial_services"),
          "households": store.value("vup_component_households", "vup_component", "financial_services"),
          "poverty_rate": metric(store, "vup_poverty_rate", "vup_component", "financial_services")}
    shocks = [{"response": o["breakdown"], "all": o["value"],
               "poor": store.value("shock_response", "poverty_status", "poor", o["breakdown"]),
               "non_poor": store.value("shock_response", "poverty_status", "non_poor", o["breakdown"])}
              for o in store.query("shock_response", "national")]
    corr = correlations(store, ["poverty_rate", "fs_banked", "fs_formally_served", "fs_excluded", "fs_informal_only",
                                "smartphone", "mobile_phone", "internet_home"])
    return {
        "national_strand": {"2024": strand("national", "rwanda", "2024"), "2020": strand("national", "rwanda", "2020")},
        "area": {a: {"2024": strand("area", a, "2024"), "2020": strand("area", a, "2020")} for a in ("urban", "rural")},
        "sex": {s: {"2024": strand("sex", s, "2024"), "2020": strand("sex", s, "2020")} for s in ("male", "female")},
        "provinces": provinces, "districts": districts, "headline": headline, "eicv": eicv, "vup": vup,
        "vup_financial_services": fs, "shock_responses": shocks, "correlations": corr,
        "unavailable": store.unavailable_financial,
        "sources": [store.source_ref(s) for s in ("finscope_2024", "eicv7_pp", "eicv7_vup", "eicv7_questionnaire")],
        "caveats": [
            "FinScope measures ADULTS (16+) in 2024; EICV7 savings/MoMo items measure HOUSEHOLDS (any member) in 2023/24.",
            "FinScope district values are transcribed from printed chart labels (rounded integers); segments may sum to 99–101%.",
            "EICV7 collects credit and savings details (Section 10) but NISR has not published aggregate tables; those "
            "indicators are shown as unavailable rather than estimated.",
        ],
    }
