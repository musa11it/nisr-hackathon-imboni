from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import streamlit as st

from backend.app import reports

from .. import data
from ..ui import callout, guarded, hero, section
from .insights import to_markdown


def methodology_report() -> str:
    s = data.store()
    v = s.validation["summary"]
    man = s.manifest
    lines = [
        "# Imboni — data and methodology report", "",
        f"Generated {dt.date.today().isoformat()} from pipeline version {man.get('pipeline_version', 'n/a')} "
        f"(processed {man.get('generated_at', 'n/a')}). Team DataMinds, NISR 2026 Big Data Hackathon.", "",
        reports.DISCLAIMER, "",
        "## Sources", "",
    ]
    for src in s.sources:
        r = src.get("retrieval") or {}
        lines.append(f"- **{src['title']}** ({src['publisher']}), period {src['period']}. Access: {src['access']}. "
                     f"URL: {src['url']}. Retrieved: {r.get('retrieved_at', 'n/a')}; SHA-256: {r.get('sha256', 'n/a')}. "
                     f"Used for: {src['used_for']}")
    lines += ["", "## Validation", "",
              f"{v['passed']} of {v['total']} automated checks passed; {v['errors']} pipeline errors; {v['warnings']} "
              "documented source inconsistencies (warnings).", ""]
    lines += [f"- WARNING `{c['check']}`: {c['detail']}" for c in s.validation["checks"] if c["severity"] == "warning"]
    lines += ["", "## Methods", "",
              "- Values are reproduced from official tables; values transcribed from printed figures are labelled "
              "'official · transcribed'; derived values are labelled 'calculated' with their formula.",
              "- 95% confidence intervals use NISR's published standard errors (x̂ ± 1.96·SE). Area-vs-national tests are "
              "approximate two-sample z-tests assuming independence (conservative).",
              "- Rank intervals: 4,000 Monte-Carlo draws from Normal(x̂, SE); 5th–95th percentile of ranks.",
              "- MPI: Alkire–Foster M0 = H × A; contributions recomputed as w·CH / Σ w·CH.",
              "- District associations: Spearman ρ, Fisher-z intervals (SE = 1.06/√(n−3)), Benjamini–Hochberg q-values. "
              "Ecological; not causal.",
              "- Simulator: budget arithmetic (amount ÷ unit cost, capped by Census households × measured need rate). "
              "Not an impact model.",
              "- Survey-weighted estimation from microdata was NOT performed: EICV7 microdata require authorised access.",
              "", "## Known limitations", "",
              "- MPI and its indicators are not published by district; district pages show the parent province's MPI.",
              "- FinScope district values are rounded chart labels without standard errors.",
              "- Credit, loan sources and savings depth are collected by EICV7 but not published; shown as gaps.",
              "- Map boundaries are geoBoundaries (CC BY 4.0) rather than files from the NISR GIS portal.", ""]
    return "\n".join(lines)


@guarded
def render() -> None:
    s = data.store()
    hero("Data · Reports & Exports", "Take the evidence with you",
         "Area profiles, validated datasets, methodology and insights — every export carries its sources.",
         ["Aggregate data only", "CSV · PDF · Markdown · JSON"],
         accent="with you")

    section("Area profile report", "Indicators with confidence intervals, rank among peers and significance vs national.")
    c1, c2 = st.columns([1, 2])
    with c1:
        level = st.radio("Level", ["national", "province", "district"], horizontal=True, format_func=str.title, key="rep_level")
    with c2:
        if level == "national":
            gid = "rwanda"
            st.selectbox("Area", ["Rwanda"], disabled=True, key="rep_nat")
        else:
            opts = data.province_options() if level == "province" else data.district_options()
            gid = st.selectbox("Area", [g for g, _ in opts], format_func=lambda g: data.name_of(level, g), key=f"rep_{level}")
    p = data.profile(level, gid)
    d1, d2 = st.columns(2)
    d1.download_button(f"Profile CSV — {p['name']}", reports.profile_csv(p).encode("utf-8"),
                       f"imboni_profile_{gid}.csv", "text/csv", width="stretch")
    srcs = [s.source_index[x] for x in ("eicv7_mi", "eicv7_mpi", "finscope_2024", "rphc5_main")]
    with d2:
        if st.toggle("Prepare PDF", key=f"pdf_{level}_{gid}", help="Generated on demand with ReportLab."):
            try:
                pdf = reports.area_report_pdf(p, srcs)
                st.download_button(f"Profile PDF — {p['name']}", pdf, f"imboni_profile_{gid}.pdf", "application/pdf",
                                   width="stretch")
            except Exception as exc:  # noqa: BLE001 — CSV remains available
                st.warning(f"PDF could not be generated ({type(exc).__name__}); use the CSV export.")

    section("Datasets", "Validated aggregate outputs of the reproducible pipeline (data/processed).")
    pre = f"# Imboni (DataMinds) export {dt.date.today().isoformat()} — {reports.DISCLAIMER}\n"
    obs = data.observations_df()
    e1, e2, e3 = st.columns(3)
    e1.download_button("All observations (CSV)", (pre + obs.to_csv(index=False)).encode("utf-8"),
                       "imboni_observations.csv", "text/csv", width="stretch")
    e2.download_button("Indicator catalogue (CSV)", (pre + data.indicators_df().to_csv(index=False)).encode("utf-8"),
                       "imboni_indicators.csv", "text/csv", width="stretch")
    e3.download_button("Source registry (CSV)", (pre + data.sources_df().to_csv(index=False)).encode("utf-8"),
                       "imboni_sources.csv", "text/csv", width="stretch")
    f1, f2, f3 = st.columns(3)
    checks = pd.DataFrame(s.validation["checks"])
    f1.download_button("Validation checks (CSV)", checks.to_csv(index=False).encode("utf-8"), "imboni_validation.csv",
                       "text/csv", width="stretch")
    f2.download_button("Data-quality summary (CSV)", data.missingness_df().to_csv(index=False).encode("utf-8"),
                       "imboni_data_quality.csv", "text/csv", width="stretch")
    f3.download_button("MPI framework (JSON)", json.dumps(s.mpi_framework, indent=1, ensure_ascii=False).encode("utf-8"),
                       "imboni_mpi_framework.json", "application/json", width="stretch")

    section("Analytical reports")
    g1, g2 = st.columns(2)
    g1.download_button("Methodology & data report (Markdown)", methodology_report().encode("utf-8"),
                       "imboni_methodology_report.md", "text/markdown", width="stretch")
    g2.download_button("Policy insights (Markdown)", to_markdown(data.policy_insights()["insights"]).encode("utf-8"),
                       "imboni_policy_insights.md", "text/markdown", width="stretch")
    callout("method", "Scenario exports", "Budget scenarios (CSV, PDF and side-by-side comparisons) are exported from "
            "the Intervention Simulator page, where the assumptions are set.")
    with st.expander("Preview the methodology report"):
        st.markdown(methodology_report())
