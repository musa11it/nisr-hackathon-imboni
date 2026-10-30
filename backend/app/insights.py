"""Evidence-backed policy insights generated from the validated observations.

Every insight is computed at request time from ``data/processed`` — no number is
typed in here. Each one carries the supporting statistic, its source table, the
geographic scope the source supports, a *potential* implication (the team's
interpretation, labelled as such) and the limitations that bound it.
If an input is missing the insight is skipped rather than approximated.
"""
from __future__ import annotations

from . import analytics
from .store import DataStore

IMPLICATION_LABEL = "Potential implication (DataMinds interpretation, not an NISR finding)"


def _p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _src(store: DataStore, source_id: str, table: str) -> dict:
    ref = store.source_ref(source_id)
    return {**ref, "table": table}


def _two_lenses(store: DataStore) -> dict | None:
    d = analytics.dashboard(store)
    ov = d["overlap"]["cells"]
    if any(v is None for v in ov.values()):
        return None
    pov, mpi = store.value("poverty_rate", "national", "rwanda"), store.value("mpi_incidence", "national", "rwanda")
    either = d["overlap"]["either"]
    return {
        "id": "two_lenses", "theme": "Targeting",
        "title": "Monetary and multidimensional poverty identify different people",
        "finding": f"{ov['mpi_poor__monetary_poor']:.1f}% of Rwandans are poor on both measures, but "
                   f"{either:.1f}% are poor on at least one. Only "
                   f"{d['overlap']['share_of_monetary_poor_also_mpi_poor']:.0f}% of the monetary poor are also MPI-poor.",
        "statistics": [
            {"label": "Monetary poverty (headcount)", "value": pov, "unit": "%", "status": "official"},
            {"label": "MPI incidence (H)", "value": mpi, "unit": "%", "status": "official"},
            {"label": "Poor on both measures", "value": ov["mpi_poor__monetary_poor"], "unit": "%", "status": "official"},
            {"label": "Poor on at least one measure", "value": either, "unit": "%", "status": "calculated"},
        ],
        "sources": [_src(store, "eicv7_mpi", "Table 3.1"), _src(store, "eicv7_mi", "Table A9.23")],
        "scope": "National (2023/24)",
        "implication": "Programmes that screen on one poverty measure alone are likely to miss a substantial group "
                       "visible only in the other; combining consumption and deprivation criteria could reduce "
                       "exclusion errors.",
        "limitations": ["The two measures use different concepts (consumption vs. 13 deprivations) and are not "
                        "interchangeable.", "The overlap table is published at national/area/province level only."],
    }


def _rural_urban(store: DataStore) -> dict | None:
    r, u = analytics.metric(store, "poverty_rate", "area", "rural"), analytics.metric(store, "poverty_rate", "area", "urban")
    hr, hu = store.value("mpi_incidence", "area", "rural"), store.value("mpi_incidence", "area", "urban")
    if not r or not u or hr is None or hu is None:
        return None
    test = analytics.compare_to_reference(r, u)
    sig = (f"The monetary gap is statistically significant (approximate z-test, {_p(test['p_value'])})."
           if test.get("available") and test["label"] != "not statistically different from" else
           "The monetary gap is not statistically significant at the 95% level.")
    return {
        "id": "rural_urban", "theme": "Geography",
        "title": "Poverty is concentrated in rural areas on both measures",
        "finding": f"Rural MPI incidence is {hr:.1f}% vs {hu:.1f}% in urban areas ({hr / hu:.1f}×). Rural monetary "
                   f"poverty is {r['value']:.1f}% (95% CI {r['ci_low']:.1f}–{r['ci_high']:.1f}) vs urban "
                   f"{u['value']:.1f}% ({u['ci_low']:.1f}–{u['ci_high']:.1f}). {sig}",
        "statistics": [
            {"label": "Rural MPI incidence", "value": hr, "unit": "%", "status": "official"},
            {"label": "Urban MPI incidence", "value": hu, "unit": "%", "status": "official"},
            {"label": "Rural − urban MPI gap", "value": hr - hu, "unit": "pp", "status": "calculated"},
            {"label": "Rural − urban monetary gap", "value": r["value"] - u["value"], "unit": "pp", "status": "calculated"},
        ],
        "sources": [_src(store, "eicv7_mpi", "Table B.5"), _src(store, "eicv7_mi", "Table A9.23")],
        "scope": "Urban / rural (2023/24)",
        "implication": "Rural service delivery (housing, cooking energy, water) is likely to reach most of the "
                       "multidimensionally poor population.",
        "limitations": ["Independence is assumed in the z-test; NISR urban/rural definitions follow EICV7."],
    }


