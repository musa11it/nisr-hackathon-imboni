from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .. import charts, data
from ..theme import BRAND_500, S1, S2, S3, SERIES
from ..ui import callout, chart, guarded, hero, kpi_cards, metric_card, section, sources_line

DIM_COLORS = {"Education": S1, "Health": S2, "Living standards": S3}


@guarded
def render() -> None:
    s = data.store()
    m = data.mpi()
    d = data.dashboard()
    fw = m["framework"]
    k_pct = fw["poverty_cutoff_k"] * 100  # stored as a fraction (1/3); the k-curve is in percent
    hero("Multidimensional Poverty", "Which deprivations drive the MPI",
         "Rwanda's national MPI (EICV7) uses 13 indicators in 3 dimensions. A person is MPI-poor when their household's "
         "weighted deprivation score is at least one-third. Censored headcounts count people who are both MPI-poor "
         "and deprived in an indicator.",
         [fw["method"], f"k = {k_pct:.1f}%", "Published to province & quintile level"])
    k = d["kpis"]
    kpi_cards([metric_card(k["mpi_incidence"], "Incidence (H)", accent=S3),
               metric_card(k["mpi_intensity"], "Intensity (A)", accent=S3),
               metric_card(k["mpi"], "MPI (M0 = H × A)", accent=S3),
               {"label": "Indicators", "value": str(len(fw["indicators"])), "sub": "3 dimensions, nested weights",
                "status": "official", "help": fw["source"]}])

    section("Deprivation headcounts", "Uncensored: everyone deprived in the indicator. Censored: deprived AND MPI-poor. "
                                      "National, 2023/24.")
    dep = d["deprivations"]
    chart(charts.grouped_bars([r["label"] for r in dep],
                              [("Censored (MPI-poor & deprived)", [r["censored"] for r in dep], BRAND_500),
                               ("Uncensored (all deprived)", [r["uncensored"] for r in dep], S1)],
                              horizontal=True), key="mpi_heads")

    section("Compare groups", "Censored headcounts by area, province or consumption quintile.")
    table = m["table"]
    labels = {f"{r['level']}:{r['geo_id']}": r["name"] for r in table}
    pick = st.multiselect("Groups", list(labels), default=["national:rwanda", "area:urban", "area:rural"],
                          format_func=lambda k_: labels[k_], max_selections=4,
                          help="Up to four groups so each keeps a fixed, distinguishable colour.")
    rows = {f"{r['level']}:{r['geo_id']}": r for r in table}
    inds = fw["indicators"]
    if pick:
        series = [(labels[g], [rows[g]["censored"].get(i["id"]) for i in inds], SERIES[n]) for n, g in enumerate(pick)]
        chart(charts.grouped_bars([i["label"] for i in inds], series, horizontal=True), key="mpi_groups")

    section("Contribution of each indicator to the MPI",
            "Share of M0 attributable to each indicator: w·CH / Σ w·CH (Alkire–Foster decomposition).")
    callout("caution", "Published contributions are not reproducible", m["contribution_note"])
    which = st.radio("Contribution values", ["Recomputed (calculated)", "Published by NISR (Tables B.7–B.9)"],
                     horizontal=True)
    key = "contrib_calc" if which.startswith("Recomputed") else "contrib_published"
    grp = [r for r in table if r["level"] in ("national", "area", "province")]
    palette = {i["id"]: DIM_COLORS.get(i["dimension"], BRAND_500) for i in inds}
    fig = charts.stacked_share([r["name"] for r in grp], [])
    shades = {}
    for i in inds:
        n = sum(1 for j in inds[:inds.index(i)] if j["dimension"] == i["dimension"])
        shades[i["id"]] = 1 - 0.13 * n
    for i in inds:
        fig.add_trace(go.Bar(y=[r["name"] for r in grp], x=[r[key].get(i["id"]) for r in grp], orientation="h",
                             name=f"{i['label']} ({i['dimension']})",
                             marker=dict(color=palette[i["id"]], opacity=shades[i["id"]], line=dict(color="white", width=2)),
                             hovertemplate=f"<b>%{{y}}</b><br>{escape(i['label'])}: %{{x:.1f}}%<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.12, yanchor="top"), height=520, xaxis=dict(range=[0, 101]))
    chart(fig, key=f"mpi_contrib_{key}")
    st.caption("Colour = dimension (Education / Health / Living standards); shades separate indicators within a "
               "dimension — hover or use the table for exact values.")

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        section("Sensitivity to the poverty cut-off k")
        kc = m["k_curve"]
        chart(charts.line_chart([r["k"] for r in kc], [("Incidence (H)", [r["incidence"] for r in kc], S3),
                                                         ("Intensity (A)", [r["intensity"] for r in kc], S1)],
                                "k (% weighted deprivations)", vline=k_pct, vline_label="official k"),
              key="mpi_k")
    with c2:
        section("H, A and M0 by group")
        df = pd.DataFrame([{"Group": r["name"], "Population share %": r["population_share"], "H %": r["mpi_incidence"],
                            "A %": r["mpi_intensity"], "M0": r["mpi"], "H×A check": round(r["mpi_check_HxA"], 3)}
                           for r in table])
        st.dataframe(df, hide_index=True, width="stretch", height=420)

    section("The official framework")
    fdf = pd.DataFrame([{"Dimension": i["dimension"], "Indicator": i["label"], "Weight": i["weight_label"],
                         "Deprived if": i["deprived_if"]} for i in inds])
    st.dataframe(fdf, hide_index=True, width="stretch")
    with st.expander("Methodology and changes vs EICV5"):
        st.markdown(f"""
* **Identification:** {escape(fw['unit_of_identification'])}; **analysis:** {escape(fw['unit_of_analysis'])}.
* **Dual cut-off:** each indicator has a deprivation cut-off; a person is poor if the weighted sum ≥ k = {k_pct:.1f}%.
* **H** = share of people who are poor; **A** = average weighted deprivation share among the poor; **M0 = H × A**.
* **Censored headcount (CH):** share of the population that is poor and deprived in the indicator, so Σ wⱼ·CHⱼ = M0.
* **Limitations:** no standard errors are published for the MPI tables; the MPI is not published by district.
""")
        st.markdown("**Changes vs EICV5:**\n" + "\n".join(f"- {escape(c)}" for c in fw["changes_vs_eicv5"]))
    sources_line([{**s.source_ref("eicv7_mpi"), "table": "Tables B.3–B.9, 3.1, k-sensitivity"},
                  {**s.source_ref("eicv7_mpi_pdf"), "table": "framework pp. 22–23"}])
