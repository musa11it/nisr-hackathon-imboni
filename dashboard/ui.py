"""Reusable presentation components (HTML is escaped; data never reaches the page unescaped)."""
from __future__ import annotations

import functools
import logging
import traceback
from html import escape

import streamlit as st

from .theme import BRAND_500, CHART_CONFIG

log = logging.getLogger("imboni.dashboard")

STATUS_LABELS = {
    "official": "Official", "official_transcribed": "Official · transcribed", "calculated": "Calculated",
    "illustrative": "Illustrative", "assumption": "Your assumption", "experimental": "Experimental",
    "restricted": "Restricted", "unavailable": "Not published",
}
STATUS_HELP = {
    "official": "Value read directly from an NISR statistical table.",
    "official_transcribed": "Official value transcribed from a printed figure/chart label in the publication (rounded).",
    "calculated": "Derived by Imboni from official values with a documented formula.",
    "illustrative": "Scenario arithmetic based on user assumptions — not a measured outcome.",
    "assumption": "Set by you in the simulator.",
    "experimental": "Imboni research output; not an official statistic.",
}


def badge(status: str | None) -> str:
    s = status or "official"
    return (f'<span class="im-badge {escape(s)}" title="{escape(STATUS_HELP.get(s, ""))}">'
            f'{escape(STATUS_LABELS.get(s, s))}</span>')


def hero(eyebrow: str, title: str, lede: str, meta: list[str] | None = None,
         stats: list[tuple[str, str, str]] | None = None, accent: str | None = None) -> None:
    """Editorial page header: eyebrow, serif headline (the `accent` words set in teal italic), one-line lede,
    optional (value, unit, label) stats, a quiet source line, and Rwanda's district map as the graphic."""
    from .data import DataUnavailable, rwanda_svg

    h1 = escape(title)
    if accent and escape(accent) in h1:
        h1 = h1.replace(escape(accent), f"<em>{escape(accent)}</em>", 1)
    strip = "".join(f'<div class="im-stat"><div class="v">{escape(v)}<small>{escape(u)}</small></div>'
                    f'<div class="l">{escape(lab)}</div></div>' for v, u, lab in stats or [])
    strip_html = f'<div class="im-stats">{strip}</div>' if strip else ""
    meta_html = f'<div class="meta">{" · ".join(escape(m) for m in meta)}</div>' if meta else ""
    try:
        art = f'<div class="art" aria-hidden="true">{rwanda_svg()}</div>'
    except DataUnavailable:
        art = ""
    st.markdown(f'<div class="im-hero"><div class="txt"><div class="eyebrow">{escape(eyebrow)}</div><h1>{h1}</h1>'
                f'<p>{escape(lede)}</p>{strip_html}{meta_html}</div>{art}</div>', unsafe_allow_html=True)


def findings(items: list[tuple[str, str, str]]) -> None:
    """Key-finding cards: (headline number, one-line finding, source/status note). Values come from the data."""
    cards = "".join(f'<div class="im-find"><div class="n">{escape(n)}</div><div class="t">{escape(t)}</div>'
                    f'<div class="s">{escape(s)}</div></div>' for n, t, s in items)
    st.markdown(f'<div class="im-finds">{cards}</div>', unsafe_allow_html=True)


def section(title: str, caption: str | None = None, eyebrow: str | None = None) -> None:
    cap = f"<p>{escape(caption)}</p>" if caption else ""
    ey = f'<div class="ey">{escape(eyebrow)}</div>' if eyebrow else ""
    st.markdown(f'<div class="im-section">{ey}<h3>{escape(title)}</h3>{cap}</div>', unsafe_allow_html=True)


def note(title: str, body: str, kind: str = "method") -> None:
    """Collapsed explanation: available on demand, so the page leads with numbers and charts."""
    st.markdown(f'<details class="im-note {escape(kind)}"><summary>{escape(title)}</summary>'
                f'<div class="b">{escape(body)}</div></details>', unsafe_allow_html=True)


def fmt(v, unit: str | None = "%", d: int = 1) -> str:
    if v is None:
        return "—"
    if unit and unit.startswith("index (0–1)"):
        return f"{v:.3f}"
    if unit in {"households", "RWF", "persons_count"} or (isinstance(v, (int, float)) and abs(v) >= 10_000):
        return f"{v:,.0f}"
    return f"{v:,.{d}f}"


def unit_suffix(unit: str | None) -> str:
    if not unit:
        return ""
    if unit.startswith("%"):
        return "%"
    if unit in {"pp", "percentage points"}:
        return " pp"
    return ""