def _district_hotspots(store: DataStore) -> dict | None:
    layer = analytics.map_layer(store, "poverty_rate", "district")
    above = [r for r in layer["rows"] if (r.get("vs_national") or {}).get("label") == "higher than"]
    if not above:
        return None
    above.sort(key=lambda r: -r["value"])
    top = above[0]
    nat = layer["national"]["value"]
    names = ", ".join(r["geo_name"] for r in above[:5])
    overlap_top = [r["geo_name"] for r in layer["rows"] if r.get("rank_low") is not None and r["rank_low"] <= 1]
    return {
        "id": "district_hotspots", "theme": "Geography",
        "title": f"{len(above)} of {layer['summary']['n']} districts have poverty significantly above the national rate",
        "finding": f"The highest estimate is {top['geo_name']} at {top['value']:.1f}% (95% CI "
                   f"{top['ci_low']:.1f}–{top['ci_high']:.1f}) vs {nat:.1f}% nationally. Highest five of those "
                   f"significantly above: {names}. {len(overlap_top)} district(s) have a 90% rank interval that "
                   f"includes rank 1, so a single 'poorest district' should not be singled out.",
        "statistics": [
            {"label": "Districts significantly above national", "value": len(above), "unit": "districts", "status": "calculated"},
            {"label": f"Poverty rate, {top['geo_name']}", "value": top["value"], "unit": "%", "status": "official"},
            {"label": "District range (max ÷ min)", "value": layer["summary"]["range_ratio"], "unit": "×", "status": "calculated"},
        ],
        "sources": [_src(store, "eicv7_mi", "Table A9.23 (with standard errors)")],
        "scope": "District (30 districts, 2023/24)",
        "implication": "District allocation formulas could weight these districts more heavily, while treating "
                       "close rankings as ties.",
        "limitations": ["Approximate z-tests vs the national estimate (which contains the district) are conservative.",
                        "Rank intervals come from Monte-Carlo draws using published standard errors."],
    }


def _top_deprivations(store: DataStore) -> dict | None:
    rows = analytics.dashboard(store)["deprivations"]
    rows = [r for r in rows if r["censored"] is not None]
    if len(rows) < 3:
        return None
    a, b, c = rows[:3]
    return {
        "id": "top_deprivations", "theme": "Multidimensional poverty",
        "title": f"{a['label']} and {b['label'].lower()} are the most common deprivations among the MPI-poor",
        "finding": f"{a['censored']:.1f}% of Rwandans are MPI-poor and deprived in {a['label'].lower()}, "
                   f"{b['censored']:.1f}% in {b['label'].lower()} and {c['censored']:.1f}% in {c['label'].lower()} "
                   "(censored headcounts).",
        "statistics": [{"label": f"Censored headcount — {r['label']}", "value": r["censored"], "unit": "%",
                        "status": "official"} for r in rows[:3]] +
                      [{"label": f"Recomputed contribution — {r['label']}", "value": r["contribution_calc"], "unit": "%",
                        "status": "calculated"} for r in rows[:2] if r["contribution_calc"] is not None],
        "sources": [_src(store, "eicv7_mpi", "Table B.3; contributions recomputed as w·CH / Σ w·CH")],
        "scope": "National (2023/24); province tables also available",
        "implication": "Clean-cooking and housing-materials programmes target the deprivations most widespread "
                       "among the multidimensionally poor.",
        "limitations": ["Published contribution tables (B.7–B.9) are internally inconsistent; Imboni shows the "
                        "recomputed values labelled 'calculated'.", "Censored headcounts are not published by district."],
    }


