#!/usr/bin/env python3
"""
PostureCare CSV to Prometheus Metrics Ingester
Reads CSV files with sensor data and pushes metrics to Prometheus Push Gateway
"""

import csv
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVMetricsIngester:
    """Converts PostureCare CSV data to Prometheus metrics"""

    # Expected CSV columns
    EXPECTED_COLUMNS = {
        'patient_id': str,
        'session_id': str,
        'timestamp': str,  # ISO format: 2026-03-31T10:30:00
        'spine_angle': float,
        'shoulder_roll': float,
        'head_tilt': float,
        'measurement_id': str,
    }

    def __init__(self, push_gateway_url: str = "http://localhost:9091"):
        """
        Initialize ingester

        Args:
            push_gateway_url: Prometheus Push Gateway endpoint
        """
        self.push_gateway_url = push_gateway_url
        self.metrics: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}

    def read_csv(self, csv_path: str) -> List[Dict]:
        """
        Read and validate CSV file

        Args:
            csv_path: Path to CSV file

        Returns:
            List of validated row dictionaries
        """
        logger.info(f"Reading CSV from {csv_path}")
        rows = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate headers
                if not reader.fieldnames:
                    raise ValueError("CSV file is empty or has no headers")

                missing_cols = set(self.EXPECTED_COLUMNS.keys()) - set(reader.fieldnames)
                if missing_cols:
                    raise ValueError(f"Missing columns: {missing_cols}")

                # Read and validate rows
                for i, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    try:
                        validated_row = self._validate_row(row, i)
                        rows.append(validated_row)
                    except ValueError as e:
                        logger.warning(f"Skipping row {i}: {e}")
                        continue

            logger.info(f"Successfully read {len(rows)} rows from CSV")
            return rows

        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            sys.exit(1)

    def _validate_row(self, row: Dict, row_num: int) -> Dict:
        """Validate and type-convert a CSV row"""
        validated = {}

        for col, col_type in self.EXPECTED_COLUMNS.items():
            value = row.get(col, '').strip()

            if not value:
                raise ValueError(f"Missing value for column '{col}'")

            try:
                if col_type == float:
                    validated[col] = float(value)
                elif col_type == int:
                    validated[col] = int(value)
                else:
                    validated[col] = value
            except ValueError:
                raise ValueError(f"Invalid {col_type.__name__} for '{col}': {value}")

        return validated

    def convert_to_metrics(self, rows: List[Dict]) -> str:
        """
        Convert CSV rows to Prometheus text format metrics

        Args:
            rows: List of validated row dicts

        Returns:
            Prometheus text format string
        """
        logger.info("Converting CSV rows to Prometheus metrics")
        metrics_lines = []

        # Track aggregates
        patient_sessions = set()
        alert_count = 0
        measurement_count = 0

        for row in rows:
            patient_id = row['patient_id']
            session_id = row['session_id']
            measurement_id = row['measurement_id']
            patient_sessions.add((patient_id, session_id))
            measurement_count += 1

            # Posture metrics
            spine_angle = row['spine_angle']
            shoulder_roll = row['shoulder_roll']
            head_tilt = row['head_tilt']

            # Gauge: Current posture angles
            metrics_lines.append(
                f'posture_spine_angle{{patient_id="{patient_id}",session_id="{session_id}",measurement_id="{measurement_id}"}} {spine_angle}'
            )
            metrics_lines.append(
                f'posture_shoulder_roll{{patient_id="{patient_id}",session_id="{session_id}",measurement_id="{measurement_id}"}} {shoulder_roll}'
            )
            metrics_lines.append(
                f'posture_head_tilt{{patient_id="{patient_id}",session_id="{session_id}",measurement_id="{measurement_id}"}} {head_tilt}'
            )

            # Alert generation: Flag bad posture (>30 degrees spine angle)
            if spine_angle > 30:
                alert_count += 1
                metrics_lines.append(
                    f'posture_alert_triggered{{patient_id="{patient_id}",session_id="{session_id}",measurement_id="{measurement_id}",alert_type="excessive_spine_angle"}} 1'
                )

        # Add counters (one-time aggregates)
        for patient_id, session_id in patient_sessions:
            metrics_lines.append(
                f'posture_monitoring_active{{patient_id="{patient_id}",session_id="{session_id}"}} 1'
            )

        # Global counters
        metrics_lines.append(f'posture_measurement_count {measurement_count}')
        metrics_lines.append(f'posture_alert_count {alert_count}')
        metrics_lines.append(f'posture_patient_count {len(set(r["patient_id"] for r in rows))}')

        # Prometheus text format expects a trailing newline.
        metrics_text = '\n'.join(metrics_lines) + '\n'
        logger.info(f"Generated {len(metrics_lines)} metric lines")

        return metrics_text

    def push_to_gateway(self, metrics_text: str, job_name: str = "posture_ingester"):
        """
        Push metrics to Prometheus Push Gateway

        Args:
            metrics_text: Prometheus text format metrics
            job_name: Job name for grouping
        """
        url = f"{self.push_gateway_url}/metrics/job/{job_name}"

        try:
            logger.info(f"Pushing metrics to {url}")
            response = requests.post(url, data=metrics_text, headers={'Content-Type': 'text/plain'})

            if response.status_code in (200, 202):
                logger.info("✓ Metrics successfully pushed to Push Gateway")
            else:
                logger.error(f"Failed to push metrics: {response.status_code} {response.text}")
                return False

            return True

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Push Gateway at {self.push_gateway_url}")
            logger.error("Make sure Prometheus Push Gateway is running")
            return False
        except Exception as e:
            logger.error(f"Error pushing metrics: {e}")
            return False

    def publish_events_to_graphql(self, rows: List[Dict], graphql_api_url: str = "http://localhost:8000"):
        """
        Publish sensor frame events to GraphQL API for real-time subscriptions

        Args:
            rows: List of validated row dicts
            graphql_api_url: GraphQL API endpoint
        """
        try:
            logger.info(f"Publishing events to GraphQL API at {graphql_api_url}")
            api_key = os.getenv("GRAPHQL_API_KEY", "test-key-123")

            for row in rows:
                patient_id = row['patient_id']
                session_id = row['session_id']
                measurement_id = row['measurement_id']
                timestamp = row['timestamp']

                # Create event data
                frame_data = {
                    "measurement_id": measurement_id,
                    "patient_id": patient_id,
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "spine_angle": row['spine_angle'],
                    "shoulder_roll": row['shoulder_roll'],
                    "head_tilt": row['head_tilt'],
                }

                # Build channel name for new_frame subscription
                channel = f"new_frame:{patient_id}"

                # POST event to GraphQL API
                url = f"{graphql_api_url}/api/publish_event"
                headers = {
                    "X-API-Key": api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "event_type": "sensor_frame",
                    "channel": channel,
                    "data": frame_data,
                }

                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=5)
                    if response.status_code == 200:
                        logger.debug(f"Published event for {patient_id} to {channel}")
                    else:
                        logger.warning(f"Failed to publish event: {response.status_code}")
                except requests.exceptions.Timeout:
                    logger.warning("Timeout publishing event to GraphQL API - continuing")
                except requests.exceptions.ConnectionError:
                    logger.warning("Cannot connect to GraphQL API - events will not be published")
                    break

            logger.info("✓ Events published to GraphQL API for subscriptions")

        except Exception as e:
            logger.error(f"Error publishing events: {e}")
            # Don't fail the ingestion if GraphQL publishing fails

    def save_metrics(self, metrics_text: str, output_path: str):
        """
        Save metrics to file (for debugging/inspection)

        Args:
            metrics_text: Prometheus text format metrics
            output_path: Path to save metrics file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(metrics_text)
            logger.info(f"Metrics saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert PostureCare CSV to Prometheus metrics'
    )
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument(
        '--push-gateway',
        default='http://localhost:9091',
        help='Prometheus Push Gateway URL (default: http://localhost:9091)'
    )
    parser.add_argument(
        '--graphql-api',
        default='http://localhost:8000',
        help='GraphQL API URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--output',
        help='Save metrics to file instead of pushing'
    )
    parser.add_argument(
        '--job-name',
        default='posture_ingester',
        help='Job name for Push Gateway'
    )

    args = parser.parse_args()

    # Initialize ingester
    ingester = CSVMetricsIngester(push_gateway_url=args.push_gateway)

    # Read and convert
    rows = ingester.read_csv(args.csv_file)
    metrics_text = ingester.convert_to_metrics(rows)

    # Save or push
    if args.output:
        ingester.save_metrics(metrics_text, args.output)
        print(f"Metrics saved to {args.output}")
    else:
        success = ingester.push_to_gateway(metrics_text, args.job_name)
        if success:
            # Publish events to GraphQL API for real-time subscriptions
            ingester.publish_events_to_graphql(rows, args.graphql_api)
            print("✓ CSV data ingested successfully")
            sys.exit(0)
        else:
            print("✗ Failed to ingest CSV data")
            sys.exit(1)


if __name__ == '__main__':
    main()
