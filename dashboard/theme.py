"""Visual identity: deep navy + teal-green, shared with the React frontend (frontend/src/lib/colors.ts).

The categorical slots were validated with the dataviz palette validator (lightness band, chroma floor,
CVD separation); the two light slots (aqua, yellow) fall below 3:1 contrast, so charts that use them
always carry a legend or direct labels and a table view.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

NAVY = "#0b1a2b"
NAVY_2 = "#12263c"
NAVY_3 = "#1d3550"
INK = "#0f1b2d"
TEXT_2 = "#4a4f58"
MUTED = "#7b7f86"
PAPER = "#f7f5f0"
PAPER_2 = "#efece4"
LINE = "#e3dfd5"
GRID = "#ebe7de"
AXIS = "#cfc9bb"
BRAND = "#0f6e64"
BRAND_500 = "#1d8477"
BRAND_100 = "#d2ede8"
GLOW = "#5fd0c0"

# Categorical slots in FIXED order: colour follows the entity, never its rank.
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SERIES = [S1, S2, S3, S4]
# Single-hue sequential ramp (teal), light -> dark = less -> more deprived.
SEQ = ["#d7ece8", "#9fd1c8", "#5faea3", "#2b867d", "#0d5755"]
NO_DATA = "#e9e6df"
# Diverging blue <-> red, neutral grey midpoint (correlations).
DIVERGING = ["#104281", "#2a78d6", "#86b6ef", "#cde2fb", "#f0efec", "#fbd5d4", "#f08f8e", "#e34948", "#9b2726"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

STRAND = [("fs_banked", "Banked", S1), ("fs_other_formal", "Other formal (non-bank)", S2),
          ("fs_informal_only", "Informal only", S3), ("fs_excluded", "Excluded", S4)]

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
# Charts use the system UI font: Plotly measures label widths at draw time, and a web font that finishes loading
# afterwards would be wider than measured and clip axis labels.
CHART_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def _register_template() -> None:
    axis = dict(gridcolor=GRID, gridwidth=1, linecolor=AXIS, zeroline=False, ticks="", showline=False,
                tickfont=dict(color=MUTED, size=12), title=dict(font=dict(color=TEXT_2, size=12)), automargin=True)
    pio.templates["imboni"] = go.layout.Template(layout=dict(
        font=dict(family=CHART_FONT, color=TEXT_2, size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=SERIES, xaxis=axis, yaxis=axis,
        hoverlabel=dict(bgcolor="white", bordercolor=LINE, font=dict(family=CHART_FONT, color=INK, size=13), align="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                    font=dict(color=TEXT_2, size=12)),
        margin=dict(l=8, r=16, t=40, b=8), bargap=0.35, bargroupgap=0.08, barcornerradius=4,
        title=dict(font=dict(family=CHART_FONT, color=INK, size=15), x=0, xanchor="left"),
    ))
    pio.templates.default = "imboni"


_register_template()

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');
:root {{ --navy:{NAVY}; --ink:{INK}; --text2:{TEXT_2}; --muted:{MUTED}; --line:{LINE}; --brand:{BRAND}; --glow:{GLOW}; }}
html, body, [class*="css"] {{ font-family: {FONT}; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1320px; }}
h1, h2, h3 {{ font-family: 'Fraunces', Georgia, serif; letter-spacing: -0.015em; color: var(--ink); }}
footer {{ visibility: hidden; }}

/* hero */
.im-hero {{ position: relative; overflow: hidden; border-radius: 20px; padding: 28px 32px 26px;
  background: radial-gradient(1200px 300px at 85% -40%, rgba(95,208,192,.28), transparent 60%),
              linear-gradient(135deg, {NAVY} 0%, {NAVY_2} 55%, #0c3b3a 100%);
  color: #eef3f7; margin-bottom: 1.4rem; box-shadow: 0 18px 40px -22px rgba(11,26,43,.55); }}
.im-hero .eyebrow {{ text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; font-weight: 600; color: var(--glow); }}
.im-hero h1 {{ color: #fff; font-size: 2.05rem; line-height: 1.15; margin: .35rem 0 .45rem; padding: 0; }}
.im-hero p {{ color: #c9d4de; font-size: 1rem; max-width: 860px; margin: 0; line-height: 1.55; }}
.im-hero .meta {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; }}
.im-hero .meta span {{ font-size: .76rem; color: #dce6ee; border: 1px solid rgba(255,255,255,.16);
  background: rgba(255,255,255,.06); padding: 3px 10px; border-radius: 999px; }}

/* KPI cards */
.im-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); margin: 4px 0 18px; }}
.im-kpi {{ background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px 14px;
  box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 8px 24px -14px rgba(15,27,45,.16); position: relative; }}
.im-kpi::before {{ content: ""; position: absolute; left: 0; top: 16px; bottom: 16px; width: 3px; border-radius: 3px; background: var(--accent, {BRAND_500}); }}
.im-kpi .label {{ font-size: .8rem; font-weight: 600; color: var(--text2); display: flex; gap: 6px; align-items: center; }}
.im-kpi .label .tip {{ cursor: help; color: var(--muted); font-weight: 500; border: 1px solid var(--line); border-radius: 999px;
  width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: .66rem; }}
.im-kpi .value {{ font-family: 'Fraunces', Georgia, serif; font-size: 2rem; font-weight: 600; color: var(--ink); line-height: 1.15; margin-top: 6px; }}
.im-kpi .value small {{ font-family: {FONT}; font-size: .95rem; font-weight: 500; color: var(--muted); margin-left: 2px; }}
.im-kpi .sub {{ font-size: .78rem; color: var(--muted); margin-top: 4px; line-height: 1.4; }}
.im-kpi .foot {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; font-size: .72rem; color: var(--muted); }}

/* badges */
.im-badge {{ display: inline-block; font-size: .68rem; font-weight: 600; letter-spacing: .02em; padding: 2px 8px; border-radius: 999px; border: 1px solid; white-space: nowrap; }}
.im-badge.official {{ color: #0c5951; background: #ecf7f5; border-color: #a6dad1; }}
.im-badge.official_transcribed {{ color: #3d4a5c; background: #eef1f5; border-color: #cfd6df; }}
.im-badge.calculated {{ color: #104281; background: #edf4fd; border-color: #b9d4f5; }}
.im-badge.illustrative, .im-badge.assumption {{ color: #7a4b00; background: #fff6e0; border-color: #f2d48a; }}
.im-badge.experimental {{ color: #8a2f12; background: #fdeee8; border-color: #f3c3ae; }}
.im-badge.restricted {{ color: #7d1f1f; background: #fbecec; border-color: #efbcbc; }}
.im-badge.unavailable {{ color: #5b6472; background: #f2f1ee; border-color: #dcd8cf; }}

/* section heading */
.im-section {{ margin: 1.6rem 0 .5rem; }}
.im-section h3 {{ font-size: 1.32rem; margin: 0; padding: 0; }}
.im-section p {{ color: var(--text2); margin: .25rem 0 0; font-size: .92rem; max-width: 900px; }}

/* callouts */
.im-callout {{ border-radius: 14px; padding: 14px 16px; border: 1px solid var(--line); background: #fff; margin: 6px 0 14px; font-size: .9rem; line-height: 1.55; color: var(--ink); }}
.im-callout b.t {{ display: block; font-size: .82rem; letter-spacing: .02em; margin-bottom: 2px; }}
.im-callout.method {{ border-left: 4px solid {S1}; }}
.im-callout.caution {{ border-left: 4px solid {STATUS['warning']}; background: #fffbf0; }}
.im-callout.gap {{ border-left: 4px solid {MUTED}; background: #faf9f6; }}
.im-callout.insight {{ border-left: 4px solid {BRAND_500}; }}

.im-source {{ font-size: .78rem; color: var(--muted); margin: 4px 0 10px; line-height: 1.5; }}
.im-source a {{ color: var(--brand); text-decoration: none; }}
.im-source a:hover {{ text-decoration: underline; }}

/* insight card */
.im-card {{ background:#fff; border:1px solid var(--line); border-radius:18px; padding:20px 22px; margin-bottom:16px;
  box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 10px 28px -18px rgba(15,27,45,.2); }}
.im-card .theme {{ font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; color:var(--brand); font-weight:700; }}
.im-card h4 {{ font-family:'Fraunces',Georgia,serif; font-size:1.2rem; margin:.3rem 0 .5rem; color:var(--ink); }}
.im-card .finding {{ color:var(--ink); font-size:.95rem; line-height:1.6; }}
.im-chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }}
.im-chip {{ border:1px solid var(--line); border-radius:12px; padding:8px 12px; background:#fcfbf8; min-width:150px; }}
.im-chip .v {{ font-family:'Fraunces',Georgia,serif; font-weight:600; font-size:1.15rem; color:var(--ink); }}
.im-chip .l {{ font-size:.74rem; color:var(--text2); margin-top:2px; }}
.im-kv {{ display:grid; grid-template-columns: 160px 1fr; gap:6px 14px; font-size:.86rem; margin-top:10px; }}
.im-kv .k {{ color:var(--muted); font-weight:600; }}
.im-kv .v {{ color:var(--ink); }}

/* overlap matrix */
.im-matrix {{ display:grid; grid-template-columns: 140px 1fr 1fr; gap:8px; font-size:.85rem; }}
.im-matrix .h {{ color:var(--muted); font-weight:600; display:flex; align-items:end; padding:4px; }}
.im-matrix .c {{ border-radius:14px; padding:14px; color:var(--ink); border:1px solid var(--line); background:#fff; }}
.im-matrix .c .n {{ font-family:'Fraunces',Georgia,serif; font-size:1.6rem; font-weight:600; }}
.im-matrix .c.both {{ background:#0d5755; color:#fff; border-color:#0d5755; }}
.im-matrix .c.one {{ background:#d7ece8; }}

/* sidebar brand */
.im-brand {{ display:flex; gap:10px; align-items:center; padding: 4px 2px 10px; }}
.im-brand .mark {{ width:36px; height:36px; border-radius:10px; background: linear-gradient(135deg, {GLOW}, {BRAND}); display:flex; align-items:center; justify-content:center; color:{NAVY}; font-weight:800; font-family:'Fraunces',Georgia,serif; font-size:1.2rem; }}
.im-brand .name {{ font-family:'Fraunces',Georgia,serif; font-size:1.35rem; color:#fff; line-height:1; }}
.im-brand .tag {{ font-size:.72rem; color:#9fb3c5; margin-top:3px; }}
.im-brand-tag {{ font-size:.74rem; color:#9fb3c5; margin:-6px 0 6px; letter-spacing:.02em; }}
.im-side-note {{ font-size:.72rem; color:#9fb3c5; line-height:1.5; border-top:1px solid {NAVY_3}; padding-top:10px; margin-top:8px; }}

div[data-testid="stTabs"] button p {{ font-weight: 600; }}
div[data-testid="stMetricValue"] {{ font-family: 'Fraunces', Georgia, serif; }}
@media (max-width: 640px) {{
  .im-hero {{ padding: 22px 18px; }} .im-hero h1 {{ font-size: 1.55rem; }}
  .im-kv {{ grid-template-columns: 1fr; }} .im-matrix {{ grid-template-columns: 90px 1fr 1fr; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
