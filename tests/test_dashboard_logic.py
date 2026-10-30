"""Pure dashboard logic, insights, data-quality and pipeline-preflight behaviour."""
import copy

import pandas as pd
import pytest

from backend.app import insights, reports, simulator
from backend.pipeline import build, inventory
from backend.pipeline.quality import missingness_summary
from backend.pipeline.validate import validate
from dashboard.logic import (allocation_status, compare_scenarios, correlation_matrix, equal_split,
                             filter_observations, round_shares, scenario_row)


# ---------------------------------------------------------------- allocation helpers
@pytest.mark.parametrize("n", [1, 2, 3, 6, 7, 8])
def test_equal_split_totals_exactly_100(n):
    shares = equal_split([f"i{k}" for k in range(n)])
    assert len(shares) == n
    assert round(sum(shares.values()), 6) == 100
    assert max(shares.values()) - min(shares.values()) <= 0.2


def test_allocation_status_states():
    assert allocation_status({"a": 60, "b": 40})["state"] == "complete"
    under = allocation_status({"a": 60, "b": 30})
    assert under["state"] == "under" and under["remaining"] == 10
    assert allocation_status({"a": 60, "b": 45})["state"] == "over"
    assert allocation_status({"a": 33.3, "b": 33.3, "c": 33.4})["state"] == "complete"


def test_round_shares_preserves_100(store):
    ids = list(simulator.INTERVENTIONS)
    raw = simulator.suggest_need_weighted(store, "district", "nyamagabe", ids)
    rounded = round_shares(raw)
    assert round(sum(rounded.values()), 6) == 100
    assert all(abs(rounded[k] - raw[k]) < 0.2 for k in ids)


def test_round_shares_does_not_inflate_partial_allocations():
    assert round(sum(round_shares({"a": 20.04, "b": 30.03}).values()), 6) == 50.0


def _scenario(store, name, shares):
    inp = simulator.ScenarioInput(name=name, total_budget_rwf=2_000_000_000,
                                  interventions=[{"id": k, "share_pct": v, "unit_cost_rwf": simulator.INTERVENTIONS[k]["default_unit_cost"]}
                                                 for k, v in shares.items()])
    return simulator.run_scenario(store, inp)


def test_scenario_comparison_tables(store):
    a = _scenario(store, "A", {"housing": 50, "water": 50})
    b = _scenario(store, "B", {"housing": 20, "water": 30, "cooking": 50})
    long = compare_scenarios([a, b])
    assert set(long["scenario"]) == {"A", "B"} and len(long) == 5
    assert long.groupby("scenario")["amount_rwf"].sum().to_dict() == {"A": 2_000_000_000, "B": 2_000_000_000}
    row = scenario_row(b)
    assert row["allocated_rwf"] == 2_000_000_000 and row["unallocated_rwf"] == 0
    assert row["household_interventions"] == sum(l["households_reached"] for l in b["lines"])


def test_scenario_reach_never_exceeds_measured_need(store):
    r = _scenario(store, "Huge", {"water": 100})
    line = r["lines"][0]
    assert line["households_reached"] <= line["eligible_households"]
    assert line["amount_used_rwf"] + line["amount_idle_rwf"] == line["amount_rwf"]


def test_over_allocation_is_rejected():
    with pytest.raises(ValueError):
        simulator.ScenarioInput(total_budget_rwf=1_000, interventions=[{"id": "water", "share_pct": 70, "unit_cost_rwf": 10},
                                                                      {"id": "housing", "share_pct": 40, "unit_cost_rwf": 10}])


# ---------------------------------------------------------------- explorer helpers
def test_filter_observations():
    df = pd.DataFrame([
        {"indicator_id": "poverty_rate", "theme": "monetary_poverty", "level": "district", "geo_name": "Nyamagabe", "status": "official", "value": 51.4},
        {"indicator_id": "fs_banked", "theme": "financial_inclusion", "level": "district", "geo_name": "Gasabo", "status": "official_transcribed", "value": None},
        {"indicator_id": "poverty_rate", "theme": "monetary_poverty", "level": "national", "geo_name": "Rwanda", "status": "official", "value": 27.4},
    ])
    assert len(filter_observations(df, themes=["monetary_poverty"])) == 2
    assert len(filter_observations(df, levels=["district"], geo_text="nyama")) == 1
    assert len(filter_observations(df, only_with_values=True)) == 2
    assert len(filter_observations(df, geo_text="(")) == 0  # literal match, not regex


def test_correlation_matrix_is_symmetric():
    pairs = [{"a": "x", "b": "y", "rho": 0.5}, {"a": "y", "b": "z", "rho": -0.2}]
    mat, info = correlation_matrix(pairs, ["x", "y", "z"])
    assert mat[0][1] == mat[1][0] == 0.5 and mat[2][1] == -0.2 and mat[0][2] is None
    assert all(mat[i][i] == 1.0 for i in range(3))


