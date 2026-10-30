"""Imboni — Streamlit entrypoint (Streamlit Community Cloud: main file = streamlit_app.py).

    streamlit run streamlit_app.py

Reads the validated, committed outputs in data/processed via the same analytics modules as the
FastAPI backend. Needs no database, no secrets and no network access at runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Imboni · Rwanda Data-to-Action Intelligence", page_icon="🔭", layout="wide",
                   initial_sidebar_state="auto",
                   menu_items={"About": "Imboni by team DataMinds — NISR 2026 Big Data Hackathon. "
                                        "Not an official NISR product."})

from dashboard import data  # noqa: E402
from dashboard.theme import inject_css  # noqa: E402
from dashboard.views import (explorer, financial, geographic, insights, mpi, national, reports,  # noqa: E402
                             simulator, sources)

inject_css()

PAGES = {
    "Intelligence": [
        st.Page(national.render, title="National Intelligence", icon=":material/insights:", default=True),
        st.Page(geographic.render, title="Geographic Intelligence", icon=":material/map:", url_path="geographic"),
        st.Page(mpi.render, title="Multidimensional Poverty", icon=":material/grid_view:", url_path="mpi"),
        st.Page(financial.render, title="Financial Inclusion", icon=":material/account_balance:", url_path="financial-inclusion"),
    ],
    "Decide": [
        st.Page(simulator.render, title="Intervention Simulator", icon=":material/tune:", url_path="simulator"),
        st.Page(insights.render, title="Policy Insights", icon=":material/lightbulb:", url_path="insights"),
    ],
    "Data": [
        st.Page(explorer.render, title="Data Explorer", icon=":material/table_view:", url_path="explorer"),
        st.Page(reports.render, title="Reports & Exports", icon=":material/download:", url_path="reports"),
        st.Page(sources.render, title="Sources & Methods", icon=":material/verified:", url_path="sources"),
    ],
}

ASSETS = ROOT / "dashboard" / "assets"
st.logo(str(ASSETS / "imboni-logo.svg"), size="large", icon_image=str(ASSETS / "imboni-mark.svg"))

page = st.navigation(PAGES, position="sidebar")

with st.sidebar:
    try:
        v = data.store().validation["summary"]
        st.markdown(f'<div class="im-side-card"><div class="k">From data to development action</div>'
                    f'<div class="row"><span>Team</span><b>DataMinds</b></div>'
                    f'<div class="row"><span>Track</span><b>Financial inclusion &amp; poverty</b></div>'
                    f'<div class="row"><span>Data</span><b>EICV7 · FinScope · Census</b></div>'
                    f'<div class="row"><span>Checks</span><b>{v["passed"]}/{v["total"]} passed</b></div>'
                    f'<div style="margin-top:8px">NISR 2026 Big Data Hackathon · student project, not an official NISR '
                    f'product.</div></div>', unsafe_allow_html=True)
    except data.DataUnavailable:
        st.warning("Processed data missing — run the pipeline.")

page.run()
