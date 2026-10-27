"""
PostureCare CSV Parser V2 - Full Sensor Data Format

Parses CSV with complete BLE frame structure (IMU, EMG, SmO2, ESP32 status)
"""

import csv
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json
from scripts.data_models import (
    BLEFrameHeader,
    IMUData,
    EMGData,
    SmO2Data,
    ESP32Status,
    SensorFrame,
    SensorBatch,
    MessageType,
    ChargeState,
)


class CSVParserV2:
    """
    Parse CSV with full wearable sensor data (v2 format)

    CSV Columns (21 total):
    - metadata: patient_id, session_id, measurement_id, timestamp
    - imu: imu_id, roll_deg, pitch_deg, yaw_deg, acc_rms_mg, gyro_rms_mdps
    - emg: emg_id, rms_uv, mav_uv, iemg_uvs, mdf_cHz, mnf_cHz, activation_q15
    - smo2: smo2_id, smo2_cPct, trend_cPct_per_min, quality_q15
    - esp32: battery_mV, battery_pct, charge_state, uptime_s, temp_cC, heap_free, error_flags
    """

    EXPECTED_COLUMNS = {
        # Metadata (4)
        'patient_id': str,
        'session_id': str,
        'measurement_id': str,
        'timestamp': str,

        # IMU (6)
        'imu_id': int,
        'roll_deg': float,
        'pitch_deg': float,
        'yaw_deg': float,
        'acc_rms_mg': int,
        'gyro_rms_mdps': int,

        # EMG (7)
        'emg_id': int,
        'rms_uv': int,
        'mav_uv': int,
        'iemg_uvs': int,
        'mdf_cHz': int,
        'mnf_cHz': int,
        'activation_q15': int,

        # SmO2 (4)
        'smo2_id': int,
        'smo2_cPct': int,
        'trend_cPct_per_min': float,
        'quality_q15': int,

        # ESP32 Status (7)
        'battery_mV': int,
        'battery_pct': int,
        'charge_state': int,
        'uptime_s': int,
        'temp_cC': float,
        'heap_free': int,
        'error_flags': int,
    }

    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []

    def validate_headers(self, headers: List[str]) -> Tuple[bool, str]:
        """Validate CSV headers"""
        expected = set(self.EXPECTED_COLUMNS.keys())
        found = set(headers)

        missing = expected - found
        extra = found - expected

        if missing:
            msg = f"Missing columns: {', '.join(sorted(missing))}"
            return False, msg

        if extra:
            msg = f"Extra columns (will be ignored): {', '.join(sorted(extra))}"
            self.warnings.append({'type': 'extra_columns', 'message': msg})

        return True, "Headers valid"

    def parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse ISO 8601 timestamp"""
        try:
            return datetime.fromisoformat(ts_str.strip())
        except ValueError:
            return None

    def validate_row(self, row: Dict, row_num: int) -> Tuple[bool, str]:
        """Validate single CSV row"""
        try:
            # Check for empty cells
            for key, value in row.items():
                if key in self.EXPECTED_COLUMNS and not value:
                    return False, f"Empty cell in column '{key}'"

            # Type conversions and validation
            for col_name, col_type in self.EXPECTED_COLUMNS.items():
                if col_name not in row:
                    return False, f"Missing column '{col_name}'"

                value_str = row[col_name].strip()

                try:
                    if col_type == str:
                        if not value_str:
                            return False, f"Empty string in '{col_name}'"
                    elif col_type == int:
                        int(value_str)
                    elif col_type == float:
                        float(value_str)
                except ValueError:
                    return False, f"Invalid {col_type.__name__} in '{col_name}': '{value_str}'"

            # Special validation for timestamp
            if not self.parse_timestamp(row['timestamp']):
                return False, "Invalid timestamp (expected ISO 8601)"

            # Timestamp must be in reasonable range
            ts = self.parse_timestamp(row['timestamp'])
            if ts and ts.year < 2000 or ts.year > 2100:
                return False, f"Timestamp year out of range: {ts.year}"

            return True, "Row valid"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def row_to_sensor_frame(self, row: Dict) -> Tuple[Optional[SensorFrame], str]:
        """Convert CSV row to SensorFrame"""
        try:
            # Parse timestamp
            ts = self.parse_timestamp(row['timestamp'])
            if not ts:
                return None, "Failed to parse timestamp"

            # Create BLE Frame Header
            frame_header = BLEFrameHeader(
                magic=0x5043,
                version=1,
                msg_type=MessageType.SENSOR,
                sequence=0,  # Will be set by device
                timestamp_ms=int(ts.timestamp() * 1000),
                payload_length=0,  # Variable
                crc16=0,  # Will be calculated by device
            )

            # Create IMU Data
            imu = IMUData(
                imu_id=int(row['imu_id']),
                roll_deg=float(row['roll_deg']),
                pitch_deg=float(row['pitch_deg']),
                yaw_deg=float(row['yaw_deg']),
                acc_rms_mg=int(row['acc_rms_mg']),
                gyro_rms_mdps=int(row['gyro_rms_mdps']),
            )

            if not imu.validate():
                return None, "IMU data out of range"

            # Create EMG Data
            emg = EMGData(
                emg_id=int(row['emg_id']),
                rms_uv=int(row['rms_uv']),
                mav_uv=int(row['mav_uv']),
                iemg_uvs=int(row['iemg_uvs']),
                mdf_cHz=int(row['mdf_cHz']),
                mnf_cHz=int(row['mnf_cHz']),
                activation_q15=int(row['activation_q15']),
            )

            if not emg.validate():
                return None, "EMG data out of range"

            # Create SmO2 Data
            smo2 = SmO2Data(
                smo2_id=int(row['smo2_id']),
                smo2_cPct=int(row['smo2_cPct']),
                trend_cPct_per_min=float(row['trend_cPct_per_min']),
                quality_q15=int(row['quality_q15']),
            )

            if not smo2.validate():
                return None, "SmO2 data out of range"

            # Create ESP32 Status
            charge_state_val = int(row['charge_state'])
            status = ESP32Status(
                battery_mV=int(row['battery_mV']),
                battery_pct=int(row['battery_pct']),
                charge_state=ChargeState(charge_state_val),
                uptime_s=int(row['uptime_s']),
                temp_cC=float(row['temp_cC']),
                heap_free=int(row['heap_free']),
                error_flags=int(row['error_flags']),
            )

            if not status.validate():
                return None, "ESP32 status data out of range"

            # Create SensorFrame
            frame = SensorFrame(
                patient_id=row['patient_id'].strip(),
                session_id=row['session_id'].strip(),
                measurement_id=row['measurement_id'].strip(),
                timestamp=ts,
                frame_header=frame_header,
                imu=imu,
                emg=emg,
                smo2=smo2,
                status=status,
            )

            # Validate complete frame
            is_valid, errors = frame.validate()
            if not is_valid:
                return None, f"Frame validation failed: {', '.join(errors)}"

            return frame, "OK"

        except Exception as e:
            return None, f"Error converting row: {str(e)}"

    def read_csv(self, csv_path: str) -> Tuple[List[SensorFrame], int]:
        """
        Read and parse CSV file

        Returns:
            (list of valid frames, number of rows with errors)
        """
        frames = []
        error_count = 0
        self.errors = []
        self.warnings = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate headers
                if not reader.fieldnames:
                    return [], -1

                valid, msg = self.validate_headers(reader.fieldnames)
                if not valid:
                    self.errors.append({'type': 'headers', 'message': msg})
                    return [], -1

                # Process rows
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
                    # Validate row
                    valid, msg = self.validate_row(row, row_num)
                    if not valid:
                        error_count += 1
                        self.errors.append({
                            'row': row_num,
                            'message': msg,
                            'data': row
                        })
                        continue

                    # Convert to SensorFrame
                    frame, msg = self.row_to_sensor_frame(row)
                    if frame is None:
                        error_count += 1
                        self.errors.append({
                            'row': row_num,
                            'message': f"Conversion failed: {msg}",
                            'data': row
                        })
                        continue

                    frames.append(frame)

        except FileNotFoundError:
            self.errors.append({'type': 'file', 'message': f"File not found: {csv_path}"})
            return [], -1
        except Exception as e:
            self.errors.append({'type': 'read', 'message': f"Error reading file: {str(e)}"})
            return [], -1

        return frames, error_count

    def frames_to_batch(self, frames: List[SensorFrame]) -> SensorBatch:
        """Convert list of frames to SensorBatch"""
        if not frames:
            batch = SensorBatch(session_id="", patient_id="")
        else:
            batch = SensorBatch(
                session_id=frames[0].session_id,
                patient_id=frames[0].patient_id,
            )
            for frame in frames:
                batch.add_frame(frame)

        return batch

    def print_report(self):
        """Print parsing report"""
        print("\n" + "="*60)
        print("CSV PARSING REPORT")
        print("="*60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - Row {error.get('row', 'N/A')}: {error.get('message')}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:5]:
                print(f"  - {warning.get('message')}")

        print()

    def save_frames_json(self, frames: List[SensorFrame], output_path: str):
        """Save frames to JSON file"""
        batch = self.frames_to_batch(frames)
        with open(output_path, 'w') as f:
            json.dump(batch.to_dict(), f, indent=2)
