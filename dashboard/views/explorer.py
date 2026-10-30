from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from backend.app import nlq

from .. import charts, data
from ..logic import filter_observations
from ..theme import STATUS
from ..ui import badge, callout, chart, empty_state, guarded, hero, kpi_cards, section, sources_line

COLUMNS = ["indicator_id", "indicator_name", "level", "geo_name", "breakdown", "period", "value", "unit", "se",
           "ci_low", "ci_high", "cv", "status", "source_id", "table_ref", "flags", "note"]


def _observations_tab() -> None:
    df = data.observations_df()
    s = data.store()
    c1, c2, c3, c4 = st.columns([1.2, 1.6, 1.2, 1])
    themes = sorted(df["theme"].dropna().unique())
    with c1:
        th = st.multiselect("Theme", themes, format_func=lambda t: data.THEME_LABELS.get(t, t))
    pool = df if not th else df[df["theme"].isin(th)]
    with c2:
        inds = st.multiselect("Indicator", sorted(pool["indicator_id"].unique()),
                              format_func=lambda i: s.indicator_index.get(i, {}).get("name", i))
    with c3:
        lv = st.multiselect("Level", sorted(df["level"].unique()), format_func=lambda l: data.LEVEL_LABELS.get(l, l))
    with c4:
        stt = st.multiselect("Status", sorted(df["status"].unique()))
    c5, c6 = st.columns([2, 1])
    with c5:
        geo = st.text_input("Geography contains", placeholder="e.g. Nyamagabe, Rural, Q1")
    with c6:
        only = st.toggle("Only rows with a value", value=False)
    out = filter_observations(df, th, inds, lv, stt, geo, only)
    st.caption(f"{len(out):,} of {len(df):,} observations · aggregate published statistics only (no microdata).")
    if out.empty:
        empty_state("No rows match", "Relax a filter to see observations.")
        return
    st.dataframe(out[COLUMNS], hide_index=True, width="stretch", height=460,
                 column_config={"value": st.column_config.NumberColumn(format="%.3f"),
                                "se": st.column_config.NumberColumn(format="%.3f"),
                                "ci_low": st.column_config.NumberColumn(format="%.2f"),
                                "ci_high": st.column_config.NumberColumn(format="%.2f"),
                                "cv": st.column_config.NumberColumn(format="%.1f")})
    st.download_button("Download filtered rows (CSV)", out[COLUMNS].to_csv(index=False).encode("utf-8"),
                       "imboni_observations_filtered.csv", "text/csv")


def _variables_tab() -> None:
    s = data.store()
    idf = data.indicators_df()
    q = st.text_input("Search variables", placeholder="name, definition or id")
    view = idf
    if q:
        mask = idf[["id", "name", "definition"]].apply(lambda c: c.str.contains(q, case=False, na=False, regex=False)).any(axis=1)
        view = idf[mask]
    st.dataframe(view[["id", "name", "theme", "unit", "universe", "levels", "period", "status", "source_id", "table_ref"]],
                 hide_index=True, width="stretch", height=320)
    if view.empty:
        return
    ind = st.selectbox("Inspect a variable", view["id"].tolist(), format_func=lambda i: s.indicator_index[i]["name"])
    m = s.indicator_index[ind]
    obs = [o for o in s.observations if o["indicator_id"] == ind]
    n_val = sum(o["value"] is not None for o in obs)
    n_se = sum(o["se"] is not None for o in obs)
    src = s.source_ref(m["source_id"])
    notes = f'<div class="k">Notes</div><div class="v">{escape(m["notes"])}</div>' if m.get("notes") else ""
    st.markdown(f"""
<div class="im-card"><div class="theme">{escape(data.THEME_LABELS.get(m['theme'], m['theme']))}</div>
<h4>{escape(m['name'])} {badge(m['status'])}</h4>
<div class="finding">{escape(m['definition'])}</div>
<div class="im-kv">
<div class="k">Identifier</div><div class="v"><code>{escape(m['id'])}</code></div>
<div class="k">Unit · universe</div><div class="v">{escape(m['unit'])} · {escape(m['universe'])}</div>
<div class="k">Reference period</div><div class="v">{escape(str(m['period']))}</div>
<div class="k">Published levels</div><div class="v">{escape(', '.join(data.LEVEL_LABELS.get(l, l) for l in m['levels']))}</div>
<div class="k">Observations</div><div class="v">{len(obs)} ({n_val} with a value, {n_se} with a standard error)</div>
<div class="k">Polarity</div><div class="v">{escape(m['polarity'].replace('_', ' '))}</div>
<div class="k">Source</div><div class="v"><a href="{escape(src.get('landing_page') or src.get('url') or '')}" target="_blank">{escape(src.get('title') or '')}</a> — {escape(m['table_ref'])}</div>
{notes}
</div></div>""", unsafe_allow_html=True)


