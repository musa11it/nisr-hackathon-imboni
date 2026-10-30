from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from .. import data
from ..ui import badge, callout, fmt, guarded, hero


def _stat(v, unit: str) -> str:
    if unit == "%":
        return f"{fmt(v)}%"
    if unit == "pp":
        return f"{v:+.1f} pp"
    if unit == "×":
        return f"{v:.1f}×"
    if isinstance(v, float) and abs(v) < 1:
        return f"{v:.2f}"
    return fmt(v, None, 0) + (f" {unit}" if unit else "")


def to_markdown(items: list[dict]) -> str:
    out = ["# Imboni — evidence-backed policy insights", "",
           "Generated from validated NISR/FinScope/Census aggregates. Not an official NISR publication.", ""]
    for i in items:
        out += [f"## {i['title']}", "", f"**Finding.** {i['finding']}", "", "**Supporting statistics**", ""]
        out += [f"- {s['label']}: {_stat(s['value'], s['unit'])} ({s['status']})" for s in i["statistics"]]
        out += ["", "**Sources:** " + "; ".join(f"{s['title']} — {s['table']} ({s.get('landing_page') or s.get('url')})"
                                                 for s in i["sources"]),
                f"**Geographic scope:** {i['scope']}", "", f"**{i['implication_label']}.** {i['implication']}", "",
                "**Limitations**", ""] + [f"- {l}" for l in i["limitations"]] + [""]
    return "\n".join(out)


@guarded
def render() -> None:
    res = data.policy_insights()
    items = res["insights"]
    hero("Decide · Policy Insights", "What the evidence supports",
         "Findings recomputed from validated tables, each with its statistics, source and limits.",
         ["Recomputed live from processed data", "Implications are the team's interpretation"],
         stats=[(str(len(items)), "", "evidence-backed insights"),
                (str(len({i['theme'] for i in items})), "", "themes"),
                (str(len({s['id'] for i in items for s in i['sources']})), "", "official sources cited")],
         accent="evidence")
    themes = sorted({i["theme"] for i in items})
    pick = st.pills("Theme", themes, selection_mode="multi", default=themes)
    shown = [i for i in items if i["theme"] in (pick or themes)]
    for i in shown:
        chips = "".join(f'<div class="im-chip"><div class="v">{escape(_stat(s["value"], s["unit"]))}</div>'
                        f'<div class="l">{escape(s["label"])} {badge(s["status"])}</div></div>' for s in i["statistics"])
        srcs = " · ".join(f'<a href="{escape(s.get("landing_page") or s.get("url") or "")}" target="_blank">'
                          f'{escape(s.get("short") or s.get("title") or "")}</a> — {escape(s["table"])}' for s in i["sources"])
        lims = "".join(f"<li>{escape(l)}</li>" for l in i["limitations"])
        st.markdown(f"""
<div class="im-card"><div class="theme">{escape(i['theme'])}</div><h4>{escape(i['title'])}</h4>
<div class="finding">{escape(i['finding'])}</div>
<div class="im-chips">{chips}</div>
<div class="im-kv">
 <div class="k">Potential implication</div><div class="v">{escape(i['implication'])} <span class="im-badge experimental" title="{escape(i['implication_label'])}">interpretation</span></div>
</div>
<details class="im-note" style="margin:12px 0 0"><summary>Evidence trail — source, scope and limitations</summary><div class="b">
<div class="im-kv" style="margin-top:0">
 <div class="k">Source</div><div class="v im-source" style="margin:0">{srcs}</div>
 <div class="k">Geographic scope</div><div class="v">{escape(i['scope'])}</div>
 <div class="k">Limitations</div><div class="v"><ul style="margin:0;padding-left:18px">{lims}</ul></div>
</div></div></details></div>""", unsafe_allow_html=True)
    if res["skipped"]:
        callout("gap", "Insights not shown", "These could not be computed from the available data and were skipped rather "
                "than approximated: " + ", ".join(f"{s['id']} ({s['reason']})" for s in res["skipped"]))
    st.caption(res["method"])
    c1, c2 = st.columns(2)
    c1.download_button("Download insights (Markdown)", to_markdown(shown).encode("utf-8"), "imboni_policy_insights.md",
                       "text/markdown", width="stretch")
    flat = pd.DataFrame([{"insight": i["title"], "statistic": s["label"], "value": s["value"], "unit": s["unit"],
                          "status": s["status"], "scope": i["scope"],
                          "sources": "; ".join(f"{x['short']} {x['table']}" for x in i["sources"])}
                         for i in shown for s in i["statistics"]])
    c2.download_button("Download supporting statistics (CSV)", flat.to_csv(index=False).encode("utf-8"),
                       "imboni_insight_statistics.csv", "text/csv", width="stretch")
