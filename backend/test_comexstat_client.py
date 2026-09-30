import os

def test_comexstat_base_url():
    from comexstat_client import BASE_URL
    assert BASE_URL.startswith("http")

def test_comexstat_payload_shape():
    payload = {
        "flow": "export",
        "monthDetail": False,
        "period": {"from": "2026-01", "to": "2026-08"},
        "filters": [],
        "details": ["ncm", "country"],
        "metrics": ["metricFOB", "metricKG"],
    }
    assert payload["flow"] in {"export", "import"}
    assert "metricFOB" in payload["metrics"]
    assert "metricKG" in payload["metrics"]
