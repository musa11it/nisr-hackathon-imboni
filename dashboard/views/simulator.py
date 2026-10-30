from __future__ import annotations

import re
from html import escape

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from backend.app import reports, simulator

from .. import charts, data
from ..logic import allocation_status, compare_scenarios, equal_split, round_shares, scenario_row
from ..theme import BRAND_500, S1, S2, SERIES, STATUS
from ..ui import badge, callout, chart, guarded, hero, kpi_cards, section

CATALOGUE = {c["id"]: c for c in simulator.catalogue()}
MAX_SAVED = 6


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("sim_ids", [k for k, c in CATALOGUE.items() if c["default_share"] > 0])
    for k, c in CATALOGUE.items():
        ss.setdefault(f"share_{k}", float(c["default_share"]))
        ss.setdefault(f"cost_{k}", int(c["default_unit_cost"]))
    ss.setdefault("sim_saved", [])


def _set_shares(shares: dict[str, float]) -> None:
    for k, v in shares.items():
        st.session_state[f"share_{k}"] = float(v)


def _cb_equal() -> None:
    _set_shares(equal_split(st.session_state["sim_ids"]))


def _cb_need(level: str, gid: str) -> None:
    ids = st.session_state["sim_ids"]
    if ids:
        _set_shares(round_shares(simulator.suggest_need_weighted(data.store(), level, gid, ids)))


def _cb_defaults() -> None:
    for k, c in CATALOGUE.items():
        st.session_state[f"share_{k}"] = float(c["default_share"])
        st.session_state[f"cost_{k}"] = int(c["default_unit_cost"])
    st.session_state["sim_ids"] = [k for k, c in CATALOGUE.items() if c["default_share"] > 0]


def _geo_picker() -> tuple[str, str]:
    c1, c2 = st.columns([1, 2])
    with c1:
        level = st.radio("Target geography", ["national", "province", "district"], horizontal=True,
                         format_func=str.title, key="sim_level")
    with c2:
        if level == "national":
            st.selectbox("Area", ["rwanda"], format_func=lambda _: "Rwanda", disabled=True, key="sim_geo_nat")
            gid = "rwanda"
        else:
            opts = data.province_options() if level == "province" else data.district_options()
            gid = st.selectbox("Area", [g for g, _ in opts], format_func=lambda g: data.name_of(level, g),
                               key=f"sim_geo_{level}")
    return level, gid


def _meter(status: dict) -> None:
    total, state = status["total"], status["state"]
    color = {"complete": STATUS["good"], "under": STATUS["warning"], "over": STATUS["critical"]}[state]
    msg = {"complete": "Allocation complete — shares total 100%.",
           "under": f"{status['remaining']:.1f}% of the budget is unallocated.",
           "over": f"Shares exceed 100% by {-status['remaining']:.1f} points — reduce an allocation to run the scenario."}[state]
    icon = {"complete": "✓", "under": "!", "over": "✕"}[state]
    width = min(total, 100)
    st.markdown(f"""
<div style="margin:6px 0 14px">
  <div style="display:flex;justify-content:space-between;font-size:.85rem;font-weight:600;color:#0f1b2d">
    <span>{icon} Allocated {total:.1f}%</span><span style="color:#7b7f86">target 100%</span></div>
  <div style="height:8px;border-radius:999px;background:#ebe7de;margin-top:6px;overflow:hidden">
    <div style="width:{width}%;height:100%;background:{color};border-radius:999px"></div></div>
  <div style="font-size:.8rem;color:#4a4f58;margin-top:6px">{escape(msg)}</div>
</div>""", unsafe_allow_html=True)


