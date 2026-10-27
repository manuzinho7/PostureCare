# PostureCare Testing Evidence Report

## Scope

This report summarizes the implemented GraphQL API surface, dashboard validation, integration checks, and runtime evidence gathered from the current project structure.

## GraphQL Surface

### Implemented Query Operations

| Operation | Purpose |
|---|---|
| `patientSession` | Return a complete session for one patient |
| `sensorReadings` | Return recent readings for a patient |
| `alertSummary` | Return alert summary data |
| `healthStatus` | Return API health |
| `patient` | Return patient metadata |
| `patients` | Return paginated patients |
| `patientSessions` | Return sessions for one patient |
| `alerts` | Return patient alerts |
| `sessionAggregates` | Return session-level aggregates |
| `patientSummary` | Return patient summary |

### Implemented Mutation Operations

No GraphQL mutations are implemented in the current schema. `mutationType` is `null`.

### Implemented Subscription Operations

| Operation | Purpose |
|---|---|
| `onNewFrame` | Stream sensor frames |
| `onAlert` | Stream alerts |
| `onDeviceStatus` | Stream device status updates |

## GraphQL Test Suite

| Test ID | Purpose | Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| GQL-001 | Validate schema fields | Introspection query | Query and subscription fields exposed as implemented | Matches current schema | PASS |
| GQL-002 | Validate health query | `healthStatus` | Returns `ok` payload with timestamp | Matches | PASS |
| GQL-003 | Validate patient query | `patient(patientId: \"patient_001\")` | Returns object or `null` without schema error | Matches | PASS |
| GQL-004 | Validate list pagination | `patients(limit: 5, offset: 0)` | Returns list structure | Matches | PASS |
| GQL-005 | Validate session query | `patientSessions(patientId: \"patient_001\")` | Returns list structure | Matches | PASS |
| GQL-006 | Validate alert query | `alerts(patientId: \"patient_001\")` | Returns list structure | Matches | PASS |
| GQL-007 | Validate summary query | `patientSummary(patientId: \"patient_001\")` | Returns object or `null` | Matches | PASS |
| GQL-008 | Validate invalid field handling | `invalidField` query | GraphQL errors returned | Matches | PASS |
| GQL-009 | Validate missing argument handling | `alerts { timestamp }` | GraphQL errors returned | Matches | PASS |
| GQL-010 | Validate invalid scalar handling | `patientId: 1` | GraphQL errors returned | Matches | PASS |
| GQL-011 | Validate auth behavior | Missing API key | Endpoint still answers, resolver-level auth not enforced | Matches current code | PASS |
| GQL-012 | Validate empty results | Monkeypatched empty data access | Empty lists / null values | Matches | PASS |

### Response Time Evidence

Observed response times on the local stack were below 1500 ms for the read-path queries used in the suite.

## Grafana Dashboard Validation

| Dashboard | Panel | Data Source | Query Used | Expected Behaviour | Validation Result |
|---|---|---|---|---|---|
| patient-monitoring | Current Posture Angle | Prometheus | `max without (session_id, measurement_id, exported_job) (posture_spine_angle{patient_id=\"$patient_id\"})` | Live posture value shown | PASS |
| patient-monitoring | Current Battery Level | Prometheus | `max without (session_id, measurement_id, exported_job) (device_battery_percent{patient_id=\"$patient_id\"})` | Live battery value shown | PASS |
| patient-monitoring | Current Muscle Activation | Prometheus | `max without (session_id, measurement_id, exported_job) (posture_emg_activation_normalized{patient_id=\"$patient_id\"})` | Live activation value shown | PASS |
| research-analytics | Total Studies Patients | Prometheus | `count(count by (patient_id) (posture_monitoring_active{patient_id=~\"$patient_id\"}))` | Aggregate patient count | PASS |
| research-analytics | Measurements/Hour | Prometheus | `sum(posture_measurement_count{patient_id=~\"$patient_id\"})` | Measurement volume shown | PASS |
| research-analytics | Alert Rate % | Prometheus | `(sum(posture_alert_count{patient_id=~\"$patient_id\"}) / sum(posture_measurement_count{patient_id=~\"$patient_id\"})) * 100` | Alert percentage shown | PASS |
| system-health | Prometheus Status | Prometheus | `up{job="prometheus"}` | UP status shown | PASS |
| system-health | Sensor Service Status | Prometheus | `up{job="posture-sensors"}` | UP/DOWN status shown | FAIL |
| system-health | Disk Usage (MB) | Prometheus | `prometheus_tsdb_symbol_table_size_bytes / 1024 / 1024` | Non-empty gauge | PASS |
| system-health | Query Rate (ops/s) | Prometheus | `rate(prometheus_http_requests_total[5m])` | Query rate shown | PASS |

## Identified Issues

- Broken panel: `Sensor Service Status` references `up{job="posture-sensors"}`, but that series is not currently published in the running Prometheus data.
- Missing alert configurations: the dashboards are provisioned without explicit Grafana alert rules.
- No GraphQL mutations are implemented in the live schema, so mutation validation is not applicable beyond confirming the absence of a mutation root.
- Resolver-level auth enforcement is not present; authentication is effectively public at the GraphQL endpoint.

## Integration Findings

| Scenario | Components | Expected Behaviour | Actual Behaviour | Status |
|---|---|---|---|---|
| Database -> GraphQL API | PostgreSQL, GraphQL API | Patient/session queries return structured data | Queries respond successfully | PASS |
| GraphQL API -> Grafana | GraphQL-driven metrics surface in dashboards | Grafana can reach the same Prometheus backend | Service is reachable | PASS |
| Application Metrics -> Prometheus | GraphQL/ingestion publisher -> Pushgateway -> Prometheus | Metrics available for scraping | Core metrics are present | PASS |
| Prometheus -> Grafana | Prometheus datasource -> dashboard panels | Panels resolve PromQL queries | Most panels resolve | PASS |
| Docker Containers -> Internal Services | postgres, prometheus, redis, graphql-api, grafana | Services reachable on expected ports | Running and reachable | PASS |
| End-to-End Analytics Flow | API, Pushgateway, Prometheus, Grafana | Data appears across the stack | Current stack supports the flow | PASS |

## Recommendations

1. Add a real mutation root only if the product requirement expects GraphQL writes.
2. Apply resolver-level authorization decorators to protected patient queries.
3. Replace the `posture-sensors` system-health panel or publish the missing metric family.
4. Add Grafana alert rules for the high-value operational panels.
5. Preserve the new pytest suite as the regression harness for the API and dashboards.
