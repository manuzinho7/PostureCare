# PostureCare Dashboard Platform

**Digital Health Analytics for Continuous Posture Monitoring**

## What is PostureCare?

PostureCare is a health data platform that monitors patient posture using wearable sensors and provides real-time analytics dashboards for clinicians and researchers.

This repository contains the analytics and visualization layer of PostureCare, built with:
- **Prometheus** - Time-series database for sensor data
- **Grafana** - Interactive dashboards for clinicians and researchers
- **PostgreSQL** - Structured patient and session data
- **Docker** - Containerized development and deployment

## Quick Start

```bash
# Start all services
docker-compose up -d

# Access services
# Grafana:     http://localhost:3000 (admin / admin)
# Prometheus:  http://localhost:9090
# PostgreSQL:  localhost:5432
```

See [SETUP.md](docs/SETUP.md) for detailed installation and troubleshooting.

## Apresentação Das Dashboards

### O Que Acontece Quando Corres `docker compose up -d`
Quando este comando é lançado, o Docker sobe o conjunto completo de serviços do PostureCare:
- **PostgreSQL** guarda os dados estruturados de pacientes e sessões.
- **Redis** suporta eventos em tempo real para as subscriptions da GraphQL API.
- **Push Gateway** recebe métricas enviadas por lotes ou por geração sintética.
- **Prometheus** recolhe essas métricas e torna-as consultáveis.
- **GraphQL API** arranca, expõe queries/subscriptions e gera métricas sintéticas para demonstração.
- **Grafana** carrega as dashboards já provisionadas.

Na inicialização, a GraphQL API também pode semear dados sintéticos para que as dashboards tenham informação logo ao arrancar, mesmo antes de haver ingestão de CSV.

### Fluxo De Dados
```
docker compose up -d
    ↓
Serviços arrancam (PostgreSQL, Redis, Push Gateway, Prometheus, GraphQL API, Grafana)
    ↓
GraphQL API gera métricas sintéticas e publica eventos em tempo real
    ↓
CSV Ingester pode enviar métricas de ficheiros CSV para o Push Gateway
    ↓
Prometheus recolhe as métricas do Push Gateway e expõe-as para consulta
    ↓
Grafana mostra os painéis com base nas queries PromQL
```

### Fontes De Dados
- **GraphQL API**: gera telemetria sintética e suporta eventos em tempo real.
- **CSV ingestion**: permite carregar dados históricos de exemplos ou testes.
- **PostgreSQL**: fornece o contexto estruturado de pacientes e sessões.

### Painéis Principais
#### Patient Posture Monitoring
Painel clínico para acompanhar um paciente selecionado.
- **Current Posture Angle**: indicador rápido do estado atual da postura do paciente selecionado.
- **Patient Posture Timeline (Spine Angle)**: evolução temporal da coluna/postura para o paciente selecionado.
- **IMU Orientation / EMG / SmO2 / Bateria**: métricas clínicas detalhadas para o paciente em foco.
- **Posture Alerts Summary**: resumo dos alertas disparados.

#### Research Analytics
Painel para análise agregada.
- **Total Studies Patients**: número de pacientes presentes no conjunto de dados.
- **Measurements/Hour**: velocidade de ingestão.
- **Alert Rate %**: percentagem de medições com alerta.
- **Critical Events**: total de eventos críticos.
- **Posture Distribution (p95)**: percentil 95 da postura para identificar piores casos.
- **Hourly Aggregate Posture Metrics**: tendência horária da postura.

#### System Health
Painel de operação e infraestrutura.
- Estado do Prometheus.
- Estado do serviço de sensores/dados.
- Uso de disco e carga de queries.
- Latência e saúde geral da pipeline.

#### Sensor and Device Telemetry
Painel técnico-clínico para IMU, EMG, SmO2 e estado do ESP32.
- Filtro por paciente (ou todos).
- Séries de orientação, intensidade de movimento, atividade muscular e qualidade NIRS.
- Estado de bateria, temperatura e memória livre do dispositivo.

## Project Structure

```
PostureCare/
├── docker-compose.yml              # Service orchestration
├── .env                             # Configuration
├── prometheus/                      # Time-series database
├── grafana/                         # Dashboarding platform
│   └── provisioning/dashboards/
│       ├── patient-monitoring.json  # Clinician dashboard
│       ├── research-analytics.json  # Researcher dashboard
│       ├── system-health.json       # DevOps dashboard
│       └── sensor-device-telemetry.json # Sensor/ESP32 dashboard
├── docs/
│   ├── SETUP.md                    # Setup & deployment guide
│   ├── DASHBOARDS.md               # Dashboard design documentation
│   └── README.md                   # This file
└── sample-data/                    # Example metrics for testing
```

## Dashboards

### 1. Patient Posture Monitoring (Clinician)
Real-time patient posture tracking with alerts and session history.
- Current posture angle
- Timeline of spine angle deviations
- Alert summary
- Configurable by patient (patient_id filter)

### 2. Research Analytics (Researcher)
Population-level insights for clinical research and intervention analysis.
- Cohort statistics (patient count, measurements/hour)
- Alert rate analysis
- Posture distribution and trends
- Data export ready

### 3. System Health (DevOps)
Infrastructure monitoring and performance metrics.
- Service uptime (Prometheus, sensors)
- Data ingestion health
- Query performance (p95 latency)
- Disk usage monitoring

