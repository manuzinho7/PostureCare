# PostureCare CSV Data Ingestion Guide

## Overview

Este guia descreve como importar dados de postura de ficheiros CSV para o Prometheus, onde os dados fica disponível para visualização nas dashboards Grafana do PostureCare.

### Fluxo de dados

```
Ficheiro CSV → CSV Ingester (Python) → Prometheus Push Gateway → Prometheus → Grafana
```

---

## CSV Format Specification

### Expected Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `patient_id` | string | Identificador único do paciente | `patient_001` |
| `session_id` | string | Identificador da sessão de monitorização | `session_2026_03_31_001` |
| `timestamp` | ISO datetime | Data/hora da medição (ISO 8601) | `2026-03-31T10:00:00` |
| `spine_angle` | float | Ângulo da coluna (desvio em graus) | `22.5` |
| `shoulder_roll` | float | Inclinação do ombro (graus) | `5.2` |
| `head_tilt` | float | Inclinação da cabeça (graus) | `3.1` |
| `measurement_id` | string | ID único da medição | `m001` |

### CSV Example

```csv
patient_id,session_id,timestamp,spine_angle,shoulder_roll,head_tilt,measurement_id
patient_001,session_2026_03_31_001,2026-03-31T10:00:00,22.5,5.2,3.1,m001
patient_001,session_2026_03_31_001,2026-03-31T10:01:00,23.1,5.8,2.9,m002
patient_002,session_2026_03_31_002,2026-03-31T11:00:00,26.8,6.5,3.8,m011
```

**Validações:**
- Todas as colunas são obrigatórias
- Valores numéricos (spine_angle, shoulder_roll, head_tilt) devem ser válidos
- Timestamp deve estar em formato ISO 8601
- Sem valores vazios permitidos

---

## Quick Start

### 1. Preparar dados CSV

Coloque o ficheiro CSV em `sample-data/`:

```bash
cp seu_ficheiro_dados.csv PostureCare/sample-data/
```

### 2. Iniciar os serviços

```bash
cd PostureCare
docker-compose up -d
```

