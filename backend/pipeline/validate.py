"""Automated validation of processed observations.

Severity:
  error   – pipeline output is wrong (parsing bug, range violation, duplicate); build fails
  warning – the *source* is internally inconsistent; documented and surfaced in the app
  info    – passed benchmark / consistency checks are recorded for transparency
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction

from .geography import DISTRICT_PROVINCE, PROVINCES
from .indicators import INDICATOR_INDEX, MPI_INDICATORS

# Published benchmarks (EICV7 reports). Used ONLY to validate parsed values.
BENCHMARKS = [
    ("poverty_rate", "national", "rwanda", 27.4, 0.05, "EICV7 monetary poverty 27.4%"),
    ("mpi_incidence", "national", "rwanda", 30.5, 0.001, "MPI incidence 30.5%"),
    ("mpi_incidence", "area", "rural", 36.7, 0.001, "Rural MPI incidence 36.7%"),
    ("mpi_incidence", "area", "urban", 14.8, 0.001, "Urban MPI incidence 14.8%"),
    ("mpi_incidence", "province", "kigali", 12.4, 0.001, "City of Kigali 12.4%"),
    ("mpi_incidence", "province", "southern", 35.2, 0.001, "Southern 35.2%"),
    ("mpi_incidence", "province", "western", 33.5, 0.001, "Western 33.5%"),
    ("mpi_incidence", "province", "northern", 28.7, 0.001, "Northern 28.7%"),
    ("mpi_incidence", "province", "eastern", 34.4, 0.001, "Eastern 34.4%"),
    ("mpi", "national", "rwanda", 0.136, 0.0001, "MPI 0.136"),
    ("mpi", "area", "urban", 0.065, 0.0001, "Urban MPI 0.065"),
    ("mpi", "area", "rural", 0.164, 0.0001, "Rural MPI 0.164"),
    ("mpi_ch_cooking_fuel", "national", "rwanda", 29.2, 0.001, "CH cooking fuel 29.2%"),
    ("mpi_ch_housing_materials", "national", "rwanda", 28.1, 0.001, "CH housing materials 28.1%"),
    ("mpi_ch_drinking_water", "national", "rwanda", 17.4, 0.001, "CH drinking water 17.4%"),
    ("mpi_ch_health_insurance", "national", "rwanda", 15.1, 0.001, "CH health insurance 15.1%"),
    ("mpi_intensity", "national", "rwanda", 44.6, 0.001, "MPI intensity 44.6%"),
]

WEIGHTS = {i[0]: i[3] for i in MPI_INDICATORS}


def _key(o):
    return (o["indicator_id"], o["level"], o["geo_id"], o["period"], o.get("breakdown") or "")


def validate(observations: list[dict], extra_checks: list[dict]) -> dict:
    checks: list[dict] = []

    def add(name, passed, detail, severity_if_fail="error"):
        checks.append({"check": name, "passed": bool(passed), "detail": detail,
                       "severity": "info" if passed else severity_if_fail})

    idx = {}
    for o in observations:
        idx[_key(o)] = o

    def val(ind, level, gid, period=None, breakdown=""):
        for k, o in idx.items():
            if k[0] == ind and k[1] == level and k[2] == gid and k[4] == breakdown and (period is None or k[3] == period):
                return o["value"]
        return None

    # 1. duplicates
    dupes = [k for k, n in Counter(_key(o) for o in observations).items() if n > 1]
    add("no_duplicate_observations", not dupes, f"{len(dupes)} duplicates: {dupes[:5]}")

    # 2. unknown indicators & ranges
    unknown = {o["indicator_id"] for o in observations} - set(INDICATOR_INDEX)
    add("all_indicators_catalogued", not unknown, f"unknown: {sorted(unknown)}")
    bad = []
    for o in observations:
        v, unit = o["value"], INDICATOR_INDEX.get(o["indicator_id"], {}).get("unit", "")
        if v is None:
            continue
        if unit.startswith("%") and not (0 <= v <= 100):
            bad.append((o["indicator_id"], o["geo_id"], v))
        if unit == "index (0–1)" and not (0 <= v <= 1):
            bad.append((o["indicator_id"], o["geo_id"], v))
        if unit in {"households", "persons", "RWF", "RWF '000/yr"} and v < 0:
            bad.append((o["indicator_id"], o["geo_id"], v))
    add("values_within_valid_ranges", not bad, f"{len(bad)} out of range: {bad[:5]}")

    # 3. missing values are explicit, never silently zero
    miss = [o for o in observations if o["value"] is None]
    add("missing_values_flagged", all(o["flags"] for o in miss),
        f"{len(miss)} missing values, all carry an explicit flag")

    # 4. expected coverage
    for ind in ["poverty_rate", "health_insurance_cov", "electricity_lighting", "improved_water",
                "improved_sanitation", "internet_home", "mobile_phone", "smartphone", "roof_metal",
                "umudugudu", "workforce_ratio", "sending_transfers", "fs_banked", "fs_excluded",
                "households_census", "household_size_census"]:
        got = {o["geo_name"] for o in observations if o["indicator_id"] == ind and o["level"] == "district"}
        add(f"district_coverage:{ind}", got == set(DISTRICT_PROVINCE),
            f"{len(got)}/30 districts; missing {sorted(set(DISTRICT_PROVINCE) - got)}")
    for ind in ["poverty_rate", "mpi_incidence", "mpi", "mpi_ch_cooking_fuel", "fs_banked"]:
        got = {o["geo_id"] for o in observations if o["indicator_id"] == ind and o["level"] == "province"}
        add(f"province_coverage:{ind}", got == set(PROVINCES), f"{len(got)}/5 provinces")

    # 5. benchmarks
    for ind, lvl, gid, expected, tol, label in BENCHMARKS:
        v = val(ind, lvl, gid)
        ok = v is not None and abs(v - expected) <= tol
        add(f"benchmark:{label}", ok, f"parsed={v} expected={expected}")

    # 6. precision fields are coherent: CI contains the estimate; CI ~ estimate ± 1.96·SE
    incoh = []
    for o in observations:
        if o["se"] is None or o["ci_low"] is None or o["value"] is None:
            continue
        if not (o["ci_low"] - 1e-6 <= o["value"] <= o["ci_high"] + 1e-6):
            incoh.append((o["indicator_id"], o["geo_id"], "estimate outside CI"))
        half = (o["ci_high"] - o["ci_low"]) / 2
        if o["se"] > 0 and abs(half / o["se"] - 1.96) > 0.1:
            incoh.append((o["indicator_id"], o["geo_id"], f"half-width/SE={half / o['se']:.2f}"))
    add("ci_consistent_with_se", not incoh, f"{len(incoh)} incoherent: {incoh[:5]}", "warning")

    # 7. MPI identities
    rows = defaultdict(dict)
    for o in observations:
        if o["indicator_id"] in {"mpi_incidence", "mpi_intensity", "mpi", "population_share"}:
            rows[(o["level"], o["geo_id"])][o["indicator_id"]] = o["value"]
    worst = 0.0
    for (lvl, gid), r in rows.items():
        if {"mpi_incidence", "mpi_intensity", "mpi"} <= r.keys():
            worst = max(worst, abs(r["mpi_incidence"] * r["mpi_intensity"] / 1e4 - r["mpi"]))
    add("mpi_identity_M0_equals_H_times_A", worst <= 0.0015, f"max |H·A − M0| = {worst:.4f} (rounding tolerance 0.0015)")

    for lvl, gid in [("national", "rwanda"), ("area", "urban"), ("area", "rural"),
                     *[("province", p) for p in PROVINCES], *[("quintile", f"q{i}") for i in range(1, 6)]]:
        chs = {w: val(f"mpi_ch_{w}", lvl, gid) for w in WEIGHTS}
        m0 = val("mpi", lvl, gid)
        if None in chs.values() or m0 is None:
            add(f"mpi_weighted_ch_sum:{gid}", False, "missing inputs")
            continue
        s = float(sum(Fraction(str(c)) * WEIGHTS[w] for w, c in chs.items())) / 100
        add(f"mpi_weighted_ch_sum:{gid}", abs(s - m0) <= 0.004,
            f"Σ w·CH = {s:.4f} vs published M0 = {m0:.3f} (diff {s - m0:+.4f}; CH printed to 1 decimal)", "warning")

    # population-share-weighted aggregation
    for parts, label in [([("province", p) for p in PROVINCES], "provinces"), ([("area", "urban"), ("area", "rural")], "areas")]:
        shares = [rows[p].get("population_share") for p in parts]
        hs = [rows[p].get("mpi_incidence") for p in parts]
        if None not in shares and None not in hs:
            agg = sum(s * h for s, h in zip(shares, hs)) / sum(shares)
            nat = rows[("national", "rwanda")]["mpi_incidence"]
            add(f"mpi_H_aggregates_from_{label}", abs(agg - nat) <= 0.6,
                f"share-weighted H = {agg:.2f} vs national {nat} (population shares printed as integers)", "warning")

    # 8. Published contributions vs recomputed
    for lvl, gid in [("national", "rwanda"), ("area", "urban"), ("area", "rural"), *[("province", p) for p in PROVINCES]]:
        pub = {w: val(f"mpi_contrib_{w}", lvl, gid) for w in WEIGHTS}
        calc = {w: val(f"mpi_contrib_calc_{w}", lvl, gid) for w in WEIGHTS}
        if None in pub.values() or None in calc.values():
            continue
        tot = sum(pub.values())
        diff = max(abs(pub[w] - calc[w]) for w in WEIGHTS)
        worst_ind = max(WEIGHTS, key=lambda w: abs(pub[w] - calc[w]))
        add(f"mpi_published_contributions_sum_100:{gid}", abs(tot - 100) <= 0.6, f"sum = {tot:.1f}", "warning")
        add(f"mpi_published_contributions_reproducible:{gid}", diff <= 1.0,
            f"max |published − recomputed| = {diff:.1f} pp (worst: {worst_ind}: published {pub[worst_ind]} vs "
            f"recomputed {calc[worst_ind]:.1f})", "warning")

    # 9. MPI × monetary overlap tables
    def ov(gid, lvl, cell):
        return val("mpi_monetary_overlap", lvl, gid, breakdown=cell)
    for lvl, gid in [("national", "rwanda"), ("area", "urban"), ("area", "rural"), *[("province", p) for p in PROVINCES]]:
        cells = {c: ov(gid, lvl, c) for c in ["mpi_nonpoor__monetary_nonpoor", "mpi_nonpoor__monetary_poor",
                                              "mpi_poor__monetary_nonpoor", "mpi_poor__monetary_poor", "total__total"]}
        if None in cells.values():
            add(f"overlap_cells_present:{gid}", False, "missing")
            continue
        inner = sum(v for k, v in cells.items() if k != "total__total")
        add(f"overlap_cells_sum_to_total:{gid}", abs(inner - cells["total__total"]) <= 0.3,
            f"Σ cells = {inner:.1f} vs total {cells['total__total']}", "warning")
    add("overlap_margin_equals_MPI_H", abs((ov("rwanda", "national", "mpi_poor__total") or 0) - 30.5) <= 0.05,
        f"MPI-poor margin = {ov('rwanda', 'national', 'mpi_poor__total')}")
    add("overlap_margin_equals_poverty_rate", abs((ov("rwanda", "national", "total__monetary_poor") or 0) - 27.4) <= 0.05,
        f"monetary-poor margin = {ov('rwanda', 'national', 'total__monetary_poor')}")
    sub_sum = sum(ov(p, "province", "total__total") or 0 for p in PROVINCES)
    add("overlap_province_totals_are_population_shares", abs(sub_sum - 100) <= 0.6,
        f"Σ province totals = {sub_sum:.1f}% of national population — province overlap cells are shares of the NATIONAL population",
        "warning")

    # 10. VUP payment channels sum to 100
    for comp in ["direct_support", "classic_public_works", "expanded_public_works", "nsds"]:
        s = (val("vup_payment_sacco", "vup_component", comp) or 0) + (val("vup_payment_momo", "vup_component", comp) or 0)
        add(f"vup_payment_channels_sum_100:{comp}", abs(s - 100) <= 0.1, f"SACCO + MoMo = {s:.2f}")

    # 11. Cross-source sanity: EICV7 household estimate vs Census 2022 count
    e = val("households_eicv", "national", "rwanda")
    c = val("households_census", "national", "rwanda")
    if e and c:
        add("households_eicv_vs_census_within_5pct", abs(e * 1000 - c) / c <= 0.05,
            f"EICV7 {e * 1000:,.0f} vs Census 2022 {c:,.0f} ({(e * 1000 - c) / c:+.1%}); different dates and frames", "warning")

    # 12. Poverty rate: national vs population-weighted provinces (population shares from MPI table B.5)
    shares = {p: rows[("province", p)].get("population_share") for p in PROVINCES}
    pov = {p: val("poverty_rate", "province", p) for p in PROVINCES}
    if None not in shares.values() and None not in pov.values():
        agg = sum(shares[p] * pov[p] for p in PROVINCES) / sum(shares.values())
        nat = val("poverty_rate", "national", "rwanda")
        add("poverty_rate_aggregates_from_provinces", abs(agg - nat) <= 0.8,
            f"share-weighted = {agg:.2f} vs national {nat:.2f} (integer population shares)", "warning")

    checks.extend({"severity": "info" if c["passed"] else c.get("severity", "warning"), **c} for c in extra_checks)

    summary = Counter(c["severity"] for c in checks)
    return {
        "summary": {"total": len(checks), "passed": sum(c["passed"] for c in checks),
                    "errors": summary.get("error", 0), "warnings": summary.get("warning", 0)},
        "checks": checks,
    }
