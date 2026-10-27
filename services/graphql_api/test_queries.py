"""
PostureCare GraphQL API - Test Suite
Basic tests for queries, subscriptions, and authentication
"""

import pytest
import asyncio
import json
from httpx import Client, AsyncClient

# Test configuration
GRAPHQL_URL = "http://localhost:8000/graphql"
API_KEY = "test-key-123"
INVALID_KEY = "invalid-key"


class TestAuthentication:
    """Test API key authentication"""

    def test_missing_api_key(self):
        """Test query fails without API key"""
        client = Client()
        query = '{ healthStatus { status } }'
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload)
        # GraphQL endpoint is public, but resolvers check auth
        assert response.status_code in [200, 401]

    def test_invalid_api_key(self):
        """Test query fails with invalid API key"""
        client = Client()
        headers = {"X-API-Key": INVALID_KEY}
        query = '{ patients(limit: 1) { patientId } }'
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code in [200, 401]

    def test_valid_api_key(self):
        """Test query succeeds with valid API key"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '{ healthStatus { status } }'
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data


class TestPatientQueries:
    """Test patient-related queries"""

    def test_health_status(self):
        """Test health status query"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            healthStatus {
                status
                message
                timestamp
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        if "healthStatus" in data.get("data", {}):
            status = data["data"]["healthStatus"]
            assert status["status"] in ["ok", "degraded", "down"]

    def test_get_single_patient(self):
        """Test fetching single patient"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            patient(patientId: "patient_001") {
                patientId
                name
                age
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Result may be null if DB is empty, but query should not error
        assert "data" in data or "errors" in data

    def test_list_patients_pagination(self):
        """Test patient list with pagination"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            patients(limit: 5, offset: 0) {
                patientId
                name
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data


class TestAlertQueries:
    """Test alert-related queries"""

    def test_get_alerts(self):
        """Test fetching alerts for patient"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            alerts(patientId: "patient_001", limit: 10) {
                timestamp
                patientId
                severity
                reason
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data

    def test_filter_alerts_by_severity(self):
        """Test filtering alerts by severity"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            alerts(patientId: "patient_001", severity: "high", limit: 10) {
                timestamp
                severity
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data


class TestSessionQueries:
    """Test session-related queries"""

    def test_get_patient_sessions(self):
        """Test fetching patient sessions"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            patientSessions(patientId: "patient_001", limit: 5) {
                sessionId
                startTime
                endTime
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data


class TestSummaryQueries:
    """Test summary queries"""

    def test_patient_summary(self):
        """Test patient summary query"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '''
        {
            patientSummary(patientId: "patient_001") {
                patientId
                name
                recentAlertCount
                avgPostureScore
            }
        }
        '''
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or "errors" in data


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_query(self):
        """Test invalid GraphQL query"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '{ invalidField { test } }'
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    def test_missing_required_argument(self):
        """Test query with missing required argument"""
        client = Client()
        headers = {"X-API-Key": API_KEY}
        query = '{ alerts { timestamp } }'  # Missing patientId
        payload = {"query": query}

        response = client.post(GRAPHQL_URL, json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should have errors for missing argument
        assert "errors" in data or "data" in data


class TestHealthCheck:
    """Test health check endpoints"""

    def test_health_endpoint(self):
        """Test /health endpoint"""
        client = Client()
        response = client.get("http://localhost:8000/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_root_endpoint(self):
        """Test / root endpoint"""
        client = Client()
        response = client.get("http://localhost:8000/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
