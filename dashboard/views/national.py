from __future__ import annotations

from html import escape

import streamlit as st

from .. import charts, data
from ..theme import S1, S2, S3
from ..ui import callout, chart, guarded, hero, kpi_cards, metric_card, section, sources_line


@guarded
def render() -> None:
    s = data.store()
    d = data.dashboard()
    k = d["kpis"]
    hero("National Intelligence · EICV7 2023/24",
         "Where Rwanda stands on poverty",
         "Two official lenses on poverty — monetary (consumption below the poverty line) and multidimensional "
         "(deprivation in at least one-third of 13 weighted indicators). They measure different things and are "
         "shown side by side, never merged.",
         ["Source: NISR EICV7", f"{d['validation']['passed']}/{d['validation']['total']} validation checks passed",
          "Not an official NISR product"])

    section("Monetary poverty", "Share of people in households whose consumption per adult equivalent is below the "
                                "national poverty line (January 2024 prices).")
    pc = k["poverty_change"]
    kpi_cards([
        metric_card(k["poverty_rate"], "Monetary poverty rate", accent=S1),
        metric_card(k["extreme_poverty_rate"], "Extreme poverty rate", accent=S1),
        {"label": "Change since 2016/17", "value": f"{pc['value']:+.1f}", "unit": " pp",
         "sub": f"{pc['from']:.1f}% → {pc['to']:.1f}% (2017 modelled on EICV7 methodology)", "status": "calculated",
         "period": pc["period"], "help": pc["formula"], "accent": S1},
        metric_card(k["gini"], "Gini coefficient", show_ci=True, accent=S1),
    ])
    section("Multidimensional poverty (MPI)", "Alkire–Foster method: a person is MPI-poor if their household is "
                                              "deprived in ≥ 33.3% of weighted indicators.")
    ov = d["overlap"]
    kpi_cards([
        metric_card(k["mpi_incidence"], "MPI incidence (H)", accent=S3),
        metric_card(k["mpi_intensity"], "Intensity among the poor (A)", accent=S3),
        metric_card(k["mpi"], "MPI (M0 = H × A)", accent=S3),
        {"label": "Poor on both measures", "value": f"{ov['cells']['mpi_poor__monetary_poor']:.1f}", "unit": "%",
         "sub": f"{ov['either']:.1f}% poor on at least one", "status": "official", "period": "2023/24",
         "table": ov["table"], "help": "Share of the population that is both monetary-poor and MPI-poor.", "accent": S3},
    ])
    callout("method", "Two measures, two concepts",
            "Monetary poverty has published standard errors (95% confidence intervals shown). The MPI tables publish "
            "point estimates only, so no interval is shown for them. Do not subtract one from the other: a household "
            "can be consumption-poor without being multidimensionally deprived, and vice-versa.")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        section("Rural and urban comparison")
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
        st.caption(f"Rural MPI incidence is {gap['ratio']:.1f}× urban ({gap['rural']:.1f}% vs {gap['urban']:.1f}%). "
                   "Whiskers: 95% CI for monetary poverty (EICV7 Table A9.23).")
    with right:
        section("Overlap of the two measures", "% of the national population (EICV7 MPI Table 3.1)")
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
        st.caption(f"Only {ov['share_of_monetary_poor_also_mpi_poor']:.0f}% of the monetary poor are also MPI-poor "
                   "(calculated). Targeting on one measure misses people visible only in the other.")

    section("Provinces", "Monetary poverty and MPI incidence by province — both percentages of people, different concepts.")
    provs = sorted(d["provinces"], key=lambda p: -(p["poverty_rate"] or 0))
    p1, p2 = st.columns([1.3, 1], gap="large")
    with p1:
        fig = charts.grouped_bars([p["name"] for p in provs],
                                  [("Monetary poverty", [p["poverty_rate"] for p in provs], S1),
                                   ("MPI incidence (H)", [p["mpi_incidence"] for p in provs], S3)],
                                  horizontal=True, height=360)
        chart(fig, key="nat_prov")
    with p2:
        tr = data.trends()
        rows = [r for r in tr["poverty"] if r["level"] == "province"]
        rows.sort(key=lambda r: -r["p2024"])
        fig = charts.dumbbell([r["name"] for r in rows], [r["p2017"] for r in rows], [r["p2024"] for r in rows],
                              "2016/17 (modelled)", "2024", title="Monetary poverty, 2016/17 → 2024")
        chart(fig, key="nat_trend")
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
