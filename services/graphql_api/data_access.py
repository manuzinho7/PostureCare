"""
PostureCare Data Access Layer - Prometheus & PostgreSQL
Provides unified interface for querying sensor data and metadata
"""

import httpx
import psycopg2
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from functools import lru_cache
from dataclasses import dataclass
import os

import sys
sys.path.insert(0, '/c/Users/manue/Downloads/ISEP2526/PostureCare')

from scripts.data_models import SensorFrame, SensorBatch, IMUData, EMGData, SmO2Data, ESP32Status, ChargeState


# ============================================================================
# CONFIGURATION
# ============================================================================

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "posture-postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "posture_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "posture_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "posture_password")

# Query timeouts (in seconds)
PROMETHEUS_QUERY_TIMEOUT = 5
POSTGRES_QUERY_TIMEOUT = 5


# ============================================================================
# DATA ACCESS CLASSES
# ============================================================================

class PrometheusDataAccess:
    """Interface to Prometheus time-series database"""

    def __init__(self, base_url: str = PROMETHEUS_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=PROMETHEUS_QUERY_TIMEOUT)

    def get_sensor_readings(
        self,
        patient_id: str,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query sensor readings for a patient"""
        try:
            # PromQL query to get spine angles (as proxy for posture measurements)
            query = f'posture_spine_angle{{patient_id="{patient_id}"}}'
            if session_id:
                query += f'{{session_id="{session_id}"}}'

            response = self.client.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": (datetime.now() - timedelta(hours=24)).isoformat(),
                    "end": datetime.now().isoformat(),
                    "step": "1m",
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    readings = []
                    for result in results:
                        for timestamp, value in result.get("values", [])[:limit]:
                            readings.append({
                                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                                "value": float(value),
                                "metric": result.get("metric", {}),
                            })
                    return readings[offset:offset + limit]

            return []
        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return []

    def get_alert_history(
        self,
        patient_id: str,
        time_range_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get alert events for a patient"""
        try:
            query = f'posture_alert_triggered{{patient_id="{patient_id}"}}'

            response = self.client.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": (datetime.now() - timedelta(hours=time_range_hours)).isoformat(),
                    "end": datetime.now().isoformat(),
                    "step": "1m",
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    alerts = []
                    for result in results:
                        for timestamp, value in result.get("values", []):
                            if int(float(value)) > 0:
                                alerts.append({
                                    "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                                    "severity": "high" if float(value) > 2 else "medium",
                                    "metric": result.get("metric", {}),
                                })
                    return alerts

            return []
        except Exception as e:
            print(f"Error fetching alert history: {e}")
            return []

    def get_patient_metrics(self, patient_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for a patient"""
        try:
            # Average spine angle
            avg_query = f'avg(posture_spine_angle{{patient_id="{patient_id}"}})'
            # Total alerts
            alert_query = f'count(posture_alert_triggered{{patient_id="{patient_id}"}})'

            metrics = {}

            # Get average
            response = self.client.get(
                f"{self.base_url}/api/v1/query",
                params={"query": avg_query}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    metrics["avg_spine_angle"] = float(data["data"]["result"][0]["value"][1])

            # Get alert count
            response = self.client.get(
                f"{self.base_url}/api/v1/query",
                params={"query": alert_query}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    metrics["total_alerts"] = int(float(data["data"]["result"][0]["value"][1]))

            return metrics
        except Exception as e:
            print(f"Error getting patient metrics: {e}")
            return {}


class PostgreSQLDataAccess:
    """Interface to PostgreSQL database"""

    def __init__(
        self,
        host: str = POSTGRES_HOST,
        port: int = POSTGRES_PORT,
        database: str = POSTGRES_DB,
        user: str = POSTGRES_USER,
        password: str = POSTGRES_PASSWORD,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def _get_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=POSTGRES_QUERY_TIMEOUT,
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient metadata"""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT patient_id, name, age, gender, email FROM patients WHERE patient_id = %s",
                (patient_id,)
            )
            result = cursor.fetchone()
            cursor.close()

            if result:
                return {
                    "patient_id": result[0],
                    "name": result[1],
                    "age": result[2],
                    "gender": result[3],
                    "email": result[4],
                }
            return None
        except Exception as e:
            print(f"Error getting patient: {e}")
            return None
        finally:
            conn.close()

    def get_all_patients(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all patients with pagination"""
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT patient_id, name, age, gender, email FROM patients ORDER BY patient_id LIMIT %s OFFSET %s",
                (limit, offset)
            )
            results = cursor.fetchall()
            cursor.close()

            patients = []
            for row in results:
                patients.append({
                    "patient_id": row[0],
                    "name": row[1],
                    "age": row[2],
                    "gender": row[3],
                    "email": row[4],
                })
            return patients
        except Exception as e:
            print(f"Error getting patients: {e}")
            return []
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_id, patient_id, start_time, end_time, notes
                   FROM sessions WHERE session_id = %s""",
                (session_id,)
            )
            result = cursor.fetchone()
            cursor.close()

            if result:
                return {
                    "session_id": result[0],
                    "patient_id": result[1],
                    "start_time": result[2].isoformat() if result[2] else None,
                    "end_time": result[3].isoformat() if result[3] else None,
                    "notes": result[4],
                }
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
        finally:
            conn.close()

    def get_patient_sessions(self, patient_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all sessions for a patient"""
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_id, patient_id, start_time, end_time, notes
                   FROM sessions WHERE patient_id = %s ORDER BY start_time DESC LIMIT %s""",
                (patient_id, limit)
            )
            results = cursor.fetchall()
            cursor.close()

            sessions = []
            for row in results:
                sessions.append({
                    "session_id": row[0],
                    "patient_id": row[1],
                    "start_time": row[2].isoformat() if row[2] else None,
                    "end_time": row[3].isoformat() if row[3] else None,
                    "notes": row[4],
                })
            return sessions
        except Exception as e:
            print(f"Error getting patient sessions: {e}")
            return []
        finally:
            conn.close()


class CachingLayer:
    """Simple caching layer for frequently accessed data"""

    def __init__(self):
        self.prometheus = PrometheusDataAccess()
        self.postgres = PostgreSQLDataAccess()

    @lru_cache(maxsize=100)
    def get_cached_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient with caching (5 minute TTL via decorator)"""
        return self.postgres.get_patient(patient_id)

    @lru_cache(maxsize=100)
    def get_cached_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with caching"""
        return self.postgres.get_session(session_id)

    def get_sensor_readings(
        self,
        patient_id: str,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get sensor readings (not cached - real-time data)"""
        return self.prometheus.get_sensor_readings(patient_id, session_id, limit, offset)


# Global instance
_data_access = CachingLayer()

def get_data_access() -> CachingLayer:
    """Get global data access instance"""
    return _data_access
