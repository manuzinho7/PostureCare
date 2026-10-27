# PostureCare Dashboards Documentation

## Overview

This document describes the foundation dashboards designed for PostureCare's analytics platform, targeting three user personas:
- **Clinicians:** Patient-centric posture monitoring
- **Researchers:** Aggregate analytics and cohort analysis
- **DevOps/System Admins:** Infrastructure health and performance

## Dashboard & Analytics Layer

The dashboard layer is the presentation and decision-support surface of PostureCare. It connects telemetry ingestion to clinician-facing views and platform analytics.

### Core Responsibilities
- **Prometheus** stores and queries real-time posture telemetry, alert counters, and operational metrics.
- **Grafana** visualizes time-series data in dashboards tailored to clinicians, researchers, and operators.
- **Real-time metrics** support active monitoring of posture, alert state, and data freshness.
- **Clinician dashboards** focus on patient sessions, posture anomalies, and episode history.
- **Monitoring flows** move from wearable or ingested telemetry into Prometheus, then into Grafana dashboards and alerts.

### Reference Flow
```
Wearable Sensors / Mobile App
  ↓
Telemetry Ingestion / CSV Import
  ↓
Prometheus
  ↓
Grafana Dashboards and Alerts
  ↓
Clinicians, Researchers, DevOps
```

---

## Dashboard 1: Patient Posture Monitoring (Clinician Dashboard)

### Purpose
Real-time posture monitoring dashboard for individual patient sessions, enabling clinicians to:
- Track current posture status
- Identify abnormal patterns
- Review session history
- Respond to alerts

### User: Clinician
**Time Horizon:** Real-time to last 6 hours
**Refresh Rate:** 10 seconds

### Panels

#### 1. Active Patient Sessions (Pie Chart)
- **Metric:** `count(posture_monitoring_active)`
- **Purpose:** Quick overview of monitoring activity
- **Interpretation:** Shows how many patients are currently being monitored

#### 2. Current Average Posture Angle (Stat Card - Gauge)
- **Metric:** `avg(posture_current_angle)`
- **Purpose:** Current aggregate posture quality indicator
- **Interpretation:** 0-15° = excellent, 15-25° = good, 25-35° = caution, >35° = poor
- **Unit:** Degrees (spine deviation from vertical)

#### 3. Posture Timeline - Spine Angle (Time Series Graph)
- **Metric:** `posture_spine_angle{patient_id="$patient_id"}`
- **Purpose:** Detailed visualization of posture over time for selected patient
- **X-axis:** Time
- **Y-axis:** Spine angle in degrees
- **Features:**
  - Filterable by Patient ID (variable `$patient_id`)
  - Shows sustained good/bad posture periods
  - Shaded regions can highlight threshold violations

#### 4. Posture Alerts Summary (Donut Chart)
- **Metric:** `count(posture_alert_triggered)`
- **Purpose:** Summary of triggered alerts during session
- **Interpretation:** Helps clinician understand alert frequency and type

### Variables / Filters
- **Patient ID:** Dropdown selector between available patients
- **Time Range:** Last 6 hours (default), user-adjustable

### Alert Rules (Future)
- Spine angle > 35° for > 5 minutes → YELLOW alert
- Spine angle > 40° for > 10 minutes → RED alert
- No data for > 5 minutes → GRAY alert (data loss)

---

## Dashboard 2: Research Analytics - Posture Metrics (Researcher Dashboard)

### Purpose
Aggregate analytics dashboard for researchers to:
- Analyze population-level posture metrics
- Compare cohorts or interventions
- Identify trends and patterns
- Export data for statistical analysis

### User: Researcher
**Time Horizon:** 24 hours to 30 days
**Refresh Rate:** 30 seconds

### Panels

#### 1. Total Studies Patients (Stat Card)
- **Metric:** `count(distinct(posture_patient_id))`
- **Purpose:** Snapshot of enrolled subjects in current study
- **Interpretation:** Total N for the dataset

#### 2. Measurements/Hour (Stat Card)
- **Metric:** `sum(rate(posture_measurement_count[1h]))`
- **Purpose:** Data ingestion velocity
- **Interpretation:** Helps assess sensor reliability and data loss

