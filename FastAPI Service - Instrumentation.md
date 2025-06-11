# FastAPI Service - Instrumentation

## Key Metrics to Monitor

**Default FastAPI metrics you'll get:**

- Request count by method, endpoint, and status code
- Request duration histograms
- Requests in progress
- Response size

**Custom business metrics to consider:**

- Database operation counts and latencies
- Cache hit/miss rates
- User authentication events
- Background task processing
- External API call metrics
- Queue sizes and processing times

## Usage Instructions

1. **Basic setup**: Use the first example with `prometheus-fastapi-instrumentator` for quick setup
2. **Custom metrics**: Use the manual setup for more control over what you measure
3. **Production**: Use the advanced example with proper error handling and business metrics

Here's how to set up Prometheus metrics collection and reporting for a FastAPI application:

## Installation

First, install the required dependencies:

```bash
pip install fastapi prometheus-client prometheus-fastapi-instrumentator
```

## Basic Setup with Instrumentator

The easiest approach is using `prometheus-fastapi-instrumentator`:

```python
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="My API", version="1.0.0")

# Initialize and configure the instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_unhealthy=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],  # Don't track metrics endpoint itself
    env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True,
)

# Add custom metrics
instrumentator.add(
    lambda info: info.modified_duration < 0.1,  # Track requests under 100ms
    lambda info: info.response.status_code < 400,  # Track successful requests
)

# Instrument the app and expose metrics
instrumentator.instrument(app).expose(app, endpoint="/metrics")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## Manual Metrics Setup

For more control over your metrics, you can set up Prometheus manually:

```python
import time
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import psutil

app = FastAPI()

# Define custom metrics
REQUEST_COUNT = Counter(
    'fastapi_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'fastapi_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'fastapi_active_requests',
    'Number of active requests'
)

