# PostureCare GraphQL API Documentation

**Version:** 0.1.0  
**Status:** ✅ Phase 1 Complete - Queries & Subscriptions  
**Latest Update:** 2026-05-14

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Queries](#queries)
5. [Subscriptions](#subscriptions)
6. [Examples](#examples)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Overview

The PostureCare GraphQL API exposes real-time wearable sensor data, patient metadata, and clinical insights. It provides both synchronous queries for batch operations and WebSocket subscriptions for real-time event streaming.

### Key Features

- ✅ **Historical Queries** - Retrieve patient data, sessions, sensor readings, and aggregates
- ✅ **Real-time Subscriptions** - Stream sensor frames and alerts via WebSocket
- ✅ **API Key Authentication** - Simple header-based authentication
- ✅ **Pagination** - Efficient data retrieval for large datasets
- ✅ **Caching** - Optimized Prometheus and PostgreSQL queries
- ✅ **Error Handling** - Standardized error responses

### Base URL

```
http://localhost:8000
```

### GraphQL Endpoint

```
http://localhost:8000/graphql
```

Playground (for development):

```
http://localhost:8000/graphql?debug=true
```

---

## Getting Started

### Quick Test

```bash
# Health check
curl -s http://localhost:8000/health | jq

# GraphQL query (with API key)
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ healthStatus { status message } }"
  }'
```

---

## Authentication

### API Keys

All GraphQL queries require an API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ patients(limit: 5) { patientId name } }"}'
```

### Available Keys (Development)

```
test-key-123      # Testing
dev-key-456       # Development
prod-key-789      # Production
```

**⚠️ Change these in production!** Set via `.env`:

```env
GRAPHQL_API_KEYS=key1,key2,key3
```

### Error Response (Unauthorized)

```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```

---

## Queries

### Patient Queries

#### Get Single Patient

```graphql
query {
  patient(patientId: "patient_001") {
    patientId
    name
    age
    gender
    email
  }
}
```

**Response:**

```json
{
  "data": {
    "patient": {
      "patientId": "patient_001",
      "name": "John Doe",
      "age": 45,
      "gender": "M",
      "email": "john@example.com"
    }
  }
}
```

#### List All Patients

```graphql
query {
  patients(limit: 10, offset: 0) {
    patientId
    name
    age
    gender
  }
}
```

### Session Queries

#### Get Patient Sessions

```graphql
query {
  patientSessions(patientId: "patient_001", limit: 5) {
    sessionId
    patientId
    startTime
    endTime
    notes
  }
}
```

### Alert Queries

#### Get Alerts for Patient

```graphql
query {
  alerts(
    patientId: "patient_001"
    severity: "high"
    limit: 20
  ) {
    timestamp
    patientId
    severity
    reason
    affectedMetric
  }
}
```

### Summary Queries

#### Get Patient Summary

```graphql
query {
  patientSummary(patientId: "patient_001") {
    patientId
    name
    recentAlertCount
    lastActivity
    avgPostureScore
  }
}
```

#### Get Session Aggregates

```graphql
query {
  sessionAggregates(sessionId: "session_2026_03_31_001") {
    patientId
    sessionId
    avgSpineAngle
    totalFrames
    totalAlerts
    alertRate
    avgMuscleActivation
    avgOxygenSaturation
  }
}
```

### System Status

#### Health Check

```graphql
query {
  healthStatus {
    status
    message
    uptimeS
    timestamp
  }
}
```

---

## Subscriptions

### Subscribe to New Sensor Frames

```graphql
subscription {
  onNewFrame(patientId: "patient_001") {
    measurementId
    timestamp
    imu {
      rollDeg
      pitchDeg
      yawDeg
    }
    emg {
      rmsUv
      activationNormalized
    }
    smo2 {
      smo2Percent
      qualityNormalized
    }
    isAlertWorthy
  }
}
```

### Subscribe to Patient Alerts

```graphql
subscription {
  onAlert(patientId: "patient_001", severity: "high") {
    timestamp
    patientId
    severity
    reason
    affectedMetric
  }
}
```

### Subscribe to Device Status

```graphql
subscription {
  onDeviceStatus(deviceId: "esp32_001") {
    batteryMV
    batteryPct
    chargeState
    tempCC
    heapFree
    hasErrors
    errorList
  }
}
```

---

## Examples

### Python Client

```python
import asyncio
import aiohttp
import json
from gql import gql, Client
from gql.transport.websockets import WebsocketsHTTPTransport

async def query_patients():
    """Query patients via HTTP"""
    url = "http://localhost:8000/graphql"
    headers = {"X-API-Key": "test-key-123"}
    
    query = """
    query {
      patients(limit: 5) {
        patientId
        name
        age
      }
    }
    """
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json={"query": query},
            headers=headers
        ) as resp:
            result = await resp.json()
            print(json.dumps(result, indent=2))

async def subscribe_alerts():
    """Subscribe to alerts via WebSocket"""
    url = "ws://localhost:8000/graphql"
    headers = {"X-API-Key": "test-key-123"}
    
    transport = WebsocketsHTTPTransport(url=url, headers=headers)
    async with Client(transport=transport) as session:
        subscription = gql("""
        subscription {
          onAlert(patientId: "patient_002") {
            timestamp
            severity
            reason
          }
        }
        """)
        
        async for result in session.subscribe(subscription):
            print(f"Alert: {result['data']['onAlert']}")

# Run examples
asyncio.run(query_patients())
# asyncio.run(subscribe_alerts())
```

### JavaScript/Node.js Client

```javascript
import { gql, ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const client = new ApolloClient({
  cache: new InMemoryCache(),
  link: new HttpLink({
    uri: 'http://localhost:8000/graphql',
    credentials: 'include',
    headers: {
      'X-API-Key': 'test-key-123',
    },
  }),
});

// Query patients
const PATIENTS_QUERY = gql`
  query GetPatients($limit: Int) {
    patients(limit: $limit) {
      patientId
      name
      age
    }
  }
`;

client.query({
  query: PATIENTS_QUERY,
  variables: { limit: 5 },
}).then(result => {
  console.log(JSON.stringify(result.data, null, 2));
});
```

### cURL Examples

#### Query with Authentication

```bash
curl -X POST http://localhost:8000/graphql \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ patients(limit: 3) { patientId name age } }"
  }' | jq
```

#### Test Health

```bash
curl -s http://localhost:8000/health | jq '.status'
```

---

## Error Handling

### Unauthorized Request

```json
{
  "errors": [
    {
      "message": "Unauthorized",
      "extensions": {
        "code": "UNAUTHENTICATED"
      }
    }
  ]
}
```

### Invalid Query

```json
{
  "errors": [
    {
      "message": "Cannot query field 'invalidField' on type 'Query'",
      "locations": [{"line": 1, "column": 3}]
    }
  ]
}
```

### Database Error

```json
{
  "errors": [
    {
      "message": "Database connection error",
      "extensions": {
        "code": "INTERNAL_SERVER_ERROR"
      }
    }
  ]
}
```

---

## Rate Limiting

Currently **no rate limiting** is enforced. Recommended for production:

- **Queries:** 100 req/min per API key
- **Subscriptions:** 10 concurrent connections per API key
- **Mutations:** 50 req/min per API key

---

## API Versions

### v0.1.0 (Current)

- ✅ Patient queries
- ✅ Session queries
- ✅ Alert queries
- ✅ Real-time subscriptions
- ✅ API key authentication

### v0.2.0 (Planned)

- 🔜 Mutations (create/update patient sessions)
- 🔜 Advanced filtering and sorting
- 🔜 Rate limiting
- 🔜 OAuth2 authentication
- 🔜 GraphQL federation

---

## Troubleshooting

### Connection Refused

```
Error: ECONNREFUSED 127.0.0.1:8000
```

**Solution:** Verify GraphQL API is running:

```bash
docker-compose ps | grep graphql-api
docker-compose logs graphql-api
```

### Invalid API Key

```
Error: Unauthorized - Invalid API key
```

**Solution:** Check your API key in `.env`:

```bash
grep GRAPHQL_API_KEYS .env
```

### Subscription Timeout

```
Error: Subscription timeout after 300 seconds
```

**Solution:** Subscriptions expire after 5 minutes of inactivity. Reconnect to resume.

---

## Performance Tips

1. **Use pagination** for large datasets (limit + offset)
2. **Filter early** - use patientId in queries to reduce data transfer
3. **Cache results** client-side when appropriate
4. **Use subscriptions sparingly** - only for real-time data needs
5. **Batch queries** when possible to reduce round-trips

---

## Support

For issues or questions:

1. Check logs: `docker-compose logs graphql-api`
2. Test health: `curl http://localhost:8000/health`
3. Review plan: `docs/README.md`