def _quality_tab() -> None:
    q = data.quality()
    v = q["validation"]["summary"]
    miss = data.missingness_df()
    n_missing = int(miss["n_missing"].sum())
    kpi_cards([
        {"label": "Observations", "value": f"{q['n_observations']:,}", "sub": ", ".join(f"{k}: {n}" for k, n in q["status_counts"].items()),
         "status": "calculated"},
        {"label": "Validation checks passed", "value": f"{v['passed']}/{v['total']}",
         "sub": f"{v['errors']} pipeline errors · {v['warnings']} source warnings", "status": "calculated",
         "accent": STATUS["good"] if v["errors"] == 0 else STATUS["critical"]},
        {"label": "Missing values", "value": f"{n_missing:,}", "sub": "Each carries an explicit reason flag; never zero-filled",
         "status": "calculated"},
        {"label": "Imprecise estimates", "value": f"{sum(q['precision_flags'].values())}",
         "sub": f"CV > 15%: {q['precision_flags']['cv_gt_15_use_with_caution']} · CV > 30%: {q['precision_flags']['cv_gt_30_unreliable']}",
         "status": "calculated", "help": q["cv_rule"]},
    ])
    section("Missing-value assessment", "Per indicator and level, as produced by the pipeline (data_quality_summary.csv).")
    show = miss[miss["n_missing"] > 0] if st.toggle("Only indicators with missing values", value=True) else miss
    st.dataframe(show, hide_index=True, width="stretch", height=300)
    se = miss.groupby("level")[["n_observations", "n_with_se"]].sum().reset_index()
    se["share_with_se"] = (se["n_with_se"] / se["n_observations"] * 100).round(1)
    chart(charts.ranked_bars([{"geo_id": r.level, "geo_name": data.LEVEL_LABELS.get(r.level, r.level), "value": r.share_with_se}
                              for r in se.itertuples()], title="Share of observations with a published standard error, by level",
                             worse_high=False), key="dq_se")
    section("Validation checks", "Errors fail the build; warnings document inconsistencies in the source publications.")
    checks = pd.DataFrame(q["validation"]["checks"])
    sev = st.radio("Show", ["warning", "error", "info", "all"], horizontal=True,
                   format_func=lambda x: {"warning": "Source warnings", "error": "Errors", "info": "Passed", "all": "All"}[x])
    view = checks if sev == "all" else checks[checks["severity"] == sev]
    st.dataframe(view[["check", "severity", "passed", "detail"]], hide_index=True, width="stretch", height=300)
    if q["flagged_observations"]:
        section("Estimates flagged for precision")
        st.dataframe(pd.DataFrame([{"Indicator": o["name"], "Area": o["geo_name"], "Value": o["value"], "CV %": o["cv"],
                                    "Flags": ", ".join(o["flags"])} for o in q["flagged_observations"]]),
                     hide_index=True, width="stretch")


def _ask_tab() -> None:
    st.caption("Deterministic question answering over the validated tables — keyword rules, no language model, "
               "no external service. Unmatched questions get suggestions instead of a guess.")
    ex = st.selectbox("Example questions", [""] + nlq.EXAMPLES, format_func=lambda x: x or "Choose an example…")
    q = st.text_input("Your question", value=ex, max_chars=300, placeholder="e.g. Which districts have the highest poverty rate?")
    if not q.strip():
        return
    ans = data.ask(q)
    callout("insight" if ans["kind"] != "unmatched" else "gap", "Answer", ans["answer"])
    if ans["rows"]:
        rows = pd.DataFrame([{"Area": r["geo_name"], "Level": r["level"], "Value": r["value"], "95% CI low": r.get("ci_low"),
                              "95% CI high": r.get("ci_high"), "Period": r["period"], "Status": r["status"],
                              "Table": r["table_ref"]} for r in ans["rows"]])
        st.dataframe(rows, hide_index=True, width="stretch")
        if ans.get("chart") and len(ans["rows"]) > 1:
            unit = (ans.get("indicator") or {}).get("unit", "%")
            chart(charts.ranked_bars(ans["rows"], unit="%" if unit.startswith("%") else unit, worse_high=True), key="ask_chart")
    for c in ans.get("caveats") or []:
        st.caption(f"⚠ {c}")
    sources_line(ans.get("sources") or [])
    if ans.get("examples"):
        st.markdown("**Try:** " + " · ".join(f"*{escape(e)}*" for e in ans["examples"][:5]))


def _restricted_tab() -> None:
    callout("gap", "Restricted microdata are not part of this platform",
            "EICV7 household and individual records (NISR Microdata Portal catalogs 119 and 121) require registration and "
            "acceptance of NISR's terms. Imboni never downloads, stores, deploys or displays them. Everything in the "
            "explorer is a published aggregate statistic.")
    inv = [r for r in data.inventory() if r["role"] == "restricted"]
    if inv:
        st.dataframe(pd.DataFrame([{"Source": r["short"], "Access": r["access"], "Where": r["landing_page"]} for r in inv]),
                     hide_index=True, width="stretch")
    st.markdown("""
**If your team obtains authorised access**, follow `docs/MICRODATA_IMPORT.md`: keep files in `data/restricted/`
(git-ignored), estimate with the survey design (weights, strata, PSUs), and export **aggregates only** — with design-based
standard errors and suppression of cells with too few observations — into the observation schema.
""")


@guarded
def render() -> None:
    hero("Data Explorer", "Every number, with its source",
         "Browse the tidy observation table behind the dashboard, inspect variable definitions, review data quality "
         "and validation, ask questions in plain language, and download authorised aggregate data.",
         [f"{len(data.store().observations):,} observations", f"{len(data.store().indicators)} indicators",
          "Aggregates only"])
    tabs = st.tabs(["Observations", "Variables", "Data quality", "Ask a question", "Restricted data"])
    with tabs[0]:
        _observations_tab()
    with tabs[1]:
        _variables_tab()
    with tabs[2]:
        _quality_tab()
    with tabs[3]:
        _ask_tab()
    with tabs[4]:
        _restricted_tab()
