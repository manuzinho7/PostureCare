# 📊 PostureCare Dashboards - Guia Completo

## 🎯 Objetivo
Entender como as dashboards funcionam, visualizar dados de postura em tempo real e analisar padrões clínicos.

---

## 🚀 QUICK START (5 minutos)

### 1️⃣ Iniciar Serviços
```bash
cd c:\Users\manue\Downloads\ISEP2526\PostureCare
docker-compose up -d
```

Aguarde 30 segundos para os serviços estabilizarem.

### 2️⃣ Carregar Dados de Teste
```bash
./scripts/ingest-csv.sh sample-data/posture_session_example.csv
```

### 3️⃣ Abrir Grafana
Abra no browser: **http://localhost:3000**
- **Login:** admin / admin
- **Dashboards aparecem automaticamente**

---

## 🏗️ ARQUITETURA DO SISTEMA

```
CSV Data (postura_session_example.csv)
         ↓
    Python Parser (csv_ingester.py)
         ↓
    Prometheus Push Gateway (9091)
         ↓
    Prometheus Time-Series DB (9090)
         ↓
    Grafana Dashboards (3000)
         ↓
    Clinicians & Researchers
```

### Componentes:

| Componente | Porta | URL | Função |
|-----------|-------|-----|--------|
| **Grafana** | 3000 | http://localhost:3000 | Dashboards interativas |
| **Prometheus** | 9090 | http://localhost:9090 | Banco de dados de séries temporais |
| **Push Gateway** | 9091 | http://localhost:9091 | Recebe dados do parser CSV |
| **PostgreSQL** | 5432 | localhost:5432 | Metadados pacientes (futuro) |

### Dashboard & Analytics Layer

Esta camada transforma os dados recebidos em informação clínica e analítica em tempo real.

- **Prometheus** guarda e consulta métricas temporais do sistema, incluindo telemetria de postura e métricas operacionais.
- **Grafana** apresenta dashboards para clínicos, investigadores e DevOps.
- **Real-time metrics** permitem acompanhar postura ativa, alertas e frescura dos dados sem esperar por relatórios.
- **Clinician dashboards** focam-se em sessões de pacientes, eventos clínicos e histórico de episódios.
- **Monitoring flow**: wearable ou importação CSV → ingestão/exports → Prometheus → Grafana → equipas clínicas e técnicas.

---

## 📈 AS 3 DASHBOARDS

### Dashboard 1: 👨‍⚕️ Patient Posture Monitoring (Clínica)
**Para:** Médicos e enfermeiros
**Objetivo:** Monitorar postura de pacientes em tempo real
**Atualização:** A cada 10 segundos

#### Painéis:
1. **Active Patient Sessions** (Pie Chart)
   - Quantos pacientes estão sendo monitorados
   - Dados: Contagem de sessões ativas

2. **Current Average Posture Angle** (Gauge)
   - Ângulo atual da coluna vertebral em graus
   - Verde (0-15°) = Excelente
   - Amarelo (15-25°) = Bom
   - Laranja (25-35°) = Cuidado
   - Vermelho (>35°) = Ruim

3. **Posture Timeline** (Gráfico de Linha)
   - Histórico de ângulo de coluna ao longo do tempo
   - **Filtrável por:** Patient ID (dropdown)
   - Mostra padrões: recuperação, deterioração

4. **Posture Alerts Summary** (Donut Chart)
   - Quantos alertas foram acionados
   - Se >2 alertas = Risco elevado

#### Como Usar:
1. Vá em Dashboards → PostureCare → Patient Posture Monitoring
2. Clique no dropdown "Patient ID"
3. Selecione: patient_001, patient_002 ou patient_003
4. Observe:
   - **patient_001:** 1 alerta (padrão de recuperação)
   - **patient_002:** 4 alertas (RISCO ALTO - postura sustentada ruim)
   - **patient_003:** 0 alertas (excelente - baseline controle)

---

### Dashboard 2: 📊 Research Analytics (Pesquisa)
**Para:** Pesquisadores e epidemiologistas
**Objetivo:** Análise de população inteira e tendências
**Atualização:** A cada 30 segundos

#### Painéis:
1. **Total Studies Patients** (Card)
   - Total de doentes na coorte
   - Exemplo: 3 doentes no teste

2. **Measurements/Hour** (Card)
   - Quantas medidas são feitas por hora
   - Exemplo: 30 medições/hora

3. **Alert Rate %** (Card)
   - Percentagem de medições com alerta
   - Fórmula: (alertas / medições) × 100
   - Exemplo: 5/30 = 16.7%

4. **Critical Events** (Card)
   - Total de eventos críticos (alertas)
   - Exemplo: 5 eventos

5. **Posture Distribution** (Bar Chart)
   - Percentil 95 dos ângulos
   - Mostra os piores 5% de medições
   - Identifica outliers

6. **Hourly Aggregate** (Gráfico Linha)
   - Tendência horária do ângulo médio
   - Mostra melhoria/deterioração ao longo do tempo

