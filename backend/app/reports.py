"""PDF and CSV exports generated server-side (works identically on any deployment)."""
from __future__ import annotations

import csv
import datetime as dt
import io

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

INK = colors.HexColor("#0f1b2d")
TEAL = colors.HexColor("#0f766e")
TEAL_LIGHT = colors.HexColor("#99d5cf")
MUTED = colors.HexColor("#5b6472")
RULE = colors.HexColor("#d9dee5")
DISCLAIMER = ("Imboni is a student project by team DataMinds for the NISR 2026 Big Data Hackathon. It is not an official "
              "NISR publication and is not endorsed by NISR. All statistics are reproduced from the cited official "
              "publications; calculated values are labelled.")


def _styles():
    ss = getSampleStyleSheet()
    base = dict(fontName="Helvetica", textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24,
                                textColor=INK, alignment=TA_LEFT, spaceAfter=4),
        "sub": ParagraphStyle("s", fontSize=10, leading=13, textColor=MUTED, **{k: v for k, v in base.items() if k != "textColor"}),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("b", fontSize=9.5, leading=13, **base),
        "small": ParagraphStyle("sm", fontSize=8, leading=10.5, textColor=MUTED,
                                **{k: v for k, v in base.items() if k != "textColor"}),
        "cell": ParagraphStyle("c", fontSize=8, leading=10, **base),
    }


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL)]
    t.setStyle(TableStyle(style))
    return t


def _bar(labels, values, ref=None, ref_label="National", unit="%", width=170 * mm, title=None):
    n = len(labels)
    h = max(60, 16 * n + 30)
    d = Drawing(width, h)
    bc = HorizontalBarChart()
    bc.x, bc.y, bc.width, bc.height = 150, 18, width - 190, h - 30
    bc.data = [[v or 0 for v in values]]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.boxAnchor = "e"
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max([v or 0 for v in values] + [ref or 0]) * 1.15 or 1
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.strokeColor = RULE
    bc.bars[0].fillColor = TEAL
    bc.bars[0].strokeColor = None
    bc.barWidth = 8
    d.add(bc)
    if title:
        d.add(String(0, h - 10, title, fontName="Helvetica-Bold", fontSize=8, fillColor=INK))
    return d


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 10 * mm, "Imboni — DataMinds · Student project, not an official NISR publication")
    canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _fmt(v, d=1, unit="%"):
    if v is None:
        return "—"
    if unit.startswith("index (0–1)"):
        return f"{v:.3f}"
    if unit in {"households", "RWF"}:
        return f"{v:,.0f}"
    return f"{v:,.{d}f}"