def kpi_cards(cards: list[dict]) -> None:
    """cards: label, value (str), unit, sub, status, help, period, table, accent,
    meter (0–100: draws a proportion bar), delta (str) with delta_kind good/bad/neutral."""
    html = []
    for c in cards:
        meter = ""
        if c.get("meter") is not None:
            meter = f'<div class="meter"><i style="width:{max(0.0, min(100.0, float(c["meter"]))):.1f}%"></i></div>'
        delta = (f'<div class="delta {escape(c.get("delta_kind") or "neutral")}">{escape(c["delta"])}</div>'
                 if c.get("delta") else "")
        tip = f'<span class="tip" title="{escape(c["help"])}">i</span>' if c.get("help") else ""
        foot = [badge(c.get("status"))] if c.get("status") else []
        if c.get("period"):
            foot.append(escape(str(c["period"])))
        if c.get("table"):
            foot.append(escape(str(c["table"])))
        accent = escape(c.get("accent") or BRAND_500)
        sub = f'<div class="sub">{escape(c["sub"])}</div>' if c.get("sub") else ""
        unit = escape(c.get("unit") or "")
        html.append(
            f'<div class="im-kpi" style="--accent:{accent}">'
            f'<div class="label">{escape(c["label"])}{tip}</div>'
            f'<div class="value">{escape(c["value"])}<small>{unit}</small></div>'
            f'{meter}{delta}{sub}<div class="foot">{" · ".join(foot)}</div></div>')
    st.markdown(f'<div class="im-grid">{"".join(html)}</div>', unsafe_allow_html=True)


def metric_card(m: dict | None, label: str | None = None, help: str | None = None, accent: str | None = None,
                show_ci: bool = True, meter: bool = True) -> dict:
    """Build a KPI card dict from an enriched metric (analytics.metric). Percentages get a proportion bar."""
    if not m:
        return {"label": label or "Not available", "value": "—", "sub": "Not published at this level",
                "status": "unavailable"}
    sub = None
    if show_ci and m.get("ci_low") is not None and m.get("ci_high") is not None:
        sub = f"95% CI {m['ci_low']:.1f}–{m['ci_high']:.1f}"
    elif m.get("universe"):
        sub = m["universe"]
    return {"label": label or m.get("short_name") or m.get("name"), "value": fmt(m["value"], m.get("unit"), m.get("decimals", 1)),
            "unit": unit_suffix(m.get("unit")), "sub": sub, "status": m.get("status"), "period": m.get("period"),
            "table": m.get("table_ref"), "help": help or m.get("definition"), "accent": accent,
            "meter": m["value"] if meter and (m.get("unit") or "").startswith("%") and m["value"] is not None else None}


def callout(kind: str, title: str, body: str) -> None:
    st.markdown(f'<div class="im-callout {escape(kind)}"><b class="t">{escape(title)}</b>{escape(body)}</div>',
                unsafe_allow_html=True)


def sources_line(sources: list[dict], prefix: str = "Source") -> None:
    seen, parts = set(), []
    for s in sources:
        if not s or s.get("id") in seen:
            continue
        seen.add(s.get("id"))
        name = escape(s.get("short") or s.get("title") or s.get("id", ""))
        url = s.get("landing_page") or s.get("url")
        tbl = f" — {escape(s['table'])}" if s.get("table") else ""
        parts.append(f'<a href="{escape(url)}" target="_blank" rel="noopener">{name}</a>{tbl}' if url else name + tbl)
    if parts:
        st.markdown(f'<div class="im-source"><b>{escape(prefix)}:</b> {" · ".join(parts)}</div>',
                    unsafe_allow_html=True)


def empty_state(title: str, body: str) -> None:
    callout("gap", title, body)


def chart(fig, key: str | None = None) -> None:
    """Render a figure; when it has both a title and a legend, stack them so they never overlap."""
    has_title = bool(fig.layout.title and fig.layout.title.text)
    legend_items = [t for t in fig.data if t.showlegend is not False and t.name]
    legend_on = fig.layout.showlegend is not False and len(legend_items) > 1
    if legend_on and len(legend_items) > 3:  # long legends wrap: pin them to the bottom edge, below any axis title
        n = len(legend_items)
        rows = -(-n // 2) if n <= 6 else -(-n // 3)
        fig.update_layout(legend=dict(orientation="h", y=0, yanchor="bottom", x=0, yref="container"),
                          margin=dict(b=48 + 20 * rows))
    elif has_title and legend_on:
        fig.update_layout(title=dict(y=0.985, yref="container", yanchor="top"), margin=dict(t=84),
                          legend=dict(y=1.0, yanchor="bottom", yref="paper"))
    fig.update_layout(paper_bgcolor="#fff", plot_bgcolor="#fff")  # charts sit on white panels (theme.py)
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG, key=key)


def guarded(fn):
    """Render a page; if it fails, show a calm error instead of a stack trace and keep navigation working."""
    from .data import DataUnavailable

    @functools.wraps(fn)
    def wrapper():
        try:
            fn()
        except DataUnavailable as exc:
            st.error("The processed datasets are not available.")
            st.markdown(f"`{exc}`\n\nRun the pipeline locally: `python -m backend.pipeline.build --fetch`, "
                        "then commit `data/processed/` and `data/metadata/`.")
        except Exception as exc:  # noqa: BLE001 — page-level boundary
            log.error("Page %s failed: %s\n%s", fn.__name__, exc, traceback.format_exc())
            st.error(f"This section could not be rendered ({type(exc).__name__}). Other sections remain available.")
    return wrapper
