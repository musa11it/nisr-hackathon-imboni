"""Streamlit smoke tests: the entrypoint boots and every page renders without exceptions or error states."""
from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = st_testing.AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["national", "geographic", "mpi", "financial", "simulator", "insights", "explorer", "reports", "sources"]


def _page(name: str):
    src = (f"import sys\nsys.path.insert(0, {str(ROOT)!r})\n"
           f"from dashboard.views import {name}\n{name}.render()\n")
    at = AppTest.from_string(src, default_timeout=120)
    at.run()
    return at


def test_entrypoint_boots():
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error


@pytest.mark.parametrize("name", PAGES)
def test_page_renders(name):
    at = _page(name)
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert len(at.markdown) > 3  # hero, sections and content were drawn


def test_pages_have_charts_or_tables():
    for name in ("national", "geographic", "mpi", "financial", "simulator"):
        assert _page(name).get("plotly_chart"), name


def _allocated(at) -> float:
    import re
    md = [m.value for m in at.markdown if "target 100%" in m.value]
    return float(re.search(r"Allocated ([\d.]+)%", md[0]).group(1))


def test_simulator_interactions():
    at = _page("simulator")
    assert _allocated(at) == 100.0
    at.slider(key="share_housing").set_value(60).run()
    assert _allocated(at) == 135.0
    assert not at.get("plotly_chart")  # results withheld while over-allocated
    next(b for b in at.button if b.label == "Equal split").click().run()
    assert _allocated(at) == 100.0 and at.get("plotly_chart")
    at.radio(key="sim_level").set_value("district").run()
    at.selectbox(key="sim_geo_district").set_value("nyamagabe").run()
    next(b for b in at.button if b.label == "Need-weighted split").click().run()
    assert _allocated(at) == 100.0
    next(b for b in at.button if b.label == "Save for comparison").click().run()
    at.text_input(key="sim_name").set_value("Scenario B").run()
    next(b for b in at.button if b.label == "Save for comparison").click().run()
    assert [r["name"] for r in at.session_state["sim_saved"]] == ["Scenario A", "Scenario B"]
    assert len(at.get("download_button")) >= 3  # scenario CSV, PDF, comparison CSV
    assert not at.exception


def test_geographic_province_only_indicator():
    at = _page("geographic")
    at.selectbox[0].set_value("mpi_incidence").run()
    assert not at.exception and not at.error
    assert [r.value for r in at.radio if r.label == "Geographic level"] == ["province"]


def test_explorer_question_answering():
    at = _page("explorer")
    at.text_input[2].set_value("Which districts have the highest poverty rate?").run()
    assert not at.exception
    assert any("Nyamagabe" in str(df.value) for df in at.dataframe)