#### 3. Alert Rate % (Stat Card)
- **Metric:** `(count(posture_alert_triggered) / count(posture_measurement_count)) * 100`
- **Purpose:** Proportion of problematic posture measurements
- **Interpretation:** High rate (>30%) suggests intervention need or cohort at risk

#### 4. Critical Events (Stat Card)
- **Metric:** `count(posture_alert_triggered)`
- **Purpose:** Total adverse posture events in period
- **Interpretation:** Aggregated alert count for the cohort

#### 5. Posture Distribution (p95) (Bar Chart)
- **Metric:** `histogram_quantile(0.95, rate(posture_spine_angle_bucket[5m]))`
- **Purpose:** 95th percentile posture angle across cohort
- **Interpretation:** Shows worst 5% of measurements during period
- **Use:** Identifies extreme posture deviations

#### 6. Hourly Aggregate Posture Metrics (Time Series)
- **Metric:** `avg_over_time(posture_spine_angle[1h])`
- **Purpose:** Trend analysis of posture over time
- **X-axis:** Time (hourly intervals)
- **Y-axis:** Average spine angle
- **Use:** Identify deterioration or improvement trends

### Variables / Filters
- None currently (aggregate view)
- Future: Intervention type, cohort, date range

### Statistical Queries (Future)
```promql
# Mean spine angle
avg(posture_spine_angle)

# Standard deviation
stddev(posture_spine_angle)

# Percentile distributions
histogram_quantile(0.25, ...) # Q1
histogram_quantile(0.50, ...) # Median
histogram_quantile(0.75, ...) # Q3
```

---

## Dashboard 3: System Health - Infrastructure (DevOps Dashboard)

### Purpose
Monitor health and performance of the PostureCare analytics platform:
- Service uptime
- Data ingestion health
- Query performance
- Resource utilization

### User: DevOps / System Admin
**Time Horizon:** 24 hours
**Refresh Rate:** 30 seconds

### Panels

#### 1. Prometheus Status (Stat Card - Binary)
- **Metric:** `up{job="prometheus"}`
- **Color Coding:** Green=UP (1), Red=DOWN (0)
- **Purpose:** Is the time-series database running?

#### 2. Sensor Service Status (Stat Card - Binary)
- **Metric:** `up{job="posture-sensors"}`
- **Color Coding:** Green=UP (1), Red=DOWN (0)
- **Purpose:** Are sensors sending data to Prometheus?

#### 3. Disk Usage (Stat Card)
- **Metric:** `prometheus_tsdb_symbol_table_size_bytes / 1024 / 1024`
- **Unit:** MB
- **Purpose:** Check if storage is filling up (retention policy enforcement)
- **Action:** Alert if >80% of retention threshold usage

#### 4. Query Rate (Stat Card)
- **Metric:** `rate(prometheus_http_requests_total[5m])`
- **Unit:** ops/s (operations per second)
- **Purpose:** Dashboard traffic / query load
- **Normal:** 1-10 ops/s, Spike: >50 ops/s suggests issue

#### 5. Service Uptime (Time Series)
- **Metric:** `up{job=~"prometheus|posture-sensors"}`
- **Purpose:** Historical uptime trend
- **Y-axis:** 1 (up) or 0 (down)
- **Use:** Identify reliability issues or outages

#### 6. Query Performance - p95 Latency (Time Series)
- **Metric:** `prometheus_http_request_duration_seconds_bucket`
- **Purpose:** Query response time trend
- **Interpretation:** p95 >1s suggests Prometheus overload
- **Action:** May need query optimization or scaling

### SLOs (Service Level Objectives)
- **Availability:** 99.5% uptime
- **Query Latency:** p95 < 1s
- **Data Freshness:** <30s scrape interval

---

## Metrics Dictionary

### Core Posture Metrics

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `posture_spine_angle` | Gauge | patient_id, session_id, measurement_id | Spine deviation from vertical (degrees) |
| `posture_current_angle` | Gauge | patient_id | Real-time current angle |
| `posture_monitoring_active` | Counter | patient_id, session_id | Binary: is this session being monitored? |
| `posture_alert_triggered` | Counter | patient_id, alert_type, session_id | Count of alerts for patient in period |
| `posture_measurement_count` | Counter | patient_id | Total measurements collected |

