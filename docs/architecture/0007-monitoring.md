# ADR 0007: Monitoring & Observability - Prometheus + Simple Dashboard

**Date:** 2026-02-09  
**Status:** Accepted

## Context

We need visibility into platform health and performance:
- Is the API responding correctly?
- Are analytics queries slow?
- Is the data refresh working?
- Are there data quality issues?
- What's using database resources?

For a production internal tool, even with 10 users, monitoring is essential for debugging issues quickly.

## Decision

We implement **Prometheus-based monitoring** with alert rules and simple HTML dashboard:

**Metrics Collected**

```
API Metrics:
  - http_requests_total (counter: by endpoint, method, status)
  - http_request_duration_seconds (histogram: response times)
  - http_requests_in_progress (gauge)

Database Metrics:
  - database_queries_total (counter: by query type)
  - database_query_duration_seconds (histogram)
  - database_connections_active (gauge)
  - database_connection_pool_size (gauge)

Cache Metrics:
  - redis_hits_total (counter)
  - redis_misses_total (counter)
  - redis_memory_bytes (gauge)

Business Metrics:
  - prospects_total (gauge)
  - data_refresh_duration_seconds (histogram)
  - data_quality_completeness_percent (gauge)
  - data_refresh_last_timestamp (gauge)

System Metrics:
  - process_cpu_percent (gauge)
  - process_memory_bytes (gauge)
  - process_uptime_seconds (gauge)
```

**Implementation**

```python
# FastAPI + Prometheus client
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Metrics
request_count = Counter('http_requests_total', 'HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])
db_query_duration = Histogram('database_query_duration_seconds', 'Database query latency', ['operation'])
cache_hits = Counter('redis_hits_total', 'Cache hits')
cache_misses = Counter('redis_misses_total', 'Cache misses')

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(endpoint=request.url.path).observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Alert Rules**

```yaml
# prometheus_rules.yml
groups:
  - name: api_health
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate ({{ $value }}%)"

      - alert: SlowRequests
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow requests (p95: {{ $value }}s)"

  - name: data_health
    rules:
      - alert: DataRefreshFailed
        expr: increase(data_refresh_duration_seconds[1d]) == 0
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Data refresh has not completed in 24h"

      - alert: DataQualityIssue
        expr: data_quality_completeness_percent < 99
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Data completeness below 99% ({{ $value }}%)"

  - name: resource_health
    rules:
      - alert: HighMemoryUsage
        expr: process_memory_bytes / 1e9 > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage high ({{ $value }}GB)"

      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_active / database_connection_pool_size > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Connection pool {{ $value }}% full"
```

**Alert Notification**

```python
# Send alerts via email
@app.post("/api/alerts/notify")
async def send_alert(alert_data: dict):
    """Webhook from Alertmanager"""
    for alert in alert_data.get('alerts', []):
        send_email(
            to="admin@company.com",
            subject=f"Alert: {alert['labels']['alertname']}",
            body=alert['annotations']['summary']
        )
    return {"status": "ok"}
```

**Simple HTML Dashboard**

```html
<!-- dashboard/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Analytics Platform Health</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <h1>Platform Health Dashboard</h1>
    
    <div id="status-grid">
        <div class="metric">
            <h3>API Uptime</h3>
            <p class="value" id="uptime">-</p>
        </div>
        <div class="metric">
            <h3>Error Rate (5m)</h3>
            <p class="value" id="error-rate">-</p>
        </div>
        <div class="metric">
            <h3>P95 Latency</h3>
            <p class="value" id="latency">-</p>
        </div>
        <div class="metric">
            <h3>Cache Hit Rate</h3>
            <p class="value" id="cache-hit">-</p>
        </div>
    </div>
    
    <div id="charts">
        <div id="requests-chart"></div>
        <div id="latency-chart"></div>
        <div id="data-quality-chart"></div>
    </div>
    
    <script>
        async function updateMetrics() {
            const response = await fetch('/api/metrics/summary');
            const data = await response.json();
            
            document.getElementById('uptime').innerText = data.uptime;
            document.getElementById('error-rate').innerText = data.error_rate;
            document.getElementById('latency').innerText = data.p95_latency;
            document.getElementById('cache-hit').innerText = data.cache_hit_rate;
            
            // Update charts
            Plotly.newPlot('requests-chart', data.requests_chart_data);
            Plotly.newPlot('latency-chart', data.latency_chart_data);
            Plotly.newPlot('data-quality-chart', data.quality_chart_data);
        }
        
        // Refresh every 30 seconds
        updateMetrics();
        setInterval(updateMetrics, 30000);
    </script>
</body>
</html>
```

## Consequences

### Positive
- Visibility: quickly see health status and performance
- Debugging: metrics pinpoint root causes
- Alerts: issues detected automatically; no manual monitoring
- Industry-standard: Prometheus widely used; team likely familiar
- Low overhead: Prometheus lightweight; minimal performance impact
- Historical data: Prometheus retains 30 days of metrics

### Negative
- Additional infrastructure: Prometheus server to manage
- Configuration complexity: alert rules require tuning
- Limited long-term storage: 30 days default; need external storage for archiving
- Dashboard simple: not as fancy as Grafana (but simpler to maintain)
- Learning curve: understanding metrics and alerts takes time

### Alert Fatigue Risk
- Start conservative: only critical alerts first
- Tune thresholds: avoid alert storms
- Regular review: adjust rules based on false positives

## Alternatives Considered

### Grafana + Prometheus (Full Stack)
- Better: beautiful dashboards; advanced features
- Worse: more complex setup; not needed for internal tool
- Decision: Start simple; upgrade to Grafana if dashboards become critical

### Cloud Monitoring (AWS CloudWatch, GCP Stackdriver)
- Better: managed service; no infrastructure
- Worse: vendor lock-in; potentially expensive; overkill for single instance
- Decision: Rejected for MVP; Prometheus sufficient

### No Monitoring (Manual Checks Only)
- Rejected: unacceptable for production; issues not caught quickly

### ELK Stack (Elasticsearch, Logstash, Kibana)
- Better: powerful log analysis and visualization
- Worse: heavyweight; complex setup; overkill for application logs
- Decision: Prometheus sufficient for metrics; simple log files for debugging

### Datadog, New Relic, etc.
- Rejected: SaaS cost unjustified for internal 10-user tool

## Related Decisions
- ADR-0006: Deployment (monitoring confirms deployment health)
- ADR-0002: Data Architecture (pipeline health metrics)
