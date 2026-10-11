"""Data-pipeline tests: parsing, missing-value handling, benchmarks and validation."""
import json

import pytest

from backend.app.db import quote_mysql_identifier
from backend.pipeline.geography import DISTRICT_PROVINCE, canonical
from backend.pipeline.model import num
from backend.pipeline.paths import PROCESSED_DIR, RAW_DIR


def test_num_never_turns_missing_into_zero():
    assert num(None) == (None, ["missing"])
    assert num("-") == (None, ["suppressed_or_no_observations_in_source"])
    assert num("") == (None, ["missing"])
    assert num(0) == (0.0, [])
    assert num("1,234.5") == (1234.5, [])
    assert num(100.00000000000031)[0] == 100.0


@pytest.mark.parametrize("label,expected", [
    ("Kigali City", ("province", "kigali", "City of Kigali")),
    ("South", ("province", "southern", "Southern Province")),
    ("Southern Province", ("province", "southern", "Southern Province")),
    (" Urban ", ("area", "urban", "Urban")),
    ("Nyamagabe", ("district", "nyamagabe", "Nyamagabe")),
    ("All Rwanda", ("national", "rwanda", "Rwanda")),
])
def test_canonical_geography(label, expected):
    assert canonical(label) == expected


def test_thirty_districts_five_provinces():
    assert len(DISTRICT_PROVINCE) == 30
    assert set(DISTRICT_PROVINCE.values()) == {"kigali", "southern", "western", "northern", "eastern"}


def test_mysql_identifier_quoting_is_safe():
    assert quote_mysql_identifier("nisr-hachathon") == "`nisr-hachathon`"
    for bad in ["x`; DROP DATABASE y; --", "a b", "", "x" * 65]:
        with pytest.raises(ValueError):
            quote_mysql_identifier(bad)


def test_raw_files_checksummed():
    log = json.loads((RAW_DIR.parent / "metadata" / "retrieval_log.json").read_text("utf-8"))
    for sid in ["eicv7_mi", "eicv7_mpi", "eicv7_pp", "eicv7_vup", "finscope_2024", "rphc5_main"]:
        assert log[sid]["sha256"] and len(log[sid]["sha256"]) == 64
        raw = RAW_DIR / log[sid]["file"]
        if not raw.exists():
            pytest.skip("raw files not downloaded (fresh clone): run python -m backend.pipeline.build --fetch")
        from backend.pipeline.fetch import sha256
        assert sha256(raw) == log[sid]["sha256"], f"{sid} differs from the recorded checksum"


def test_validation_report_has_no_errors_and_benchmarks_pass():
    rep = json.loads((PROCESSED_DIR / "validation_report.json").read_text("utf-8"))
    assert rep["summary"]["errors"] == 0
    bench = [c for c in rep["checks"] if c["check"].startswith("benchmark:")]
    assert len(bench) == 17 and all(c["passed"] for c in bench)


def test_published_contribution_inconsistency_is_surfaced_as_warning():
    rep = json.loads((PROCESSED_DIR / "validation_report.json").read_text("utf-8"))
    c = next(c for c in rep["checks"] if c["check"] == "mpi_published_contributions_reproducible:rwanda")
    assert c["passed"] is False and c["severity"] == "warning"


def test_key_official_values(store):
    assert store.value("poverty_rate", "national", "rwanda") == pytest.approx(27.36, abs=0.01)
    assert store.value("poverty_rate", "district", "nyamagabe") == pytest.approx(51.39, abs=0.01)
    assert store.value("mpi_incidence", "province", "kigali") == 12.4
    assert store.value("mpi", "national", "rwanda") == 0.136
    assert store.value("hh_savings_account", "national", "rwanda") == 68.0
    assert store.value("households_census", "national", "rwanda") == 3_312_743
    assert store.value("fs_banked", "district", "gasabo") == 51


def test_no_district_mpi_exists(store):
    """MPI is published only to province level: the pipeline must not create district MPI values."""
    for ind in ["mpi", "mpi_incidence", "mpi_intensity", "mpi_ch_cooking_fuel"]:
        assert store.query(ind, "district") == []


def test_unlabelled_figure_segment_is_missing_not_zero(store):
    o = store.one("fs_informal_only", "district", "nyarugenge")
    assert o["value"] is None and "unlabelled_segment_in_source_figure" in o["flags"]


def test_every_observation_has_known_indicator_and_source(store):
    for o in store.observations:
        assert o["indicator_id"] in store.indicator_index
        assert o["source_id"] in store.source_index
        assert o["status"] in {"official", "official_transcribed", "calculated"}


def test_recomputed_contributions_sum_to_100(store):
    for gid in ["rwanda"]:
        s = sum(store.value(f"mpi_contrib_calc_{i['id']}", "national", gid) for i in store.mpi_framework["indicators"])
        assert s == pytest.approx(100, abs=0.05)


def test_mpi_weights_sum_to_one(store):
    assert sum(i["weight"] for i in store.mpi_framework["indicators"]) == pytest.approx(1.0)
    assert len(store.mpi_framework["indicators"]) == 13
