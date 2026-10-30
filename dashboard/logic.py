"""Pure helpers behind the dashboard (no Streamlit import, so they are unit-tested directly)."""
from __future__ import annotations


import pandas as pd

TOLERANCE = 0.05  # percentage points


def allocation_status(shares: dict[str, float]) -> dict:
    total = round(sum(shares.values()), 4)
    if abs(total - 100) <= TOLERANCE:
        state = "complete"
    elif total < 100:
        state = "under"
    else:
        state = "over"
    return {"total": total, "remaining": round(100 - total, 4), "state": state}


def _fix_drift(shares: dict[str, float], decimals: int) -> dict[str, float]:
    drift = round(100 - sum(shares.values()), decimals)
    if shares and drift:
        k = max(shares, key=shares.get)
        shares[k] = round(shares[k] + drift, decimals)
    return shares


def equal_split(ids: list[str], decimals: int = 1) -> dict[str, float]:
    """Equal shares in steps of 10^-decimals; leftover steps go one each to the first lines, so shares differ by at
    most one step and total exactly 100."""
    if not ids:
        return {}
    units = 100 * 10 ** decimals
    base, extra = divmod(units, len(ids))
    return {i: (base + (1 if n < extra else 0)) / 10 ** decimals for n, i in enumerate(ids)}


def round_shares(shares: dict[str, float], decimals: int = 1) -> dict[str, float]:
    """Round to slider precision while keeping the total at exactly 100 when the input totals 100."""
    out = {k: round(v, decimals) for k, v in shares.items()}
    if abs(sum(shares.values()) - 100) <= TOLERANCE:
        out = _fix_drift(out, decimals)
    return out


def scenario_row(result: dict) -> dict:
    s = result["summary"]
    return {"scenario": result["name"], "geography": result["context"]["name"],
            "budget_rwf": s["total_budget_rwf"], "allocated_rwf": s["allocated_rwf"],
            "unallocated_rwf": s["unallocated_rwf"], "household_interventions": s["household_interventions"],
            "people_reached_est_sum": s["people_reached_est_sum"], "idle_rwf": s["idle_rwf"],
            "unique_households_lower_bound": s["max_unique_households_bound"]}


def compare_scenarios(results: list[dict]) -> pd.DataFrame:
    """Long table: one row per scenario × intervention line."""
    rows = []
    for r in results:
        for line in r["lines"]:
            rows.append({"scenario": r["name"], "geography": r["context"]["name"], "intervention": line["label"],
                         "share_pct": line["share_pct"], "amount_rwf": line["amount_rwf"],
                         "unit_cost_rwf": line["unit_cost_rwf"], "eligible_households": line["eligible_households"],
                         "households_reached": line["households_reached"],
                         "coverage_of_need_pct": line["coverage_of_need_pct"],
                         "amount_idle_rwf": line["amount_idle_rwf"]})
    return pd.DataFrame(rows)


def filter_observations(df: pd.DataFrame, themes: list[str] | None = None, indicators: list[str] | None = None,
                        levels: list[str] | None = None, statuses: list[str] | None = None,
                        geo_text: str | None = None, only_with_values: bool = False) -> pd.DataFrame:
    out = df
    if themes:
        out = out[out["theme"].isin(themes)]
    if indicators:
        out = out[out["indicator_id"].isin(indicators)]
    if levels:
        out = out[out["level"].isin(levels)]
    if statuses:
        out = out[out["status"].isin(statuses)]
    if geo_text:
        out = out[out["geo_name"].str.contains(geo_text, case=False, na=False, regex=False)]
    if only_with_values:
        out = out[out["value"].notna()]
    return out


def correlation_matrix(pairs: list[dict], keys: list[str]) -> tuple[list[list[float | None]], list[list[dict | None]]]:
    idx = {k: i for i, k in enumerate(keys)}
    n = len(keys)
    mat: list[list[float | None]] = [[1.0 if i == j else None for j in range(n)] for i in range(n)]
    info: list[list[dict | None]] = [[None] * n for _ in range(n)]
    for p in pairs:
        if p["a"] in idx and p["b"] in idx:
            i, j = idx[p["a"]], idx[p["b"]]
            mat[i][j] = mat[j][i] = p["rho"]
            info[i][j] = info[j][i] = p
    return mat, info