#### Como Usar:
1. Vá em Dashboards → PostureCare → Research Analytics - Posture Metrics
2. Veja métricas agregadas da população inteira
3. Use para:
   - Comparar coortes
   - Identificar tendências
   - Preparar relatórios para investigação

---

### Dashboard 3: 🔧 System Health (DevOps)
**Para:** Administradores de sistema
**Objetivo:** Monitorar saúde da infraestrutura
**Atualização:** A cada 30 segundos

#### Painéis:
1. **Prometheus Status** (Card Binário)
   - Verde = Sistema UP
   - Vermelho = Sistema DOWN

2. **Sensor Service Status** (Card Binário)
   - Verde = Sensores enviando dados
   - Vermelho = Sensores offline

3. **Disk Usage** (Card)
   - Espaço em disco utilizado (MB)
   - Alerta se >80% da retenção

4. **Query Rate** (Card)
   - Operações por segundo
   - Normal: 1-10 ops/s
   - Spike: >50 ops/s = Problema

5. **Service Uptime** (Gráfico Linha)
   - Histórico de disponibilidade
   - 1 = UP | 0 = DOWN

6. **Query Performance** (Gráfico Linha)
   - Latência p95 das queries
   - Alerta se >1 segundo

#### Como Usar:
1. Vá em Dashboards → PostureCare → System Health - Infrastructure
2. Verifique que todos os serviços estão GREEN
3. Use para:
   - Diagnosticar problemas
   - Monitorar recursos
   - Planejar escalabilidade

---

## 🔄 FLUXO DE DADOS COMPLETO

### Passo 1: Arquivo CSV
```csv
patient_001,session_2026_03_31_001,2026-03-31T10:00:00,22.5,5.2,3.1,m001
patient_001,session_2026_03_31_001,2026-03-31T10:01:00,23.1,4.8,3.2,m002
patient_002,session_2026_03_31_002,2026-03-31T11:00:00,26.8,6.1,3.5,m003
...
```

**Colunas necessárias:**
- `patient_id` - Identificador do doente
- `session_id` - ID da sessão de monitoramento
- `timestamp` - Data/hora (ISO 8601)
- `spine_angle` - Ângulo da coluna (graus)
- `shoulder_roll` - Rotação dos ombros
- `head_tilt` - Inclinação da cabeça
- `measurement_id` - ID único da medida

### Passo 2: Parser Converte para Prometheus
O script `csv_ingester.py` transforma cada linha em **métricas Prometheus**:

```
posture_spine_angle{patient_id="patient_001", session_id="session_2026_03_31_001"} 22.5
posture_shoulder_roll{patient_id="patient_001", ...} 5.2
posture_head_tilt{patient_id="patient_001", ...} 3.1
posture_alert_triggered{patient_id="patient_001", ...} 1  [se angle > 30°]
```

### Passo 3: Push Gateway Recebe
As métricas são enviadas ao **Push Gateway** (9091):
```bash
curl -d @metrics.txt http://localhost:9091/metrics/job/posture_ingester
```

### Passo 4: Prometheus Scrapa
A cada 15 segundos, Prometheus vai buscar ao Push Gateway:
```
GET http://localhost:9091/metrics
```

### Passo 5: Grafana Consulta
As dashboards fazem queries PromQL ao Prometheus:
```promql
# Exemplo: Todos os ângulos do patient_001
posture_spine_angle{patient_id="patient_001"}

# Média de todos os ângulos
avg(posture_spine_angle)

# Contagem de alertas
count(posture_alert_triggered)
```

### Passo 6: Visualização
Os dados aparecem nos gráficos em tempo real!

---

## 💡 EXEMPLO PRÁTICO COM DADOS REAIS

### Cenário: 3 Doentes, 30 Medições

#### Doente 001 (Recuperação Normal)
- Ângulo inicial: 22.5° (Bom)
- Pico: 31.2° (Alerta acionado)
- Final: 22.1° (Recuperação)
- **Resultado:** 1 alerta | Padrão NORMAL

#### Doente 002 (RISCO ALTO) ⚠️
- Ângulo consistente: 26.8° → 33.2° (Deterioração)
- **4 alertas consecutivos** entre 11:04-11:07
- Pico: 33.2° (11:05)
- **Resultado:** 4 alertas | Padrão CRÍTICO

#### Doente 003 (Excelente)
- Ângulo consistente: 17.9° - 21.3° (Muito bom)
- **0 alertas**
- **Resultado:** Baseline de controlo

---

## 🎨 INTERPRETAÇÃO DE CORES

### Ângulo de Coluna:
```
0-15°    ✅ Green   = Postura excelente
15-25°   🟢 Green   = Postura boa
25-35°   🟡 Yellow  = Cuidado
>35°     🔴 Red     = Alerta crítico
```

### Status do Sistema:
```
1         ✅ Green   = UP (funcionando)
0         🔴 Red     = DOWN (offline)
```

### Taxa de Alertas:
```
0-5%      ✅ Green   = Raro
5-15%     🟢 Green   = Ocasional
15-30%    🟡 Yellow  = Frequente
>30%      🔴 Red     = Crítico
```

