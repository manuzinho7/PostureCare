import os
import pathlib
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRAPHQL_URL = os.getenv("POSTURECARE_GRAPHQL_URL", "http://localhost:8000/graphql")
PROMETHEUS_URL = os.getenv("POSTURECARE_PROMETHEUS_URL", "http://localhost:9090")
API_KEY = os.getenv("GRAPHQL_API_KEY", "test-key-123")


@dataclass
class OperationSpec:
    name: str
    kind: str
    query: str
    variables: Dict[str, Any]


@pytest.fixture(scope="session")
def gql_headers() -> Dict[str, str]:
    return {"X-API-Key": API_KEY}


@pytest.fixture(scope="session")
def gql_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


@pytest.fixture(scope="session")
def graphql_introspection(gql_client, gql_headers) -> Dict[str, Any]:
    query = """
    query Introspection {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          kind
          name
          fields {
            name
            args {
              name
              type {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    response = gql_client.post(GRAPHQL_URL, json={"query": query}, headers=gql_headers, timeout=15)
    response.raise_for_status()
    payload = response.json()
    assert "errors" not in payload, payload.get("errors")
    return payload["data"]["__schema"]


@pytest.fixture(scope="session")
def graphql_operations(graphql_introspection) -> List[OperationSpec]:
    query_type = graphql_introspection["queryType"]["name"]
    subscription_type = graphql_introspection["subscriptionType"]["name"]
    operations: List[OperationSpec] = []
    for type_def in graphql_introspection["types"]:
        if type_def.get("kind") == "OBJECT" and type_def.get("name") == query_type:
            for field in type_def.get("fields", []):
                operations.append(OperationSpec(name=field["name"], kind="query", query="", variables={}))
        if type_def.get("kind") == "OBJECT" and type_def.get("name") == subscription_type:
            for field in type_def.get("fields", []):
                operations.append(OperationSpec(name=field["name"], kind="subscription", query="", variables={}))
    return operations


@pytest.fixture(scope="session")
def sample_patients() -> List[Dict[str, Any]]:
    return [
        {
            "patient_id": "patient_001",
            "name": "Ana Silva",
            "age": 42,
            "gender": "F",
            "email": "ana.silva@example.com",
        },
        {
            "patient_id": "patient_002",
            "name": "Bruno Costa",
            "age": 58,
            "gender": "M",
            "email": "bruno.costa@example.com",
        },
    ]


@pytest.fixture(scope="session")
def sample_sensor_snapshot() -> Dict[str, Any]:
    return {
        "patient_id": "patient_001",
        "session_id": "session_2026_06_12_2336_001",
        "measurement_id": "m000001",
        "spine_angle": 45.93,
        "battery_percent": 83,
    }


@pytest.fixture(scope="session")
def dashboard_dir() -> pathlib.Path:
    return ROOT / "grafana" / "provisioning" / "dashboards"


@pytest.fixture(scope="session")
def prometheus_client():
    session = requests.Session()
    yield session
    session.close()