Isto inicia:
- ✅ Prometheus (http://localhost:9090)
- ✅ Grafana (http://localhost:3000)
- ✅ Push Gateway (http://localhost:9091)
- ✅ PostgreSQL (localhost:5432)

### 3. Carregar dados

#### Opção A: Script Bash (Recomendado)

```bash
# Com o exemplo incluído
./scripts/ingest-csv.sh

# Ou com um ficheiro específico
./scripts/ingest-csv.sh sample-data/seu_ficheiro.csv
```

#### Opção B: Python Direct

```bash
# Setup
python -m pip install requests

# Run
python scripts/csv_ingester.py sample-data/seu_ficheiro.csv
```

#### Opção C: Docker

```bash
# Build image
docker build -f Dockerfile.ingester -t posture-ingester .

# Run com volume
docker run --network posture_posture-net \
  -v $(pwd)/sample-data:/data \
  posture-ingester /data/seu_ficheiro.csv
```

### 4. Verificar dados nos dashboards

1. Aceder a http://localhost:3000
2. Login: `admin` / `admin`
3. Ver dashboards:
   - **Patient Posture Monitoring** - Dados em tempo real
   - **Research Analytics** - Agregações
   - **System Health** - Status dos serviços

---

## Detailed Ingestion Process

### Python Ingester (`csv_ingester.py`)

O script Python faz as seguintes operações:

1. **Validação de CSV**
   - Verifica se existem todas as colunas necessárias
   - Valida tipos de dados (floats, strings, timestamps)
   - Reporta erros por linha

2. **Conversão para Prometheus**
   - Converte cada linha do CSV em métricas Prometheus
   - Gera alerts automáticos (postura > 30°)
   - Calcula agregações (total medições, pacientes, etc.)

3. **Push para Gateway**
   - Envia métricas ao Prometheus Push Gateway
   - Push Gateway armazena as métricas
   - Prometheus scrapes o Push Gateway (configurado cada 15s)

### Metrics Generated

Para cada linha do CSV, são geradas as seguintes métricas:

```promql
# Gauges (valores actuais)
posture_spine_angle{patient_id="patient_001",session_id="session_001"} 22.5
posture_shoulder_roll{patient_id="patient_001",session_id="session_001"} 5.2
posture_head_tilt{patient_id="patient_001",session_id="session_001"} 3.1

# Counters (contadores globais)
posture_monitoring_active{patient_id="patient_001",session_id="session_001"} 1
posture_measurement_count 30
posture_alert_count 5
posture_patient_count 3

# Alerts (gerados automaticamente)
posture_alert_triggered{patient_id="patient_001",alert_type="excessive_spine_angle"} 1
```

---

## Usage Examples

### Example 1: Ingerir dados de teste

```bash
# Usar o CSV de exemplo incluído
cd PostureCare
./scripts/ingest-csv.sh sample-data/posture_session_example.csv

# Verificar métricas no Prometheus
# http://localhost:9090/graph?query=posture_spine_angle
```

### Example 2: Ingerir dados de múltiplas sessões

```bash
# Ficheiros separados por sessão
for csv in data/session_*.csv; do
  ./scripts/ingest-csv.sh "$csv" "posture_session_$(basename $csv .csv)"
done
```

### Example 3: Validar CSV sem fazer push

```bash
python scripts/csv_ingester.py dados.csv --output metrics.txt

# Inspeccionar o ficheiro de métricas
cat metrics.txt
```

### Example 4: Custom Push Gateway

```bash
# Se Push Gateway está noutro servidor
./scripts/ingest-csv.sh dados.csv --push-gateway http://192.168.1.100:9091
```

---

## Troubleshooting

### "Connection refused" ao Push Gateway

**Problema:** Script não consegue contactar Push Gateway

**Solução:**
```bash
# Verificar se Push Gateway está a correr
docker-compose ps push-gateway

# Ou se em outro servidor
curl http://localhost:9091/metrics
```

### CSV file not found

**Problema:** Ficheiro CSV não existe no caminho especificado

**Solução:**
```bash
# Verificar caminhos
ls -la sample-data/

# Usar caminho absoluto
python scripts/csv_ingester.py /home/user/dados.csv
```

### Invalid CSV format

**Problema:** Script reporta erros de validação

**Solução:**
- Verificar que todas as colunas estão presentes
- Validar tipos de dados (numbers vs strings)
- Confirmar formato ISO 8601 dos timestamps
- Verificar que não há valores vazios

```bash
# Inspecionar CSV
head -5 dados.csv
```

### Métricas não aparecem no Prometheus

**Problema:** Dados foram pushed mas não aparecem nos gráficos

**Solução:**
1. Verificar Push Gateway: http://localhost:9091/metrics
2. Verificar Prometheus targets: http://localhost:9090/targets
3. Aguardar scrape interval (padrão 15s)
4. Verificar que o job_name está correto

```bash
# Forçar scrape no Prometheus
curl http://localhost:9090/api/v1/targets
```

---

## Performance & Scaling

### Large CSV Files (>100 MB)

Para ficheiros muito grandes:

1. **Dividir em chunks:**
   ```bash
   # Processar em lotes
   split -l 10000 grande_dados.csv chunk_
   for chunk in chunk_*; do
     ./scripts/ingest-csv.sh "$chunk"
   done
   ```

2. **Aumentar retention:**
   ```yaml
   # docker-compose.yml
   prometheus:
     command:
       - '--storage.tsdb.retention.time=30d'  # Aumentar
   ```

3. **Otimizar Push Gateway:**
   ```bash
   # docker-compose.yml > push-gateway
   command:
     - '--persistence.file=/prometheus/metrics'
     - '--persistence.interval=5m'
   ```

### Batch Ingestion

Para múltiplos ficheiros em paralelo:

```bash
# Usar GNU parallel (se instalado)
parallel ./scripts/ingest-csv.sh ::: sample-data/*.csv

# Ou com xargs
find sample-data -name "*.csv" | xargs -I {} ./scripts/ingest-csv.sh {}
```

---

## Best Practices

### 1. Nomenclatura Consistente

```
✓ GOOD: patient_001, patient_002, ...
✗ BAD:  P1, P2, ... (difícil de rastrear)

✓ GOOD: session_2026_03_31_001
✗ BAD:  session1 (ambíguo)
```

### 2. Timestamps Precisos

```
✓ GOOD: 2026-03-31T10:30:45 (ISO 8601)
✗ BAD:  31/03/2026 10:30 (ambíguo)
```

### 3. Validar Dados Antes

```bash
# Preview do CSV antes de ingerir
head -20 dados.csv

# Contar linhas
wc -l dados.csv

# Verificar se há valores vazios
grep -c '^$' dados.csv
```

### 4. Manter Backup

```bash
# Backup de dados antes de processar
cp dados.csv dados_backup_$(date +%Y%m%d_%H%M%S).csv
```

### 5. Documentar Origem

```bash
# Adicionar comentário ao CSV sobre origem
echo "# Session recorded on 2026-03-31 by Device_XYZ" >> dados.csv
```

---

## FAQ

**Q: Posso atualizar dados de uma sessão existente?**

A: Sim. Cada vez que faz push, as novas métricas substituem as antigas para esse job. Use job names únicos por sessão:
```bash
./scripts/ingest-csv.sh dados.csv --job-name "session_2026_03_31_001"
```

**Q: Qual é o volume máximo de dados?**

A: Prometheus pode lidar com milhões de time-series. Para 100 MB de dados (~500k medições), espere 1-2 minutos de ingestão.

**Q: Posso integrar isto com um pipeline de ETL?**

A: Sim! O script Python pode ser chamado de qualquer orquestrador (Airflow, Cron, etc.):
```bash
30 */2 * * * /home/posture/scripts/ingest-csv.sh /data/daily_export.csv
```

**Q: Os dados são deletados automaticamente?**

A: Sim, conforme Prometheus retention policy (default 15 dias). Altere em `docker-compose.yml`.

---

## Next Steps

1. ✅ Preparar ficheiro CSV com seus dados
2. ✅ Executar ingestão
3. ✅ Visualizar em Grafana
4. 🔲 Configurar ingestão automática (Cron/Airflow)
5. 🔲 Implementar GraphQL API para queries estruturadas
6. 🔲 Adicionar role-based access control

---

**Last Updated:** 2026-03-31
**Version:** 1.0
**Status:** Production Ready
