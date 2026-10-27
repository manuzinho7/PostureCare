# PostureCare Dashboard Setup Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Port availability: 3000 (Grafana), 9090 (Prometheus), 5432 (PostgreSQL)

### Installation & Launch

1. **Clone/Enter the project directory:**
   ```bash
   cd PostureCare
   ```

2. **Configure environment (optional, defaults provided):**
   ```bash
   # Edit .env file if needed
   cat .env
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

### Access the Services

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | N/A |
| **PostgreSQL** | localhost:5432 | posture_user / posture_password |

## Architecture Overview

```
┌─────────────────┐
│  Wearable Data  │
│  (Sensors)      │
└────────┬────────┘
         │
         ├──→ ┌──────────────┐
         │    │  Prometheus  │ (Time-series DB)
         │    │ :9090        │
         │    └──────┬───────┘
         │           │
         └──→ ┌──────┴──────┐
              │  Grafana    │ (Dashboarding)
              │ :3000       │
              └─────────────┘

┌──────────────────┐
│ Patient Data     │
│ PostgreSQL :5432 │
└──────────────────┘
```

## Project Structure

```
PostureCare/
├── docker-compose.yml          # Service orchestration
├── .env                         # Environment variables
├── prometheus/
│   ├── prometheus.yml           # Prometheus scrape config
│   └── data/                    # Metrics storage (volume)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yml  # Prometheus & PostgreSQL sources
│   │   └── dashboards/
│   │       ├── patient-monitoring.json      # Clinician view
│   │       ├── research-analytics.json      # Researcher analytics
│   │       └── system-health.json           # Infrastructure health
│   └── data/                    # Grafana state (volume)
├── docs/
│   ├── SETUP.md                 # This file
│   └── DASHBOARDS.md            # Dashboard guide
└── sample-data/
    └── prometheus-metrics.txt   # Example metrics
```

## Common Commands

### Manage Services
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Restart specific service
docker-compose restart grafana
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U posture_user -d posture_db

# Check PostgreSQL status
docker-compose exec postgres pg_isready
```

### Monitor Data Ingestion
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query Prometheus metrics
curl 'http://localhost:9090/api/v1/query?query=up'
```

## Troubleshooting

### Grafana won't start
- **Check logs:** `docker-compose logs grafana`
- **Reset Grafana:** `docker-compose down && docker volume rm posture_grafana_data && docker-compose up -d grafana`
- **Ensure port 3000 is free:** `netstat -an | grep 3000`

### Prometheus not scraping metrics
- **Verify config:** Check `prometheus/prometheus.yml` syntax
- **Check targets status:** http://localhost:9090/targets
- **Restart Prometheus:** `docker-compose restart prometheus`

### PostgreSQL connection fails
- **Verify credentials:** `.env` file matches datasources config
- **Restart service:** `docker-compose restart postgres`
- **Check port:** `netstat -an | grep 5432`

### Volume permission errors (Linux)
```bash
# Fix permissions
sudo chown -R $USER: prometheus/data grafana/data
```

## Data Ingestion

### Adding Sample Metrics
Currently, sample metrics are provided in `sample-data/prometheus-metrics.txt`. To push metrics to Prometheus:

1. **Using Prometheus remote write (recommended for production):**
   - Configure a metrics exporter to send data to Prometheus
   - Update `prometheus.yml` scrape_configs

2. **Local testing:**
   - Manually configure a metrics endpoint
   - Add target to `prometheus/prometheus.yml`
   - Restart Prometheus

### Future: GraphQL API
The project will expose a GraphQL API to query patient/session data from PostgreSQL and correlate with sensor time-series data in Prometheus.

## Performance Tuning

### Storage Retention
Edit `docker-compose.yml` Prometheus command to adjust:
```yaml
- '--storage.tsdb.retention.time=15d'  # Change retention period
```

### Scrape Frequency
Edit `prometheus/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s  # Increase for less frequent scraping
```

## GDPR & Security Considerations

⚠️ **Before Production Deployment:**
- [ ] Change default Grafana credentials
- [ ] Implement authentication (OAuth, LDAP, SAML)
- [ ] Enable SSL/TLS for all connections
- [ ] Review database access patterns
- [ ] Implement role-based access control (RBAC)
- [ ] Audit data retention policies
- [ ] Ensure logging compliance
- [ ] Remove sample/test data

### Security Best Practices
1. **Credentials management:** Use Docker secrets for production
2. **Network isolation:** Use VPC and private networking
3. **Data anonymization:** Use patient IDs, not names
4. **Access control:** Implement Grafana organizations & teams
5. **Encryption:** Enable database SSL, encrypted volumes

## Next Steps

1. **Deploy GraphQL API** to expose patient metadata (Task T5.2)
2. **Integrate real sensor data** from wearable devices
3. **Create PromQL queries** for standard posture analytics
4. **Implement role-based access** in Grafana
5. **Set up alerting rules** for clinically relevant events
6. **Conduct GDPR compliance review**
7. **Deploy to production environment**

## Support & Documentation

- **Prometheus docs:** https://prometheus.io/docs/prometheus/latest/
- **Grafana docs:** https://grafana.com/docs/grafana/latest/
- **PromQL guide:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Project context:** See `Project description.txt`

---

**Last Updated:** 2026-03-31
**Version:** 1.0
**Status:** PoC / Development
