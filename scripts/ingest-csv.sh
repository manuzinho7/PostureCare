#!/bin/bash
# PostureCare CSV Ingester Script
# Loads CSV data into Prometheus via Push Gateway

set -e

# Configuration
PUSH_GATEWAY_URL="${PUSH_GATEWAY_URL:-http://localhost:9091}"
CSV_FILE="${1:-sample-data/posture_session_example.csv}"
JOB_NAME="${2:-posture_ingester}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== PostureCare CSV Ingester ===${NC}\n"

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}✗ CSV file not found: $CSV_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  CSV File: $CSV_FILE"
echo "  Push Gateway: $PUSH_GATEWAY_URL"
echo "  Job Name: $JOB_NAME"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is required but not installed${NC}"
    exit 1
fi

# Install requirements if needed
echo -e "${BLUE}Checking dependencies...${NC}"
python3 -m pip install -q requests 2>/dev/null || true

# Run ingester
echo -e "${YELLOW}Loading CSV data...${NC}\n"
python3 scripts/csv_ingester.py "$CSV_FILE" --push-gateway "$PUSH_GATEWAY_URL" --job-name "$JOB_NAME"

echo -e "\n${GREEN}✓ CSV ingestion complete!${NC}"
echo -e "${BLUE}View metrics:${NC}"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000"
echo "  - Push Gateway: ${PUSH_GATEWAY_URL}"
