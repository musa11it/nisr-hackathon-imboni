from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from backend.app.analytics import DISTRICT_INDICATORS

from .. import charts, data
from ..logic import correlation_matrix
from ..theme import S1, S2, S3
from ..ui import badge, callout, chart, empty_state, fmt, guarded, hero, kpi_cards, note, section, sources_line

MAP_EXCLUDE = {"households_census", "household_size_census"}


def _map_indicators() -> list[str]:
    s = data.store()
    out = []
    for i in s.indicators:
        if i["id"] in MAP_EXCLUDE or (i["theme"] == "mpi_indicator" and not i["id"].startswith("mpi_ch_")):
            continue
        if ("district" in i["levels"] or "province" in i["levels"]) and i["unit"].startswith("%") \
                and not i["id"].startswith(("mpi_k_", "mpi_monetary", "population_share", "vup_")):
            out.append(i["id"])
    return out


def _map_tab() -> None:
    s = data.store()
    inds = _map_indicators()
    c1, c2, c3 = st.columns([2.2, 1, 1.2])
    with c1:
        ind = st.selectbox("Indicator", inds, index=inds.index("poverty_rate"),
                           format_func=lambda i: f"{s.indicator_index[i]['name']}",
                           help="Only indicators NISR/FinScope publish at sub-national level are listed.")
    meta = s.indicator_index[ind]
    levels = [lv for lv in ("district", "province") if lv in meta["levels"]]
    with c2:
        level = st.radio("Geographic level", levels, horizontal=True, format_func=str.title,
                         help="District is offered only when the source publishes district estimates.")
    with c3:
        highlight = st.selectbox("Highlight area", [None] + [g for g, _ in (data.district_options() if level == "district"
                                                                             else data.province_options())],
                                 format_func=lambda g: "None" if g is None else data.name_of(level, g))
    if "district" not in meta["levels"]:
        st.caption(f"{meta['short_name']} is published down to province level only — no district values are shown or "
                   "estimated.")
    layer = data.map_layer(ind, level)
    rows = layer["rows"]
    if not rows:
        empty_state("No data", "This indicator has no published values at this level.")
        return
    worse_high = meta["polarity"] != "higher_better"
    nat = layer["national"]
    summ = layer["summary"]
    above = sum(1 for r in rows if (r.get("vs_national") or {}).get("label") == "higher than")
    below = sum(1 for r in rows if (r.get("vs_national") or {}).get("label") == "lower than")
    has_tests = any((r.get("vs_national") or {}).get("available") for r in rows)
    unit = meta["unit"]
    kpi_cards([
        {"label": "National", "value": fmt(nat and nat["value"], unit), "unit": "%" if unit.startswith("%") else "",
         "status": nat and nat["status"], "period": meta["period"], "table": meta["table_ref"], "help": meta["definition"]},
        {"label": f"Range across {summ['n']} {level}s", "value": f"{fmt(summ['min'], unit)}–{fmt(summ['max'], unit)}",
         "unit": "%" if unit.startswith("%") else "",
         "sub": f"max ÷ min = {summ['range_ratio']:.1f}×" if summ.get("range_ratio") else None, "status": "calculated"},
        {"label": "Significantly above national", "value": str(above) if has_tests else "—",
         "sub": f"{below} significantly below" if has_tests else "No standard errors published",
         "status": "calculated" if has_tests else "unavailable",
         "help": "Approximate two-sample z-test at the 95% level using NISR standard errors."},
    ])
    m1, m2 = st.columns([1.2, 1], gap="large")
    with m1:
        chart(charts.choropleth(s.geo[level], rows, meta["short_name"], unit, worse_high, meta.get("decimals", 1),
                                height=600), key=f"map_{ind}_{level}")
        st.caption("Boundaries: geoBoundaries (CC BY 4.0). Colour classes are continuous; hover for value, CI, "
                   "rank interval and test vs national. Grey = not published.")
    with m2:
        chart(charts.ranked_bars(rows, unit="%" if unit.startswith("%") else unit, ref=nat and nat["value"],
                                 highlight=highlight, worse_high=worse_high, decimals=meta.get("decimals", 1),
                                 title=f"{meta['short_name']} by {level} (most deprived first)"),
              key=f"bars_{ind}_{level}")
    note("Reading ranks honestly", layer["rank_note"] + " Overlapping intervals mean two areas cannot be "
         "reliably ordered.")
    df = pd.DataFrame([{
        "Area": r["geo_name"], "Value": r["value"], "95% CI low": r["ci_low"], "95% CI high": r["ci_high"],
        "CV %": r["cv"], "Rank": r.get("rank"), "Rank 90% low": r.get("rank_low"), "Rank 90% high": r.get("rank_high"),
        "vs national": (r.get("vs_national") or {}).get("label"), "p-value": (r.get("vs_national") or {}).get("p_value"),
        "Status": r["status"], "Flags": ", ".join(r["flags"]), "Table": r["table_ref"]} for r in rows]).sort_values("Rank")
    with st.expander(f"Table — {len(df)} {level}s", expanded=False):
        st.dataframe(df, hide_index=True, width="stretch",
                     column_config={"Value": st.column_config.NumberColumn(format="%.1f"),
                                    "95% CI low": st.column_config.NumberColumn(format="%.1f"),
                                    "95% CI high": st.column_config.NumberColumn(format="%.1f"),
                                    "CV %": st.column_config.NumberColumn(format="%.1f"),
                                    "p-value": st.column_config.NumberColumn(format="%.4f")})
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), f"imboni_{ind}_{level}.csv",
                           "text/csv", key=f"dl_{ind}_{level}")
    sources_line([{**s.source_ref(meta["source_id"]), "table": meta["table_ref"]}])


