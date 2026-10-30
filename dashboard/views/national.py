from __future__ import annotations

from html import escape

import streamlit as st

from .. import charts, data
from ..theme import S1, S2, S3
from ..ui import chart, findings, guarded, hero, kpi_cards, metric_card, note, section, sources_line


@guarded
def render() -> None:
    s = data.store()
    d = data.dashboard()
    k = d["kpis"]
    man = s.manifest
    pc = k["poverty_change"]
    hero("Rwanda · National Intelligence",
         "Rwanda's poverty, seen through two lenses",
         "Monetary and multidimensional poverty from NISR's EICV7 2023/24 — side by side, never merged.",
         [f"{man.get('observations', len(s.observations)):,} values", f"{man.get('indicators_with_data', '')} indicators",
          f"{d['validation']['passed']}/{d['validation']['total']} validation checks passed", "Source: NISR EICV7",
          "Not an official NISR product"],
         stats=[(f"{k['poverty_rate']['value']:.1f}", "%", "monetary poor"),
                (f"{k['mpi_incidence']['value']:.1f}", "%", "MPI-poor"),
                (f"{d['overlap']['cells']['mpi_poor__monetary_poor']:.1f}", "%", "poor on both"),
                (f"{pc['value']:+.1f}", "pp", "since 2016/17")],
         accent="two lenses")

    section("Monetary poverty", "Consumption per adult equivalent below the national poverty line (Jan 2024 prices).",
            eyebrow="Lens 1 · Consumption")
    kpi_cards([
        metric_card(k["poverty_rate"], "Monetary poverty rate", accent=S1),
        metric_card(k["extreme_poverty_rate"], "Extreme poverty rate", accent=S1),
        {"label": "Change since 2016/17", "value": f"{pc['value']:+.1f}", "unit": " pp",
         "delta": f"{'▼' if pc['value'] < 0 else '▲'} {pc['from']:.1f}% → {pc['to']:.1f}%",
         "delta_kind": "good" if pc["value"] < 0 else "bad",
         "sub": "2016/17 modelled on EICV7 methodology", "status": "calculated",
         "period": pc["period"], "help": pc["formula"], "accent": S1},
        metric_card(k["gini"], "Gini coefficient", show_ci=True, accent=S1, meter=False),
    ])
    section("Multidimensional poverty (MPI)", "MPI-poor = household deprived in ≥ 33.3% of 13 weighted indicators.",
            eyebrow="Lens 2 · Deprivations")
    ov = d["overlap"]
    kpi_cards([
        metric_card(k["mpi_incidence"], "MPI incidence (H)", accent=S3),
        metric_card(k["mpi_intensity"], "Intensity among the poor (A)", accent=S3),
        metric_card(k["mpi"], "MPI (M0 = H × A)", accent=S3),
        {"label": "Poor on both measures", "value": f"{ov['cells']['mpi_poor__monetary_poor']:.1f}", "unit": "%",
         "meter": ov["cells"]["mpi_poor__monetary_poor"],
         "sub": f"{ov['either']:.1f}% poor on at least one", "status": "official", "period": "2023/24",
         "table": ov["table"], "help": "Share of the population that is both monetary-poor and MPI-poor.", "accent": S3},
    ])
    note("Two measures, two concepts — how to read these cards",
         "Monetary poverty has published standard errors (95% confidence intervals shown). The MPI tables publish "
         "point estimates only, so no interval is shown for them. Do not subtract one from the other: a household "
         "can be consumption-poor without being multidimensionally deprived, and vice-versa.")

    layer = data.map_layer("poverty_rate", "district")
    ranked = sorted([r for r in layer["rows"] if r["value"] is not None], key=lambda r: -r["value"])
    gap = k["rural_urban_gap"]
    section("What stands out", eyebrow="Key findings")
    findings([
        (f"{ov['share_of_monetary_poor_also_mpi_poor']:.0f}%",
         "of the monetary poor are also MPI-poor — targeting on one measure misses the other group.",
         "Calculated · EICV7 MPI Table 3.1"),
        (f"{gap['ratio']:.1f}×", f"rural MPI incidence vs urban ({gap['rural']:.1f}% vs {gap['urban']:.1f}%).",
         "Calculated · EICV7 MPI Table B.5"),
        (f"{ranked[0]['value']:.1f}%", f"poverty in {ranked[0]['geo_name']}, the highest of 30 districts — "
                                       f"{ranked[-1]['geo_name']} is lowest at {ranked[-1]['value']:.1f}%.",
         "Official · EICV7 Table A9.23 · see rank intervals"),
    ])

    section("Poverty across Rwanda", "Monetary poverty by district (map) and both measures by province.",
            eyebrow="Geography")
    meta = s.indicator_index["poverty_rate"]
    g1, g2 = st.columns([1.05, 1], gap="large")
    with g1:
        chart(charts.choropleth(s.geo["district"], layer["rows"], meta["short_name"], "%", True, 1, height=440),
              key="nat_map")
        st.caption("Darker = higher poverty. Hover a district for its 95% CI and rank interval; full rankings on "
                   "Geographic Intelligence.")
    provs = sorted(d["provinces"], key=lambda p: -(p["poverty_rate"] or 0))
    with g2:
        fig = charts.grouped_bars([p["name"] for p in provs],
                                  [("Monetary poverty", [p["poverty_rate"] for p in provs], S1),
                                   ("MPI incidence (H)", [p["mpi_incidence"] for p in provs], S3)],
                                  horizontal=True, height=440)
        chart(fig, key="nat_prov")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        section("Rural and urban", eyebrow="Gaps")
        areas = ["Urban", "Rural"]
        pov = [data.store().one("poverty_rate", "area", a.lower()) for a in areas]
        ext = [s.value("extreme_poverty_rate", "area", a.lower()) for a in areas]
        mpi_h = [s.value("mpi_incidence", "area", a.lower()) for a in areas]
        fig = charts.grouped_bars(
            areas, [("Monetary poverty", [p and p["value"] for p in pov], S1),
                    ("Extreme poverty", ext, S2), ("MPI incidence (H)", mpi_h, S3)],
            errors={"Monetary poverty": [(p and p["ci_low"], p and p["ci_high"]) for p in pov]}, height=380)
        chart(fig, key="nat_area")
        gap = k["rural_urban_gap"]
        st.caption("Whiskers: 95% CI for monetary poverty (EICV7 Table A9.23).")
    with right:
        section("Who is poor on which measure", "% of the national population (EICV7 MPI Table 3.1)",
                eyebrow="Overlap")
        c = ov["cells"]
        st.markdown(f"""
<div class="im-matrix">
  <div class="h"></div><div class="h">Monetary poor</div><div class="h">Not monetary poor</div>
  <div class="h">MPI poor</div>
  <div class="c both"><div class="n">{c['mpi_poor__monetary_poor']:.1f}%</div>Poor on both</div>
  <div class="c one"><div class="n">{c['mpi_poor__monetary_nonpoor']:.1f}%</div>MPI-poor only</div>
  <div class="h">Not MPI poor</div>
  <div class="c one"><div class="n">{c['mpi_nonpoor__monetary_poor']:.1f}%</div>Monetary-poor only</div>
  <div class="c"><div class="n">{c['mpi_nonpoor__monetary_nonpoor']:.1f}%</div>Neither</div>
</div>""", unsafe_allow_html=True)

    section("Progress since 2016/17", "Monetary poverty by province; 2016/17 is NISR's re-estimate on the EICV7 "
                                      "methodology.", eyebrow="Trend")
    p1, p2 = st.columns([1, 1.25], gap="large")
    with p1:
        tr = data.trends()
        rows = [r for r in tr["poverty"] if r["level"] == "province"]
        rows.sort(key=lambda r: -r["p2024"])
        fig = charts.dumbbell([r["name"] for r in rows], [r["p2017"] for r in rows], [r["p2024"] for r in rows],
                              "2016/17 (modelled)", "2024", title="Monetary poverty, 2016/17 → 2024")
        chart(fig, key="nat_trend")
    with p2:
        st.dataframe(
        [{"Province": p["name"], "Monetary poverty %": round(p["poverty_rate"], 1) if p["poverty_rate"] is not None else None,
          "Extreme poverty %": round(p["extreme_poverty_rate"], 1) if p["extreme_poverty_rate"] is not None else None,
          "MPI incidence %": p["mpi_incidence"], "MPI (M0)": p["mpi"]} for p in provs],
        hide_index=True, width="stretch")
    with st.expander("Notes on comparability"):
        for n in tr["notes"]:
            st.markdown(f"- {escape(n)}")
    sources_line([{**s.source_ref("eicv7_mi"), "table": "Tables A9.23, 9.2"},
                  {**s.source_ref("eicv7_mpi"), "table": "Tables B.5, 3.1"},
                  {**s.source_ref("eicv7_pp"), "table": "Tables 0.1, 5.2, 7.1"}])
