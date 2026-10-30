from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from .. import charts, data
from ..theme import S1, S2, STRAND
from ..ui import badge, callout, chart, guarded, hero, kpi_cards, section, sources_line

SEGMENTS = {k: label for k, label, _ in STRAND} | {"formally_served": "Formally served (banked + other formal)"}


@guarded
def render() -> None:
    s = data.store()
    f = data.financial()
    hero("Financial Inclusion", "Access is near-universal; depth is not",
         "FinScope 2024 measures how adults (16+) access financial services; EICV7 adds household savings and "
         "mobile-money accounts by poverty status, and VUP payment channels. Variables that are collected but not "
         "published are listed as gaps, not estimated.",
         ["FinScope Rwanda 2024 (adults 16+)", "EICV7 2023/24 (households)", "Transcribed chart values are labelled"])
    n24, n20 = f["national_strand"]["2024"], f["national_strand"]["2020"]
    hl = {h["key"]: h for h in f["headline"]}
    eicv = f["eicv"]
    cards = [
        {"label": "Adults banked", "value": f"{n24['fs_banked']:.0f}", "unit": "%", "sub": f"2020: {n20['fs_banked']:.0f}%",
         "status": "official_transcribed", "period": "2024", "help": s.indicator_index["fs_banked"]["definition"], "accent": S1},
        {"label": "Adults financially excluded", "value": f"{n24['fs_excluded']:.0f}", "unit": "%",
         "sub": f"2020: {n20['fs_excluded']:.0f}%", "status": "official_transcribed", "period": "2024",
         "help": s.indicator_index["fs_excluded"]["definition"], "accent": S1},
    ]
    if "formal_inclusion" in hl:
        cards.append({"label": hl["formal_inclusion"]["label"], "value": f"{hl['formal_inclusion']['value']:.0f}", "unit": "%",
                      "status": hl["formal_inclusion"]["status"], "period": "2024", "accent": S1})
    for key, label in (("hh_savings_account", "Households with a savings account"),
                       ("hh_momo_account", "Households with a mobile-money account")):
        e = eicv[key]
        cards.append({"label": label, "value": f"{e['all']:.1f}", "unit": "%",
                      "sub": f"Poor {e['poor']:.1f}% · non-poor {e['non_poor']:.1f}%", "status": "official",
                      "period": e["meta"]["period"], "table": e["meta"]["table_ref"], "help": e["meta"]["definition"],
                      "accent": S2})
    kpi_cards(cards)
    callout("caution", "Different universes", " ".join(f["caveats"]))

    section("FinScope Access Strand", "Mutually exclusive segments: banked → other formal (non-bank) → informal only → "
                                      "excluded. Each adult is counted once, in the most formal segment used.")
    strand_rows = [("Rwanda 2024", n24), ("Rwanda 2020", n20)]
    for a in ("urban", "rural"):
        strand_rows.append((f"{a.title()} 2024", f["area"][a]["2024"]))
    for sx in ("male", "female"):
        strand_rows.append((f"{sx.title()} 2024", f["sex"][sx]["2024"]))
    strand_rows += [(p["name"], p) for p in f["provinces"]]
    chart(charts.strand_bars(strand_rows), key="fi_strand")

    section("Districts", "FinScope 2024 publishes the Access Strand for all 30 districts (rounded chart labels).")
    c1, c2 = st.columns([1, 2])
    with c1:
        seg = st.selectbox("Segment", list(SEGMENTS), format_func=SEGMENTS.get, index=0)
    dists = f["districts"]
    worse_high = seg in ("fs_excluded", "fs_informal_only")
    nat = (n24.get(seg) if seg != "formally_served" else (n24["fs_banked"] or 0) + (n24["fs_other_formal"] or 0))
    rows = [{"geo_id": d["geo_id"], "geo_name": d["name"], "value": d[seg]} for d in dists]
    for i, r in enumerate(sorted([r for r in rows if r["value"] is not None], key=lambda r: r["value"], reverse=worse_high), 1):
        r["rank"] = i
    a, b = st.columns([1.1, 1], gap="large")
    with a:
        geo_rows = [{**r, "ci_low": None, "flags": [], "status": "official_transcribed"} for r in rows]
        chart(charts.choropleth(s.geo["district"], geo_rows, SEGMENTS[seg], "%", worse_high, 0), key=f"fi_map_{seg}")
    with b:
        chart(charts.ranked_bars(rows, ref=nat, worse_high=worse_high, decimals=0,
                                 title=f"{SEGMENTS[seg]} by district"), key=f"fi_bars_{seg}")
    st.caption("No standard errors are published for FinScope district values, so ranks carry unquantified uncertainty.")

    section("Savings and mobile money by poverty status", "EICV7 households with at least one account (Poverty Profile "
                                                          "Table 6.9 memo items). Not published by district or province.")
    labels = ["Savings account", "Mobile-money account"]
    chart(charts.grouped_bars(labels, [("Poor households", [eicv[k]["poor"] for k in ("hh_savings_account", "hh_momo_account")], S2),
                                       ("Non-poor households", [eicv[k]["non_poor"] for k in ("hh_savings_account", "hh_momo_account")], S1)],
                              height=340), key="fi_eicv")

    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        section("How VUP transfers are paid", "EICV7 VUP thematic tables, by programme component.")
        vup = f["vup"]
        chart(charts.stacked_share([v["component"] for v in vup],
                                   [("Umurenge SACCO", [v["sacco"] for v in vup], S1),
                                    ("Mobile money", [v["momo"] for v in vup], S2)]), key="fi_vup")
        st.dataframe(pd.DataFrame([{"Component": v["component"], "Paid on time %": v["on_time"],
                                    "Weighted households (est.)": round(v["households"]) if v["households"] is not None else None, "Poverty rate among beneficiaries %": v["poverty_rate"]}
                                   for v in vup]).round(1), hide_index=True, width="stretch")
    with c2:
        section("Responses to shocks", "Main coping response among households reporting a shock (% of those households).")
        sh = pd.DataFrame(f["shock_responses"]).rename(columns={"response": "Response", "all": "All", "poor": "Poor",
                                                                 "non_poor": "Non-poor"})
        if not sh.empty:
            sh["Response"] = sh["Response"].str.replace("_", " ").str.capitalize()
            st.dataframe(sh.round(1).sort_values("All", ascending=False), hide_index=True, width="stretch", height=380)
        fs = f["vup_financial_services"]
        if fs.get("loan_approved") is not None:
            st.markdown(f"VUP Financial Services: **{fs['loan_approved']:.1f}%** of applicants had a loan approved; "
                        f"average loan **RWF {fs['avg_loan']:,.0f}** {badge('official')}", unsafe_allow_html=True)

    section("Data gaps", "Financial-inclusion variables that EICV7 collects but NISR has not published as tables. "
                         "Imboni shows them as unavailable rather than estimating them.")
    gaps = pd.DataFrame(f["unavailable"]).rename(columns={"variable": "Variable", "where_collected": "Where collected",
                                                          "status": "Status", "how_to_obtain": "How to obtain"})
    st.dataframe(gaps, hide_index=True, width="stretch")
    callout("gap", "What would close these gaps",
            "Authorised access to the EICV7 microdata (NISR Microdata Portal, catalog 119) with survey weights, strata and "
            "PSUs would allow design-based estimates of credit, loan sources and savings by district. Imboni does not "
            "download or display microdata; see docs/MICRODATA_IMPORT.md.")
    sources_line([{**src, "table": None} for src in f["sources"]])
    with st.expander("Why insurance, credit and savings depth are not shown"):
        st.markdown("\n".join(f"- **{escape(g['variable'])}** — {escape(g['how_to_obtain'])}" for g in f["unavailable"]))
