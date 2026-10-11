"""Indicator calculations and statistical methods."""
import pytest

from backend.app import analytics, nlq


def test_dashboard_derived_values_are_calculated_not_hardcoded(store):
    d = analytics.dashboard(store)
    gap = d["kpis"]["rural_urban_gap"]
    assert gap["value"] == pytest.approx(36.7 - 14.8)
    assert gap["ratio"] == pytest.approx(36.7 / 14.8)
    assert gap["status"] == "calculated"
    assert d["kpis"]["poverty_change"]["value"] == pytest.approx(27.4 - 39.8)
    assert d["overlap"]["either"] == pytest.approx(14.3 + 16.2 + 13.1)
    # leading deprivations sorted by censored headcount
    assert [x["id"] for x in d["deprivations"][:2]] == ["cooking_fuel", "housing_materials"]


def test_every_kpi_has_source_and_period(store):
    for k, v in analytics.dashboard(store)["kpis"].items():
        assert v["period"], k
        assert v["source"]["url"].startswith("https://"), k


def test_compare_to_reference_z_test():
    a = {"value": 51.39, "se": 3.214}
    b = {"value": 27.36, "se": 0.4962}
    r = analytics.compare_to_reference(a, b)
    assert r["label"] == "higher than" and r["p_value"] < 0.001
    same = analytics.compare_to_reference({"value": 28.0, "se": 2.0}, b)
    assert same["label"] == "not statistically different from"
    assert analytics.compare_to_reference({"value": 1, "se": None}, b)["available"] is False


def test_rank_intervals_contain_point_rank():
    vals = {"a": 50, "b": 49, "c": 10, "d": 9.5}
    ses = {"a": 3, "b": 3, "c": 0.5, "d": 0.5}
    r = analytics.rank_intervals(vals, ses, higher_is_rank1=True)
    for k, (point, lo, hi) in r.items():
        assert lo <= point <= hi
    assert r["a"][0] == 1 and r["d"][0] == 4


def test_map_layer_ranks_and_significance(store):
    layer = analytics.map_layer(store, "poverty_rate", "district")
    assert layer["summary"]["n"] == 30
    nyam = next(r for r in layer["rows"] if r["geo_id"] == "nyamagabe")
    assert nyam["rank"] == 1 and nyam["vs_national"]["label"] == "higher than"
    good = analytics.map_layer(store, "electricity_lighting", "district")
    # higher_better: rank 1 must be the LOWEST access
    r1 = min(good["rows"], key=lambda r: r["rank"])
    assert r1["value"] == min(r["value"] for r in good["rows"])


def test_correlations_use_spearman_with_fdr(store):
    c = analytics.correlations(store, ["poverty_rate", "fs_banked", "electricity_lighting"])
    assert len(c["pairs"]) == 3
    for p in c["pairs"]:
        assert -1 <= p["rho"] <= 1 and p["ci_low"] <= p["rho"] <= p["ci_high"]
        assert p["q_value"] >= p["p_value"] - 1e-12
        assert p["n"] == 30
    assert any("causal" in w for w in c["caveats"])


def test_composite_is_labelled_experimental_and_validated(store):
    comp = analytics.composite_index(store)
    assert comp["status"] == "experimental"
    assert "poverty_rate" not in [c["indicator_id"] for c in comp["components"]]
    assert comp["validation"]["n"] == 30
    scores = [r["score"] for r in comp["rows"]]
    assert min(scores) == pytest.approx(0) and max(scores) == pytest.approx(100)


def test_district_profile_uses_parent_province_mpi_with_note(store):
    p = analytics.profile(store, "district", "nyamagabe")
    assert p["mpi"]["is_parent_province"] and p["mpi"]["geo_id"] == "southern"
    assert "must not be read as the district" in p["mpi"]["note"]
    assert any(f["kind"] == "concern" for f in p["findings"])


def test_profile_unknown_area_raises(store):
    with pytest.raises(KeyError):
        analytics.profile(store, "district", "atlantis")


@pytest.mark.parametrize("q,kind", [
    ("How does rural MPI incidence compare with urban incidence?", "comparison"),
    ("Which deprivation indicators have the highest reported censored headcounts?", "ranking"),
    ("Show the available financial inclusion indicators.", "list"),
    ("What is the MPI?", "definition"),
    ("What is the MPI in Gasabo?", "unavailable"),
    ("asdfgh", "unmatched"),
])
def test_nlq_intents(store, q, kind):
    assert nlq.ask(store, q)["kind"] == kind


def test_nlq_rural_urban_answer_is_grounded(store):
    r = nlq.ask(store, "How does rural MPI incidence compare with urban incidence?")
    assert "36.7%" in r["answer"] and "14.8%" in r["answer"] and "21.9" in r["answer"]
    assert r["sources"][0]["url"].startswith("https://statistics.gov.rw")
    assert any("not the monetary poverty rate" in c for c in r["caveats"])
