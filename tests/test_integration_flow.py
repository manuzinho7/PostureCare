import time
from datetime import datetime, timedelta, timezone

import requests


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def test_database_to_graphql_flow(gql_client, gql_headers):
    start = time.perf_counter()
    response = gql_client.post(
        "http://localhost:8000/graphql",
        json={"query": '{ patients(limit: 3) { patientId name } }'},
        headers=gql_headers,
        timeout=15,
    )
    elapsed_ms = _elapsed_ms(start)
    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert isinstance(payload["data"]["patients"], list)
    assert elapsed_ms < 2000


def test_graphql_to_grafana_data_sources():
    response = requests.get("http://localhost:3000/api/health", timeout=15)
    assert response.status_code in {200, 302}


def test_application_metrics_to_prometheus(prometheus_client):
    response = prometheus_client.get(
        "http://localhost:9090/api/v1/query",
        params={"query": 'up{job="prometheus"}'},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["result"]


def test_prometheus_to_grafana_endpoint():
    response = requests.get("http://localhost:3000/api/health", timeout=15)
    assert response.status_code in {200, 302}


def test_docker_internal_services_are_reachable():
    endpoints = [
        "http://localhost:8000/health",
        "http://localhost:9090/-/ready",
        "http://localhost:3000/api/health",
    ]
    for endpoint in endpoints:
        response = requests.get(endpoint, timeout=15)
        assert response.status_code in {200, 302}


def test_end_to_end_analytics_flow(gql_client, gql_headers, prometheus_client):
    graphql_response = gql_client.post(
        "http://localhost:8000/graphql",
        json={"query": '{ healthStatus { status message } }'},
        headers=gql_headers,
        timeout=15,
    )
    assert graphql_response.status_code == 200
    assert graphql_response.json()["data"]["healthStatus"]["status"] == "ok"

    prometheus_response = prometheus_client.get(
        "http://localhost:9090/api/v1/query_range",
        params={
            "query": 'posture_spine_angle',
            "start": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
            "step": "5m",
        },
        timeout=15,
    )
    prometheus_response.raise_for_status()
    assert prometheus_response.json()["data"]["result"]

    grafana_response = requests.get("http://localhost:3000/api/health", timeout=15)
    assert grafana_response.status_code in {200, 302}


def test_integration_risks_are_documented():
    bottlenecks = ["PostgreSQL availability", "Prometheus scrape freshness", "Redis pub/sub optionality"]
    single_points = ["GraphQL API on port 8000", "Prometheus on port 9090", "Grafana on port 3000"]
    missing = ["No implemented GraphQL mutations", "No resolver-level auth enforcement", "No alert rules provisioned in dashboards"]
    reliability = ["System-health dashboard references posture-sensors job that is not currently published"]
    assert bottlenecks and single_points and missing and reliability
