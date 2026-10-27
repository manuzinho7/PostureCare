# PostureCare GraphQL API - Quick Start Guide

**Status:** ✅ Phase 1 Implementation Complete  
**Date:** 2026-05-14  
**Version:** 0.1.0

---

## 🎯 What's Implemented

### Phase 1 ✅ COMPLETE
- ✅ **GraphQL Schema** - Patient, Session, Alert, and Aggregate types
- ✅ **Query Resolvers** - Historical data queries with pagination
- ✅ **Subscriptions** - Real-time WebSocket event streaming
- ✅ **Authentication** - API key validation middleware
- ✅ **Data Access Layer** - Prometheus + PostgreSQL integration
- ✅ **Pub/Sub System** - Redis-backed event distribution
- ✅ **CSV Ingester Integration** - Auto-publish events on data ingestion
- ✅ **Docker Setup** - Redis service + updated compose config
- ✅ **Documentation** - Full API reference guide
- ✅ **Tests** - Basic test suite for queries and auth

---

## 🚀 Quick Start

### 1. Start Services

```bash
cd PostureCare
docker-compose up -d
sleep 10
```

Verify all services running:

```bash
docker-compose ps
```

Expected output:
```
posture-postgres        ✓ Up (healthy)
posture-redis           ✓ Up (healthy)
posture-push-gateway    ✓ Up
posture-prometheus      ✓ Up
posture-graphql-api     ✓ Up (healthy)
posture-grafana         ✓ Up
```

### 2. Test GraphQL API

**Health check:**

```bash
curl http://localhost:8000/health | jq
```

**Simple query (requires API key):**

```bash
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ healthStatus { status message } }"
  }' | jq
```

### 3. Ingest CSV Data

```bash
./scripts/ingest-csv.sh sample-data/sensor_data_v2.csv
```

This will:
- Convert CSV to Prometheus metrics
- Push metrics to Push Gateway
- Publish events to GraphQL API for subscriptions
- Trigger real-time updates for subscribers

### 4. Query Patients

```bash
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ patients(limit: 5) { patientId name age } }"
  }' | jq
```

### 5. Access GraphQL Playground

Open in browser: **http://localhost:8000/graphql**

(In development mode with debug enabled)

---

## 📊 Core Features

### Queries Available

```graphql
# Patient Management
patient(patientId: String!) -> PatientType
patients(limit: Int, offset: Int) -> [PatientType]

# Sessions
patientSessions(patientId: String!, limit: Int) -> [SessionMetadataType]

# Sensor Data & Alerts
alerts(patientId: String, severity: String, limit: Int) -> [AlertType]

# Aggregates & Summaries
patientSummary(patientId: String!) -> PatientSummaryType
sessionAggregates(sessionId: String!) -> AggregateMetricsType

# System Status
healthStatus() -> HealthStatusType
```

### Subscriptions Available

```graphql
# Real-time Sensor Frames
onNewFrame(patientId: String!) -> SensorReadingType

# Real-time Alerts
onAlert(patientId: String!, severity: String) -> AlertType

# Device Status Updates
onDeviceStatus(deviceId: String!) -> ESP32StatusType
```

---

## 🔑 Authentication

### API Keys

Required for all queries and subscriptions via header:

```
X-API-Key: test-key-123
```

Available test keys:
- `test-key-123`
- `dev-key-456`
- `prod-key-789`

### Change Keys (Production)

Edit `.env`:

```env
GRAPHQL_API_KEYS=your-key-1,your-key-2,your-key-3
```

Then restart: `docker-compose restart graphql-api`

---

## 📁 Project Structure

```
PostureCare/
├── services/graphql_api/
│   ├── main.py                    ← FastAPI + GraphQL schema
│   ├── data_access.py             ← Prometheus + PostgreSQL access
│   ├── auth.py                    ← API key authentication
│   ├── pubsub.py                  ← Real-time event pub/sub
│   ├── test_queries.py            ← Test suite
│   ├── requirements.txt           ← Dependencies
│   └── Dockerfile                 ← Container image
│
├── scripts/
│   ├── csv_ingester.py            ← CSV→Prometheus (NOW WITH EVENT PUBLISHING!)
│   ├── data_models.py             ← Sensor data models
│   └── ingest-csv.sh              ← Bash wrapper
│
├── docs/
│   └── GRAPHQL_API.md             ← Full API documentation
│
├── docker-compose.yml             ← Updated with Redis service
├── .env                           ← Updated with GraphQL config
└── prometheus/prometheus.yml      ← Prometheus config
```

---

## 🔌 Integration Points

### CSV Ingester → GraphQL API

When you run:

```bash
./scripts/ingest-csv.sh data.csv
```

The ingester now:
1. ✅ Reads and validates CSV
2. ✅ Converts to Prometheus metrics
3. ✅ Pushes to Push Gateway
4. ✅ **NEW:** Publishes events to GraphQL API via `/api/publish_event`
5. ✅ **NEW:** Triggers real-time subscriptions for subscribers