---

## 🔧 COMMANDS ÚTEIS

### Verificar Status
```bash
# Todos os serviços
docker-compose ps

# Logs da Grafana
docker-compose logs -f grafana

# Logs do Prometheus
docker-compose logs -f prometheus
```

### Testar Métrica no Prometheus
1. Aceda: http://localhost:9090
2. Separador "Graph"
3. Digite query:
```promql
# Ver todas as métricas de um doente
posture_spine_angle{patient_id="patient_001"}

# Média global
avg(posture_spine_angle)

# Alertas por doente
sum by (patient_id) (posture_alert_triggered)
```

### Recarregar Dados
```bash
# Se os dados não aparecem, força scrape ao Push Gateway
curl http://localhost:9091/metrics

# Limpar histórico de Push Gateway
curl -X DELETE http://localhost:9091/metrics/job/posture_ingester
```

### Resetar Grafana (se não funcionar)
```bash
docker-compose down
docker volume rm posture_grafana_data
docker-compose up -d
```

---

## 📋 CHECKLIST - ANTES DE COMEÇAR

Certifique-se que:

- [ ] **Docker instalado:** `docker --version` mostra versão
- [ ] **Serviços correm:** `docker-compose ps` mostra 4 serviços UP
- [ ] **Grafana acessível:** http://localhost:3000 abre sem erro
- [ ] **Prometheus acessível:** http://localhost:9090 abre sem erro
- [ ] **Dados carregados:** Correu `./scripts/ingest-csv.sh`
- [ ] **Prometheus tem métricas:** http://localhost:9091/metrics tem dados
- [ ] **30 segundos passaram:** Para Prometheus buscar ao Push Gateway

---

## ❓ TROUBLESHOOTING

### Problema: Grafana mostra "No data"

**Solução:**
1. Espere 30-45 segundos (tempo de scrape)
2. Verifique Push Gateway: `curl http://localhost:9091/metrics`
3. Verifique Prometheus targets: http://localhost:9090/targets

### Problema: Portas já em uso

**Solução:**
```bash
# Encontre processo na porta 3000
netstat -ano | findstr :3000

# Mate o processo
taskkill /PID <PID> /F

# Inicie novamente
docker-compose up -d
```

### Problema: CSV ingestion falha

**Solução:**
```bash
# Verifique Python
python --version

# Execute parser directly
python scripts/csv_ingester.py sample-data/posture_session_example.csv
```

### Problema: Gráficos vazios após carregar dados

**Solução 1:** Refresque a página (Ctrl+F5)

**Solução 2:** Verifique se dados chegaram ao Prometheus
```bash
# Via Prometheus UI
http://localhost:9090/graph
# Digite: posture_spine_angle
# Execute: Pressione Enter
```

**Solução 3:** Aguarde o scrape interval (15 segundos)

---

## 📚 PRÓXIMAS FASES

### Phase 2: GraphQL API
- Consultar metadados dos doentes
- Correlacionar dados de sensores com informações clínicas
- Histórico de intervenções

### Phase 3: RBAC (Controlo de Acesso)
- Diferentes roles: Admin, Editor, Viewer
- Segregação por clínica
- Audit logging

### Phase 4: Alertas em Tempo Real
- Notificações por email
- Integração com sistemas hospitalares
- Regras customizadas por doente

---

## 🎓 CONCEITOS IMPORTANTES

### PromQL (Prometheus Query Language)

Exemplos de queries usadas nas dashboards:

```promql
# 1. Valor instantâneo atual
posture_spine_angle{patient_id="patient_001"}

# 2. Média nos últimos 5 minutos
avg_over_time(posture_spine_angle[5m])

# 3. Taxa de mudança (derivative)
rate(posture_measurement_count[1h])

# 4. Agregação por label
sum by (patient_id) (posture_alert_triggered)

# 5. Percentil 95
histogram_quantile(0.95, rate(posture_spine_angle_bucket[5m]))

# 6. Contagem de valores únicos
count(distinct(posture_patient_id))

# 7. Condição (se angle > 30)
posture_spine_angle > 30
```

### Tipos de Métricas

1. **Gauge** - Valor que sobe e desce
   - Exemplo: `posture_spine_angle` (pode aumentar ou diminuir)

2. **Counter** - Só sobe (reseta quando reinicia)
   - Exemplo: `posture_alert_triggered` (acumula alertas)

3. **Histogram** - Distribuição de valores
   - Exemplo: Percentis de ângulos

---

## 📞 HELP

Se precisar de ajuda:

1. **Logs:** `docker-compose logs -f`
2. **Prometheus Docs:** https://prometheus.io/docs/
3. **Grafana Docs:** https://grafana.com/docs/
4. **PromQL Cheat Sheet:** https://prometheus.io/docs/prometheus/latest/querying/basics/

---

**Última atualização:** 2026-03-31
**Versão:** 1.0
**Status:** Pronto para Produção (PoC)
