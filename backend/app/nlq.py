"""Deterministic natural-language explorer.

Questions are mapped to stored, validated statistics with keyword rules — no
language model, no external API. Every answer returns the metric, value, period,
definition, source and a chart-ready table. Unmatched questions get suggestions
instead of a guessed answer.
"""
from __future__ import annotations

import re

from .analytics import enrich
from .store import DataStore

# Synonyms -> indicator id. Longer phrases are matched first.
SYNONYMS: dict[str, str] = {
    "extreme poverty": "extreme_poverty_rate", "extremely poor": "extreme_poverty_rate",
    "monetary poverty": "poverty_rate", "poverty rate": "poverty_rate", "consumption poverty": "poverty_rate",
    "poverty gap": "poverty_gap", "mpi incidence": "mpi_incidence", "multidimensional poverty incidence": "mpi_incidence",
    "multidimensionally poor": "mpi_incidence", "multidimensional poverty": "mpi_incidence",
    "mpi intensity": "mpi_intensity", "intensity": "mpi_intensity", "multidimensional poverty index": "mpi",
    "mpi": "mpi", "health insurance": "health_insurance_cov", "insurance coverage": "health_insurance_cov",
    "electricity": "electricity_lighting", "electrified": "electricity_lighting", "lighting": "electricity_lighting",
    "drinking water": "improved_water", "water": "improved_water", "sanitation": "improved_sanitation",
    "toilet": "improved_sanitation", "internet": "internet_home", "smartphone": "smartphone",
    "mobile phone": "mobile_phone", "phone": "mobile_phone", "roof": "roof_metal", "umudugudu": "umudugudu",
    "workforce": "workforce_ratio", "employment": "workforce_ratio", "transfers": "sending_transfers",
    "banked": "fs_banked", "bank account": "fs_banked", "banking": "fs_banked",
    "financially excluded": "fs_excluded", "financial exclusion": "fs_excluded", "excluded": "fs_excluded",
    "informal": "fs_informal_only", "formally served": "fs_formally_served", "formal inclusion": "fs_formally_served",
    "savings account": "hh_savings_account", "savings": "hh_savings_account", "mobile money": "hh_momo_account",
    "momo": "hh_momo_account", "gini": "gini", "inequality": "gini", "median consumption": "median_consumption_ae",
    "consumption": "median_consumption_ae", "households": "households_census", "household size": "household_size_census",
    "poverty": "poverty_rate",
}

DEPRIVATION_WORDS = ("deprivation", "deprivations", "censored headcount", "deprived")
LIST_WORDS = ("available", "which indicators", "list", "what indicators", "show the")
DEF_WORDS = ("what is", "what does", "define", "definition", "how is", "meaning", "explain")
HIGH_WORDS = ("highest", "most", "worst", "largest", "top", "biggest", "maximum")
LOW_WORDS = ("lowest", "least", "best", "smallest", "minimum", "bottom")
COMPARE_WORDS = ("compare", " vs ", "versus", "compared", "difference between", "gap between", "relative to")

EXAMPLES = [
    "How does rural MPI incidence compare with urban incidence?",
    "Which deprivation indicators have the highest reported censored headcounts?",
    "Show the available financial inclusion indicators.",
    "Which districts have the highest poverty rate?",
    "Compare poverty in Gasabo and Nyamagabe",
    "What is the MPI?",
    "Which districts have the lowest share of banked adults?",
    "Health insurance coverage in Northern Province",
]


def _norm(q: str) -> str:
    return " " + re.sub(r"[^a-z0-9%\- ]+", " ", q.lower()).strip() + " "


def _find_geos(store: DataStore, q: str) -> list[tuple[str, str]]:
    """Geographies mentioned in the question, in the order they appear."""
    hits: dict[tuple[str, str], int] = {}

    def hit(pattern: str, geo: tuple[str, str]):
        m = re.search(rf"\b{pattern}\b", q)
        if m and geo not in hits:
            hits[geo] = m.start()

    for d in store.districts():
        hit(d["name"].lower(), ("district", d["geo_id"]))
    for alias, pid in [("city of kigali", "kigali"), ("kigali", "kigali"), ("southern", "southern"), ("south", "southern"),
                       ("western", "western"), ("west", "western"), ("northern", "northern"),
                       ("north", "northern"), ("eastern", "eastern"), ("east", "eastern")]:
        hit(alias, ("province", pid))
    for a in ("urban", "rural"):
        hit(a, ("area", a))
    hit("(?:rwanda|national|nationally|country)", ("national", "rwanda"))
    return sorted(hits, key=hits.get)


