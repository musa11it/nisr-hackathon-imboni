"""Plotly figure builders with one consistent visual grammar.

Thin bars with 4px rounded ends, hairline recessive grids, one y-axis, a legend whenever there are
two or more series, hover tooltips on every mark, and categorical colours in fixed slot order.
"""
from __future__ import annotations

import functools
import json

import plotly.graph_objects as go

from .theme import AXIS, BRAND_500, DIVERGING, INK, MUTED, NO_DATA, S1, S2, SEQ, STRAND, TEXT_2


def wrap(label: str, width: int = 22) -> str:
    """Break long category labels onto two lines so narrow columns never clip them."""
    if len(label) <= width or " " not in label:
        return label
    cut = label.rfind(" ", 0, width + 1)
    cut = cut if cut > 0 else label.find(" ")
    return label[:cut] + "<br>" + label[cut + 1:]


def _h(n: int, per: int = 30, base: int = 90, lo: int = 220) -> int:
    return max(lo, base + per * n)


def ranked_bars(rows: list[dict], unit: str = "%", ref: float | None = None, ref_label: str = "National",
                highlight: str | None = None, title: str | None = None, worse_high: bool = True,
                decimals: int = 1) -> go.Figure:
    """Horizontal bars sorted most- to least-deprived, with 95% CI whiskers when published."""
    data = sorted([r for r in rows if r.get("value") is not None], key=lambda r: r["value"], reverse=worse_high)
    names = [wrap(r["geo_name"]) for r in data]
    vals = [r["value"] for r in data]
    has_ci = any(r.get("ci_low") is not None for r in data)
    colors = [S2 if r["geo_id"] == highlight else BRAND_500 for r in data]
    custom = [[r.get("ci_low"), r.get("ci_high"), r.get("cv"), r.get("rank"), r.get("rank_low"), r.get("rank_high"),
               (r.get("vs_national") or {}).get("label") or "n/a"] for r in data]
    ht = f"<b>%{{y}}</b><br>Value: %{{x:.{decimals}f}}{unit if unit == '%' else ''}"
    if has_ci:
        ht += f"<br>95% CI: %{{customdata[0]:.{decimals}f}}–%{{customdata[1]:.{decimals}f}}<br>CV: %{{customdata[2]:.1f}}%"
    if any(r.get("rank") is not None for r in data):
        ht += "<br>Rank %{customdata[3]}"
    if any(r.get("rank_low") is not None for r in data):
        ht += " (90% interval %{customdata[4]}–%{customdata[5]})"
    if ref is not None:
        ht += f"<br>vs {ref_label.lower()}: %{{customdata[6]}}"
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h", marker=dict(color=colors, line=dict(width=0)), customdata=custom,
        hovertemplate=ht + "<extra></extra>",
        error_x=dict(type="data", symmetric=False, array=[(r["ci_high"] - r["value"]) if r.get("ci_high") is not None else 0 for r in data],
                     arrayminus=[(r["value"] - r["ci_low"]) if r.get("ci_low") is not None else 0 for r in data],
                     color=INK, thickness=1, width=3, visible=has_ci),
    ))
    if ref is not None:
        fig.add_vline(x=ref, line=dict(color=INK, width=1.5, dash="dot"),
                      annotation=dict(text=f"{ref_label} {ref:.{decimals}f}", font=dict(color=INK, size=12),
                                      yanchor="bottom", y=1.0, bgcolor="rgba(255,255,255,.85)"))
    fig.update_layout(title=title, height=_h(len(data), 24), bargap=0.28, showlegend=False,
                      yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(color=TEXT_2, size=12)),
                      xaxis=dict(ticksuffix="%" if unit == "%" else "", rangemode="tozero"))
    return fig


def _signed_area(ring: list) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0, *_), (x1, y1, *_) in zip(ring, ring[1:] + ring[:1], strict=False)) / 2


def _rewind(ring: list, clockwise: bool) -> list:
    return ring[::-1] if (_signed_area(ring) < 0) != clockwise else ring


@functools.lru_cache(maxsize=4)
def _plotly_geojson(key: str, raw: str) -> dict:
    """Plotly renders with d3-geo, which treats counter-clockwise exterior rings (RFC 7946) as 'the whole globe
    minus the shape'. Rewind exteriors clockwise and holes counter-clockwise."""
    gj = json.loads(raw)
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        fixed = [[_rewind(r, clockwise=(i == 0)) for i, r in enumerate(p)] for p in polys]
        g["coordinates"] = fixed[0] if g["type"] == "Polygon" else fixed
    return gj


def plotly_geojson(geojson: dict) -> dict:
    return _plotly_geojson(str(len(geojson["features"])), json.dumps(geojson))


