# Monitoring & Observability

This document describes the monitoring and observability features implemented in the Short Story Pipeline application.

## Overview

The application includes comprehensive monitoring and observability features:

1. **Prometheus Metrics** - Metrics collection for HTTP requests, LLM API calls, story generation, and pipeline stages
2. **Sentry Error Tracking** - Automatic error tracking and performance monitoring
3. **StatsD Support** - Optional StatsD metrics forwarding
4. **Performance Monitoring** - Request/response timing and active request tracking
5. **LLM API Usage Tracking** - Detailed tracking of LLM API calls, tokens, and errors

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Sentry Error Tracking
SENTRY_DSN=your-sentry-dsn-here
SENTRY_ENVIRONMENT=production  # or staging, development
SENTRY_RELEASE=1.0.0  # Optional: release version
SENTRY_TRACES_SAMPLE_RATE=0.1  # 0.0 to 1.0 (0.1 = 10% sampled in production)

# Prometheus Metrics
ENABLE_PROMETHEUS=true  # Enable Prometheus metrics (default: true)

# StatsD Metrics (optional)
ENABLE_STATSD=false  # Enable StatsD forwarding (default: false)
STATSD_HOST=localhost
STATSD_PORT=8125
STATSD_PREFIX=shortstory
```

### Sentry Setup

1. Create a Sentry account at https://sentry.io/
2. Create a new project (select Flask)
3. Copy the DSN from the project settings
4. Add `SENTRY_DSN` to your `.env` file

Sentry will automatically:
- Capture exceptions and errors
- Track performance for Flask routes
- Provide error context and stack traces
- Send alerts for critical errors

### Prometheus Setup

Prometheus metrics are automatically enabled by default. The metrics endpoint is available at:

```
GET /metrics
```

This endpoint returns Prometheus-formatted metrics that can be scraped by a Prometheus server.

#### Key Metrics

**HTTP Request Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, and status
- `http_request_duration_seconds` - HTTP request duration histogram
- `active_requests` - Current number of active HTTP requests

**LLM API Metrics:**
- `llm_api_calls_total` - Total LLM API calls by provider, model, operation, and status
- `llm_api_duration_seconds` - LLM API call duration histogram
- `llm_api_tokens_total` - Total tokens used (input and output)
- `llm_api_errors_total` - Total LLM API errors by error type

**Story Generation Metrics:**
- `story_generation_total` - Total story generations by genre and status
- `story_generation_duration_seconds` - Story generation duration histogram
- `story_word_count` - Generated story word count histogram
- `active_story_generations` - Current number of active story generations

**Pipeline Stage Metrics:**
- `pipeline_stage_duration_seconds` - Pipeline stage execution duration by stage and status

**Background Job Metrics:**
- `background_jobs_total` - Total background jobs by type and status
- `background_job_duration_seconds` - Background job duration histogram

### StatsD Setup (Optional)

StatsD is an optional metrics forwarding service. To enable:

1. Install and run a StatsD server (or use a hosted service like Datadog)
2. Set `ENABLE_STATSD=true` in your `.env` file
3. Configure `STATSD_HOST` and `STATSD_PORT`

StatsD metrics use the same naming convention as Prometheus metrics but are forwarded to your StatsD server in real-time.

## Usage

### Monitoring Module

The monitoring functionality is implemented in `src/shortstory/utils/monitoring.py`. Key functions:

```python
from src.shortstory.utils.monitoring import (
    track_http_request,
    track_llm_api_call,
    track_story_generation,
    track_pipeline_stage,
    track_background_job,
    init_monitoring
)
```

### Automatic Tracking

Most monitoring happens automatically:

- **HTTP Requests**: Automatically tracked via Flask middleware
- **LLM API Calls**: Automatically tracked in the Gemini provider
- **Story Generation**: Automatically tracked in the `/api/generate` route
- **Errors**: Automatically captured by Sentry

### Manual Tracking

You can manually track custom metrics:

```python
from src.shortstory.utils.monitoring import track_pipeline_stage
import time

start_time = time.time()
# ... your code ...
duration = time.time() - start_time
track_pipeline_stage('custom_stage', duration, status='success')
```

## Prometheus Queries

Example Prometheus queries for common monitoring needs:

### Request Rate
```promql
rate(http_requests_total[5m])
```

### Error Rate
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

### Average Request Duration
```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### LLM API Call Rate
```promql
rate(llm_api_calls_total[5m])
```

### LLM Token Usage
```promql
sum(rate(llm_api_tokens_total[1h])) by (token_type)
```

### Story Generation Success Rate
```promql
sum(rate(story_generation_total{status="success"}[5m])) / sum(rate(story_generation_total[5m]))
```

### Average Story Generation Duration
```promql
rate(story_generation_duration_seconds_sum[5m]) / rate(story_generation_duration_seconds_count[5m])
```

## Grafana Dashboards

You can create Grafana dashboards using the Prometheus metrics. Recommended panels:

1. **Request Rate** - Line graph of `rate(http_requests_total[5m])`
2. **Error Rate** - Line graph of errors by status code
3. **Request Duration** - Histogram of `http_request_duration_seconds`
4. **LLM API Usage** - Bar chart of `llm_api_calls_total` by model
5. **Token Usage** - Stacked area of `llm_api_tokens_total` by token_type
6. **Story Generation** - Line graph of `story_generation_total` by genre
7. **Active Requests** - Gauge of `active_requests`

## Troubleshooting

### Metrics Not Appearing

1. Check that `ENABLE_PROMETHEUS=true` in your `.env` file
2. Verify Prometheus client is installed: `pip install prometheus-client`
3. Check application logs for monitoring initialization messages

### Sentry Not Capturing Errors

1. Verify `SENTRY_DSN` is set correctly in your `.env` file
2. Check Sentry project settings to ensure Flask integration is enabled
3. Review application logs for Sentry initialization messages
4. Test with a deliberate error to verify capture

### StatsD Not Forwarding

1. Verify `ENABLE_STATSD=true` in your `.env` file
2. Check that StatsD server is running and accessible
3. Verify `STATSD_HOST` and `STATSD_PORT` are correct
4. Check application logs for StatsD client initialization

## Best Practices

1. **Production**: Set `SENTRY_TRACES_SAMPLE_RATE=0.1` (10%) to avoid overwhelming Sentry
2. **Development**: Set `SENTRY_TRACES_SAMPLE_RATE=1.0` (100%) for full visibility
3. **Metrics Retention**: Configure Prometheus retention based on your needs
4. **Alerting**: Set up alerts in Prometheus/Grafana for:
   - High error rates
   - Slow request durations
   - LLM API failures
   - Story generation failures
5. **Cost Management**: Monitor Sentry quota usage, especially in high-traffic environments

## Architecture

The monitoring system is designed to be:

- **Non-blocking**: All metrics collection is asynchronous and doesn't block request processing
- **Optional**: All monitoring features are optional and gracefully degrade if dependencies are missing
- **Extensible**: Easy to add new metrics or tracking points
- **Production-ready**: Designed for production use with minimal performance impact

## Dependencies

Monitoring features require these optional dependencies:

- `prometheus-client>=0.19.0` - Prometheus metrics
- `sentry-sdk[flask]>=2.0.0` - Sentry error tracking
- `statsd>=4.0.0` - StatsD metrics forwarding (optional)

All dependencies are listed in `requirements.txt` and are optional - the application will work without them, but monitoring features will be disabled.