def area_report_pdf(profile: dict, sources: list[dict]) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                            bottomMargin=18 * mm, title=f"Imboni area profile — {profile['name']}", author="DataMinds")
    el = [Paragraph("IMBONI · DATA-TO-ACTION BRIEF", st["small"]),
          Paragraph(f"{profile['name']}: poverty &amp; financial-inclusion profile", st["title"]),
          Paragraph(f"Geography: {profile['level'].title()}"
                    + (f" (in {profile['province_name']})" if profile.get("province_name") else "")
                    + f" · Reference period: EICV7 2023/24, FinScope 2024, Census 2022 · Generated "
                    f"{dt.date.today().isoformat()}", st["sub"]),
          Spacer(1, 4), Paragraph(DISCLAIMER, st["small"]), Spacer(1, 6)]

    el.append(Paragraph("Key indicators", st["h2"]))
    rows = [["Indicator", "Value", "95% CI", "National", "Rank", "Status", "Source"]]
    for e in profile["indicators"]:
        ci = f"{e['ci_low']:.1f}–{e['ci_high']:.1f}" if e.get("ci_low") is not None else "—"
        rank = f"{e['rank']}/{e['n_peers']}" if e.get("rank") and e.get("n_peers") else "—"
        rows.append([Paragraph(e["name"], st["cell"]), _fmt(e["value"], e["decimals"], e["unit"]), ci,
                     _fmt(e.get("national"), e["decimals"], e["unit"]), rank, e["status"].replace("_", " "),
                     Paragraph(f"{e['source']['short']} {e['table_ref']}", st["cell"])])
    el.append(_table(rows, [52 * mm, 16 * mm, 20 * mm, 16 * mm, 12 * mm, 24 * mm, 40 * mm]))
    el.append(Paragraph("Rank 1 = most deprived among peers. CI = 95% confidence interval published by NISR.", st["small"]))

    if profile["fingerprint"]:
        el.append(Paragraph("Deprivation fingerprint", st["h2"]))
        fp = profile["fingerprint"]
        el.append(_bar([f["label"] for f in fp], [f["value"] for f in fp], title=f"Share lacking each service (%) — {profile['name']}"))
        rows = [["Deprivation", profile["name"], "Province" if profile["level"] == "district" else "", "National"]]
        for f in fp:
            rows.append([f["label"], _fmt(f["value"]), _fmt(f.get("province")) if profile["level"] == "district" else "",
                         _fmt(f["national"])])
        el.append(_table(rows, [70 * mm, 30 * mm, 30 * mm, 30 * mm]))

    if profile.get("findings"):
        el.append(Paragraph("Findings", st["h2"]))
        for f in profile["findings"][:10]:
            el.append(Paragraph(("<b>Concern:</b> " if f["kind"] == "concern" else "<b>Strength:</b> ") + f["text"], st["body"]))

    mpi = profile.get("mpi")
    if mpi and mpi.get("incidence"):
        block = [Paragraph(f"Multidimensional poverty — {mpi['geo_name']}", st["h2"])]
        if mpi.get("note"):
            block.append(Paragraph(mpi["note"], st["small"]))
        block.append(Paragraph(
            f"Incidence H = {_fmt(mpi['incidence']['value'])}%, intensity A = {_fmt(mpi['intensity']['value'])}%, "
            f"MPI M0 = {mpi['mpi']['value']:.3f} (Alkire–Foster, k = 33.3%).", st["body"]))
        ch = sorted(mpi["censored_headcounts"], key=lambda c: -(c["censored_headcount"] or 0))
        block.append(_bar([c["label"] for c in ch], [c["censored_headcount"] for c in ch],
                          title="Censored headcount ratio (%) — MPI-poor and deprived"))
        el.append(KeepTogether(block))

    el.append(Paragraph("Methodology", st["h2"]))
    for t in [
        "Values are reproduced from official NISR tables by an automated, validated pipeline (raw files kept unchanged, "
        "checksummed). Comparisons with the national estimate use an approximate z-test with published standard errors.",
        "Monetary poverty (consumption below the national poverty line) and MPI incidence (deprived in at least 1/3 of weighted "
        "indicators) are different concepts and are not interchangeable.",
        "FinScope values (adults 16+) are transcribed from published figure labels; EICV7 values refer to households or "
        "population as stated.",
    ]:
        el.append(Paragraph(t, st["body"]))
    el.append(Paragraph("Limitations &amp; uncertainty", st["h2"]))
    for t in [
        "District estimates have wider confidence intervals than national ones; ranks between neighbouring districts are often not statistically distinguishable.",
        "No district-level MPI is published; district profiles show the parent province's MPI for context only.",
        "Associations between indicators are descriptive and must not be read as causal effects.",
    ]:
        el.append(Paragraph("• " + t, st["body"]))
    el.append(Paragraph("Sources", st["h2"]))
    for s in sources:
        el.append(Paragraph(f"{s.get('citation') or s['title']} <font color='#5b6472'>{s['url']}</font>", st["small"]))
    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def scenario_pdf(result: dict, sources: list[dict]) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                            bottomMargin=18 * mm, title=f"Imboni scenario — {result['name']}", author="DataMinds")
    ctx, s = result["context"], result["summary"]
    el = [Paragraph("IMBONI · ILLUSTRATIVE BUDGET SCENARIO", st["small"]),
          Paragraph(result["name"], st["title"]),
          Paragraph(f"Target: {ctx['name']} ({ctx['level']}) · {ctx['households']:,.0f} households (Census 2022) · "
                    f"Generated {dt.date.today().isoformat()}", st["sub"]),
          Spacer(1, 4), Paragraph(DISCLAIMER, st["small"]),
          Paragraph("<b>Illustrative only.</b> " + result["labels"]["not_measured"] + " " + result["labels"]["unit_costs"], st["small"]),
          Paragraph("Budget reconciliation", st["h2"])]
    el.append(_table([["Total budget (RWF)", "Allocated", "Unallocated", "Allocated %", "Reconciles"],
                      [f"{s['total_budget_rwf']:,}", f"{s['allocated_rwf']:,}", f"{s['unallocated_rwf']:,}",
                       f"{s['allocated_pct']:.2f}%", "Yes" if s["reconciles"] else "NO"]],
                     [38 * mm, 36 * mm, 36 * mm, 30 * mm, 30 * mm]))
    el.append(Paragraph("Allocation and estimated reach", st["h2"]))
    rows = [["Intervention", "Share", "Amount (RWF)", "Unit cost", "Eligible HH", "HH reached", "Coverage", "People (est.)"]]
    for l in result["lines"]:
        rows.append([Paragraph(l["label"], st["cell"]), f"{l['share_pct']:.1f}%", f"{l['amount_rwf']:,}",
                     f"{l['unit_cost_rwf']:,.0f}", _fmt(l["eligible_households"], unit="households"),
                     f"{l['households_reached']:,}",
                     "—" if l["coverage_of_need_pct"] is None else f"{l['coverage_of_need_pct']:.1f}%",
                     _fmt(l["people_reached_est"], unit="households")])
    el.append(_table(rows, [40 * mm, 14 * mm, 26 * mm, 20 * mm, 22 * mm, 20 * mm, 18 * mm, 20 * mm]))
    el.append(Paragraph(result["labels"]["reach_definition"], st["small"]))
    el.append(_bar([l["label"] for l in result["lines"]], [l["coverage_of_need_pct"] or 0 for l in result["lines"]],
                   title="Estimated coverage of need (%)"))
    el.append(Paragraph("Sensitivity to unit costs (households reached)", st["h2"]))
    mults = [x["multiplier"] for x in result["lines"][0]["sensitivity"]]
    rows = [["Intervention"] + [f"×{m:g}" for m in mults]]
    for l in result["lines"]:
        rows.append([Paragraph(l["label"], st["cell"])] + [f"{x['households_reached']:,}" for x in l["sensitivity"]])
    el.append(_table(rows, [50 * mm] + [26 * mm] * len(mults)))
    el.append(Paragraph("Need basis & assumptions", st["h2"]))
    for l in result["lines"]:
        nb = l["need_basis"]
        txt = (f"<b>{l['label']}</b>: {l['need_label']}. Need rate {_fmt(l['need_rate_pct'])}% measured at "
               f"{nb.get('geo_used')} ({nb.get('level_used')})" + (" — finer level not published, coarser level applied." if nb.get("fallback") else ".")
               + (f" {l['proxy_note']}" if l.get("proxy_note") else "")
               + (" Unit cost is the illustrative default." if l["unit_cost_is_default"] else " Unit cost entered by user."))
        el.append(Paragraph(txt, st["body"]))
    el.append(Paragraph("Sources", st["h2"]))
    for src in sources:
        el.append(Paragraph(f"{src.get('citation') or src['title']} <font color='#5b6472'>{src['url']}</font>", st["small"]))
    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def to_csv(rows: list[dict], columns: list[str] | None = None, preamble: list[str] | None = None) -> str:
    buf = io.StringIO()
    for line in preamble or []:
        buf.write(f"# {line}\n")
    cols = columns or (list(rows[0].keys()) if rows else [])
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in r.items() if k in cols})
    return buf.getvalue()


def scenario_csv(result: dict) -> str:
    rows = []
    for l in result["lines"]:
        rows.append({"scenario": result["name"], "geography": result["context"]["name"], "intervention": l["label"],
                     "share_pct": l["share_pct"], "amount_rwf": l["amount_rwf"], "unit_cost_rwf": l["unit_cost_rwf"],
                     "need_rate_pct": l["need_rate_pct"], "need_measured_at": l["need_basis"].get("geo_used"),
                     "eligible_households": l["eligible_households"], "households_reached": l["households_reached"],
                     "coverage_of_need_pct": l["coverage_of_need_pct"], "people_reached_est": l["people_reached_est"],
                     "amount_idle_rwf": l["amount_idle_rwf"], "unit_cost_is_illustrative_default": l["unit_cost_is_default"]})
    s = result["summary"]
    pre = ["Imboni (DataMinds) — ILLUSTRATIVE budget scenario. Not an official NISR product.",
           f"Total budget RWF {s['total_budget_rwf']:,}; allocated {s['allocated_rwf']:,}; unallocated {s['unallocated_rwf']:,}",
           result["labels"]["not_measured"], result["labels"]["reach_definition"]]
    return to_csv(rows, preamble=pre)