def choropleth(geojson: dict, rows: list[dict], indicator_name: str, unit: str, worse_high: bool,
               decimals: int = 1, height: int = 520) -> go.Figure:
    by_id = {r["geo_id"]: r for r in rows}
    ids = [f["properties"]["geo_id"] for f in geojson["features"]]
    present = [i for i in ids if by_id.get(i) and by_id[i]["value"] is not None]
    missing = [i for i in ids if i not in present]
    scale = [[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ if worse_high else SEQ[::-1])]
    names = {f["properties"]["geo_id"]: f["properties"]["name"] for f in geojson["features"]}

    def tip(r):
        bits = [f"<b>{names[r['geo_id']]}</b>", f"{indicator_name}: {r['value']:.{decimals}f}{'%' if unit == '%' else ' ' + unit}"]
        if r.get("ci_low") is not None:
            bits.append(f"95% CI {r['ci_low']:.{decimals}f}–{r['ci_high']:.{decimals}f} · CV {r['cv']:.1f}%")
        if r.get("rank") is not None:
            rk = f"Rank {r['rank']}"
            if r.get("rank_low") is not None:
                rk += f" (90% interval {r['rank_low']}–{r['rank_high']})"
            bits.append(rk)
        vs = (r.get("vs_national") or {})
        if vs.get("available"):
            bits.append(f"{vs['label'].capitalize()} national (p = {vs['p_value']:.3f})")
        if r.get("flags"):
            bits.append("Flags: " + ", ".join(r["flags"]))
        return "<br>".join(bits)

    geojson = plotly_geojson(geojson)
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=geojson, featureidkey="properties.geo_id", locations=present,
        z=[by_id[i]["value"] for i in present], colorscale=scale, marker=dict(line=dict(color="white", width=1.2)),
        text=[tip(by_id[i]) for i in present], hovertemplate="%{text}<extra></extra>",
        colorbar=dict(title=dict(text=("darker = more deprived" if worse_high else "darker = less coverage"),
                                 side="right", font=dict(size=11, color=MUTED)),
                      thickness=10, len=0.75, outlinewidth=0, ticksuffix="%" if unit == "%" else "",
                      tickfont=dict(color=MUTED, size=11)),
    ))
    if missing:
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="properties.geo_id", locations=missing, z=[0] * len(missing),
            colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker=dict(line=dict(color="white", width=1.2)),
            text=[f"<b>{names[i]}</b><br>Not published at this level" for i in missing],
            hovertemplate="%{text}<extra></extra>"))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), dragmode=False)
    return fig


def grouped_bars(categories: list[str], series: list[tuple[str, list[float | None], str]], unit: str = "%",
                 title: str | None = None, horizontal: bool = False, errors: dict[str, list] | None = None,
                 decimals: int = 1, height: int | None = None) -> go.Figure:
    fig = go.Figure()
    categories = [wrap(c) for c in categories]
    for name, vals, color in series:
        err = (errors or {}).get(name)
        kw = dict(name=name, marker=dict(color=color), hovertemplate=f"<b>%{{{'y' if horizontal else 'x'}}}</b><br>{name}: "
                  f"%{{{'x' if horizontal else 'y'}:.{decimals}f}}{unit if unit == '%' else ''}<extra></extra>",
                  texttemplate=f"%{{{'x' if horizontal else 'y'}:.{decimals}f}}", textposition="outside",
                  textfont=dict(color=TEXT_2, size=11), cliponaxis=False)
        if err:  # whiskers carry the uncertainty; a value label would collide with them (tooltip keeps the value)
            kw.pop("texttemplate")
            e = dict(type="data", symmetric=False, array=[h - v if h is not None and v is not None else 0 for v, (_, h) in zip(vals, err, strict=False)],
                     arrayminus=[v - lo if lo is not None and v is not None else 0 for v, (lo, _) in zip(vals, err, strict=False)],
                     color=INK, thickness=1, width=3)
            kw["error_x" if horizontal else "error_y"] = e
        if horizontal:
            fig.add_trace(go.Bar(y=categories, x=vals, orientation="h", **kw))
        else:
            fig.add_trace(go.Bar(x=categories, y=vals, **kw))
    ax = dict(ticksuffix="%" if unit == "%" else "", rangemode="tozero")
    fig.update_layout(title=title, barmode="group", showlegend=len(series) > 1,
                      height=height or (_h(len(categories) * len(series), 22) if horizontal else 380),
                      **({"xaxis": ax, "yaxis": dict(autorange="reversed", showgrid=False)} if horizontal else
                         {"yaxis": ax, "xaxis": dict(showgrid=False)}))
    return fig