def _financial_strand(store: DataStore) -> dict | None:
    g = lambda k, lvl, gid, p: (store.one(k, lvl, gid, period=p) or {}).get("value")  # noqa: E731
    b24, b20 = g("fs_banked", "national", "rwanda", "2024"), g("fs_banked", "national", "rwanda", "2020")
    x24, x20 = g("fs_excluded", "national", "rwanda", "2024"), g("fs_excluded", "national", "rwanda", "2020")
    rb, ub = g("fs_banked", "area", "rural", "2024"), g("fs_banked", "area", "urban", "2024")
    o24 = g("fs_other_formal", "national", "rwanda", "2024")
    if None in (b24, x24, x20, rb, ub, o24):
        return None
    return {
        "id": "financial_strand", "theme": "Financial inclusion",
        "title": "Almost all adults are financially included, but few are banked",
        "finding": f"FinScope 2024 finds {x24:.0f}% of adults financially excluded (down from {x20:.0f}% in 2020), yet "
                   f"only {b24:.0f}% are banked — {rb:.0f}% in rural areas vs {ub:.0f}% in urban areas. "
                   f"{o24:.0f}% of adults use formal non-bank products only (FinScope 'other formal' segment).",
        "statistics": [
            {"label": "Adults banked, 2024", "value": b24, "unit": "%", "status": "official_transcribed"},
            {"label": "Adults banked, 2020", "value": b20, "unit": "%", "status": "official_transcribed"},
            {"label": "Adults excluded, 2024", "value": x24, "unit": "%", "status": "official_transcribed"},
            {"label": "Urban − rural banked gap", "value": ub - rb, "unit": "pp", "status": "calculated"},
        ],
        "sources": [_src(store, "finscope_2024", "Access Strand figures")],
        "scope": "National, urban/rural, province and district (adults 16+, 2024)",
        "implication": "The next frontier may be deepening use (savings, credit, insurance) through channels people "
                       "already use, rather than first-time access.",
        "limitations": ["Values are transcribed from chart labels (rounded integers).",
                        "FinScope measures adults (16+), not households."],
    }


def _savings_gap(store: DataStore) -> dict | None:
    poor, nonpoor = store.value("hh_savings_account", "poverty_status", "poor"), store.value("hh_savings_account", "poverty_status", "non_poor")
    mp, mn = store.value("hh_momo_account", "poverty_status", "poor"), store.value("hh_momo_account", "poverty_status", "non_poor")
    if None in (poor, nonpoor, mp, mn):
        return None
    return {
        "id": "savings_gap", "theme": "Financial inclusion",
        "title": "Poor households are less likely to hold savings and mobile-money accounts",
        "finding": f"{poor:.1f}% of poor households have at least one savings account vs {nonpoor:.1f}% of non-poor "
                   f"households (gap {nonpoor - poor:.1f} pp). For mobile money the figures are {mp:.1f}% vs {mn:.1f}%.",
        "statistics": [
            {"label": "Savings account — poor households", "value": poor, "unit": "%", "status": "official"},
            {"label": "Savings account — non-poor households", "value": nonpoor, "unit": "%", "status": "official"},
            {"label": "Mobile-money account — poor households", "value": mp, "unit": "%", "status": "official"},
            {"label": "Mobile-money account — non-poor households", "value": mn, "unit": "%", "status": "official"},
        ],
        "sources": [_src(store, "eicv7_pp", "Table 6.9 (memo items)")],
        "scope": "National, by poverty status (households, 2024)",
        "implication": "Mobile money is already widespread among poor households and may be a practical channel for "
                       "savings products and transfers.",
        "limitations": ["Not published by district or province; no standard errors published for these items.",
                        "Account ownership does not measure active use or balances."],
    }


def _vup_channels(store: DataStore) -> dict | None:
    rows = analytics.financial_inclusion(store)["vup"]
    if not rows or any(r["sacco"] is None or r["momo"] is None for r in rows):
        return None
    ontime = [r["on_time"] for r in rows if r["on_time"] is not None]
    return {
        "id": "vup_channels", "theme": "Social protection",
        "title": "VUP transfers still flow mainly through SACCOs, and few arrive on time",
        "finding": "Across VUP components, " + "; ".join(
            f"{r['component']}: {r['sacco']:.0f}% via SACCO, {r['momo']:.0f}% via mobile money" for r in rows) +
                   (f". Only {min(ontime):.0f}–{max(ontime):.0f}% of beneficiaries report the last payment arriving on time."
                    if ontime else "."),
        "statistics": [{"label": f"Paid via mobile money — {r['component']}", "value": r["momo"], "unit": "%",
                        "status": "official"} for r in rows],
        "sources": [_src(store, "eicv7_vup", "VUP thematic tables (payment channel, timeliness)")],
        "scope": "National, by VUP component (2023/24)",
        "implication": "Given high household mobile-money ownership, digital payment of transfers could be assessed "
                       "for timeliness gains — an evaluation question, not a demonstrated effect.",
        "limitations": ["Self-reported timeliness; component samples are small and no SEs are published here."],
    }