def _find_indicator(q: str) -> str | None:
    for phrase in sorted(SYNONYMS, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", q):
            return SYNONYMS[phrase]
    return None


def _top_n(q: str, default: int = 5) -> int:
    m = re.search(r"\b(?:top|bottom)\s+(\d{1,2})\b", q) or re.search(r"\b(\d{1,2})\s+(?:districts|provinces)\b", q)
    return max(1, min(int(m.group(1)), 30)) if m else default


def _answer(kind, text, store, ind=None, rows=None, chart=None, caveats=None, sources=None):
    meta = store.indicator_index.get(ind) if ind else None
    srcs = sources or ([store.source_ref(meta["source_id"])] if meta else [])
    return {"kind": kind, "answer": text, "indicator": meta, "rows": rows or [], "chart": chart,
            "caveats": caveats or [], "sources": srcs, "examples": EXAMPLES if kind == "unmatched" else None}


def _fmt(v, unit="%", d=1):
    if v is None:
        return "not available"
    if unit and unit.startswith("index (0–1)"):
        return f"{v:.3f}"
    if unit in {"households", "RWF"}:
        return f"{v:,.0f}"
    return f"{v:.{d}f}{'%' if unit == '%' else ''}"


def ask(store: DataStore, question: str) -> dict:
    q = _norm(question)
    if len(q.strip()) < 3:
        return _answer("unmatched", "Please type a question about Rwanda's poverty or financial-inclusion statistics.", store)

    # 1. list available financial inclusion indicators
    if any(w in q for w in LIST_WORDS) and ("financial" in q or "inclusion" in q):
        fi = [i for i in store.indicators if i["theme"] == "financial_inclusion" and i["levels"]]
        rows = [{"indicator": i["name"], "levels": ", ".join(i["levels"]), "period": i["period"],
                 "status": i["status"], "source": store.source_ref(i["source_id"])["short"]} for i in fi]
        rows += [{"indicator": u["variable"], "levels": "—", "period": "—", "status": u["status"],
                  "source": u["where_collected"]} for u in store.unavailable_financial]
        return _answer("list", f"{len(fi)} financial-inclusion indicators have published data; "
                               f"{len(store.unavailable_financial)} further variables are collected but not published "
                               "(shown as unavailable, never estimated).", store, rows=rows,
                       sources=[store.source_ref(s) for s in ("finscope_2024", "eicv7_pp", "eicv7_vup")])

    # 2. deprivation ranking (MPI censored headcounts)
    if any(w in q for w in DEPRIVATION_WORDS):
        geos = [g for g in _find_geos(store, q) if g[0] in {"national", "area", "province"}] or [("national", "rwanda")]
        lvl, gid = geos[0]
        rows = []
        for i in store.mpi_framework["indicators"]:
            o = store.one(f"mpi_ch_{i['id']}", lvl, gid)
            if o and o["value"] is not None:
                rows.append({"label": i["label"], "dimension": i["dimension"], "value": o["value"], "weight": i["weight_label"]})
        rows.sort(key=lambda r: -r["value"])
        low = any(w in q for w in LOW_WORDS)
        if low:
            rows = rows[::-1]
        top = rows[:3]
        where = store.geo_name(lvl, gid)
        text = (f"In {where} (EICV7 2023/24), the {'lowest' if low else 'highest'} censored headcounts — people who are "
                f"multidimensionally poor and deprived in the indicator — are: "
                + "; ".join(f"{r['label']} {r['value']:.1f}%" for r in top) + ".")
        caveats = ["Censored headcounts count only people who are MPI-poor (k = 33.3%).",
                   "Province is the finest level at which NISR publishes MPI indicators."]
        if lvl == "national":
            caveats.append("Uncensored headcounts (all people, Table B.1) are higher, e.g. cooking fuel 78.1%.")
        return _answer("ranking", text, store, "mpi_ch_cooking_fuel", rows=rows,
                       chart={"type": "bar", "x": "label", "y": "value", "unit": "%"}, caveats=caveats)

    ind = _find_indicator(q)
    geos = _find_geos(store, q)

    # 3. definitions
    if any(w in q for w in DEF_WORDS) and ind and not geos:
        meta = store.indicator_index[ind]
        text = f"{meta['name']}: {meta['definition']}"
        if ind in {"mpi", "mpi_incidence", "mpi_intensity"}:
            fw = store.mpi_framework
            text += (f" Rwanda's national MPI uses {len(fw['indicators'])} indicators in 4 equally weighted dimensions "
                     f"(education, health, basic services, living standards); a person is MPI-poor if deprived in at least "
                     f"one third of weighted indicators.")
        nat = enrich(store, store.one(ind, "national", "rwanda"))
        if nat:
            text += f" National value: {_fmt(nat['value'], meta['unit'])} ({nat['period']})."
        return _answer("definition", text, store, ind, rows=[nat] if nat else [],
                       caveats=[meta["notes"]] if meta.get("notes") else [])

    if not ind:
        return _answer("unmatched", "I couldn't match that to a stored statistic. Imboni only answers from validated "
                                    "NISR-published figures — try one of the examples.", store)
    meta = store.indicator_index[ind]

    # 4. rankings across districts/provinces
    if any(w in q for w in HIGH_WORDS + LOW_WORDS) and not (len(geos) >= 2):
        level = "province" if "province" in q else "district"
        if level not in meta["levels"]:
            level = "province" if "province" in meta["levels"] else None
        if level is None:
            return _answer("unavailable", f"{meta['name']} is not published for districts or provinces "
                                          f"(available levels: {', '.join(meta['levels'])}).", store, ind)
        rows = [enrich(store, o) for o in store.query(ind, level) if not o.get("breakdown") and o["value"] is not None]
        high = any(w in q for w in HIGH_WORDS) and not any(w in q for w in LOW_WORDS)
        if any(w in q for w in ("worst",)) and meta["polarity"] == "higher_better":
            high = False
        rows.sort(key=lambda r: r["value"], reverse=high)
        n = _top_n(q)
        top = rows[:n]
        nat = store.value(ind, "national", "rwanda")
        text = (f"{'Highest' if high else 'Lowest'} {meta['short_name'].lower()} by {level} ({meta['period']}): "
                + "; ".join(f"{r['geo_name']} {_fmt(r['value'], meta['unit'])}" for r in top)
                + (f". National: {_fmt(nat, meta['unit'])}." if nat is not None else "."))
        caveats = []
        if any(r.get("se") for r in top):
            caveats.append("District estimates carry sampling error; overlapping 95% CIs mean ranks are uncertain "
                           "(see the Explorer's rank intervals).")
        if meta["status"] == "official_transcribed":
            caveats.append("Values transcribed from FinScope 2024 figure labels (rounded).")
        return _answer("ranking", text, store, ind, rows=top,
                       chart={"type": "bar", "x": "geo_name", "y": "value", "unit": meta["unit"]}, caveats=caveats)

    # 5. compare two or more geographies
    if len(geos) >= 2 or (any(w in q for w in COMPARE_WORDS) and geos):
        if len(geos) == 1:
            geos.append(("national", "rwanda"))
        rows = [enrich(store, store.one(ind, l, g)) for l, g in geos]
        rows = [r for r in rows if r]
        missing = [store.geo_name(l, g) for l, g in geos if not store.one(ind, l, g)]
        if len(rows) < 2:
            return _answer("unavailable", f"{meta['name']} is not available for "
                                          f"{', '.join(m for m in missing if m)} (published levels: {', '.join(meta['levels'])}).",
                           store, ind, rows=rows)
        a, b = rows[0], rows[1]
        diff = a["value"] - b["value"]
        text = (f"{meta['name']} ({meta['period']}): {a['geo_name']} {_fmt(a['value'], meta['unit'])} vs "
                f"{b['geo_name']} {_fmt(b['value'], meta['unit'])} — a difference of {abs(diff):.{3 if meta['unit'].startswith('index (0–1)') else 1}f}"
                f"{' percentage points' if meta['unit'] == '%' else ''}")
        if b["value"]:
            text += f" ({a['value'] / b['value']:.2f}× ratio)."
        caveats = []
        if a.get("se") and b.get("se"):
            from .analytics import compare_to_reference
            t = compare_to_reference(a, b)
            text += f" Using published standard errors, {a['geo_name']} is {t['label']} {b['geo_name']} (approx. z-test, p = {t['p_value']:.3f})."
        if ind == "mpi_incidence":
            caveats.append("MPI incidence is not the monetary poverty rate; the two measure different concepts.")
        if missing:
            caveats.append(f"Not published for: {', '.join(m for m in missing if m)}.")
        return _answer("comparison", text, store, ind, rows=rows,
                       chart={"type": "bar", "x": "geo_name", "y": "value", "unit": meta["unit"]}, caveats=caveats)

    # 6. single value
    lvl, gid = geos[0] if geos else ("national", "rwanda")
    o = enrich(store, store.one(ind, lvl, gid))
    if not o:
        return _answer("unavailable", f"{meta['name']} is not published for {store.geo_name(lvl, gid)} "
                                      f"(available levels: {', '.join(meta['levels'])}).", store, ind)
    text = f"{meta['name']} in {o['geo_name']}: {_fmt(o['value'], meta['unit'])} ({o['period']})."
    if o.get("ci_low") is not None:
        text += f" 95% CI {o['ci_low']:.1f}–{o['ci_high']:.1f}."
    if lvl != "national":
        nat = store.value(ind, "national", "rwanda")
        if nat is not None:
            text += f" National: {_fmt(nat, meta['unit'])}."
    return _answer("value", text, store, ind, rows=[o], caveats=[meta["notes"]] if meta.get("notes") else [])