### 4. Sensor and Device Telemetry
Cross-domain sensor telemetry dashboard.
- IMU (roll/pitch/yaw, accel, gyro)
- EMG (RMS/MAV/IEMG, MDF/MNF, activation)
- SmO2 (saturação, tendência, qualidade)
- ESP32 (bateria, temperatura, heap)

## Dashboard & Analytics Layer

The dashboard and analytics layer is the presentation and decision-support surface of PostureCare. It transforms incoming telemetry into real-time clinical visibility and historical analytics for clinicians, researchers, and system operators.

### Core Components
- **Prometheus** stores and queries time-series telemetry from the ingestion layer, enabling real-time monitoring, alert evaluation, and historical analysis.
- **Grafana** visualizes the telemetry through role-specific dashboards for clinicians, researchers, and DevOps/system administrators.
- **PostgreSQL** stores structured patient, session, and configuration data that contextualizes the telemetry and supports clinical interpretation.

### Monitoring Flow
```
Wearable sensors or the mobile gateway generate telemetry
    ↓
The telemetry is ingested or exported into the backend pipeline
    ↓
Prometheus stores the metrics and exposes them for queries and alerting
    ↓
Grafana consumes those metrics and displays dashboards
    ↓
Clinicians, researchers, and operators use the dashboards to monitor posture, analyze trends, and follow operational health
```

### What the Layer Supports
- **Real-time metrics** for active posture monitoring and alerting
- **Clinician dashboards** for individual patients, sessions, and clinical events
- **Analytics views** for aggregated posture trends and cohort-level analysis
- **Operational monitoring** for ingestion health, service uptime, and platform performance

### Data Sources
- Wearable telemetry streams
- CSV ingestion pipelines used for testing and demonstrations
- Session and patient metadata stored in PostgreSQL

### Dashboard Usage by Role

Clinicians:
- Monitor the posture of a selected patient in real time
- Review alert summaries and session history
- Observe posture deviations and clinical events during active monitoring

Researchers:
- Analyze aggregate posture data across patients or sessions
- Compare cohorts and observe trends over time
- Use historical metrics for study and intervention analysis

DevOps / System Administrators:
- Monitor Prometheus and Grafana availability
- Check ingestion health and data freshness
- Inspect system performance, query load, and storage usage

## Key Features

✅ **Real-time Monitoring** - refresh configurado a partir de 1 segundo
✅ **CSV Stream Pipeline** - geração contínua de CSV e ingestão automática para Prometheus
✅ **Multi-user Support** - Separate views for clinicians, researchers, DevOps
✅ **Patient Privacy** - Anonymous IDs, no PII in metrics
✅ **Production Ready** - Docker-based, scalable architecture
✅ **Extensible** - GraphQL API for patient metadata, synthetic telemetry, and real-time subscriptions

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Time-Series DB | Prometheus | Store and query sensor data |
| Dashboarding | Grafana | Visualize metrics, create alerts |
| Data Storage | PostgreSQL | Patient/session metadata |
| Containerization | Docker | Development and deployment |

## Development Status

🔷 **Phase 1: Foundation (Current)**
- ✅ Docker infrastructure setup
- ✅ 4 dashboards (Clinician, Researcher, DevOps, Sensor/Device)
- ✅ Prometheus configuration
- ✅ Grafana provisioning
- ✅ Sample data generation contínua (1 linha/segundo)

🔶 **Phase 2: Integration (Next)**
- GraphQL API for patient data and telemetry
- Real sensor data ingestion
- PromQL queries optimization
- Role-based access control

🔴 **Phase 3: Production**
- GDPR compliance review
- Alerting rules and notifications
- Performance tuning and scaling
- Security hardening

## Documentation

- **[SETUP.md](docs/SETUP.md)** - Installation, configuration, and troubleshooting
- **[DASHBOARDS.md](docs/DASHBOARDS.md)** - Detailed dashboard design, metrics, and usage
- **[Project description.txt](Project%20description.txt)** - Full project context and goals

## Common Tasks

### Check service status
```bash
docker-compose ps
```

### View logs
```bash
docker-compose logs -f grafana
```

### Add metrics to Prometheus
See [SETUP.md - Data Ingestion](docs/SETUP.md#data-ingestion)

### Reset Grafana
```bash
docker-compose down
docker volume rm posture_grafana_data
docker-compose up -d
```

## GDPR & Security

⚠️ This is a development platform. Before production:
- [ ] Change default credentials
- [ ] Enable SSL/TLS
- [ ] Implement authentication (OAuth/OIDC)
- [ ] Review data retention policies
- [ ] Conduct security audit
- [ ] Implement role-based access control

See [SETUP.md - GDPR & Security](docs/SETUP.md#gdpr--security-considerations)

## Troubleshooting

**Grafana won't start?**
```bash
docker-compose logs grafana
```

**No metrics showing?**
Check Prometheus targets: http://localhost:9090/targets

**Permission denied errors?**
```bash
sudo chown -R $USER: prometheus/data grafana/data
```

See [SETUP.md - Troubleshooting](docs/SETUP.md#troubleshooting) for more.

## Contributors

This project is part of the ISEP 2025-2026 curriculum.

## License

TBD - Subject to institution guidelines

## Support

For issues and questions:
1. Check [SETUP.md](docs/SETUP.md) troubleshooting section
2. Review [DASHBOARDS.md](docs/DASHBOARDS.md) for dashboard usage
3. Consult Prometheus/Grafana official documentation links in SETUP.md

---

**Status:** PoC / Development
**Last Updated:** 2026-03-31
**Version:** 1.0