def _banked_association(store: DataStore) -> dict | None:
    pairs = analytics.correlations(store, ["poverty_rate", "fs_banked"])["pairs"]
    if not pairs:
        return None
    p = pairs[0]
    direction = "lower" if p["rho"] < 0 else "higher"
    strength = "weak" if abs(p["rho"]) < 0.3 else "moderate" if abs(p["rho"]) < 0.6 else "strong"
    return {
        "id": "banked_association", "theme": "Association analysis",
        "title": f"Poorer districts tend to have {direction} shares of banked adults ({strength} ecological association)",
        "finding": f"Across {p['n']} districts, Spearman ρ = {p['rho']:.2f} (95% CI {p['ci_low']:.2f} to "
                   f"{p['ci_high']:.2f}, {_p(p['p_value'])}) between monetary poverty and the share of banked adults.",
        "statistics": [{"label": "Spearman ρ (district level)", "value": p["rho"], "unit": "", "status": "calculated"},
                       {"label": "Number of districts", "value": p["n"], "unit": "", "status": "calculated"}],
        "sources": [_src(store, "eicv7_mi", "Table A9.23"), _src(store, "finscope_2024", "district Access Strand")],
        "scope": "District (30 districts)",
        "implication": "Financial-access gaps and poverty overlap geographically, so district-targeted inclusion "
                       "programmes would partly reach poorer areas.",
        "limitations": ["Ecological correlation: says nothing about whether poor individuals are unbanked, and is "
                        "not causal.", "Wide confidence interval with n = 30; different surveys and universes."],
    }


def _poverty_trend(store: DataStore) -> dict | None:
    p24, p17 = store.value("poverty_rate_pp", "national", "rwanda"), store.value("poverty_rate_2017_modelled", "national", "rwanda")
    if p24 is None or p17 is None:
        return None
    return {
        "id": "poverty_trend", "theme": "Trends",
        "title": f"Monetary poverty fell by {abs(p24 - p17):.1f} points between 2016/17 and 2024 on a comparable basis"
                 if p24 < p17 else "Monetary poverty did not fall between 2016/17 and 2024 on a comparable basis",
        "finding": f"Poverty fell from {p17:.1f}% (2016/17, re-estimated on the EICV7 methodology) to {p24:.1f}% in "
                   f"2024 — a change of {p24 - p17:+.1f} percentage points.",
        "statistics": [{"label": "Poverty 2016/17 (modelled, comparable)", "value": p17, "unit": "%", "status": "official"},
                       {"label": "Poverty 2024", "value": p24, "unit": "%", "status": "official"},
                       {"label": "Change", "value": p24 - p17, "unit": "pp", "status": "calculated"}],
        "sources": [_src(store, "eicv7_pp", "Table 0.1")],
        "scope": "National and province",
        "implication": "Progress is measurable on a consistent basis; the remaining poor are concentrated "
                       "geographically, which favours targeted rather than uniform approaches.",
        "limitations": ["The 2017 value is NISR's modelled re-estimate, not the originally published EICV5 rate."],
    }


BUILDERS = [_two_lenses, _rural_urban, _district_hotspots, _top_deprivations, _poverty_trend,
            _financial_strand, _savings_gap, _vup_channels, _banked_association]


def policy_insights(store: DataStore) -> dict:
    out, skipped = [], []
    for build in BUILDERS:
        try:
            item = build(store)
        except (KeyError, TypeError, ZeroDivisionError) as exc:  # missing inputs: skip, never approximate
            skipped.append({"id": build.__name__.lstrip("_"), "reason": f"{type(exc).__name__}: {exc}"})
            continue
        if item is None:
            skipped.append({"id": build.__name__.lstrip("_"), "reason": "required inputs not available"})
        else:
            out.append({**item, "implication_label": IMPLICATION_LABEL})
    return {"insights": out, "skipped": skipped,
            "method": "Each insight is recomputed from the validated observations at request time; statistics carry "
                      "their status (official / official · transcribed / calculated)."}
