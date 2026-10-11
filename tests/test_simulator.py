"""Budget-simulator reconciliation and scenario arithmetic."""
import random

import pytest
from pydantic import ValidationError

from backend.app import simulator
from backend.app.simulator import ScenarioInput, allocate_amounts, run_scenario


def _inp(**kw):
    base = dict(name="t", total_budget_rwf=5_000_000_000, geography={"level": "district", "geo_id": "nyamagabe"},
                interventions=[{"id": "water", "share_pct": 40, "unit_cost_rwf": 250_000},
                               {"id": "cooking", "share_pct": 35, "unit_cost_rwf": 45_000},
                               {"id": "financial_inclusion", "share_pct": 25, "unit_cost_rwf": 100_000}])
    base.update(kw)
    return ScenarioInput(**base)


def test_allocate_amounts_reconciles_exactly_randomised():
    rng = random.Random(7)
    for _ in range(500):
        budget = rng.randint(1, 10**12)
        k = rng.randint(1, 8)
        cuts = sorted(rng.uniform(0, 100) for _ in range(k - 1))
        shares = [b - a for a, b in zip([0] + cuts, cuts + [100])]
        shares = [round(s, 2) for s in shares]
        if sum(shares) > 100:
            shares[-1] -= sum(shares) - 100
        amounts = allocate_amounts(budget, shares)
        assert sum(amounts) == round(budget * sum(shares) / 100)
        assert all(a >= 0 for a in amounts)


def test_scenario_reconciles_and_caps_at_need(store):
    r = run_scenario(store, _inp())
    s = r["summary"]
    assert s["reconciles"] is True
    assert s["allocated_rwf"] + s["unallocated_rwf"] == s["total_budget_rwf"]
    assert sum(l["amount_rwf"] for l in r["lines"]) == s["allocated_rwf"]
    for l in r["lines"]:
        assert l["households_reached"] <= l["capacity_households"]
        if l["eligible_households"] is not None:
            assert l["households_reached"] <= l["eligible_households"]
        assert l["amount_used_rwf"] + l["amount_idle_rwf"] == l["amount_rwf"]


def test_unallocated_budget_is_reported(store):
    r = run_scenario(store, _inp(interventions=[{"id": "water", "share_pct": 60, "unit_cost_rwf": 250_000}]))
    assert r["summary"]["unallocated_rwf"] == 2_000_000_000


def test_sensitivity_is_monotonic(store):
    r = run_scenario(store, _inp())
    for l in r["lines"]:
        reached = [x["households_reached"] for x in sorted(l["sensitivity"], key=lambda x: x["multiplier"])]
        assert reached == sorted(reached, reverse=True)


@pytest.mark.parametrize("bad", [
    dict(total_budget_rwf=-5),
    dict(total_budget_rwf=0),
    dict(interventions=[{"id": "water", "share_pct": 70, "unit_cost_rwf": 1}, {"id": "cooking", "share_pct": 40, "unit_cost_rwf": 1}]),
    dict(interventions=[{"id": "water", "share_pct": -1, "unit_cost_rwf": 1}]),
    dict(interventions=[{"id": "water", "share_pct": 10, "unit_cost_rwf": 0}]),
    dict(interventions=[{"id": "water", "share_pct": 10, "unit_cost_rwf": 5}, {"id": "water", "share_pct": 10, "unit_cost_rwf": 5}]),
    dict(interventions=[{"id": "teleport", "share_pct": 10, "unit_cost_rwf": 5}]),
    dict(sensitivity=[0]),
])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValidationError):
        _inp(**bad)


def test_district_cooking_need_falls_back_to_province_and_is_flagged(store):
    ctx = simulator.context(store, "district", "nyamagabe")
    cook = ctx["needs"]["cooking"]
    assert cook["fallback"] is True and cook["level_used"] == "province"
    water = ctx["needs"]["water"]
    assert water["fallback"] is False and water["level_used"] == "district"
    assert water["rate_pct"] == pytest.approx(100 - store.value("improved_water", "district", "nyamagabe"))


def test_outputs_are_labelled_illustrative(store):
    r = run_scenario(store, _inp())
    assert r["labels"]["status"] == "illustrative scenario"
    assert "does not estimate change in monetary poverty" in r["labels"]["not_measured"]


def test_need_weighted_suggestion_sums_to_100(store):
    s = simulator.suggest_need_weighted(store, "province", "western", ["water", "cooking", "housing"])
    assert sum(s.values()) == pytest.approx(100, abs=1e-6)