def strand_bars(rows: list[tuple[str, dict]], title: str | None = None) -> go.Figure:
    """100% stacked FinScope Access Strand. rows: (label, {fs_banked:…, …})."""
    labels = [r[0] for r in rows]
    fig = go.Figure()
    for key, name, color in STRAND:
        vals = [r[1].get(key) for r in rows]
        fig.add_trace(go.Bar(y=labels, x=vals, name=name, orientation="h", marker=dict(color=color, line=dict(color="white", width=2)),
                             hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.0f}}%<extra></extra>",
                             texttemplate="%{x:.0f}%", textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="white", size=11)))
    fig.update_layout(title=title, barmode="stack", height=_h(len(rows), 40, 110), bargap=0.32,
                      legend=dict(traceorder="normal"),
                      xaxis=dict(range=[0, 101], ticksuffix="%", showgrid=False),
                      yaxis=dict(autorange="reversed", showgrid=False), uniformtext=dict(minsize=10, mode="hide"))
    return fig


def dumbbell(labels: list[str], a: list[float], b: list[float], a_name: str, b_name: str, unit: str = "%",
             title: str | None = None, decimals: int = 1) -> go.Figure:
    fig = go.Figure()
    for lab, x0, x1 in zip(labels, a, b, strict=False):
        fig.add_trace(go.Scatter(x=[x0, x1], y=[lab, lab], mode="lines", line=dict(color=AXIS, width=2),
                                 hoverinfo="skip", showlegend=False))
    for name, vals, color in ((a_name, a, S2), (b_name, b, S1)):
        fig.add_trace(go.Scatter(x=vals, y=labels, mode="markers", name=name,
                                 marker=dict(color=color, size=11, line=dict(color="white", width=2)),
                                 hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.{decimals}f}}{unit if unit == '%' else ''}<extra></extra>"))
    fig.update_layout(title=title, height=_h(len(labels), 34), xaxis=dict(ticksuffix="%" if unit == "%" else ""),
                      yaxis=dict(autorange="reversed", showgrid=False))
    return fig


def line_chart(x: list, series: list[tuple[str, list, str]], x_title: str, y_suffix: str = "%",
               title: str | None = None, vline: float | None = None, vline_label: str | None = None) -> go.Figure:
    fig = go.Figure()
    for name, ys, color in series:
        fig.add_trace(go.Scatter(x=x, y=ys, name=name, mode="lines+markers", line=dict(color=color, width=2),
                                 marker=dict(size=8, color=color, line=dict(color="white", width=2)),
                                 hovertemplate=f"{x_title} %{{x}}<br>{name}: %{{y:.1f}}{y_suffix}<extra></extra>"))
    if vline is not None:
        fig.add_vline(x=vline, line=dict(color=INK, width=1, dash="dot"),
                      annotation=dict(text=vline_label or "", font=dict(size=11, color=INK)))
    fig.update_layout(title=title, height=360, hovermode="x unified", showlegend=len(series) > 1,
                      xaxis=dict(title=x_title, showgrid=False), yaxis=dict(ticksuffix=y_suffix, rangemode="tozero"))
    return fig


def heatmap(labels: list[str], matrix: list[list[float | None]], text: list[list[str]], title: str | None = None) -> go.Figure:
    scale = [[i / (len(DIVERGING) - 1), c] for i, c in enumerate(DIVERGING[::-1])]
    fig = go.Figure(go.Heatmap(z=matrix, x=labels, y=labels, zmin=-1, zmax=1, colorscale=scale, xgap=2, ygap=2,
                               text=text, hovertemplate="%{text}<extra></extra>",
                               colorbar=dict(title=dict(text="Spearman ρ", font=dict(size=11, color=MUTED)), thickness=10,
                                             outlinewidth=0, tickfont=dict(color=MUTED, size=11))))
    fig.update_layout(title=title, height=560, xaxis=dict(showgrid=False, tickangle=-35),
                      yaxis=dict(showgrid=False, autorange="reversed"))
    return fig


def scatter(x: list[float], y: list[float], labels: list[str], x_title: str, y_title: str,
            title: str | None = None) -> go.Figure:
    fig = go.Figure(go.Scatter(x=x, y=y, mode="markers", text=labels,
                               marker=dict(size=11, color=BRAND_500, line=dict(color="white", width=2)),
                               hovertemplate=f"<b>%{{text}}</b><br>{x_title}: %{{x:.1f}}<br>{y_title}: %{{y:.1f}}<extra></extra>"))
    fig.update_layout(title=title, height=420, xaxis=dict(title=x_title), yaxis=dict(title=y_title), showlegend=False)
    return fig


def stacked_share(categories: list[str], series: list[tuple[str, list[float | None], str]], title: str | None = None,
                  unit_suffix: str = "%") -> go.Figure:
    fig = go.Figure()
    for name, vals, color in series:
        fig.add_trace(go.Bar(y=categories, x=vals, name=name, orientation="h",
                             marker=dict(color=color, line=dict(color="white", width=2)),
                             hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.1f}}{unit_suffix}<extra></extra>"))
    fig.update_layout(title=title, barmode="stack", height=_h(len(categories), 36, 110), bargap=0.32,
                      xaxis=dict(ticksuffix=unit_suffix, showgrid=False), yaxis=dict(autorange="reversed", showgrid=False))
    return fig