# ---------------------------------------------------------------- insights
def test_insights_are_complete_and_sourced(store):
    res = insights.policy_insights(store)
    assert res["skipped"] == []
    assert len(res["insights"]) >= 8
    for i in res["insights"]:
        assert i["finding"] and i["scope"] and i["implication"] and i["limitations"]
        assert i["sources"] and all(s["url"] and s["table"] for s in i["sources"])
        assert all(s["value"] is not None for s in i["statistics"])
        assert i["implication_label"].startswith("Potential implication")


def test_insight_statistics_match_store(store):
    by_id = {i["id"]: i for i in insights.policy_insights(store)["insights"]}
    lenses = {s["label"]: s["value"] for s in by_id["two_lenses"]["statistics"]}
    assert lenses["MPI incidence (H)"] == store.value("mpi_incidence", "national", "rwanda")
    assert lenses["Poor on both measures"] == store.value("mpi_monetary_overlap", "national", "rwanda", "mpi_poor__monetary_poor")


def test_insights_skip_rather_than_approximate_when_data_missing(store):
    partial = copy.copy(store)
    partial._by_ind = {k: v for k, v in store._by_ind.items() if not k.startswith("fs_")}
    res = insights.policy_insights(partial)
    ids = {i["id"] for i in res["insights"]}
    assert "financial_strand" not in ids and "banked_association" not in ids
    assert {s["id"] for s in res["skipped"]} >= {"financial_strand"}


# ---------------------------------------------------------------- data quality & pipeline preflight
def test_missingness_summary():
    obs = [{"indicator_id": "a", "level": "district", "value": 1.0, "se": 0.1, "status": "official", "flags": ""},
           {"indicator_id": "a", "level": "district", "value": None, "se": None, "status": "official",
            "flags": "suppressed_or_no_observations_in_source"},
           {"indicator_id": "a", "level": "district", "value": 3.0, "se": 0.9, "status": "official", "flags": "cv_gt_30_unreliable"}]
    (row,) = missingness_summary(obs)
    assert row["n_missing"] == 1 and row["pct_missing"] == 33.3 and row["n_with_se"] == 2
    assert row["missing_reasons"] == "suppressed_or_no_observations_in_source" and row["n_cv_gt_30"] == 1


def test_processed_quality_summary_has_every_indicator(store):
    rows = missingness_summary(store.observations)
    assert {r["indicator_id"] for r in rows} == {o["indicator_id"] for o in store.observations}
    assert sum(r["n_observations"] for r in rows) == len(store.observations)


def test_inventory_roles():
    roles = {s["id"]: inventory.role(s) for s in inventory.SOURCES}
    assert roles["eicv7_mi"] == "required" and roles["finscope_2024"] == "optional"
    assert roles["eicv7_microdata"] == "restricted" and roles["eicv7_vup_microdata"] == "restricted"
    assert roles["eicv7_mi_pdf"] == "reference"


def _fake_inventory(missing_ids):
    return [{"source_id": s["id"], "present": s["id"] not in missing_ids, "action": "download"} for s in inventory.SOURCES]


@pytest.mark.parametrize("missing_ids,optional_only", [({"finscope_2024"}, True), ({"eicv7_mi"}, False)])
def test_build_stops_before_writing_when_sources_missing(monkeypatch, missing_ids, optional_only):
    monkeypatch.setattr(build, "inventory", lambda: _fake_inventory(missing_ids))
    monkeypatch.setattr(build, "write_inventory", lambda rows: None)
    monkeypatch.setattr(build, "fetch_all", lambda *a, **k: pytest.fail("must not download"))
    monkeypatch.setattr(build, "parse_main_indicators", lambda p: pytest.fail("must not parse"))
    with pytest.raises(build.MissingSourcesError) as exc:
        build.run(fetch=False)
    assert exc.value.optional_only is optional_only
    assert {g["source_id"] for g in exc.value.gaps} == missing_ids


def test_partial_validation_downgrades_missing_source_to_warning(store):
    obs = [o for o in store.observations if not o["indicator_id"].startswith("fs_")]
    full = validate(obs, [])
    partial = validate(obs, [], missing_sources={"finscope_2024"})
    assert full["summary"]["errors"] > 0  # FinScope coverage checks fail if the gap is not declared
    assert partial["summary"]["errors"] == 0
    assert any(c["check"] == "source_available:finscope_2024" and c["severity"] == "warning" for c in partial["checks"])


def test_profile_csv_export(store):
    from backend.app import analytics
    csv_text = reports.profile_csv(analytics.profile(store, "district", "gasabo"))
    assert csv_text.startswith("# Imboni area profile: Gasabo (district)")
    assert "poverty_rate" in csv_text and "EICV7 Main Indicators tables" in csv_text
