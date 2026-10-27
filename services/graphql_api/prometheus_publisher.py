"""
PostureCare Prometheus Publisher
Converts SensorFrame objects to Prometheus metrics and publishes to Push Gateway
"""

from typing import List
import requests
from datetime import datetime
import sys

sys.path.insert(0, '/c/Users/manue/Downloads/ISEP2526/PostureCare')

from scripts.data_models import SensorFrame, SensorBatch


class PrometheusPublisher:
    """
    Convert sensor frames to Prometheus metrics and push to Push Gateway
    """

    def __init__(self, push_gateway_url: str = "http://localhost:9091"):
        self.push_gateway_url = push_gateway_url
        self.job_name = "posture_graphql"
        self.metrics_lines = []

    def _add_metric(
        self,
        metric_name: str,
        value: float,
        labels: dict = None,
        metric_type: str = "gauge",
    ):
        """Add metric line"""
        # Format: metric_name{label1="value1",label2="value2"} value
        label_str = ""
        if labels:
            label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
            label_str = "{" + ",".join(label_pairs) + "}"

        line = f"{metric_name}{label_str} {value}"
        self.metrics_lines.append(line)

    def frame_to_metrics(self, frame: SensorFrame):
        """Convert SensorFrame to Prometheus metrics"""
        base_labels = {
            "patient_id": frame.patient_id,
            "session_id": frame.session_id,
            "measurement_id": frame.measurement_id,
        }

        timestamp_ms = int(frame.timestamp.timestamp() * 1000)

        # ====== POSTURE METRICS (Dashboard-compatible) ======
        spine_angle = abs(frame.imu.pitch_deg)
        self._add_metric(
            "posture_spine_angle",
            spine_angle,
            base_labels,
        )
        self._add_metric(
            "posture_shoulder_roll",
            frame.imu.roll_deg,
            base_labels,
        )
        self._add_metric(
            "posture_head_tilt",
            frame.imu.yaw_deg,
            base_labels,
        )

        # ====== IMU METRICS ======
        self._add_metric(
            "posture_imu_roll_degrees",
            frame.imu.roll_deg,
            {**base_labels, "imu_id": str(frame.imu.imu_id)},
        )
        self._add_metric(
            "posture_imu_pitch_degrees",
            frame.imu.pitch_deg,
            {**base_labels, "imu_id": str(frame.imu.imu_id)},
        )
        self._add_metric(
            "posture_imu_yaw_degrees",
            frame.imu.yaw_deg,
            {**base_labels, "imu_id": str(frame.imu.imu_id)},
        )
        self._add_metric(
            "posture_imu_acc_rms_mg",
            frame.imu.acc_rms_mg,
            {**base_labels, "imu_id": str(frame.imu.imu_id)},
        )
        self._add_metric(
            "posture_imu_gyro_rms_mdps",
            frame.imu.gyro_rms_mdps,
            {**base_labels, "imu_id": str(frame.imu.imu_id)},
        )

        # ====== EMG METRICS ======
        self._add_metric(
            "posture_emg_rms_uv",
            frame.emg.rms_uv,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_mav_uv",
            frame.emg.mav_uv,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_iemg_uvs",
            frame.emg.iemg_uvs,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_mdf_cHz",
            frame.emg.mdf_cHz,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_mnf_cHz",
            frame.emg.mnf_cHz,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_activation_q15",
            frame.emg.activation_q15,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )
        self._add_metric(
            "posture_emg_activation_normalized",
            frame.emg.activation_q15 / 32767.0,
            {**base_labels, "emg_id": str(frame.emg.emg_id)},
        )

        # ====== SMO2 METRICS ======
        self._add_metric(
            "posture_smo2_percent",
            frame.smo2.smo2_percent,
            {**base_labels, "smo2_id": str(frame.smo2.smo2_id)},
        )
        self._add_metric(
            "posture_smo2_trend_percent_per_min",
            frame.smo2.trend_cPct_per_min,
            {**base_labels, "smo2_id": str(frame.smo2.smo2_id)},
        )
        self._add_metric(
            "posture_smo2_quality_normalized",
            frame.smo2.quality_normalized,
            {**base_labels, "smo2_id": str(frame.smo2.smo2_id)},
        )

        # ====== ESP32 STATUS METRICS ======
        self._add_metric(
            "device_battery_mv",
            frame.status.battery_mV,
            base_labels,
        )
        self._add_metric(
            "device_battery_percent",
            frame.status.battery_pct,
            base_labels,
        )
        self._add_metric(
            "device_temp_cC",
            frame.status.temp_cC,
            base_labels,
        )
        self._add_metric(
            "device_uptime_seconds",
            frame.status.uptime_s,
            base_labels,
        )
        self._add_metric(
            "device_heap_free_bytes",
            frame.status.heap_free,
            base_labels,
        )

        # ====== ALERT METRICS ======
        if frame.is_alert_worthy:
            self._add_metric(
                "posture_alert_triggered",
                1,
                {
                    **base_labels,
                    "reason": frame.alert_reasons[0] if frame.alert_reasons else "unknown",
                },
            )

    def batch_to_metrics(self, batch: SensorBatch):
        """Convert SensorBatch to Prometheus metrics"""
        self.metrics_lines = []

        # Add individual frame metrics
        for frame in batch.frames:
            self.frame_to_metrics(frame)

        # Add batch summary metrics
        self._add_metric(
            "posture_monitoring_active",
            1,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )
        self._add_metric(
            "posture_measurement_count",
            batch.frame_count,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )
        self._add_metric(
            "posture_alert_count",
            batch.alert_count,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )
        self._add_metric(
            "posture_session_frame_count",
            batch.frame_count,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )
        self._add_metric(
            "posture_session_alert_count",
            batch.alert_count,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )
        self._add_metric(
            "posture_session_alert_rate_percent",
            batch.alert_rate,
            {
                "patient_id": batch.patient_id,
                "session_id": batch.session_id,
            },
        )

    def get_prometheus_text(self) -> str:
        """Get metrics in Prometheus text format"""
        if not self.metrics_lines:
            return ""
        return "\n".join(self.metrics_lines) + "\n"

    def push_to_gateway(self) -> bool:
        """Push metrics to Prometheus Push Gateway"""
        if not self.metrics_lines:
            print("⚠️  No metrics to push")
            return False

        metrics_text = self.get_prometheus_text()
        url = f"{self.push_gateway_url}/metrics/job/{self.job_name}"

        try:
            response = requests.post(
                url,
                data=metrics_text,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=5,
            )
            response.raise_for_status()
            print(f"✅ Pushed {len(self.metrics_lines)} metrics to Push Gateway")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to push metrics: {str(e)}")
            return False

    def save_metrics(self, output_path: str) -> bool:
        """Save metrics to file"""
        try:
            with open(output_path, 'w') as f:
                f.write(self.get_prometheus_text())
            print(f"💾 Saved {len(self.metrics_lines)} metrics to {output_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to save metrics: {str(e)}")
            return False

    def print_metrics(self, limit: int = 20):
        """Print first N metrics"""
        print(f"\n📊 Prometheus Metrics (showing first {min(limit, len(self.metrics_lines))}/{len(self.metrics_lines)}):")
        print("=" * 80)
        for line in self.metrics_lines[:limit]:
            print(line)
        if len(self.metrics_lines) > limit:
            print(f"... and {len(self.metrics_lines) - limit} more")