def _profile_tab() -> None:
    s = data.store()
    c1, c2 = st.columns([1, 2])
    with c1:
        level = st.radio("Level", ["district", "province"], horizontal=True, format_func=str.title, key="prof_level")
    opts = data.district_options() if level == "district" else data.province_options()
    with c2:
        gid = st.selectbox("Area", [g for g, _ in opts], format_func=lambda g: data.name_of(level, g), key="prof_geo")
    p = data.profile(level, gid)
    st.markdown(f"#### {escape(p['name'])}" + (f" · {escape(p['province_name'])}" if p.get("province_name") else ""))
    fp = p["fingerprint"]
    if fp:
        labels = [f["label"] for f in fp]
        series = [(p["name"], [f["value"] for f in fp], S1)]
        if level == "district":
            series.append((p.get("province_name") or "Province", [f["province"] for f in fp], S2))
        series.append(("Rwanda", [f["national"] for f in fp], S3))
        chart(charts.grouped_bars(labels, series, horizontal=True, title="Deprivation fingerprint (% lacking each service)"),
              key=f"fp_{level}_{gid}")
        st.caption("All bars are deprivations (higher = worse): service-coverage indicators are shown as 100 − coverage.")
    if p["findings"]:
        section("Statistically distinguishable from national", "Approximate z-tests using NISR standard errors (95% level).")
        for f in p["findings"]:
            icon = "▲" if f["kind"] == "concern" else "▼"
            st.markdown(f"- {icon} **{'Concern' if f['kind'] == 'concern' else 'Strength'}** — {escape(f['text'])}")
    else:
        st.caption("No indicator differs significantly from the national estimate at the 95% level.")
    mpi = p.get("mpi")
    if mpi and mpi.get("incidence"):
        section(f"MPI context — {mpi['geo_name']}")
        if mpi.get("note"):
            callout("caution", "Province-level MPI", mpi["note"])
        st.markdown(f"MPI incidence **{mpi['incidence']['value']:.1f}%**, intensity **{mpi['intensity']['value']:.1f}%**, "
                    f"M0 **{mpi['mpi']['value']:.3f}** {badge('official')}", unsafe_allow_html=True)
    rows = [{"Indicator": e["name"], "Value": e["value"], "95% CI": (f"{e['ci_low']:.1f}–{e['ci_high']:.1f}"
                                                                   if e.get("ci_low") is not None else ""),
             "National": e.get("national"), "Rank": (f"{e['rank']} of {e['n_peers']}" if e.get("rank") else ""),
             "vs national": (e.get("vs_national") or {}).get("label", ""), "Status": e["status"],
             "Table": e["table_ref"]} for e in p["indicators"]]
    st.dataframe(rows, hide_index=True, width="stretch",
                 column_config={"Value": st.column_config.NumberColumn(format="%.1f"),
                                "National": st.column_config.NumberColumn(format="%.1f")})
    sources_line([s.source_ref(x) for x in ("eicv7_mi", "eicv7_mpi", "finscope_2024", "rphc5_main")])