# System metrics
CPU_USAGE = Gauge('fastapi_cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE = Gauge('fastapi_memory_usage_bytes', 'Memory usage in bytes')

# Business metrics examples
USER_REGISTRATIONS = Counter('fastapi_user_registrations_total', 'Total user registrations')
ACTIVE_USERS = Gauge('fastapi_active_users', 'Number of currently active users')

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    # Track active requests
    ACTIVE_REQUESTS.inc()
    
    # Start timer
    start_time = time.time()
    
    try:
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    finally:
        # Always decrement active requests
        ACTIVE_REQUESTS.dec()

def update_system_metrics():
    """Update system metrics"""
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.virtual_memory().used)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    update_system_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/users/register")
async def register_user():
    # Simulate user registration
    USER_REGISTRATIONS.inc()
    ACTIVE_USERS.inc()
    return {"message": "User registered"}

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    # Simulate user deletion
    ACTIVE_USERS.dec()
    return {"message": f"User {user_id} deleted"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

##### Advanced Configuration with Custom Metrics

Here's a more comprehensive example with custom business metrics and error tracking:

```python
import time
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, 
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess, REGISTRY
)
from contextlib import asynccontextmanager

# Custom metrics registry for multiprocess support
registry = CollectorRegistry()

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'version'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint'],
    registry=registry
)

# Error tracking
http_exceptions_total = Counter(
    'http_exceptions_total',
    'Total HTTP exceptions',
    ['exception_type', 'endpoint'],
    registry=registry
)

# Business metrics
database_operations_total = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table', 'status'],
    registry=registry
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],
    registry=registry
)

background_tasks_total = Counter(
    'background_tasks_total',
    'Total background tasks',
    ['task_type', 'status'],
    registry=registry
)

# Performance metrics
response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=registry
)

# Application-specific metrics
active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    registry=registry
)

class MetricsMiddleware:
    def __init__(self, app: FastAPI):
        self.app = app

    async def __call__(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        response = None
        exception_type = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except HTTPException as e:
            status_code = e.status_code
            exception_type = type(e).__name__
            http_exceptions_total.labels(
                exception_type=exception_type,
                endpoint=endpoint
            ).inc()
            raise
        except Exception as e:
            status_code = 500
            exception_type = type(e).__name__
            http_exceptions_total.labels(
                exception_type=exception_type,
                endpoint=endpoint
            ).inc()
            raise
        finally:
            # Always record duration and decrement in-progress
            duration = time.time() - start_time
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()
            
            if response is not None:
                # Record request count and response size
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    version=request.headers.get("Accept-Version", "v1")
                ).inc()
                
                if hasattr(response, 'body'):
                    response_size_bytes.observe(len(response.body))
        
        return response

# Database dependency for metrics tracking
class DatabaseMetrics:
    def __init__(self):
        pass
    
    def track_operation(self, operation: str, table: str, success: bool):
        status = "success" if success else "error"
        database_operations_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()

# Cache dependency for metrics tracking
class CacheMetrics:
    def track_operation(self, operation: str, hit: bool):
        result = "hit" if hit else "miss"
        cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()

# Application setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting up FastAPI with Prometheus metrics")
    yield
    # Shutdown
    logging.info("Shutting down FastAPI")

app = FastAPI(title="Advanced Metrics API", version="1.0.0", lifespan=lifespan)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Dependencies
db_metrics = DatabaseMetrics()
cache_metrics = CacheMetrics()

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint with multiprocess support"""
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        # Multiprocess mode
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
    else:
        # Single process mode
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    return {"message": "Hello World", "version": "1.0.0"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Simulate database operation with metrics"""
    try:
        # Simulate database query
        time.sleep(0.01)  # Simulate DB latency
        db_metrics.track_operation("select", "users", True)
        
        # Simulate cache check
        cache_hit = user_id % 2 == 0  # Simulate 50% cache hit rate
        cache_metrics.track_operation("get", cache_hit)
        
        return {"user_id": user_id, "name": f"User {user_id}", "cached": cache_hit}
    except Exception as e:
        db_metrics.track_operation("select", "users", False)
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/users")
async def create_user(user_data: Dict[str, Any]):
    """Create user with metrics tracking"""
    try:
        # Simulate user creation
        time.sleep(0.02)
        db_metrics.track_operation("insert", "users", True)
        
        # Track background task
        background_tasks_total.labels(
            task_type="user_welcome_email",
            status="queued"
        ).inc()
        
        return {"message": "User created", "user_id": 123}
    except Exception as e:
        db_metrics.track_operation("insert", "users", False)
        background_tasks_total.labels(
            task_type="user_welcome_email",
            status="failed"
        ).inc()
        raise HTTPException(status_code=500, detail="User creation failed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/metrics/custom")
async def custom_metrics():
    """Endpoint to view current metric values"""
    return {
        "active_connections": active_connections._value._value,
        "total_requests": sum([
            metric.samples[0].value for metric in http_requests_total.collect()
        ]),
        "cache_hit_rate": "See /metrics for detailed cache metrics"
    }
```

## Prometheus Configuration

Create a `prometheus.yml` configuration file to scrape your FastAPI metrics:

```yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
    scrape_timeout: 10s
    
  - job_name: 'fastapi-app-docker'
    static_configs:
      - targets: ['app:8000']  # If running in Docker
    metrics_path: '/metrics'
    scrape_interval: 5s

  # Multiple instances
  - job_name: 'fastapi-cluster'
    static_configs:
      - targets: 
        - 'app1:8000'
        - 'app2:8000'
        - 'app3:8000'
    metrics_path: '/metrics'
    scrape_interval: 10s
```

### To run:

The metrics will be available at `/metrics` endpoint in Prometheus format, ready for scraping by your Prometheus server.

```python
# Install dependencies
pip install fastapi prometheus-client prometheus-fastapi-instrumentator uvicorn

# Run your FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000

# Access metrics
curl http://localhost:8000/metrics
```