### Derived Metrics (PromQL)

```promql
# Average posture quality over time
avg(posture_spine_angle)

# Measurement frequency
rate(posture_measurement_count[5m])

# Alert frequency
rate(posture_alert_triggered[1h])

# Alert ratio
(count(posture_alert_triggered) / count(posture_measurement_count)) * 100
```

---

## Design Principles

1. **Clinical Meaningfulness:** Metrics reflect clinically relevant phenomena (sustained poor posture, not noise)
2. **Progressive Disclosure:** Summary stats on top, detailed views below
3. **Color Conventions:**
   - Green = Good / Normal
   - Yellow = Caution / Warning
   - Red = Critical / Alert
4. **Time Context:** Each panel shows appropriate time windows (real-time for clinicians, aggregate for researchers)
5. **GDPR Compliance:** No personally identifiable info; patient identifiers only via secure ID mapping

---

## Future Enhancements

### Planned Dashboards
1. **Intervention Effectiveness:** Track posture improvement before/after intervention
2. **Cohort Comparison:** Compare metrics across patient groups
3. **Session Details:** Deep dive into individual session events
4. **Data Quality:** Monitor sensor reliability, missing data, outliers

### Planned Features
- **Drill-down capability:** Click aggregate → individual patient
- **Custom alerts:** Clinician-defined thresholds per patient
- **Export to PDF:** Generate clinical reports
- **Annotations:** Mark intervention events on timelines
- **Forecasting:** Predict deterioration trends

### Integration Points
- **GraphQL API:** Query patient metadata (age, diagnosis, intervention type)
- **PostgreSQL:** Correlate sensor data with clinical events
- **Email alerts:** Send critical updates to clinicians
- **Mobile app:** Dashboard access on mobile devices

---

## Performance Considerations

### Query Optimization
- Use appropriate `rate()` windows for counters
- Aggregate at storage time when possible
- Avoid high-cardinality labels (e.g., patient names)

### Scaling Strategy
- **Current (PoC):** Docker Compose DEV environment
- **Staging:** Kubernetes with persistent volumes
- **Production:** RDS for PostgreSQL, managed Prometheus cluster

### Data Retention
- **Raw metrics:** 15 days (configurable in compose)
- **Aggregations:** Store 1h/1d bucketed data long-term
- **Session summaries:** Archive to cold storage after 90 days

---

## Security & Compliance

### Access Control
- [ ] Implement Grafana organizations (separate for clinicians/researchers)
- [ ] Role-based access: Admin, Editor, Viewer
- [ ] Patient data segregation (cannot see other clinic's data)

### Data Privacy
- [ ] Patient IDs hashed/anonymized in logs
- [ ] Query audit trail maintained
- [ ] Data minimization: Only posture metrics visible, no patient names

### Compliance Checklist
- [ ] GDPR: Data access logged, retention limits enforced
- [ ] HIPAA (if US): Encryption in transit, at rest, access logs
- [ ] ISO 27001: Information security controls

---

## Support & Maintenance

### Updating Dashboards
1. Export JSON from Grafana UI
2. Commit to `grafana/provisioning/dashboards/`
3. Restart Grafana: `docker-compose restart grafana`

### Monitoring Dashboard Health
- Check if panels show "N/A" (metric unavailable)
- Verify PromQL queries are valid via Prometheus UI
- Monitor query response times

### Common Issues

**Q: Dashboard shows no data**
- A: Check if Prometheus is scraping targets (`http://localhost:9090/targets`)
- A: Verify `scrape_configs` in `prometheus.yml`

**Q: Unusually high query latency**
- A: Check disk usage, may need pruning
- A: Review PromQL complexity; optimize queries

**Q: Alerts not triggering**
- A: Verify threshold values match metrics
- A: Check Alertmanager configuration (future)

---

**Last Updated:** 2026-03-31
**Version:** 1.0
**Status:** Foundation Dashboards - Production Ready for PoC
