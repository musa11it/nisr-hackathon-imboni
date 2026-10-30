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

/* motion: subtle, and off for people who ask for reduced motion */
@keyframes imUp {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes imGrow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes imGlow {{ 0%,100% {{ opacity: .55; }} 50% {{ opacity: .9; }} }}
.im-hero .txt, .im-kpi, .im-card, .im-matrix .c {{ animation: imUp .45s ease-out both; }}
.im-grid .im-kpi:nth-child(2) {{ animation-delay: .05s; }} .im-grid .im-kpi:nth-child(3) {{ animation-delay: .1s; }}
.im-grid .im-kpi:nth-child(4) {{ animation-delay: .15s; }} .im-grid .im-kpi:nth-child(5) {{ animation-delay: .2s; }}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ animation: none !important; transition: none !important; }} }}

/* hero: editorial header — serif headline, one-line lede, inline stats, Rwanda's districts as the graphic */
@keyframes imDraw {{ from {{ opacity: 0; transform: scale(.96); }} to {{ opacity: 1; transform: none; }} }}
.im-hero {{ position: relative; overflow: hidden; border-radius: 24px; padding: 30px 34px 26px; margin-bottom: 1.4rem;
  display: grid; grid-template-columns: minmax(0, 1fr) 250px; gap: 28px; align-items: center; color: #eef3f7;
  background: radial-gradient(900px 340px at 100% 0%, rgba(95,208,192,.22), transparent 60%),
              radial-gradient(600px 300px at 0% 120%, rgba(42,120,214,.16), transparent 60%),
              linear-gradient(140deg, #08131f 0%, {NAVY} 38%, {NAVY_2} 70%, #0b3a3a 100%);
  border: 1px solid rgba(95,208,192,.14); box-shadow: 0 26px 50px -30px rgba(11,26,43,.7); }}
.im-hero::before {{ content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .55;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 28px 28px; -webkit-mask-image: linear-gradient(100deg, transparent 30%, #000 85%);
  mask-image: linear-gradient(100deg, transparent 30%, #000 85%); }}
.im-hero::after {{ content: ""; position: absolute; left: 34px; right: 34px; bottom: 0; height: 2px; pointer-events: none;
  background: linear-gradient(90deg, {GLOW}, rgba(95,208,192,0) 70%); opacity: .7; }}
.im-hero > * {{ position: relative; z-index: 1; min-width: 0; }}
.im-hero .eyebrow {{ display: inline-flex; align-items: center; gap: 10px; text-transform: uppercase; letter-spacing: .16em;
  font-size: .68rem; font-weight: 700; color: var(--glow); }}
.im-hero .eyebrow::before {{ content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--glow);
  box-shadow: 0 0 0 4px rgba(95,208,192,.18); }}
.im-hero h1 {{ font-family: 'Fraunces', Georgia, serif; color: #fff; font-weight: 600; font-size: clamp(1.8rem, 3.1vw, 2.65rem);
  line-height: 1.06; letter-spacing: -0.025em; margin: .55rem 0 .5rem; padding: 0; max-width: 780px; }}
.im-hero h1 em {{ font-style: italic; color: var(--glow); font-weight: 500; }}
.im-hero p {{ color: #b8c7d4; font-size: 1rem; max-width: 620px; margin: 0; line-height: 1.5; }}
.im-hero .meta {{ margin-top: 16px; font-size: .74rem; color: #8ea3b6; letter-spacing: .02em; }}
.im-hero .art {{ align-self: stretch; display: flex; align-items: center; justify-content: center; }}
.im-hero .art svg {{ width: 100%; max-height: 210px; filter: drop-shadow(0 10px 24px rgba(95,208,192,.18)); }}
.im-rw path {{ animation: imDraw .6s ease-out both; transform-origin: center; transform-box: fill-box; transition: fill-opacity .2s; }}
.im-stats {{ display: flex; flex-wrap: wrap; gap: 0; margin-top: 20px; }}
.im-stat {{ padding: 2px 18px 2px 0; margin-right: 18px; border-right: 1px solid rgba(255,255,255,.12); }}
.im-stat:last-child {{ border-right: 0; margin-right: 0; }}
.im-stat .v {{ font-family: 'Fraunces', Georgia, serif; font-size: 1.75rem; font-weight: 600; color: #fff; line-height: 1.05;
  font-variant-numeric: tabular-nums; }}
.im-stat .v small {{ font-family: {FONT}; font-size: .85rem; color: #8ea3b6; font-weight: 500; margin-left: 2px; }}
.im-stat .l {{ font-size: .68rem; color: #9fb3c5; margin-top: 4px; text-transform: uppercase; letter-spacing: .05em; }}

/* key-finding cards */
.im-finds {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 6px 0 10px; }}
.im-find {{ position: relative; border-radius: 16px; padding: 16px 18px; color: #eef3f7; overflow: hidden;
  background: linear-gradient(150deg, {NAVY_2}, #0d3b3a); border: 1px solid rgba(95,208,192,.16);
  animation: imUp .45s ease-out both; }}
.im-find::after {{ content: ""; position: absolute; right: -30px; top: -30px; width: 110px; height: 110px; border-radius: 50%;
  background: radial-gradient(closest-side, rgba(95,208,192,.25), transparent); }}
.im-find .n {{ font-family: 'Fraunces', Georgia, serif; font-size: 2rem; font-weight: 600; color: var(--glow); line-height: 1; }}
.im-find .t {{ font-size: .9rem; line-height: 1.45; margin-top: 8px; color: #e6eef5; }}
.im-find .s {{ font-size: .7rem; color: #8ea3b6; margin-top: 8px; letter-spacing: .02em; }}

/* sidebar */
section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] p {{ text-transform: uppercase; letter-spacing: .14em;
  font-size: .66rem !important; font-weight: 700; color: #7f97ad !important; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {{ border-radius: 10px; margin: 1px 0; position: relative;
  transition: background .15s ease, color .15s ease; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover {{ background: rgba(95,208,192,.08); }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: linear-gradient(90deg, rgba(95,208,192,.20), rgba(95,208,192,.04)); }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"]::before {{ content: ""; position: absolute;
  left: 0; top: 7px; bottom: 7px; width: 3px; border-radius: 3px; background: {GLOW}; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] p {{ color: #fff; font-weight: 600; }}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{ color: {GLOW}; }}
.im-side-card {{ margin-top: 10px; border: 1px solid {NAVY_3}; border-radius: 14px; padding: 12px 14px;
  background: linear-gradient(160deg, rgba(95,208,192,.07), rgba(255,255,255,.01)); font-size: .74rem; color: #9fb3c5; line-height: 1.5; }}
.im-side-card .k {{ font-family: 'Fraunces', Georgia, serif; color: #fff; font-size: 1.05rem; line-height: 1.2; }}
.im-side-card .row {{ display: flex; justify-content: space-between; gap: 8px; border-top: 1px dashed {NAVY_3};
  padding-top: 6px; margin-top: 6px; }}
.im-side-card .row b {{ color: #dfe8ef; font-weight: 600; }}

/* KPI cards */
.im-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(172px, 1fr)); margin: 4px 0 18px; }}
.im-kpi {{ background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px 14px;
  box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 8px 24px -14px rgba(15,27,45,.16); position: relative; overflow: hidden;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }}
.im-kpi:hover {{ transform: translateY(-2px); border-color: #d3cdbf; box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 16px 32px -16px rgba(15,27,45,.24); }}
.im-kpi::before {{ content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: var(--accent, {BRAND_500}); opacity: .9; }}
.im-kpi .label {{ font-size: .74rem; font-weight: 600; color: var(--text2); display: flex; gap: 6px; align-items: center;
  text-transform: uppercase; letter-spacing: .05em; }}
.im-kpi .label .tip {{ cursor: help; color: var(--muted); font-weight: 500; border: 1px solid var(--line); border-radius: 999px; text-transform: none;
  width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: .66rem; flex: none; }}
.im-kpi .value {{ font-family: 'Fraunces', Georgia, serif; font-size: 2.15rem; font-weight: 600; color: var(--ink); line-height: 1.1; margin-top: 8px;
  font-variant-numeric: tabular-nums; }}
.im-kpi .value small {{ font-family: {FONT}; font-size: .95rem; font-weight: 500; color: var(--muted); margin-left: 2px; }}
.im-kpi .meter {{ height: 6px; border-radius: 999px; background: #efece4; margin: 10px 0 2px; overflow: hidden; }}
.im-kpi .meter i {{ display: block; height: 100%; border-radius: 999px; background: var(--accent, {BRAND_500});
  transform-origin: left; animation: imGrow .8s cubic-bezier(.2,.7,.2,1) both; }}
.im-kpi .sub {{ font-size: .78rem; color: var(--muted); margin-top: 5px; line-height: 1.4; }}
.im-kpi .delta {{ display: inline-flex; align-items: center; gap: 3px; font-size: .74rem; font-weight: 600; padding: 1px 8px; border-radius: 999px; margin-top: 6px; }}
.im-kpi .delta.good {{ color: #0b6b36; background: #e6f6ec; }} .im-kpi .delta.bad {{ color: #9b2726; background: #fbecec; }}
.im-kpi .delta.neutral {{ color: var(--text2); background: #f2f1ee; }}
.im-kpi .foot {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; font-size: .7rem; color: var(--muted); }}

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
.im-section {{ margin: 1.9rem 0 .6rem; }}
.im-section .ey {{ font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--brand);
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
.im-section .ey::after {{ content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--line), transparent); }}
.im-section h3 {{ font-size: 1.32rem; margin: 0; padding: 0; }}
.im-section p {{ color: var(--muted); margin: .2rem 0 0; font-size: .88rem; max-width: 820px; }}

/* collapsible "how to read" note: keeps explanations available without filling the page */
details.im-note {{ border: 1px solid var(--line); border-radius: 12px; background: #fff; margin: 4px 0 14px; font-size: .86rem; }}
details.im-note summary {{ cursor: pointer; list-style: none; padding: 9px 14px; font-weight: 600; color: var(--text2);
  display: flex; align-items: center; gap: 8px; }}
details.im-note summary::-webkit-details-marker {{ display: none; }}
details.im-note summary::before {{ content: "i"; width: 18px; height: 18px; border-radius: 999px; flex: none; display: inline-flex;
  align-items: center; justify-content: center; font-size: .7rem; color: #fff; background: var(--kind, {S1}); }}
details.im-note summary::after {{ content: "+"; margin-left: auto; color: var(--muted); font-weight: 500; }}
details.im-note[open] summary::after {{ content: "–"; }}
details.im-note .b {{ padding: 0 14px 12px 40px; color: var(--ink); line-height: 1.55; }}
details.im-note.caution {{ --kind: #b07a00; }} details.im-note.gap {{ --kind: {MUTED}; }}
details.im-note.insight {{ --kind: {BRAND_500}; }}

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
  box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 10px 28px -18px rgba(15,27,45,.2); transition: box-shadow .18s ease, transform .18s ease; }}
.im-card:hover {{ transform: translateY(-1px); box-shadow: 0 1px 0 rgba(15,27,45,.04), 0 18px 36px -20px rgba(15,27,45,.28); }}
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

/* chart panels, tabs, tables, controls */
div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]) {{ background: #fff; border: 1px solid var(--line);
  border-radius: 16px; padding: 12px 12px 6px; box-shadow: 0 1px 0 rgba(15,27,45,.03), 0 8px 22px -18px rgba(15,27,45,.18);
  height: auto !important; }}
div[data-testid="stTabs"] [role="tablist"] {{ gap: 6px; }}
div[data-testid="stTabs"] button[role="tab"] {{ padding: 6px 14px; border-radius: 10px 10px 0 0; }}
div[data-testid="stTabs"] button[role="tab"] p {{ font-weight: 600; }}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{ background: #fff; }}
div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
div[data-testid="stExpander"] details {{ border-radius: 12px; background: #fff; }}
div[data-testid="stMetricValue"] {{ font-family: 'Fraunces', Georgia, serif; }}
.stButton > button, .stDownloadButton > button {{ border-radius: 10px; font-weight: 600; transition: transform .12s ease, box-shadow .12s ease; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 6px 16px -10px rgba(15,110,100,.6); }}
@media (max-width: 900px) {{ .im-hero {{ grid-template-columns: minmax(0, 1fr) 170px; }} }}
@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  .im-hero {{ padding: 22px 18px 20px; border-radius: 18px; grid-template-columns: 1fr; }}
  .im-hero h1 {{ font-size: 1.6rem; }} .im-hero p {{ font-size: .9rem; }}
  .im-hero .art {{ position: absolute; right: -24px; top: 8px; width: 150px; opacity: .35; }}
  .im-hero .txt {{ position: relative; z-index: 2; }}
  .im-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .im-stat {{ border-right: 0; margin-right: 0; padding: 0; }} .im-stat .v {{ font-size: 1.35rem; }}
  .im-find .n {{ font-size: 1.6rem; }}
  .im-grid {{ grid-template-columns: 1fr 1fr; gap: 10px; }} .im-kpi {{ padding: 12px 12px 10px; }}
  .im-kpi .value {{ font-size: 1.55rem; }} .im-kpi .label {{ font-size: .66rem; }}
  .im-kv {{ grid-template-columns: 1fr; }} .im-matrix {{ grid-template-columns: 80px 1fr 1fr; }}
  div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]) {{ padding: 6px 4px 2px; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
