"""
PostureCare Data Models - BLE Frame Structure (V0.1)

Based on: PostureCare_estrutura de dados_V0.1.pdf
Implements all sensor types: IMU, EMG, SmO2, ESP32 Status, Actuator Commands
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json


# ============================================================================
# ENUMS
# ============================================================================

class MessageType(Enum):
    """BLE Frame message types"""
    SENSOR = 1
    COMMAND = 2
    ACK = 3
    STATUS = 4


class ActuatorMode(Enum):
    """Fiber actuator modes"""
    STOP = "STOP"
    SET = "SET"
    PATTERN = "PATTERN"
    RAMP = "RAMP"


class ChargeState(Enum):
    """Battery charge states"""
    UNKNOWN = 0
    CHARGING = 1
    DISCHARGING = 2


# ============================================================================
# BLE FRAME HEADER (8 bytes)
# ============================================================================

@dataclass
class BLEFrameHeader:
    """
    BLE Frame Header - Generic frame structure for all message types
    Total: 8 bytes header + variable payload
    """
    magic: int              # u16: 0x5043 = "PC" (PostureCare)
    version: int            # u8: Protocol version (currently 1)
    msg_type: MessageType   # u8: 1=Sensor, 2=Cmd, 3=Ack, 4=Status
    sequence: int           # u16: Counter 0-65535 (detects lost frames)
    timestamp_ms: int       # u32: Milliseconds since epoch
    payload_length: int     # u16: Payload size (0-512 bytes)
    crc16: int             # u16: CRC-16 checksum

    @property
    def is_valid(self) -> bool:
        """Validate frame header"""
        return (
            self.magic == 0x5043 and
            self.version == 1 and
            0 <= self.payload_length <= 512 and
            0 <= self.sequence <= 65535
        )

    def to_dict(self) -> dict:
        return {
            "magic": hex(self.magic),
            "version": self.version,
            "msg_type": self.msg_type.name,
            "sequence": self.sequence,
            "timestamp_ms": self.timestamp_ms,
            "payload_length": self.payload_length,
            "crc16": self.crc16,
        }


# ============================================================================
# SENSOR DATA PAYLOADS
# ============================================================================

@dataclass
class IMUData:
    """
    Inertial Measurement Unit Data
    Measures 3D orientation and acceleration
    """
    imu_id: int           # u8: Sensor ID (0-255)
    roll_deg: float       # i16 with 0.01° resolution: -180 to +180°
    pitch_deg: float      # i16 with 0.01° resolution: -180 to +180°
    yaw_deg: float        # i16 with 0.01° resolution: -180 to +180°
    acc_rms_mg: int       # u16: RMS acceleration in mg (0-16000)
    gyro_rms_mdps: int    # u16: RMS angular velocity in mdps (0-200000)

    def validate(self) -> bool:
        """Validate IMU data ranges"""
        return (
            0 <= self.imu_id <= 255 and
            -180 <= self.roll_deg <= 180 and
            -180 <= self.pitch_deg <= 180 and
            -180 <= self.yaw_deg <= 180 and
            0 <= self.acc_rms_mg <= 16000 and
            0 <= self.gyro_rms_mdps <= 200000
        )

    def to_dict(self) -> dict:
        return {
            "imu_id": self.imu_id,
            "roll_deg": round(self.roll_deg, 2),
            "pitch_deg": round(self.pitch_deg, 2),
            "yaw_deg": round(self.yaw_deg, 2),
            "acc_rms_mg": self.acc_rms_mg,
            "gyro_rms_mdps": self.gyro_rms_mdps,
        }


@dataclass
class EMGData:
    """
    Electromyography Data
    Measures muscle electrical activity for posture/fatigue detection
    Key field: iemg_uvs (integral - highlighted in PDF)
    """
    emg_id: int           # u8: Sensor ID (0-255)
    rms_uv: int           # u16: RMS amplitude in µV (0-2000)
    mav_uv: int           # u16: Mean absolute value in µV (0-2000)
    iemg_uvs: int         # u32: Integral EMG activity (0-100000 µV·s) ⭐ KEY
    mdf_cHz: int          # u16: Median frequency in 0.01Hz (2000-15000)
    mnf_cHz: int          # u16: Mean frequency in 0.01Hz (2000-15000)
    activation_q15: int   # u16: Normalized activation Q15 (0-32767) ⭐ KEY

    def validate(self) -> bool:
        """Validate EMG data ranges"""
        return (
            0 <= self.emg_id <= 255 and
            0 <= self.rms_uv <= 2000 and
            0 <= self.mav_uv <= 2000 and
            0 <= self.iemg_uvs <= 100000 and
            2000 <= self.mdf_cHz <= 15000 and
            2000 <= self.mnf_cHz <= 15000 and
            0 <= self.activation_q15 <= 32767
        )

    def to_dict(self) -> dict:
        return {
            "emg_id": self.emg_id,
            "rms_uv": self.rms_uv,
            "mav_uv": self.mav_uv,
            "iemg_uvs": self.iemg_uvs,
            "mdf_cHz": round(self.mdf_cHz * 0.01, 2),
            "mnf_cHz": round(self.mnf_cHz * 0.01, 2),
            "activation_q15": self.activation_q15,
            "activation_normalized": round(self.activation_q15 / 32767.0, 3),
        }


@dataclass
class SmO2Data:
    """
    Muscle Oxygen Saturation Data
    Measures blood oxygenation via NIRS optical sensors
    """
    smo2_id: int          # u8: Sensor ID (0-255)
    smo2_cPct: int        # u16: SmO2 percentage in 0.01% (0-10000 = 0-100%)
    trend_cPct_per_min: float  # i16 with 0.01%/min: -500 to +500
    quality_q15: int      # u16: Signal quality Q15 (0-32767)

    def validate(self) -> bool:
        """Validate SmO2 data ranges"""
        return (
            0 <= self.smo2_id <= 255 and
            0 <= self.smo2_cPct <= 10000 and
            -500 <= self.trend_cPct_per_min <= 500 and
            0 <= self.quality_q15 <= 32767
        )

    @property
    def smo2_percent(self) -> float:
        """Convert to percentage"""
        return self.smo2_cPct * 0.01

    @property
    def quality_normalized(self) -> float:
        """Normalize quality to 0-1"""
        return self.quality_q15 / 32767.0

    def to_dict(self) -> dict:
        return {
            "smo2_id": self.smo2_id,
            "smo2_percent": round(self.smo2_percent, 2),
            "trend_percent_per_min": round(self.trend_cPct_per_min * 0.01, 3),
            "quality": round(self.quality_normalized, 3),
        }


@dataclass
class ESP32Status:
    """
    ESP32 Device Status
    Monitors battery, temperature, memory, and error conditions
    """
    battery_mV: int       # u16: Battery voltage in mV (3000-4200)
    battery_pct: int      # u8: Battery percentage (0-100%)
    charge_state: ChargeState  # u8: 0=Unknown, 1=Charging, 2=Discharging
    uptime_s: int         # u32: Seconds since last boot
    temp_cC: float        # i16 with 0.01°C: -20 to +60°C
    heap_free: int        # u32: Free RAM in bytes
    error_flags: int      # u32: Error bitmask

    def validate(self) -> bool:
        """Validate ESP32 status ranges"""
        return (
            3000 <= self.battery_mV <= 4200 and
            0 <= self.battery_pct <= 100 and
            0 <= self.uptime_s and
            -20 <= self.temp_cC <= 60 and
            0 <= self.heap_free
        )

    @property
    def has_errors(self) -> bool:
        """Check if any error flags are set"""
        return self.error_flags != 0

    def get_error_list(self) -> List[str]:
        """Decode error flags"""
        errors = []
        if self.error_flags & 0x01:
            errors.append("Temperature out of range")
        if self.error_flags & 0x02:
            errors.append("Battery low")
        if self.error_flags & 0x04:
            errors.append("Memory low")
        if self.error_flags & 0x08:
            errors.append("Sensor fault")
        return errors

    def to_dict(self) -> dict:
        return {
            "battery_mV": self.battery_mV,
            "battery_pct": self.battery_pct,
            "charge_state": self.charge_state.name,
            "uptime_s": self.uptime_s,
            "temp_cC": round(self.temp_cC, 2),
            "heap_free": self.heap_free,
            "error_flags": self.error_flags,
            "errors": self.get_error_list(),
        }


@dataclass
class ActuatorCommand:
    """
    Fiber Actuator Command
    Controls electrical stimulation for posture correction
    """
    fiber_id: int         # u8: Fiber ID (0-255)
    command_id: int       # u16: Unique command ID (0-65535)
    mode: ActuatorMode    # u8: STOP/SET/PATTERN/RAMP
    target_mask: int      # u16: Bitmask - Cerv/Tor/Lomb/L/R
    intensity_q15: int    # u16: Intensity Q15 (0-32767)
    duration_ms: int      # u16: Duration (0-60000 ms)
    pattern_id: int       # u8: Pattern ID (0-255)

    def validate(self) -> bool:
        """Validate actuator command"""
        return (
            0 <= self.fiber_id <= 255 and
            0 <= self.command_id <= 65535 and
            0 <= self.target_mask <= 0xFF and
            0 <= self.intensity_q15 <= 32767 and
            0 <= self.duration_ms <= 60000 and
            0 <= self.pattern_id <= 255
        )

    def to_dict(self) -> dict:
        return {
            "fiber_id": self.fiber_id,
            "command_id": self.command_id,
            "mode": self.mode.value,
            "target_mask": hex(self.target_mask),
            "intensity": round(self.intensity_q15 / 32767.0, 3),
            "duration_ms": self.duration_ms,
            "pattern_id": self.pattern_id,
        }


# ============================================================================
# COMPLETE SENSOR FRAME
# ============================================================================

@dataclass
class SensorFrame:
    """
    Complete PostureCare sensor frame
    Contains all sensor data + metadata
    """
    # Metadata
    patient_id: str       # e.g., "patient_001"
    session_id: str       # e.g., "session_2026_03_31_001"
    measurement_id: str   # e.g., "m001"
    timestamp: datetime   # When data was collected

    # BLE Frame Header
    frame_header: BLEFrameHeader

    # Sensor Payloads
    imu: IMUData
    emg: EMGData
    smo2: SmO2Data
    status: ESP32Status

    # Optional: Actuator commands (ACKs)
    actuator_commands: List[ActuatorCommand] = field(default_factory=list)

    def validate(self) -> tuple[bool, List[str]]:
        """Validate entire frame"""
        errors = []

        if not self.frame_header.is_valid:
            errors.append("Invalid BLE frame header")

        if not self.imu.validate():
            errors.append("Invalid IMU data")

        if not self.emg.validate():
            errors.append("Invalid EMG data")

        if not self.smo2.validate():
            errors.append("Invalid SmO2 data")

        if not self.status.validate():
            errors.append("Invalid ESP32 status")

        for i, cmd in enumerate(self.actuator_commands):
            if not cmd.validate():
                errors.append(f"Invalid actuator command {i}")

        return len(errors) == 0, errors

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "metadata": {
                "patient_id": self.patient_id,
                "session_id": self.session_id,
                "measurement_id": self.measurement_id,
                "timestamp": self.timestamp.isoformat(),
            },
            "frame_header": self.frame_header.to_dict(),
            "imu": self.imu.to_dict(),
            "emg": self.emg.to_dict(),
            "smo2": self.smo2.to_dict(),
            "status": self.status.to_dict(),
            "actuator_commands": [cmd.to_dict() for cmd in self.actuator_commands],
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @property
    def is_alert_worthy(self) -> bool:
        """Determine if frame triggers alerts"""
        # Alert conditions:
        # 1. High muscle activation + low SmO2 (fatigue risk)
        # 2. Poor posture (pitch > 30°)
        # 3. Battery low
        # 4. Temperature out of range
        return (
            self.emg.activation_q15 > 24000 and self.smo2.smo2_percent < 50 or
            self.imu.pitch_deg > 30 or
            self.status.battery_pct < 20 or
            self.status.temp_cC > 45
        )

    @property
    def alert_reasons(self) -> List[str]:
        """Get list of alert reasons"""
        reasons = []
        if self.emg.activation_q15 > 24000 and self.smo2.smo2_percent < 50:
            reasons.append("Muscle fatigue risk (high activation + low O2)")
        if self.imu.pitch_deg > 30:
            reasons.append(f"Poor posture (pitch={self.imu.pitch_deg}°)")
        if self.status.battery_pct < 20:
            reasons.append(f"Battery low ({self.status.battery_pct}%)")
        if self.status.temp_cC > 45:
            reasons.append(f"Temperature high ({self.status.temp_cC}°C)")
        return reasons


# ============================================================================
# BATCH SENSOR DATA (Multiple frames)
# ============================================================================

@dataclass
class SensorBatch:
    """
    Batch of sensor frames from single session
    Used for CSV import/export and GraphQL queries
    """
    session_id: str
    patient_id: str
    frames: List[SensorFrame] = field(default_factory=list)
    timestamp_start: Optional[datetime] = None
    timestamp_end: Optional[datetime] = None

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def alert_count(self) -> int:
        return sum(1 for frame in self.frames if frame.is_alert_worthy)

    @property
    def alert_rate(self) -> float:
        """Percentage of frames with alerts"""
        if not self.frames:
            return 0.0
        return (self.alert_count / self.frame_count) * 100

    def add_frame(self, frame: SensorFrame) -> None:
        """Add frame to batch"""
        self.frames.append(frame)
        if not self.timestamp_start:
            self.timestamp_start = frame.timestamp
        self.timestamp_end = frame.timestamp

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "frame_count": self.frame_count,
            "alert_count": self.alert_count,
            "alert_rate_percent": round(self.alert_rate, 2),
            "timestamp_start": self.timestamp_start.isoformat() if self.timestamp_start else None,
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "frames": [frame.to_dict() for frame in self.frames],
        }
