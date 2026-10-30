"""Chart builders: map geometry winding and figure construction."""
from dashboard import charts


def test_plotly_geojson_rewinds_exterior_rings_clockwise(store):
    for level in ("province", "district"):
        gj = charts.plotly_geojson(store.geo[level])
        assert len(gj["features"]) == (5 if level == "province" else 30)
        for f in gj["features"]:
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for p in polys:
                assert charts._signed_area(p[0]) < 0  # clockwise exterior (d3 convention)
                assert all(charts._signed_area(h) > 0 for h in p[1:])
    # the store's own geometry is not mutated
    f0 = store.geo["district"]["features"][0]["geometry"]
    ring = f0["coordinates"][0] if f0["type"] == "Polygon" else f0["coordinates"][0][0]
    assert charts._signed_area(ring) != 0


def test_choropleth_marks_unpublished_areas_grey(store):
    rows = [{"geo_id": "gasabo", "value": 11.1}]
    fig = charts.choropleth(store.geo["district"], rows, "Poverty", "%", worse_high=True)
    assert len(fig.data) == 2 and len(fig.data[0].locations) == 1 and len(fig.data[1].locations) == 29


def test_ranked_bars_put_most_deprived_first():
    rows = [{"geo_id": "a", "geo_name": "A", "value": 10}, {"geo_id": "b", "geo_name": "B", "value": 50}]
    assert list(charts.ranked_bars(rows, worse_high=True).data[0].y) == ["B", "A"]
    assert list(charts.ranked_bars(rows, worse_high=False).data[0].y) == ["A", "B"]


def test_wrap_long_labels():
    assert charts.wrap("Housing improvement (roofing)") == "Housing improvement<br>(roofing)"
    assert charts.wrap("Gasabo") == "Gasabo"