@guarded
def render() -> None:
    _init_state()
    ss = st.session_state
    hero("Intervention Simulator", "What could a budget reach?",
         "Allocate a budget across interventions and see how many households it could pay for, capped by measured need "
         "in the chosen area. This is transparent budget arithmetic — it does not predict poverty reduction.",
         ["Need rates: EICV7 / FinScope", "Households: Census 2022", "Unit costs: your assumptions"])
    callout("caution", "Illustrative scenario only",
            "Default unit costs are placeholders chosen by the DataMinds team, not costed programme estimates. "
            "Reach is arithmetic (budget ÷ unit cost, capped by need) and is not a measured outcome or an impact estimate.")

    section("1 · Budget and geography")
    c1, c2 = st.columns([1, 1])
    with c1:
        name = st.text_input("Scenario name", value="Scenario A", max_chars=120, key="sim_name")
    with c2:
        budget_m = st.number_input("Total budget (million RWF)", min_value=1.0, max_value=10_000_000.0, value=5_000.0,
                                   step=100.0, key="sim_budget", help="Your assumption. 1,000 million RWF = 1 billion RWF.")
    budget = int(round(budget_m * 1_000_000))
    level, gid = _geo_picker()
    ctx = data.sim_context(level, gid)

    section("2 · Interventions and allocation", "Drag the sliders; amounts update immediately. Unit costs are editable.")
    st.multiselect("Interventions", list(CATALOGUE), key="sim_ids", format_func=lambda k: CATALOGUE[k]["label"])
    ids = ss["sim_ids"]
    b1, b2, b3, _ = st.columns([1, 1, 1, 1.4])
    b1.button("Equal split", on_click=_cb_equal, width="stretch", disabled=not ids)
    b2.button("Need-weighted split", on_click=_cb_need, args=(level, gid), width="stretch", disabled=not ids,
              help="Shares proportional to each intervention's measured need rate in this area — a transparent "
                   "default, not an optimisation.")
    b3.button("Reset defaults", on_click=_cb_defaults, width="stretch")
    if not ids:
        st.info("Select at least one intervention.")
        return

    shares = {}
    for k in ids:
        c = CATALOGUE[k]
        need = ctx["needs"][k]
        with st.container(border=True):
            a, b, cc = st.columns([2.3, 1.1, 1.2])
            with a:
                shares[k] = st.slider(c["label"], 0.0, 100.0, step=0.1, key=f"share_{k}", format="%.1f%%")
            with b:
                st.number_input("Unit cost (RWF / household)", min_value=1, max_value=1_000_000_000, step=5_000,
                                key=f"cost_{k}", help="Your assumption. Default: illustrative placeholder.")
            with cc:
                amt = budget * shares[k] / 100
                rate = need["rate_pct"]
                st.markdown(f"<div style='font-size:.78rem;color:#7b7f86'>Amount</div>"
                            f"<div style='font-family:Fraunces,serif;font-size:1.25rem;font-weight:600'>RWF {amt / 1e6:,.1f} M</div>"
                            f"<div style='font-size:.75rem;color:#4a4f58'>Need: {('%.1f%%' % rate) if rate is not None else 'n/a'}"
                            f"{' (from ' + escape(need['geo_used']) + ')' if need.get('fallback') and need.get('geo_used') else ''}</div>",
                            unsafe_allow_html=True)
            st.caption(c["need_label"] + (f" — {c['proxy_note']}" if c["proxy_note"] else ""))
    status = allocation_status(shares)
    _meter(status)
    if status["state"] == "over":
        return

    inp_raw = {"name": name or "Untitled scenario", "total_budget_rwf": budget,
               "geography": {"level": level, "geo_id": gid},
               "interventions": [{"id": k, "share_pct": round(shares[k], 1), "unit_cost_rwf": ss[f"cost_{k}"]} for k in ids]}
    try:
        inp = simulator.ScenarioInput.model_validate(inp_raw)
    except ValidationError as exc:
        st.error("Scenario inputs are invalid: " + "; ".join(e["msg"] for e in exc.errors()))
        return
    res = simulator.run_scenario(data.store(), inp)
    sm = res["summary"]

    section("3 · Estimated reach", f"{res['context']['name']} — {res['context']['households']:,.0f} private households "
                                   f"(Census 2022), mean size {res['context']['household_size']:.1f}.")
    kpi_cards([
        {"label": "Allocated", "value": f"{sm['allocated_rwf'] / 1e6:,.1f}", "unit": " M RWF",
         "sub": f"Unallocated RWF {sm['unallocated_rwf'] / 1e6:,.1f} M", "status": "assumption", "accent": S2},
        {"label": "Household-interventions", "value": f"{sm['household_interventions']:,}",
         "sub": f"Unique households ≥ {sm['max_unique_households_bound']:,} (overlap unknown)", "status": "illustrative",
         "help": res["labels"]["reach_definition"], "accent": S1},
        {"label": "People in reached households", "value": f"{sm['people_reached_est_sum']:,}",
         "sub": "Sum across lines × mean household size", "status": "illustrative", "accent": S1},
        {"label": "Funds exceeding need", "value": f"{sm['idle_rwf'] / 1e6:,.1f}", "unit": " M RWF",
         "sub": "Money not needed at these unit costs", "status": "illustrative", "accent": BRAND_500},
    ])
    lines = res["lines"]
    a, b = st.columns([1.15, 1], gap="large")
    with a:
        cov = [{"geo_id": l["id"], "geo_name": l["label"], "value": l["coverage_of_need_pct"] or 0} for l in lines]
        fig = charts.ranked_bars(cov, title="Coverage of measured need (%)", worse_high=True)
        fig.update_layout(xaxis=dict(range=[0, 105]))
        chart(fig, key="sim_cov")
    with b:
        mult = [s["multiplier"] for s in lines[0]["sensitivity"]]
        series = [(l["label"], [s["households_reached"] for s in l["sensitivity"]], SERIES[i])
                  for i, l in enumerate(lines[:4])]
        chart(charts.line_chart(mult, series, "Unit-cost multiplier", y_suffix="", vline=1.0, vline_label="your cost",
                                title="Sensitivity: households reached vs unit cost"), key="sim_sens")
        if len(lines) > 4:
            st.caption("Sensitivity chart shows the first four lines (fixed colours); all lines are in the table.")
    df = pd.DataFrame([{
        "Intervention": l["label"], "Share %": l["share_pct"], "Amount (RWF)": l["amount_rwf"],
        "Unit cost (RWF)": l["unit_cost_rwf"], "Need rate %": l["need_rate_pct"],
        "Need measured at": l["need_basis"].get("geo_used"), "Eligible households": l["eligible_households"],
        "Households reached": l["households_reached"], "Coverage of need %": l["coverage_of_need_pct"],
        "Idle (RWF)": l["amount_idle_rwf"], "Default cost?": l["unit_cost_is_default"]} for l in lines])
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="localized") for c in
                                ("Amount (RWF)", "Unit cost (RWF)", "Eligible households", "Households reached", "Idle (RWF)")} |
                               {c: st.column_config.NumberColumn(format="%.1f") for c in ("Need rate %", "Coverage of need %")})
    st.markdown(f"{badge('assumption')} budget, shares, unit costs &nbsp; {badge('official')} need rates & households "
                f"&nbsp; {badge('illustrative')} reach, coverage, idle funds", unsafe_allow_html=True)
    st.caption(res["labels"]["not_measured"] + " Reconciles to the franc: " + ("yes" if sm["reconciles"] else "NO"))

    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", res["name"])[:40] or "scenario"
    e1, e2, e3 = st.columns(3)
    e1.download_button("Download scenario CSV", reports.scenario_csv(res).encode("utf-8"), f"imboni_{safe}.csv",
                       "text/csv", width="stretch")
    srcs = [data.store().source_index[x] for x in ("rphc5_main", "eicv7_mi", "eicv7_mpi", "finscope_2024", "eicv7_vup")]
    try:
        pdf = reports.scenario_pdf(res, srcs)
        e2.download_button("Download scenario PDF", pdf, f"imboni_{safe}.pdf", "application/pdf", width="stretch")
    except Exception:  # noqa: BLE001 — PDF is optional; CSV always works
        e2.caption("PDF export unavailable in this environment.")
    if e3.button("Save for comparison", width="stretch", disabled=len(ss["sim_saved"]) >= MAX_SAVED):
        ss["sim_saved"] = [r for r in ss["sim_saved"] if r["name"] != res["name"]] + [res]
        st.toast(f"Saved “{res['name']}”. Rename the scenario to save another.")

    saved = ss["sim_saved"]
    section("4 · Compare scenarios", f"Saved in this browser session only (max {MAX_SAVED}); nothing is stored on a server.")
    if not saved:
        st.caption("Save at least one scenario to compare. Tip: save, change the allocation or geography, rename, save again.")
        return
    summary = pd.DataFrame([scenario_row(r) for r in saved])
    st.dataframe(summary, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="localized") for c in summary.columns
                                if c not in ("scenario", "geography")})
    long = compare_scenarios(saved)
    labels = sorted(long["intervention"].unique())
    series = []
    for i, r in enumerate(saved[:4]):
        sub = long[long["scenario"] == r["name"]].set_index("intervention")
        series.append((r["name"], [float(sub["households_reached"].get(l, 0) or 0) for l in labels], SERIES[i]))
    chart(charts.grouped_bars(labels, series, unit="", horizontal=True, decimals=0,
                              title="Households reached by intervention"), key="sim_compare")
    if len(saved) > 4:
        st.caption("Chart shows the first four saved scenarios; the table includes all.")
    c1, c2 = st.columns([1, 1])
    c1.download_button("Download comparison CSV", long.to_csv(index=False).encode("utf-8"), "imboni_scenario_comparison.csv",
                       "text/csv", width="stretch")
    if c2.button("Clear saved scenarios", width="stretch"):
        ss["sim_saved"] = []
        st.rerun()
