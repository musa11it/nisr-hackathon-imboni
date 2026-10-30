from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import data
from ..ui import callout, guarded, hero, kpi_cards, section

ROLE_LABELS = {"required": "Parsed · required", "optional": "Parsed · optional", "reference": "Reference document",
               "restricted": "Restricted / not downloaded"}


@guarded
def render() -> None:
    s = data.store()
    man = s.manifest
    inv = data.inventory()
    hero("Sources & Methods", "Data inventory and provenance",
         "Every official file Imboni uses, its access conditions, reference period, retrieval date and checksum — "
         "and the datasets that are restricted or still missing.",
         [f"Pipeline v{man.get('pipeline_version', '?')}", f"Processed {str(man.get('generated_at', '?'))[:10]}",
          "Raw files kept byte-for-byte"])
    v = s.validation["summary"]
    kpi_cards([
        {"label": "Sources registered", "value": str(len(s.sources)), "status": "official"},
        {"label": "Observations", "value": f"{man.get('observations', len(s.observations)):,}",
         "sub": f"{man.get('indicators_with_data', '?')} indicators with data", "status": "calculated"},
        {"label": "Validation", "value": f"{v['passed']}/{v['total']}", "sub": f"{v['errors']} errors · {v['warnings']} source warnings",
         "status": "calculated"},
        {"label": "Build completeness", "value": "Partial" if man.get("partial_build") else "Complete",
         "sub": ("Missing: " + ", ".join(man.get("missing_sources", []))) if man.get("partial_build") else
                "All required and optional sources parsed", "status": "calculated"},
    ])
    section("Data inventory", "Recorded by the pipeline at build time (raw files are not committed or deployed).")
    if inv:
        df = pd.DataFrame([{"Source": r["short"], "Role": ROLE_LABELS.get(r["role"], r["role"]),
                            "Status": "restricted" if r["role"] == "restricted" else ("present" if r["present"] else "MISSING"),
                            "Checksum vs log": {True: "matches", False: "CHANGED", None: ""}[r["checksum_matches_log"]],
                            "Period": r["period"], "Format": r["format"], "Retrieved": r["retrieved_at"],
                            "Access": r["access"], "URL": r["url"]} for r in inv])
        st.dataframe(df, hide_index=True, width="stretch", column_config={"URL": st.column_config.LinkColumn()})
    else:
        st.caption("No inventory file found — run `python -m backend.pipeline.inventory`.")

    section("What you may still need to obtain")
    callout("gap", "EICV7 microdata (catalog 119) and EICV7 VUP microdata (catalog 121)",
            "Needed only for survey-weighted estimates that NISR has not published (credit, loan sources, savings depth, "
            "district-level financial indicators, design-based SEs for new breakdowns). Register on the NISR Microdata "
            "Portal, review the Microdata Release Policy, and submit a data request describing the hackathon use. Keep "
            "any files in data/restricted/ (git-ignored) and publish aggregates only.")
    callout("gap", "Official NISR boundary files (optional)",
            "The NISR GIS portal (gis.statistics.gov.rw) served a self-signed TLS certificate when checked, so boundaries "
            "were not downloaded from it. Maps use geoBoundaries ADM1/ADM2 (CC BY 4.0). Replace them with official NISR "
            "files if the team obtains them; district names must match the 30 EICV7 districts.")

    section("Source registry")
    src = data.sources_df()
    st.dataframe(src[["short", "publisher", "period", "access", "license", "used_for", "retrieved_at", "sha256", "landing_page"]],
                 hide_index=True, width="stretch", column_config={"landing_page": st.column_config.LinkColumn("Landing page")})
    with st.expander("Citations"):
        for r in s.sources:
            st.markdown(f"- {r['citation']}")

    section("Methods in brief")
    st.markdown("""
* **Pipeline** — `python -m backend.pipeline.build`: inventory → parse official tables by printed labels → validate
  (benchmarks, identities, ranges, duplicates, coverage) → tidy observations + catalogue + quality summary.
* **Uncertainty** — 95% CIs from NISR standard errors; approximate z-tests vs national; Monte-Carlo rank intervals.
* **MPI** — Alkire–Foster (dual cut-off, k = 33.3%); M0 = H × A; contributions recomputed and published values shown side by side.
* **Associations** — Spearman correlations across 30 districts with Fisher-z CIs and Benjamini–Hochberg q-values;
  ecological, never causal.
* **No machine learning** — 30 districts and 5 provinces are too few observations for a defensible predictive model;
  household-level modelling would need authorised microdata.
* **Survey weights** — published aggregates already embed NISR's weighting. Weighted re-estimation is only possible with
  microdata (weights, strata, PSUs documented in the EICV7 DDI / methodological note).
""")
    callout("method", "Independence & AI disclosure",
            "Imboni is a student project by team DataMinds and is not an official NISR product. AI assistance (Claude, "
            "Anthropic) was used for coding and documentation and is disclosed in docs/AI_DISCLOSURE.md; the application "
            "calls no AI service and every statistic comes from the cited publications.")
