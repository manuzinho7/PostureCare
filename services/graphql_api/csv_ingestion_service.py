"""
CSV tail ingestion service.

Reads new rows from a CSV file, converts to SensorFrame objects, and publishes
metrics to Prometheus Pushgateway.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv
import re
import sys


# Ensure project root (folder containing scripts/) is importable in both
# local workspace and containerized /app layout.
SERVICE_DIR = Path(__file__).resolve().parent
for candidate in (SERVICE_DIR, SERVICE_DIR.parent.parent):
    if (candidate / "scripts").exists():
        sys.path.insert(0, str(candidate))
        break

from scripts.csv_parser_v2 import CSVParserV2
from scripts.data_models import SensorBatch, SensorFrame
from prometheus_publisher import PrometheusPublisher


class CSVIngestionService:
    """Stateful CSV ingestor that only processes new rows per file."""

    def __init__(self, push_gateway_url: str):
        self.push_gateway_url = push_gateway_url
        self._file_offsets: Dict[str, int] = {}
        self._parser = CSVParserV2()

    @staticmethod
    def _sanitize_job_part(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", value)

    @staticmethod
    def _group_by_session(frames: List[SensorFrame]) -> Dict[Tuple[str, str], List[SensorFrame]]:
        grouped: Dict[Tuple[str, str], List[SensorFrame]] = defaultdict(list)
        for frame in frames:
            grouped[(frame.patient_id, frame.session_id)].append(frame)
        return grouped

    def ingest_new_rows(self, csv_path: str, job_prefix: str = "graphql_csv", reset_offset: bool = False) -> Dict[str, Any]:
        """Ingest only rows not processed yet for a given CSV file path."""
        source_path = Path(csv_path)
        if not source_path.exists():
            raise FileNotFoundError(f"CSV file not found: {source_path}")

        with source_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        absolute_path = str(source_path.resolve())
        total_rows = len(rows)

        if reset_offset:
            self._file_offsets[absolute_path] = 0

        last_offset = self._file_offsets.get(absolute_path, 0)
        if total_rows < last_offset:
            # File rotation/truncation: restart from beginning.
            last_offset = 0

        delta_rows = rows[last_offset:]
        self._file_offsets[absolute_path] = total_rows

        frames: List[SensorFrame] = []
        parse_errors = 0

        for row in delta_rows:
            frame, _ = self._parser.row_to_sensor_frame(row)
            if frame is None:
                parse_errors += 1
                continue
            frames.append(frame)

        grouped = self._group_by_session(frames)
        pushed_batches = 0

        for (patient_id, session_id), session_frames in grouped.items():
            batch = SensorBatch(
                session_id=session_id,
                patient_id=patient_id,
                frames=session_frames,
            )
            publisher = PrometheusPublisher(push_gateway_url=self.push_gateway_url)
            publisher.job_name = (
                f"{self._sanitize_job_part(job_prefix)}"
                f"_{self._sanitize_job_part(patient_id)}"
                f"_{self._sanitize_job_part(session_id)}"
            )
            publisher.batch_to_metrics(batch)
            if publisher.push_to_gateway():
                pushed_batches += 1

        return {
            "csv_path": absolute_path,
            "rows_total": total_rows,
            "rows_ingested": len(delta_rows),
            "rows_parsed": len(frames),
            "rows_with_errors": parse_errors,
            "session_batches_pushed": pushed_batches,
            "offset": self._file_offsets[absolute_path],
        }
