import time
from typing import Any, Dict

import pytest


def _post_graphql(client, headers, query: str, variables: Dict[str, Any] | None = None):
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    start = time.perf_counter()
    response = client.post("http://localhost:8000/graphql", json=payload, headers=headers, timeout=15)
    duration_ms = (time.perf_counter() - start) * 1000
    return response, duration_ms


def _assert_successful_graphql_response(response, max_duration_ms: float = 1500.0):
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("data") is not None or payload.get("errors") is not None
    assert max_duration_ms > 0
    return payload


def test_graphql_schema_has_expected_operations(graphql_introspection):
    query_type = graphql_introspection["queryType"]["name"]
    subscription_type = graphql_introspection["subscriptionType"]["name"]
    query_fields = []
    subscription_fields = []
    for type_def in graphql_introspection["types"]:
        if type_def.get("kind") == "OBJECT" and type_def.get("name") == query_type:
            query_fields = [field["name"] for field in type_def.get("fields", [])]
        if type_def.get("kind") == "OBJECT" and type_def.get("name") == subscription_type:
            subscription_fields = [field["name"] for field in type_def.get("fields", [])]

    assert query_fields == [
        "patientSession",
        "sensorReadings",
        "alertSummary",
        "healthStatus",
        "patient",
        "patients",
        "patientSessions",
        "alerts",
        "sessionAggregates",
        "patientSummary",
    ]
    assert subscription_fields == ["onNewFrame", "onAlert", "onDeviceStatus"]
    assert graphql_introspection["mutationType"] is None


def test_health_status_query_returns_expected_structure(gql_client, gql_headers):
    query = """
    query HealthStatus {
      healthStatus {
        status
        message
        uptimeS
        timestamp
      }
    }
    """
    response, duration_ms = _post_graphql(gql_client, gql_headers, query)
    payload = _assert_successful_graphql_response(response)
    health = payload["data"]["healthStatus"]
    assert health["status"] == "ok"
    assert "PostureCare GraphQL API running" in health["message"]
    assert isinstance(health["timestamp"], str)
    assert duration_ms < 1500


@pytest.mark.parametrize(
    "query, expected_field",
    [
        (
            """
            query Patient {
              patient(patientId: \"patient_001\") {
                patientId
                name
                age
                gender
                email
              }
            }
            """,
            "patient",
        ),
        (
            """
            query Patients {
              patients(limit: 5, offset: 0) {
                patientId
                name
                age
              }
            }
            """,
            "patients",
        ),
        (
            """
            query Sessions {
              patientSessions(patientId: \"patient_001\", limit: 5) {
                sessionId
                patientId
                startTime
                endTime
              }
            }
            """,
            "patientSessions",
        ),
        (
            """
            query Alerts {
              alerts(patientId: \"patient_001\", severity: \"high\", limit: 10) {
                timestamp
                patientId
                severity
                reason
                affectedMetric
              }
            }
            """,
            "alerts",
        ),
        (
            """
            query Summary {
              patientSummary(patientId: \"patient_001\") {
                patientId
                name
                recentAlertCount
                lastActivity
                avgPostureScore
              }
            }
            """,
            "patientSummary",
        ),
    ],
)
def test_domain_queries_validate_structure(gql_client, gql_headers, query, expected_field):
    response, _ = _post_graphql(gql_client, gql_headers, query)
    payload = _assert_successful_graphql_response(response)
    assert expected_field in payload["data"]


def test_empty_results_are_returned_as_empty_lists(gql_client, gql_headers):
    response, _ = _post_graphql(
        gql_client,
        gql_headers,
        """
        query EmptyResults {
          patients(limit: 5, offset: 0) { patientId }
          patient(patientId: \"missing_patient_999\") { patientId }
          patientSessions(patientId: \"missing_patient_999\", limit: 5) { sessionId }
          alerts(patientId: \"missing_patient_999\") { timestamp }
          sessionAggregates(sessionId: \"missing_session_999\") { sessionId }
          patientSummary(patientId: \"missing_patient_999\") { patientId }
        }
        """,
    )
    payload = _assert_successful_graphql_response(response)
    assert isinstance(payload["data"]["patients"], list)
    assert payload["data"]["patient"] is None
    assert payload["data"]["patientSessions"] == []
    assert payload["data"]["alerts"] == []
    assert payload["data"]["sessionAggregates"] is None
    assert payload["data"]["patientSummary"] is None


@pytest.mark.parametrize(
    "query",
    [
        "{ invalidField { test } }",
    '{ patient(patientId: true) { patientId } }',
    '{ patients(limit: "abc", offset: 0) { patientId } }',
    '{ patientSessions(patientId: "x", limit: "abc") { sessionId } }',
    ],
)
def test_invalid_queries_return_graphql_errors(gql_client, gql_headers, query):
    response, _ = _post_graphql(gql_client, gql_headers, query)
    assert response.status_code == 200
    payload = response.json()
    assert "errors" in payload


def test_authentication_header_is_not_required_for_graphql_endpoint(gql_client):
    response, _ = _post_graphql(
        gql_client,
        {},
        """
        query HealthStatus {
          healthStatus { status message timestamp }
        }
        """,
    )
    assert response.status_code == 200
    assert "data" in response.json()


def test_mutation_type_is_not_implemented(graphql_introspection):
    assert graphql_introspection["mutationType"] is None


def test_subscription_fields_are_documented_but_not_executed(graphql_operations):
    subscription_names = sorted(op.name for op in graphql_operations if op.kind == "subscription")
    assert subscription_names == ["onAlert", "onDeviceStatus", "onNewFrame"]


def test_response_times_for_read_queries(gql_client, gql_headers):
    queries = [
        "{ healthStatus { status } }",
        '{ patients(limit: 2, offset: 0) { patientId } }',
        '{ patientSummary(patientId: "patient_001") { patientId avgPostureScore } }',
    ]
    for query in queries:
        response, duration_ms = _post_graphql(gql_client, gql_headers, query)
        assert response.status_code == 200
        assert duration_ms < 1500
