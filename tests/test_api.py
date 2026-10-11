"""API responses, error handling, persistence and exports."""

SCEN = {"name": "Test scenario", "total_budget_rwf": 1_000_000_000,
        "geography": {"level": "province", "geo_id": "western"},
        "interventions": [{"id": "water", "share_pct": 50, "unit_cost_rwf": 250000},
                          {"id": "housing", "share_pct": 30, "unit_cost_rwf": 1200000}]}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"]["connected"] is True
    assert body["data"]["observations"] > 1000


def test_core_endpoints_ok(client):
    for path in ["/api/meta", "/api/sources", "/api/indicators", "/api/dashboard", "/api/mpi",
                 "/api/financial-inclusion", "/api/analysis/correlations", "/api/analysis/composite",
                 "/api/analysis/trends", "/api/analysis/data-quality", "/api/geo/district", "/api/geo/province",
                 "/api/map?indicator=poverty_rate&level=district", "/api/profile/province/eastern",
                 "/api/simulator/catalogue", "/api/simulator/context/national/rwanda"]:
        assert client.get(path).status_code == 200, path


def test_not_found_and_validation_errors(client):
    assert client.get("/api/map?indicator=nope").status_code == 404
    assert client.get("/api/profile/district/atlantis").status_code == 404
    assert client.get("/api/profile/district/DROP TABLE").status_code == 422
    assert client.get("/api/geo/sector").status_code == 422
    r = client.post("/api/simulator/run", json={**SCEN, "total_budget_rwf": -1})
    assert r.status_code == 422 and r.json()["error"] == "validation_error"
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_secret_not_exposed(client):
    """The DB password from the developer's .env (if any) must never appear in API responses."""
    from pathlib import Path

    from dotenv import dotenv_values
    from sqlalchemy.engine import make_url
    env = Path(__file__).resolve().parents[1] / ".env"
    url = dotenv_values(env).get("DATABASE_URL") if env.exists() else None
    password = make_url(url).password if url else None
    body = client.get("/api/meta").text + client.get("/api/health").text
    if password:
        assert password not in body
    assert "password" not in body.lower()


def test_simulator_run(client):
    r = client.post("/api/simulator/run", json=SCEN).json()
    assert r["summary"]["reconciles"] is True
    assert r["summary"]["unallocated_rwf"] == 200_000_000


def test_scenario_crud(client):
    created = client.post("/api/scenarios", json=SCEN)
    assert created.status_code == 201
    sid, token = created.json()["id"], created.json()["delete_token"]
    listed = client.get("/api/scenarios").json()
    assert any(s["id"] == sid for s in listed)
    assert all("delete_token" not in s and "delete_token_hash" not in s for s in listed)
    got = client.get(f"/api/scenarios/{sid}").json()
    assert got["name"] == "Test scenario" and "delete_token_hash" not in got
    # deletion requires the creator's token
    assert client.delete(f"/api/scenarios/{sid}").status_code == 403
    assert client.delete(f"/api/scenarios/{sid}", headers={"X-Scenario-Token": "wrong"}).status_code == 403
    assert client.delete(f"/api/scenarios/{sid}", headers={"X-Scenario-Token": token}).status_code == 204
    assert client.get(f"/api/scenarios/{sid}").status_code == 404


def test_exports(client):
    csv_ = client.post("/api/simulator/export?format=csv", json=SCEN)
    assert csv_.status_code == 200 and csv_.headers["content-type"].startswith("text/csv")
    assert "ILLUSTRATIVE" in csv_.text and "Improved water access" in csv_.text
    pdf = client.post("/api/simulator/export?format=pdf", json=SCEN)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    rep = client.get("/api/reports/profile/district/nyamagabe.pdf")
    assert rep.status_code == 200 and rep.content[:4] == b"%PDF"
    pc = client.get("/api/reports/profile/district/gasabo.csv")
    assert pc.status_code == 200 and "poverty_rate" in pc.text
    obs = client.get("/api/observations?indicator=poverty_rate&format=csv")
    assert obs.status_code == 200 and "nyamagabe" in obs.text
    mp = client.get("/api/map?indicator=fs_banked&level=district&format=csv")
    assert mp.status_code == 200 and "Gasabo" in mp.text


def test_ask(client):
    r = client.post("/api/ask", json={"question": "Which districts have the highest poverty rate?"}).json()
    assert r["kind"] == "ranking" and r["rows"][0]["geo_name"] == "Nyamagabe"
