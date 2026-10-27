#!/usr/bin/env python3
"""
Example: Automated CSV Ingestion Pipeline

This shows how to integrate PostureCare CSV ingestion into an automated workflow.
Use cases:
- Scheduler (cron) to ingest daily exports
- Data pipeline (Airflow) for ETL
- Web service to accept uploads

Run: python scripts/example_pipeline.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from csv_ingester import CSVMetricsIngester

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_single_file():
    """Example 1: Load a single CSV file"""
    logger.info("=" * 60)
    logger.info("Example 1: Load Single CSV File")
    logger.info("=" * 60)

    ingester = CSVMetricsIngester(push_gateway_url="http://localhost:9091")

    # Read CSV
    csv_path = "sample-data/posture_session_example.csv"
    rows = ingester.read_csv(csv_path)

    # Convert to metrics
    metrics_text = ingester.convert_to_metrics(rows)

    # Push to Prometheus
    success = ingester.push_to_gateway(metrics_text, job_name="example_1")

    if success:
        logger.info(f"✓ Loaded {len(rows)} measurements")
    else:
        logger.error("✗ Failed to push metrics")


def example_2_batch_processing():
    """Example 2: Process multiple CSV files in batch"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Batch Process Multiple Files")
    logger.info("=" * 60)

    ingester = CSVMetricsIngester(push_gateway_url="http://localhost:9091")

    # Find all CSV files
    csv_dir = Path("sample-data")
    csv_files = list(csv_dir.glob("*.csv"))

    logger.info(f"Found {len(csv_files)} CSV files")

    for csv_file in csv_files:
        try:
            logger.info(f"\nProcessing: {csv_file.name}")

            # Read and convert
            rows = ingester.read_csv(str(csv_file))
            metrics_text = ingester.convert_to_metrics(rows)

            # Push with unique job name
            job_name = f"batch_{csv_file.stem}"
            success = ingester.push_to_gateway(metrics_text, job_name=job_name)

            if success:
                logger.info(f"  ✓ {len(rows)} measurements pushed")
            else:
                logger.error(f"  ✗ Failed to push metrics")

            # Small delay to avoid overwhelming Push Gateway
            time.sleep(1)

        except Exception as e:
            logger.error(f"  ✗ Error processing {csv_file.name}: {e}")
            continue


def example_3_with_preprocessing():
    """Example 3: CSV with data preprocessing/validation"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: CSV with Data Preprocessing")
    logger.info("=" * 60)

    ingester = CSVMetricsIngester(push_gateway_url="http://localhost:9091")

    csv_path = "sample-data/posture_session_example.csv"
    rows = ingester.read_csv(csv_path)

    # Preprocessing: Filter outliers
    original_count = len(rows)
    filtered_rows = [
        r for r in rows
        if 0 <= r['spine_angle'] <= 45  # Reasonable range for clinical use
    ]
    dropped_count = original_count - len(filtered_rows)

    if dropped_count > 0:
        logger.info(f"Preprocessing: Dropped {dropped_count} outlier measurements")

    # Convert and push
    metrics_text = ingester.convert_to_metrics(filtered_rows)
    success = ingester.push_to_gateway(metrics_text, job_name="example_3_filtered")

    if success:
        logger.info(f"✓ Loaded {len(filtered_rows)} measurements (after filtering)")


def example_4_save_metrics():
    """Example 4: Save metrics to file for inspection (no push)"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Save Metrics to File")
    logger.info("=" * 60)

    ingester = CSVMetricsIngester()

    csv_path = "sample-data/posture_session_example.csv"
    rows = ingester.read_csv(csv_path)

    metrics_text = ingester.convert_to_metrics(rows)

    output_path = "sample-data/example_metrics.txt"
    ingester.save_metrics(metrics_text, output_path)

    logger.info(f"Metrics saved to {output_path}")
    logger.info(f"\nFirst 10 lines:")
    with open(output_path) as f:
        for i, line in enumerate(f):
            if i >= 10:
                break
            logger.info(f"  {line.strip()}")


def example_5_error_handling():
    """Example 5: Error handling and recovery"""
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Error Handling & Recovery")
    logger.info("=" * 60)

    ingester = CSVMetricsIngester(push_gateway_url="http://localhost:9999")  # Wrong URL

    csv_path = "sample-data/posture_session_example.csv"

    try:
        rows = ingester.read_csv(csv_path)
        metrics_text = ingester.convert_to_metrics(rows)

        # This will fail (wrong gateway URL), but we handle it
        success = ingester.push_to_gateway(metrics_text)

        if not success:
            logger.warning("Push failed, but we can handle it gracefully")

            # Option 1: Save metrics for retry later
            ingester.save_metrics(metrics_text, "sample-data/failed_metrics.txt")
            logger.info("  → Saved metrics to file for later retry")

            # Option 2: Retry with correct URL
            logger.info("  → Retrying with correct URL...")
            ingester.push_gateway_url = "http://localhost:9091"
            success = ingester.push_to_gateway(metrics_text)

            if success:
                logger.info("  ✓ Retry successful!")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")


def main():
    """Run all examples"""
    logger.info("PostureCare CSV Ingestion Pipeline Examples\n")

    # Ensure Push Gateway is running
    logger.info("Checking Push Gateway connectivity...")
    try:
        import requests
        requests.get("http://localhost:9091/metrics", timeout=2)
        logger.info("✓ Push Gateway is running\n")
    except Exception as e:
        logger.error(f"✗ Cannot reach Push Gateway: {e}")
        logger.error("Start services with: docker-compose up -d\n")
        sys.exit(1)

    # Run examples
    examples = [
        example_1_single_file,
        example_2_batch_processing,
        example_3_with_preprocessing,
        example_4_save_metrics,
        example_5_error_handling,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example failed: {e}")
            continue
        time.sleep(1)

    logger.info("\n" + "=" * 60)
    logger.info("All examples completed!")
    logger.info("View metrics in Grafana: http://localhost:3000")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
