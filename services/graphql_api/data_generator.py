"""
PostureCare Data Generator
Generates realistic synthetic wearable sensor data for testing
Simulates: posture changes, muscle fatigue, oxygen saturation trends
"""

import random
import math
from datetime import datetime, timedelta
from typing import List
import sys

sys.path.insert(0, '/c/Users/manue/Downloads/ISEP2526/PostureCare')

from scripts.data_models import (
    BLEFrameHeader, IMUData, EMGData, SmO2Data, ESP32Status,
    SensorFrame, MessageType, ChargeState
)


class SyntheticDataGenerator:
    """
    Generate realistic synthetic wearable sensor data

    Patterns:
    - Patient 001: Controlled posture, occasional fatigue
    - Patient 002: High fatigue risk, poor posture, low O2
    - Patient 003: Excellent baseline, consistent data
    """

    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed"""
        random.seed(seed)
        self.sequence = 0

    def _increment_sequence(self) -> int:
        """Get next sequence number (0-65535 with wrap)"""
        self.sequence = (self.sequence + 1) % 65536
        return self.sequence

    def _brownian_motion(self, start: float, min_val: float, max_val: float, step_size: float) -> float:
        """Generate brownian motion value (smooth transitions)"""
        change = random.gauss(0, step_size)
        new_val = start + change
        return max(min_val, min(max_val, new_val))

    def _generate_imu_data(self, patient_id: str, measurement_num: int, fatigue_level: float = 0.0) -> IMUData:
        """
        Generate IMU data with realistic posture patterns

        fatigue_level: 0.0 = good posture, 1.0 = poor posture
        """
        if patient_id == "patient_001":
            # Controlled posture with occasional strain
            base_pitch = -15.0 + fatigue_level * 8
            pitch = base_pitch + random.gauss(0, 2.0)
            roll = random.gauss(0.5, 1.5)
            acc = 800 + int(fatigue_level * 300)

        elif patient_id == "patient_002":
            # Poor posture, high variability, high fatigue
            fatigue_effect = min(1.0, (measurement_num % 10) / 10.0)  # Ramps up fatigue
            base_pitch = -12.0 + fatigue_effect * 18  # -12 to +6
            pitch = base_pitch + random.gauss(0, 3.0)
            roll = random.gauss(1.2, 2.0)
            acc = 950 + int(fatigue_effect * 350)

        else:  # patient_003
            # Excellent baseline - very stable
            pitch = random.gauss(-9.0, 0.8)
            roll = random.gauss(0.3, 0.5)
            acc = 600 + random.randint(-50, 50)

        yaw = random.gauss(0, 2.0)
        gyro = 12000 + int(fatigue_level * 10000) + random.randint(-1000, 1000)

        return IMUData(
            imu_id=1,
            roll_deg=max(-180, min(180, roll)),
            pitch_deg=max(-180, min(180, pitch)),
            yaw_deg=max(-180, min(180, yaw)),
            acc_rms_mg=max(0, min(16000, acc)),
            gyro_rms_mdps=max(0, min(200000, gyro)),
        )

    def _generate_emg_data(self, patient_id: str, measurement_num: int, fatigue_level: float = 0.0) -> EMGData:
        """
        Generate EMG data with fatigue simulation

        Key fields:
        - iemg_uvs: Integral EMG (higher = more muscle activity)
        - activation_q15: Normalized activation level
        """
        if patient_id == "patient_001":
            # Normal muscle activation
            base_rms = 500 + int(fatigue_level * 200)
            base_activation = 10000 + int(fatigue_level * 8000)

        elif patient_id == "patient_002":
            # High fatigue, increasing activation
            fatigue_effect = min(1.0, (measurement_num % 10) / 10.0)
            base_rms = 800 + int(fatigue_effect * 400)
            base_activation = 15000 + int(fatigue_effect * 15000)

        else:  # patient_003
            # Baseline activation
            base_rms = 300
            base_activation = 5000

        rms = base_rms + random.randint(-50, 50)
        mav = int(rms * 0.8)  # MAV is typically 80% of RMS
        iemg = int(base_rms * 20) + random.randint(-1000, 1000)
        activation = min(32767, base_activation + random.randint(-1000, 1000))

        # Frequency decreases with fatigue (median frequency shift)
        mdf = 9000 - int(fatigue_level * 1500)  # 9000 -> 7500 Hz
        mnf = 9200 - int(fatigue_level * 1200)

        return EMGData(
            emg_id=1,
            rms_uv=max(0, min(2000, rms)),
            mav_uv=max(0, min(2000, mav)),
            iemg_uvs=max(0, min(100000, iemg)),
            mdf_cHz=int(mdf),
            mnf_cHz=int(mnf),
            activation_q15=min(32767, activation),
        )

    def _generate_smo2_data(self, patient_id: str, measurement_num: int, fatigue_level: float = 0.0) -> SmO2Data:
        """
        Generate SmO2 (oxygen saturation) data

        High fatigue + high muscle activation = low O2
        """
        if patient_id == "patient_001":
            # Good O2 saturation with slight decrease during activity
            base_smo2 = 7500 - int(fatigue_level * 1500)  # 75% -> 60%
            trend = -0.05 if fatigue_level > 0.5 else 0.02

        elif patient_id == "patient_002":
            # Poor O2 during high activity periods
            fatigue_effect = min(1.0, (measurement_num % 10) / 10.0)
            base_smo2 = 7000 - int(fatigue_effect * 2500)  # 70% -> 45%
            trend = -0.20 if fatigue_effect > 0.5 else -0.05

        else:  # patient_003
            # Excellent O2 saturation
            base_smo2 = 7800
            trend = 0.01

        smo2 = max(0, min(10000, base_smo2 + random.randint(-200, 200)))
        quality = 28000 + random.randint(-2000, 2000)

        return SmO2Data(
            smo2_id=1,
            smo2_cPct=max(0, min(10000, smo2)),
            trend_cPct_per_min=trend + random.gauss(0, 0.05),
            quality_q15=max(0, min(32767, quality)),
        )

    def _generate_esp32_status(self, battery_pct: int = None, temp_cC: float = None) -> ESP32Status:
        """Generate ESP32 device status"""
        if battery_pct is None:
            battery_pct = random.randint(78, 100)

        if temp_cC is None:
            temp_cC = 35.0 + random.gauss(0.5, 0.3)

        battery_mV = int(3000 + (battery_pct / 100.0) * 1200)  # 3000-4200 mV

        return ESP32Status(
            battery_mV=battery_mV,
            battery_pct=battery_pct,
            charge_state=ChargeState.DISCHARGING,
            uptime_s=random.randint(3600, 86400),
            temp_cC=max(15, min(50, temp_cC)),
            heap_free=random.randint(14000, 16000),
            error_flags=0,
        )

    def generate_frame(
        self,
        patient_id: str,
        session_id: str,
        measurement_id: str,
        timestamp: datetime,
        fatigue_level: float = 0.0,
    ) -> SensorFrame:
        """Generate single sensor frame"""
        frame_header = BLEFrameHeader(
            magic=0x5043,
            version=1,
            msg_type=MessageType.SENSOR,
            sequence=self._increment_sequence(),
            timestamp_ms=int(timestamp.timestamp() * 1000),
            payload_length=0,
            crc16=0,
        )

        imu = self._generate_imu_data(patient_id, int(measurement_id[1:]), fatigue_level)
        emg = self._generate_emg_data(patient_id, int(measurement_id[1:]), fatigue_level)
        smo2 = self._generate_smo2_data(patient_id, int(measurement_id[1:]), fatigue_level)
        status = self._generate_esp32_status()

        frame = SensorFrame(
            patient_id=patient_id,
            session_id=session_id,
            measurement_id=measurement_id,
            timestamp=timestamp,
            frame_header=frame_header,
            imu=imu,
            emg=emg,
            smo2=smo2,
            status=status,
        )

        return frame

    def generate_session(
        self,
        patient_id: str,
        session_id: str,
        num_measurements: int = 30,
        start_time: datetime = None,
        interval_seconds: int = 60,
    ) -> List[SensorFrame]:
        """
        Generate complete session with realistic patterns

        patient_001: Stable, occasional peaks
        patient_002: Deteriorating posture, high fatigue
        patient_003: Excellent baseline
        """
        if start_time is None:
            start_time = datetime.now()

        frames = []

        # Generate fatigue curve based on patient
        if patient_id == "patient_001":
            # Stable with slight variation
            fatigue_curve = [0.0 + random.gauss(0, 0.1) for _ in range(num_measurements)]
            fatigue_curve[3:6] = [0.5, 0.7, 0.4]  # Brief peak

        elif patient_id == "patient_002":
            # Increasing fatigue
            fatigue_curve = [min(1.0, i / (num_measurements * 0.7)) for i in range(num_measurements)]
            fatigue_curve[4:8] = [0.7, 0.8, 0.9, 0.85]  # High zone

        else:  # patient_003
            # Baseline, minimal variation
            fatigue_curve = [random.gauss(0.1, 0.05) for _ in range(num_measurements)]

        for i in range(num_measurements):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            measurement_id = f"m{str(i+1).zfill(3)}"

            frame = self.generate_frame(
                patient_id=patient_id,
                session_id=session_id,
                measurement_id=measurement_id,
                timestamp=timestamp,
                fatigue_level=max(0, min(1.0, fatigue_curve[i])),
            )
            frames.append(frame)

        return frames

    def generate_multiple_sessions(
        self,
        patient_ids: List[str] = None,
        num_measurements: int = 30,
        start_time: datetime = None,
    ) -> dict:
        """Generate sessions for multiple patients"""
        if patient_ids is None:
            patient_ids = ["patient_001", "patient_002", "patient_003"]

        if start_time is None:
            start_time = datetime(2026, 4, 1, 10, 0, 0)

        result = {}
        current_time = start_time

        for patient_id in patient_ids:
            session_id = f"session_{current_time.strftime('%Y_%m_%d_%H%M')}"
            frames = self.generate_session(
                patient_id=patient_id,
                session_id=session_id,
                num_measurements=num_measurements,
                start_time=current_time,
            )
            result[patient_id] = {
                "session_id": session_id,
                "frames": frames,
            }
            current_time += timedelta(hours=1)

        return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def demo_generate():
    """Demo: Generate sample data"""
    generator = SyntheticDataGenerator()

    # Generate session for patient_001
    print("🔧 Generating synthetic data...")
    frames = generator.generate_session(
        patient_id="patient_001",
        session_id="session_demo_001",
        num_measurements=10,
    )

    print(f"\n✅ Generated {len(frames)} frames")
    for frame in frames[:3]:
        print(f"\nFrame: {frame.measurement_id}")
        print(f"  Pitch: {frame.imu.pitch_deg:.1f}°")
        print(f"  EMG Activation: {frame.emg.activation_q15}")
        print(f"  SmO2: {frame.smo2.smo2_percent:.1f}%")
        print(f"  Alert worthy: {frame.is_alert_worthy}")
        if frame.alert_reasons:
            print(f"  Reasons: {', '.join(frame.alert_reasons)}")