### Subscription Flow

```
CSV Data Ingested
    ↓
CSV Ingester publishes event
    ↓
GraphQL API receives at /api/publish_event
    ↓
Event published to Redis channel: new_frame:{patient_id}
    ↓
Subscription resolvers deliver to connected WebSocket clients
    ↓
BI Tools / Dashboards receive real-time updates
```

---

## 📊 Example Workflows

### Scenario 1: BI Tool Queries Historical Data

```bash
# Python script or similar
while True:
    # Query latest alerts for patient
    query alerts(patientId: "patient_001", limit: 10)
    
    # Get patient summary
    query patientSummary(patientId: "patient_001")
    
    # Process and display
    sleep(60)
```

### Scenario 2: Real-time Dashboard

```javascript
// JavaScript/React
const subscription = gql`
  subscription {
    onNewFrame(patientId: "patient_001") {
      timestamp
      imu { rollDeg pitchDeg }
      emg { activationNormalized }
      smo2 { smo2Percent }
    }
  }
`;

// Update UI in real-time as frames arrive
subscribeToUpdates(subscription, (frame) => {
  updateDashboard(frame);
});
```

### Scenario 3: Alert Monitoring

```python
# Monitor high-severity alerts
query_interval = 30  # seconds
while True:
    alerts = query_alerts(
        patient_id="patient_002",
        severity="high"
    )
    if alerts:
        notify_clinician(alerts)
    sleep(query_interval)
```

---

## 🧪 Testing

### Run Test Suite

```bash
cd services/graphql_api
python -m pytest test_queries.py -v
```

### Manual Tests

```bash
# Test health
curl http://localhost:8000/health

# Test auth rejection
curl -X POST http://localhost:8000/graphql -d '{"query":"{ patients { patientId } }"}'

# Test valid query
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ healthStatus { status } }"}'
```

---

## 📝 Configuration

### Environment Variables

```env
# GraphQL API
GRAPHQL_API_KEYS=test-key-123,dev-key-456,prod-key-789
PROMETHEUS_URL=http://prometheus:9090
REDIS_URL=redis://posture-redis:6379/0
REDIS_ENABLED=true

# PostgreSQL (for patient metadata)
POSTGRES_HOST=posture-postgres
POSTGRES_PORT=5432
POSTGRES_DB=posture_db
POSTGRES_USER=posture_user
POSTGRES_PASSWORD=posture_password
```

### Service Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| GraphQL API | http://localhost:8000 | Query & subscribe endpoint |
| GraphQL Playground | http://localhost:8000/graphql | Dev UI |
| Health Check | http://localhost:8000/health | Service health |
| Prometheus | http://localhost:9090 | Metrics database |
| Push Gateway | http://localhost:9091 | Batch metrics ingestion |
| Redis | localhost:6379 | Real-time pub/sub |
| PostgreSQL | localhost:5432 | Patient metadata |
| Grafana | http://localhost:3000 | Dashboards |

---

## 🐛 Troubleshooting

### GraphQL API Won't Start

```bash
# Check logs
docker-compose logs graphql-api

# Common issues:
# - Port 8000 already in use
# - Missing dependencies (check requirements.txt)
# - Redis connection refused (check Redis is running)
```

### Subscriptions Not Working

```bash
# Verify Redis
docker-compose exec redis redis-cli ping
# Should respond: PONG

# Check Redis is connected
docker-compose logs graphql-api | grep -i redis
```

### Events Not Publishing

```bash
# Verify GraphQL API is running
curl http://localhost:8000/health

# Check CSV ingester logs
./scripts/ingest-csv.sh data.csv 2>&1 | grep -i graphql
```

### Authentication Errors

```bash
# Verify API key in request
curl -i -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ healthStatus { status } }"}'

# Should get 200 OK
```

---

## 📚 Next Steps (Phase 2)

Planned for future phases:

- [ ] GraphQL Mutations (create/update sessions)
- [ ] Advanced filtering & sorting
- [ ] Rate limiting (100 req/min)
- [ ] OAuth2 authentication
- [ ] WebSocket subscription authentication
- [ ] GraphQL federation for multi-service setup
- [ ] Performance optimization & caching strategies
- [ ] RBAC (Role-Based Access Control)
- [ ] GDPR compliance (data retention, encryption)

---

## 📖 Full Documentation

See `docs/GRAPHQL_API.md` for:
- Complete query/subscription reference
- Error handling documentation
- Example client implementations
- Performance best practices

---

## 🎓 Learning Resources

- GraphQL Basics: https://graphql.org/learn/
- Strawberry GraphQL: https://strawberry.rocks/
- Async Python: https://docs.python.org/3/library/asyncio.html
- Redis Pub/Sub: https://redis.io/topics/pubsub

---

**Questions?** Check the docs or review the implementation in `services/graphql_api/main.py`
