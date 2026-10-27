# PostureCare Quick Reference

## Start Services

```bash
docker compose up -d
```

```powershell
# If Docker daemon is not running yet
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
docker compose up -d
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Push Gateway | http://localhost:9091 | - |
| PostgreSQL | localhost:5432 | posture_user / posture_password |

## Load CSV Data

### Method 1: Bash (Easiest)
```bash
./scripts/ingest-csv.sh sample-data/posture_session_example.csv
```

### Method 2: Python Direct
```bash
python scripts/csv_ingester.py sample-data/posture_session_example.csv
```

### Method 2 (Windows PowerShell Recommended)
```powershell
python scripts/csv_ingester.py sample-data/posture_session_example.csv --push-gateway http://localhost:9091 --job-name posture_ingester
```

### Method 3: Docker
```bash
docker build -f Dockerfile.ingester -t posture-ingester .
docker run --network posture_posture-net \
  -v $(pwd)/sample-data:/data \
  posture-ingester /data/posture_session_example.csv
```

## Generate Demo Telemetry

The GraphQL API now seeds synthetic sensor data into Push Gateway on startup, so Grafana has data even before CSV ingestion runs.

### Trigger synthetic generation manually
```bash
curl -X POST http://localhost:8000/generate/synthetic \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient_001","duration_minutes":5,"sample_rate_hz":1}'
```

### Publish a sensor event from CSV ingestion
The CSV ingester still pushes metrics to Push Gateway and also forwards events to the GraphQL API via `/api/publish_event`.

## Common Tasks

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
docker compose logs -f grafana      # Grafana logs
docker compose logs -f prometheus   # Prometheus logs
```

### Stop Services
```bash
docker compose down
```

### Reset Grafana
```bash
docker compose down
docker volume rm posture_grafana_data
docker compose up -d
```

### Query Prometheus (via CLI)
```bash
curl 'http://localhost:9090/api/v1/query?query=posture_spine_angle'
```

### Reset Push Gateway
```bash
curl -X DELETE http://localhost:9091/metrics/job/posture_ingester
```

## CSV Format

**Required Columns:**
```
patient_id, session_id, timestamp (ISO), spine_angle, shoulder_roll, head_tilt, measurement_id
```

**Example:**
```csv
patient_001,session_2026_03_31_001,2026-03-31T10:00:00,22.5,5.2,3.1,m001
```

## Dashboards

1. **Patient Posture Monitoring** - Real-time clinician view
2. **Research Analytics** - Aggregate researcher insights
3. **System Health** - Infrastructure monitoring

## Documentation

- **README.md** - Project overview
- **SETUP.md** - Installation & deployment
- **DASHBOARDS.md** - Dashboard design & metrics
- **CSV_INGESTION.md** - CSV data import guide

## Troubleshooting

**Port already in use?**
```bash
# Kill process on port
lsof -i :3000  # Find process
kill -9 <PID>  # Kill it
```

**No metrics showing?**
```bash
# Check Prometheus targets
http://localhost:9090/targets

# Check Push Gateway
http://localhost:9091/metrics
```

**CSS/styling issues in Grafana?**
```bash
# Hard refresh browser
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

## Directory Structure

```
PostureCare/
├── docker-compose.yml       ← Start here
├── .env                     ← Config
├── prometheus/              ← Time-series DB config
├── grafana/                 ← Dashboards
├── scripts/
│   ├── csv_ingester.py      ← CSV parser
│   └── ingest-csv.sh        ← Easy wrapper
├── sample-data/             ← Example CSVs
└── docs/                    ← Documentation
```

## Quick Workflow

```bash
# 1. Start services
docker compose up -d

# 2. Generate or load data
curl -X POST http://localhost:8000/generate/synthetic \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient_001","duration_minutes":5,"sample_rate_hz":1}'

# Or ingest a CSV file
python scripts/csv_ingester.py sample-data/posture_session_example.csv --push-gateway http://localhost:9091 --job-name posture_ingester

# 3. Open Grafana
# http://localhost:3000

# 4. View dashboards
# Patient Posture Monitoring → Select patient → See data
```

---

For detailed info, see the documentation in `docs/` folder.
