"""
PostureCare GraphQL API - FastAPI + Strawberry GraphQL
Microservice para expor dados de sensores via GraphQL e publicar em Prometheus
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from strawberry.fastapi import GraphQLRouter
import strawberry
from datetime import datetime
from typing import List, Optional, AsyncGenerator, Any, Dict
from enum import Enum
import asyncio
import logging
import os

from pydantic import BaseModel

# Import data models
import sys
sys.path.insert(0, '/c/Users/manue/Downloads/ISEP2526/PostureCare')

from scripts.data_models import (
    SensorFrame, IMUData, EMGData, SmO2Data, ESP32Status,
    SensorBatch, MessageType, ChargeState
)
from data_generator import SyntheticDataGenerator
from prometheus_publisher import PrometheusPublisher
from csv_ingestion_service import CSVIngestionService

from data_access import get_data_access
from auth import APIKeyMiddleware
from pubsub import get_pubsub_manager, EventChannels

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PublishEventRequest(BaseModel):
    event_type: str
    channel: str
    data: Dict[str, Any]


class IngestCsvRequest(BaseModel):
    csv_path: str = "/app/sample-data/live_sensor_stream.csv"
    job_prefix: str = "graphql_csv"
    reset_offset: bool = False


csv_ingestion_service = CSVIngestionService(
    push_gateway_url=os.getenv("PUSH_GATEWAY_URL", "http://push-gateway:9091")
)
csv_polling_task: Optional[asyncio.Task] = None


def _seed_synthetic_metrics() -> Dict[str, Any]:
    """Generate a small demo dataset and push it to the Push Gateway."""
    patient_ids = ["patient_001", "patient_002", "patient_003"]
    num_measurements = int(os.getenv("GRAPHQL_SEED_MEASUREMENTS", "12"))
    push_gateway_url = os.getenv("PUSH_GATEWAY_URL", "http://push-gateway:9091")

    generator = SyntheticDataGenerator()
    generated_sessions = generator.generate_multiple_sessions(
        patient_ids=patient_ids,
        num_measurements=num_measurements,
        start_time=datetime.now(),
    )

    publisher = PrometheusPublisher(push_gateway_url=push_gateway_url)
    pushed_batches = []

    for patient_id, payload in generated_sessions.items():
        batch = SensorBatch(
            session_id=payload["session_id"],
            patient_id=patient_id,
            frames=payload["frames"],
        )
        publisher.job_name = f"graphql_seed_{patient_id}"
        publisher.batch_to_metrics(batch)
        if publisher.push_to_gateway():
            pushed_batches.append({
                "patient_id": patient_id,
                "session_id": payload["session_id"],
                "frames": batch.frame_count,
            })

    return {
        "generated_patients": patient_ids,
        "pushed_batches": pushed_batches,
    }


# ============================================================================
# GraphQL TYPES
# ============================================================================

@strawberry.type
class IMUType:
    """IMU sensor data"""
    imu_id: int
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    acc_rms_mg: int
    gyro_rms_mdps: int


@strawberry.type
class EMGType:
    """EMG sensor data"""
    emg_id: int
    rms_uv: int
    mav_uv: int
    iemg_uvs: int
    activation_q15: int
    activation_normalized: float = strawberry.field(
        description="Activation level normalized to 0-1"
    )

    @staticmethod
    def from_model(emg: EMGData) -> 'EMGType':
        return EMGType(
            emg_id=emg.emg_id,
            rms_uv=emg.rms_uv,
            mav_uv=emg.mav_uv,
            iemg_uvs=emg.iemg_uvs,
            activation_q15=emg.activation_q15,
            activation_normalized=emg.activation_q15 / 32767.0,
        )


@strawberry.type
class SmO2Type:
    """SmO2 oxygen saturation data"""
    smo2_id: int
    smo2_percent: float = strawberry.field(
        description="Oxygen saturation percentage"
    )
    trend_percent_per_min: float = strawberry.field(
        description="Trend change per minute"
    )
    quality_normalized: float = strawberry.field(
        description="Signal quality 0-1"
    )

    @staticmethod
    def from_model(smo2: SmO2Data) -> 'SmO2Type':
        return SmO2Type(
            smo2_id=smo2.smo2_id,
            smo2_percent=smo2.smo2_percent,
            trend_percent_per_min=smo2.trend_cPct_per_min * 0.01,
            quality_normalized=smo2.quality_normalized,
        )


@strawberry.type
class ESP32StatusType:
    """ESP32 device status"""
    battery_mV: int
    battery_pct: int
    charge_state: str
    uptime_s: int
    temp_cC: float
    heap_free: int
    has_errors: bool
    error_list: List[str]

    @staticmethod
    def from_model(status: ESP32Status) -> 'ESP32StatusType':
        return ESP32StatusType(
            battery_mV=status.battery_mV,
            battery_pct=status.battery_pct,
            charge_state=status.charge_state.name,
            uptime_s=status.uptime_s,
            temp_cC=status.temp_cC,
            heap_free=status.heap_free,
            has_errors=status.has_errors,
            error_list=status.get_error_list(),
        )


@strawberry.type
class SensorReadingType:
    """Complete sensor reading"""
    measurement_id: str
    timestamp: str
    imu: IMUType
    emg: EMGType
    smo2: SmO2Type
    status: ESP32StatusType
    is_alert_worthy: bool
    alert_reasons: List[str]

    @staticmethod
    def from_model(frame: SensorFrame) -> 'SensorReadingType':
        return SensorReadingType(
            measurement_id=frame.measurement_id,
            timestamp=frame.timestamp.isoformat(),
            imu=IMUType(
                imu_id=frame.imu.imu_id,
                roll_deg=frame.imu.roll_deg,
                pitch_deg=frame.imu.pitch_deg,
                yaw_deg=frame.imu.yaw_deg,
                acc_rms_mg=frame.imu.acc_rms_mg,
                gyro_rms_mdps=frame.imu.gyro_rms_mdps,
            ),
            emg=EMGType.from_model(frame.emg),
            smo2=SmO2Type.from_model(frame.smo2),
            status=ESP32StatusType.from_model(frame.status),
            is_alert_worthy=frame.is_alert_worthy,
            alert_reasons=frame.alert_reasons,
        )


@strawberry.type
class PatientSessionType:
    """Patient session data"""
    patient_id: str
    session_id: str
    frame_count: int
    alert_count: int
    alert_rate_percent: float
    readings: List[SensorReadingType]

    @staticmethod
    def from_batch(batch: SensorBatch) -> 'PatientSessionType':
        return PatientSessionType(
            patient_id=batch.patient_id,
            session_id=batch.session_id,
            frame_count=batch.frame_count,
            alert_count=batch.alert_count,
            alert_rate_percent=batch.alert_rate,
            readings=[SensorReadingType.from_model(f) for f in batch.frames],
        )


@strawberry.type
class AlertSummaryType:
    """Alert summary for patient"""
    patient_id: str
    total_alerts: int
    alert_rate_percent: float
    critical_count: int
    last_alert_time: Optional[str]

    @staticmethod
    def from_batch(batch: SensorBatch) -> 'AlertSummaryType':
        critical = sum(1 for f in batch.frames if f.is_alert_worthy and f.emg.activation_q15 > 28000)
        last_alert = None
        for frame in reversed(batch.frames):
            if frame.is_alert_worthy:
                last_alert = frame.timestamp.isoformat()
                break
        return AlertSummaryType(
            patient_id=batch.patient_id,
            total_alerts=batch.alert_count,
            alert_rate_percent=batch.alert_rate,
            critical_count=critical,
            last_alert_time=last_alert,
        )


@strawberry.type
class HealthStatusType:
    """System health status"""
    status: str = strawberry.field(description="System status: ok, degraded, down")
    message: str
    uptime_s: int = strawberry.field(description="API uptime in seconds")
    timestamp: str


# ============================================================================
# NEW GRAPHQL TYPES FOR PHASE 1
# ============================================================================

@strawberry.type
class AlertType:
    """Individual alert event"""
    timestamp: str
    patient_id: str
    severity: str = strawberry.field(description="high, medium, or low")
    reason: str
    affected_metric: str


@strawberry.type
class PatientType:
    """Patient metadata"""
    patient_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    email: Optional[str] = None


@strawberry.type
class SessionMetadataType:
    """Session metadata"""
    session_id: str
    patient_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None


@strawberry.type
class SensorReadingConnectionType:
    """Paginated sensor readings with metadata"""
    total: int
    limit: int
    offset: int
    readings: List['SensorReadingType']


@strawberry.type
class AggregateMetricsType:
    """Aggregated metrics for session or patient"""
    patient_id: str
    session_id: Optional[str]
    avg_spine_angle: Optional[float]
    total_frames: int
    total_alerts: int
    alert_rate: float
    avg_muscle_activation: Optional[float]
    avg_oxygen_saturation: Optional[float]


@strawberry.type
class PatientSummaryType:
    """Patient summary with recent activity"""
    patient_id: str
    name: Optional[str]
    recent_alert_count: int
    last_activity: Optional[str]
    avg_posture_score: float


# ============================================================================
# GraphQL QUERIES
# ============================================================================

@strawberry.type
class Query:
    """GraphQL Query interface"""

    @strawberry.field
    def patient_session(self, patient_id: str, session_id: str) -> Optional[PatientSessionType]:
        """Get complete session data for patient"""
        # TODO: Load from PostgreSQL or cache
        return None

    @strawberry.field
    def sensor_readings(
        self,
        patient_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SensorReadingType]:
        """Get latest sensor readings for patient"""
        # TODO: Load from Prometheus or cache
        return []

    @strawberry.field
    def alert_summary(self, patient_id: str) -> Optional[AlertSummaryType]:
        """Get alert summary for patient"""
        # TODO: Aggregate from Prometheus
        return None

    @strawberry.field
    def health_status(self) -> HealthStatusType:
        """Get API health status"""
        return HealthStatusType(
            status="ok",
            message="PostureCare GraphQL API running",
            uptime_s=0,
            timestamp=datetime.now().isoformat(),
        )

    # ========================================================================
    # NEW QUERIES FOR PHASE 1
    # ========================================================================

    @strawberry.field
    def patient(self, patient_id: str) -> Optional[PatientType]:
        """Get patient metadata"""
        try:
            data_access = get_data_access()
            patient_data = data_access.postgres.get_patient(patient_id)
            if patient_data:
                return PatientType(
                    patient_id=patient_data["patient_id"],
                    name=patient_data.get("name"),
                    age=patient_data.get("age"),
                    gender=patient_data.get("gender"),
                    email=patient_data.get("email"),
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching patient: {e}")
            return None

    @strawberry.field
    def patients(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PatientType]:
        """Get all patients with pagination"""
        try:
            data_access = get_data_access()
            patients_data = data_access.postgres.get_all_patients(limit, offset)
            return [
                PatientType(
                    patient_id=p["patient_id"],
                    name=p.get("name"),
                    age=p.get("age"),
                    gender=p.get("gender"),
                    email=p.get("email"),
                )
                for p in patients_data
            ]
        except Exception as e:
            logger.error(f"Error fetching patients: {e}")
            return []

    @strawberry.field
    def patient_sessions(
        self,
        patient_id: str,
        limit: int = 20,
    ) -> List[SessionMetadataType]:
        """Get all sessions for a patient"""
        try:
            data_access = get_data_access()
            sessions = data_access.postgres.get_patient_sessions(patient_id, limit)
            return [
                SessionMetadataType(
                    session_id=s["session_id"],
                    patient_id=s["patient_id"],
                    start_time=s.get("start_time"),
                    end_time=s.get("end_time"),
                    notes=s.get("notes"),
                )
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Error fetching patient sessions: {e}")
            return []

    @strawberry.field
    def alerts(
        self,
        patient_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[AlertType]:
        """Get alerts with optional filtering"""
        try:
            data_access = get_data_access()
            if not patient_id:
                return []

            alerts = data_access.prometheus.get_alert_history(patient_id)

            # Filter by severity if specified
            if severity:
                alerts = [a for a in alerts if a.get("severity") == severity]

            # Convert to AlertType
            result = []
            for alert in alerts[:limit]:
                result.append(
                    AlertType(
                        timestamp=alert["timestamp"],
                        patient_id=patient_id,
                        severity=alert.get("severity", "unknown"),
                        reason="Posture/Activity Alert",
                        affected_metric="spine_angle"
                    )
                )
            return result
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    @strawberry.field
    def session_aggregates(self, session_id: str) -> Optional[AggregateMetricsType]:
        """Get aggregated metrics for a session"""
        try:
            data_access = get_data_access()
            session = data_access.postgres.get_session(session_id)
            if not session:
                return None

            patient_id = session["patient_id"]

            return AggregateMetricsType(
                patient_id=patient_id,
                session_id=session_id,
                avg_spine_angle=None,  # Would compute from Prometheus
                total_frames=0,
                total_alerts=0,
                alert_rate=0.0,
                avg_muscle_activation=None,
                avg_oxygen_saturation=None,
            )
        except Exception as e:
            logger.error(f"Error fetching session aggregates: {e}")
            return None

    @strawberry.field
    def patient_summary(self, patient_id: str) -> Optional[PatientSummaryType]:
        """Get patient summary with recent activity"""
        try:
            data_access = get_data_access()
            patient = data_access.postgres.get_patient(patient_id)
            if not patient:
                return None

            metrics = data_access.prometheus.get_patient_metrics(patient_id)

            return PatientSummaryType(
                patient_id=patient_id,
                name=patient.get("name"),
                recent_alert_count=metrics.get("total_alerts", 0),
                last_activity=None,
                avg_posture_score=100.0 - min(
                    metrics.get("avg_spine_angle", 0) * 2, 50
                )  # Simple scoring
            )
        except Exception as e:
            logger.error(f"Error fetching patient summary: {e}")
            return None


# ============================================================================
# GraphQL SUBSCRIPTIONS
# ============================================================================

@strawberry.type
class Subscription:
    """GraphQL Subscriptions for real-time events"""

    @strawberry.subscription
    async def on_new_frame(self, patient_id: str) -> AsyncGenerator[SensorReadingType, None]:
        """Subscribe to new sensor frames for a patient"""
        try:
            pubsub = get_pubsub_manager()
            channel = EventChannels.new_frame(patient_id)
            queue = await pubsub.subscribe(channel)

            try:
                while True:
                    message = await asyncio.wait_for(queue.get(), timeout=300)
                    # Yield frame data (in real scenario, would parse from message)
                    logger.debug(f"Subscription event on {channel}")
                    # Yield mock data for now
                    yield None
            except asyncio.TimeoutError:
                logger.info(f"Subscription timeout for {channel}")
            finally:
                await pubsub.unsubscribe(channel, queue)
        except Exception as e:
            logger.error(f"Subscription error: {e}")

    @strawberry.subscription
    async def on_alert(
        self,
        patient_id: str,
        severity: Optional[str] = None,
    ) -> AsyncGenerator[AlertType, None]:
        """Subscribe to alerts for a patient"""
        try:
            pubsub = get_pubsub_manager()
            channel = EventChannels.alert(patient_id)
            queue = await pubsub.subscribe(channel)

            try:
                while True:
                    message = await asyncio.wait_for(queue.get(), timeout=300)
                    # In real scenario, parse and filter by severity
                    logger.debug(f"Alert subscription event on {channel}")
                    # Yield mock alert
                    yield None
            except asyncio.TimeoutError:
                logger.info(f"Alert subscription timeout for {channel}")
            finally:
                await pubsub.unsubscribe(channel, queue)
        except Exception as e:
            logger.error(f"Alert subscription error: {e}")

    @strawberry.subscription
    async def on_device_status(self, device_id: str) -> AsyncGenerator[ESP32StatusType, None]:
        """Subscribe to device status updates"""
        try:
            pubsub = get_pubsub_manager()
            channel = EventChannels.device_status(device_id)
            queue = await pubsub.subscribe(channel)

            try:
                while True:
                    message = await asyncio.wait_for(queue.get(), timeout=300)
                    logger.debug(f"Device status event on {channel}")
                    # Yield mock status
                    yield None
            except asyncio.TimeoutError:
                logger.info(f"Device status subscription timeout for {channel}")
            finally:
                await pubsub.unsubscribe(channel, queue)
        except Exception as e:
            logger.error(f"Device status subscription error: {e}")


# ============================================================================
# FastAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="PostureCare GraphQL API",
    description="Wearable sensor data via GraphQL",
    version="0.1.0",
)

# Add authentication middleware
app.add_middleware(APIKeyMiddleware)

# Create GraphQL schema with subscriptions
schema = strawberry.Schema(query=Query, subscription=Subscription)

# Mount GraphQL router
graphql_router = GraphQLRouter(
    schema,
    path="/graphql",
)
app.include_router(graphql_router)


# ============================================================================
# REST ENDPOINTS (Complement GraphQL)
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "PostureCare GraphQL API",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Return a valid Prometheus exposition payload so Prometheus can scrape the target.
    return PlainTextResponse(
        "# HELP posture_api_up PostureCare GraphQL API health\n"
        "# TYPE posture_api_up gauge\n"
        "posture_api_up 1\n",
        media_type="text/plain",
    )


@app.post("/api/publish_event")
async def publish_event(request: PublishEventRequest):
    """Publish an event to a channel (used by CSV ingester)"""
    try:
        pubsub = get_pubsub_manager()
        if request.event_type == "sensor_frame":
            patient_id = request.data.get("patient_id") or request.channel.split(":", 1)[-1]
            # await publish_sensor_frame(patient_id, request.data)
        else:
            await pubsub.publish(request.channel, request.data)
        return {
            "status": "ok",
            "message": f"Event published to {request.channel}",
            "event_type": request.event_type,
        }
    except Exception as e:
        logger.error(f"Error publishing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/csv")
async def ingest_csv(request: IngestCsvRequest):
    """Ingest new rows from a CSV and publish metrics to Prometheus."""
    try:
        result = await asyncio.to_thread(
            csv_ingestion_service.ingest_new_rows,
            request.csv_path,
            request.job_prefix,
            request.reset_offset,
        )
        return {
            "status": "ok",
            "message": "CSV rows processed",
            **result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error ingesting CSV: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _csv_polling_loop(csv_path: str, interval_seconds: int, job_prefix: str):
    """Background task that continuously ingests appended CSV rows."""
    while True:
        try:
            result = await asyncio.to_thread(
                csv_ingestion_service.ingest_new_rows,
                csv_path,
                job_prefix,
                False,
            )
            if result["rows_ingested"] > 0:
                logger.info(
                    "CSV polling ingested %s rows from %s",
                    result["rows_ingested"],
                    result["csv_path"],
                )
        except FileNotFoundError:
            # Wait for file to be created by the streaming service.
            pass
        except Exception as exc:
            logger.warning(f"CSV polling error: {exc}")

        await asyncio.sleep(max(1, interval_seconds))


@app.post("/generate/synthetic")
async def generate_synthetic(
    patient_id: str = "patient_synthetic",
    duration_minutes: int = 60,
    sample_rate_hz: int = 1,
):
    """Generate synthetic sensor data"""
    try:
        num_measurements = max(1, duration_minutes * max(1, sample_rate_hz))

        def _run_generation() -> Dict[str, Any]:
            generator = SyntheticDataGenerator()
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            frames = generator.generate_session(
                patient_id=patient_id,
                session_id=session_id,
                num_measurements=num_measurements,
                start_time=datetime.now(),
                interval_seconds=max(1, int(60 / max(1, sample_rate_hz))),
            )

            batch = SensorBatch(
                session_id=session_id,
                patient_id=patient_id,
                frames=frames,
            )
            publisher = PrometheusPublisher(
                push_gateway_url=os.getenv("PUSH_GATEWAY_URL", "http://push-gateway:9091")
            )
            publisher.job_name = f"graphql_synthetic_{patient_id}"
            publisher.batch_to_metrics(batch)
            pushed = publisher.push_to_gateway()

            return {
                "session_id": session_id,
                "frame_count": batch.frame_count,
                "alert_count": batch.alert_count,
                "pushed_to_gateway": pushed,
            }

        result = await asyncio.to_thread(_run_generation)
        return {
            "status": "ok",
            "message": f"Generated {duration_minutes} minutes of synthetic data",
            "patient_id": patient_id,
            **result,
        }
    except Exception as e:
        logger.error(f"Error generating synthetic data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """API root"""
    return {
        "name": "PostureCare GraphQL API",
        "version": "0.1.0",
        "endpoints": {
            "graphql": "http://localhost:8000/graphql",
            "health": "http://localhost:8000/health",
            "metrics": "http://localhost:8000/metrics",
            "docs": "http://localhost:8000/docs",
        },
    }


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global csv_polling_task

    print("✅ PostureCare GraphQL API started")
    print("📊 GraphQL endpoint: http://localhost:8000/graphql")
    print("📖 API docs: http://localhost:8000/docs")

    if os.getenv("GRAPHQL_SEED_SAMPLE_DATA", "true").lower() == "true":
        try:
            result = await asyncio.to_thread(_seed_synthetic_metrics)
            print(
                f"📈 Seeded synthetic metrics for {', '.join(result['generated_patients'])}"
            )
        except Exception as e:
            logger.warning(f"Synthetic seeding failed: {e}")

    if os.getenv("CSV_INGESTION_POLLING_ENABLED", "false").lower() == "true":
        csv_path = os.getenv("CSV_INGESTION_CSV_PATH", "/app/sample-data/live_sensor_stream.csv")
        interval_seconds = int(os.getenv("CSV_INGESTION_POLL_INTERVAL_SECONDS", "1"))
        job_prefix = os.getenv("CSV_INGESTION_JOB_PREFIX", "graphql_csv")
        csv_polling_task = asyncio.create_task(
            _csv_polling_loop(csv_path, interval_seconds, job_prefix)
        )
        logger.info(
            "CSV polling started (path=%s, interval=%ss)",
            csv_path,
            interval_seconds,
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global csv_polling_task

    if csv_polling_task is not None:
        csv_polling_task.cancel()
        try:
            await csv_polling_task
        except asyncio.CancelledError:
            pass
        csv_polling_task = None

    print("❌ PostureCare GraphQL API stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