def _associations_tab() -> None:
    s = data.store()
    note("Ecological associations — not causal effects",
            "Correlations between district averages describe districts, not households, and cannot show cause and "
            "effect. With n ≤ 30 the intervals are wide, and many indicators share common drivers (urbanisation, Kigali).",
         kind="caution")
    choices = [i for i in DISTRICT_INDICATORS]
    sel = st.multiselect("Indicators (district level)", choices,
                         default=["poverty_rate", "electricity_lighting", "improved_sanitation", "health_insurance_cov",
                                  "smartphone", "fs_banked", "fs_excluded"],
                         format_func=lambda i: s.indicator_index[i]["short_name"])
    if len(sel) < 2:
        empty_state("Choose at least two indicators", "Correlations need a pair of indicators.")
        return
    res = data.correlations(tuple(sel))
    keys = [i["id"] for i in res["indicators"]]
    mat, info = correlation_matrix(res["pairs"], keys)
    names = [s.indicator_index[k]["short_name"] for k in keys]
    text = [[("" if info[i][j] is None else
              f"{names[i]} × {names[j]}<br>ρ = {info[i][j]['rho']:.2f} (95% CI {info[i][j]['ci_low']:.2f} to "
              f"{info[i][j]['ci_high']:.2f})<br>n = {info[i][j]['n']} · BH q = {info[i][j]['q_value']:.3f}")
             for j in range(len(keys))] for i in range(len(keys))]
    a, b = st.columns([1.2, 1], gap="large")
    with a:
        chart(charts.heatmap(names, mat, text, title="Spearman rank correlation across districts"), key="corr_heat")
    with b:
        x = st.selectbox("x", keys, index=0, format_func=lambda i: s.indicator_index[i]["short_name"])
        y = st.selectbox("y", keys, index=min(1, len(keys) - 1), format_func=lambda i: s.indicator_index[i]["short_name"])
        dx, dy = res["data"][x], res["data"][y]
        common = [g for g in dx if g in dy and dx[g] is not None and dy[g] is not None]
        chart(charts.scatter([dx[g] for g in common], [dy[g] for g in common], [data.name_of("district", g) for g in common],
                             s.indicator_index[x]["short_name"], s.indicator_index[y]["short_name"]), key="corr_scatter")
    st.caption(res["method"])
    pairs = pd.DataFrame(res["pairs"]).sort_values("p_value")
    if not pairs.empty:
        pairs["a"] = pairs["a"].map(lambda i: s.indicator_index[i]["short_name"])
        pairs["b"] = pairs["b"].map(lambda i: s.indicator_index[i]["short_name"])
        st.dataframe(pairs[["a", "b", "n", "rho", "ci_low", "ci_high", "p_value", "q_value"]], hide_index=True,
                     width="stretch", column_config={c: st.column_config.NumberColumn(format="%.3f")
                                                    for c in ("rho", "ci_low", "ci_high", "p_value", "q_value")})
    with st.expander("All caveats"):
        for c in res["caveats"]:
            st.markdown(f"- {escape(c)}")


def _index_tab() -> None:
    s = data.store()
    ci = data.composite()
    note(f"{ci['name']} — experimental, read before using", " ".join(ci["warnings"]), kind="caution")
    rows = ci["rows"]
    chart(charts.ranked_bars([{"geo_id": r["geo_id"], "geo_name": r["name"], "value": r["score"], "rank": r["rank"]}
                              for r in rows], unit="", title="Service-gap score (0 = smallest gaps, 100 = largest)",
                             worse_high=True), key="sgi")
    v = ci["validation"]
    st.markdown(f"**External check:** Spearman ρ with district monetary poverty (not an input) = **{v['spearman_rho']:.2f}** "
                f"(95% CI {v['ci_low']:.2f} to {v['ci_high']:.2f}, n = {v['n']}).")
    st.caption("Formula: " + ci["formula"])
    loo = pd.DataFrame(ci["sensitivity_leave_one_out"])
    loo["dropped"] = loo["dropped"].map(lambda i: s.indicator_index[i]["short_name"])
    st.dataframe(loo.rename(columns={"dropped": "Component dropped", "rank_correlation_with_full": "ρ with full index"}),
                 hide_index=True, width="stretch")


@guarded
def render() -> None:
    pov = sorted([r for r in data.map_layer("poverty_rate", "district")["rows"] if r["value"] is not None],
                 key=lambda r: -r["value"])
    hero("Rwanda · Geographic Intelligence", "Where deprivation is concentrated",
         "District poverty rates with NISR's standard errors and honest rank intervals.",
         ["Maps: geoBoundaries ADM1/ADM2 (CC BY 4.0)", "Only published levels are mapped"],
         stats=[(f"{pov[0]['value']:.1f}", "%", f"{pov[0]['geo_name']} · highest"),
                (f"{pov[-1]['value']:.1f}", "%", f"{pov[-1]['geo_name']} · lowest"),
                (f"{pov[0]['value'] / pov[-1]['value']:.1f}", "×", "highest ÷ lowest")],
         accent="concentrated")
    t1, t2, t3, t4 = st.tabs(["Map & rankings", "Area profile", "Associations", "Service-gap index (experimental)"])
    with t1:
        _map_tab()
    with t2:
        _profile_tab()
    with t3:
        _associations_tab()
    with t4:
        _index_tab()
