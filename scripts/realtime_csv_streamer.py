#!/usr/bin/env python3
"""
Generate synthetic PostureCare rows every second and append to a CSV file.

The GraphQL API can poll and ingest this CSV continuously to publish
metrics into Prometheus.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import random
import time
from typing import Dict


CSV_HEADERS = [
    "patient_id",
    "session_id",
    "measurement_id",
    "timestamp",
    "imu_id",
    "roll_deg",
    "pitch_deg",
    "yaw_deg",
    "acc_rms_mg",
    "gyro_rms_mdps",
    "emg_id",
    "rms_uv",
    "mav_uv",
    "iemg_uvs",
    "mdf_cHz",
    "mnf_cHz",
    "activation_q15",
    "smo2_id",
    "smo2_cPct",
    "trend_cPct_per_min",
    "quality_q15",
    "battery_mV",
    "battery_pct",
    "charge_state",
    "uptime_s",
    "temp_cC",
    "heap_free",
    "error_flags",
]


def ensure_csv_with_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writeheader()


def _bounded(value: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(max_v, value))


def build_row(patient_id: str, session_id: str, measurement_id: str, uptime_s: int) -> Dict[str, object]:
    now = datetime.utcnow().isoformat(timespec="seconds")

    roll_deg = round(random.gauss(0.0, 4.0), 2)
    pitch_deg = round(random.gauss(-14.0, 8.5), 2)
    yaw_deg = round(random.gauss(0.0, 6.0), 2)

    acc_rms_mg = int(_bounded(random.gauss(950, 220), 200, 16000))
    gyro_rms_mdps = int(_bounded(random.gauss(23000, 5000), 5000, 200000))

    rms_uv = int(_bounded(random.gauss(780, 230), 50, 2000))
    mav_uv = int(_bounded(rms_uv * random.uniform(0.72, 0.88), 30, 2000))
    iemg_uvs = int(_bounded(rms_uv * random.uniform(18, 30), 1000, 100000))
    mdf_cHz = int(_bounded(random.gauss(8600, 750), 2000, 15000))
    mnf_cHz = int(_bounded(random.gauss(9000, 700), 2000, 15000))
    activation_q15 = int(_bounded(random.gauss(14500, 6200), 500, 32767))

    smo2_cPct = int(_bounded(random.gauss(7350, 620), 4500, 9800))
    trend_cPct_per_min = round(_bounded(random.gauss(-0.08, 0.18), -5.0, 5.0), 2)
    quality_q15 = int(_bounded(random.gauss(28400, 1800), 10000, 32767))

    battery_pct = int(_bounded(random.gauss(82, 7), 10, 100))
    battery_mV = int(3000 + (battery_pct / 100.0) * 1200)
    temp_cC = round(_bounded(random.gauss(36.2, 0.7), 20.0, 60.0), 2)
    heap_free = int(_bounded(random.gauss(15600, 900), 9000, 30000))

    error_flags = 0
    if battery_pct < 18:
        error_flags |= 0x02
    if temp_cC > 45:
        error_flags |= 0x01
    if heap_free < 11000:
        error_flags |= 0x04

    return {
        "patient_id": patient_id,
        "session_id": session_id,
        "measurement_id": measurement_id,
        "timestamp": now,
        "imu_id": 1,
        "roll_deg": roll_deg,
        "pitch_deg": pitch_deg,
        "yaw_deg": yaw_deg,
        "acc_rms_mg": acc_rms_mg,
        "gyro_rms_mdps": gyro_rms_mdps,
        "emg_id": 1,
        "rms_uv": rms_uv,
        "mav_uv": mav_uv,
        "iemg_uvs": iemg_uvs,
        "mdf_cHz": mdf_cHz,
        "mnf_cHz": mnf_cHz,
        "activation_q15": activation_q15,
        "smo2_id": 1,
        "smo2_cPct": smo2_cPct,
        "trend_cPct_per_min": trend_cPct_per_min,
        "quality_q15": quality_q15,
        "battery_mV": battery_mV,
        "battery_pct": battery_pct,
        "charge_state": 2,
        "uptime_s": uptime_s,
        "temp_cC": temp_cC,
        "heap_free": heap_free,
        "error_flags": error_flags,
    }


def run_stream(csv_path: Path, interval_seconds: float) -> None:
    ensure_csv_with_header(csv_path)

    patients = ["patient_001", "patient_002", "patient_003"]
    measurement_idx = 1
    uptime = 3600

    sessions: Dict[str, str] = {
        pid: f"session_{datetime.utcnow().strftime('%Y_%m_%d_%H%M')}_{pid[-3:]}" for pid in patients
    }

    print(f"Streaming synthetic rows to {csv_path} every {interval_seconds:.2f}s")

    while True:
        patient_id = patients[(measurement_idx - 1) % len(patients)]
        session_id = sessions[patient_id]
        measurement_id = f"m{measurement_idx:06d}"

        row = build_row(patient_id, session_id, measurement_id, uptime)

        with csv_path.open("a", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writerow(row)

        measurement_idx += 1
        uptime += int(interval_seconds)
        time.sleep(max(0.1, interval_seconds))


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous CSV row generator for PostureCare")
    parser.add_argument(
        "--csv-path",
        default="sample-data/live_sensor_stream.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Generation interval in seconds",
    )

    args = parser.parse_args()
    run_stream(Path(args.csv_path), args.interval)


if __name__ == "__main__":
    main()
