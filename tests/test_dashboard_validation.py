import json
import pathlib
from typing import Any, Dict, List

import pytest
import requests


def _load_dashboard(path: pathlib.Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _panel_queries(panel: Dict[str, Any]) -> List[str]:
    queries = []
    for target in panel.get("targets", []):
        expr = target.get("expr")
        if expr:
            queries.append(expr)
    return queries


def _prom_query(prometheus_url: str, query: str, session: requests.Session):
    response = session.get(f"{prometheus_url}/api/v1/query", params={"query": query}, timeout=15)
    response.raise_for_status()
    return response.json()


@pytest.mark.parametrize(
    "dashboard_file",
    sorted([
        "patient-monitoring.json",
        "research-analytics.json",
        "system-health.json",
    ]),
)
def test_dashboard_structure_and_queries(dashboard_dir, dashboard_file, prometheus_client):
    dashboard = _load_dashboard(dashboard_dir / dashboard_file)
    assert dashboard.get("panels")
    assert dashboard.get("refresh") == "1s"
    assert isinstance(dashboard.get("templating", {}).get("list", []), list)

    for panel in dashboard["panels"]:
        assert panel.get("title")
        assert panel.get("datasource") == "Prometheus"
        queries = _panel_queries(panel)
        assert queries, f"Panel {panel.get('title')} has no PromQL query"
        for query in queries:
            result = _prom_query("http://localhost:9090", query, prometheus_client)
            assert result.get("status") == "success"


def test_dashboard_variable_usage_matches_patient_filters(dashboard_dir):
    expected_variables = {
        "patient-monitoring.json": "$patient_id",
        "research-analytics.json": "$patient_id",
        "system-health.json": None,
    }
    for name, expected in expected_variables.items():
        dashboard = _load_dashboard(dashboard_dir / name)
        joined = json.dumps(dashboard)
        if expected is None:
            assert "$patient_id" not in joined
        else:
            assert expected in joined


def test_dashboard_panel_coverage_for_live_metrics(dashboard_dir, prometheus_client):
    metric_expectations = {
        "patient-monitoring.json": ["posture_spine_angle", "device_battery_percent", "posture_alert_triggered", "label_values(posture_spine_angle, patient_id)"],
        "research-analytics.json": ["posture_measurement_count", "posture_alert_count", "posture_alert_triggered"],
        "system-health.json": ["up{job=\"prometheus\"}", "rate(prometheus_http_requests_total[5m])"],
    }
    for name, queries in metric_expectations.items():
        dashboard = _load_dashboard(dashboard_dir / name)
        body = json.dumps(dashboard)
        for query in queries:
            if query.startswith("up{") or query.startswith("rate("):
                result = _prom_query("http://localhost:9090", query, prometheus_client)
                if query == 'up{job="prometheus"}':
                    assert result.get("data", {}).get("result")
                continue
            assert query in body


def test_prometheus_series_exist_for_core_dashboards(prometheus_client):
    queries = {
        "posture_spine_angle": 'posture_spine_angle{patient_id="patient_001"}',
        "posture_measurement_count": "posture_measurement_count",
        "posture_alert_count": "posture_alert_count",
        "device_battery_percent": "device_battery_percent",
        "posture_emg_activation_normalized": "posture_emg_activation_normalized",
    }
    for metric_name, query in queries.items():
        result = _prom_query("http://localhost:9090", query, prometheus_client)
        assert result.get("status") == "success"
        assert result.get("data", {}).get("result") is not None


def test_system_health_dashboard_has_known_broken_panel(dashboard_dir, prometheus_client):
    dashboard = _load_dashboard(dashboard_dir / "system-health.json")
    broken = []
    for panel in dashboard["panels"]:
        for query in _panel_queries(panel):
            result = _prom_query("http://localhost:9090", query, prometheus_client)
            if query == 'up{job="posture-sensors"}' and not result.get("data", {}).get("result"):
                broken.append(panel["title"])
    assert "Sensor Service Status" in broken
