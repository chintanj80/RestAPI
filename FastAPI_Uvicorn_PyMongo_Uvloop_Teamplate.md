# FastAPI with Advanced Connection Pooling and UVLoop Setup Guide

## 1. Installation

### Required Dependencies

##### Core dependencies

```bash
pip install fastapi motor uvicorn[standard]
```

##### Performance dependencies

```bash
pip install uvloop  # High-performance event loop (Unix only)
```

##### Optional but recommended

```python
pip install python-dotenv  # Environment variables
pip install pymongo[srv]    # SRV record support for MongoDB Atlas
```

##### Key Packages List for FastAPI app

```bash
fastapi
pydantic
pydantic-settings
uvicorn
uvicorn-worker
gunicorn
uvloop
httptools
websockets
watchfiles
pyyaml
loguru
prometheus-fastapi-instrumentator
cachetools

```



## 2. Environment Variables

Create a `.env` file:



bash

```bash
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=your_database

# Connection Pool Settings
MAX_POOL_SIZE=100          # Maximum connections in pool
MIN_POOL_SIZE=10           # Minimum connections maintained
MAX_IDLE_TIME_MS=30000     # Close idle connections after 30 seconds
CONNECT_TIMEOUT_MS=5000    # Connection timeout (5 seconds)
SERVER_SELECTION_TIMEOUT_MS=5000  # Server selection timeout
SOCKET_TIMEOUT_MS=10000    # Socket timeout (10 seconds)
HEARTBEAT_FREQUENCY_MS=10000      # Heartbeat frequency

# Wait Queue Settings
WAIT_QUEUE_TIMEOUT_MS=5000 # Wait for connection from pool
WAIT_QUEUE_MULTIPLE=5      # Queue size multiplier
```

## 3. Connection Pooling Explained

### How It Works

# Single connection pool shared across all requests

```python
client = AsyncIOMotorClient(
    "mongodb://localhost:27017",
    maxPoolSize=100,    # Max 100 connections
    minPoolSize=10      # Always keep 10 connections open
)
```

Each request reuses connections from the pool

No need to create/close connections per request

### Benefits

- **Connection Reuse**: Eliminates connection setup/teardown overhead
- **Resource Management**: Controls maximum database connections
- **Automatic Cleanup**: Closes idle connections automatically
- **Improved Performance**: Reduced latency and better throughput
- **Connection Monitoring**: Built-in health monitoring

```python
import uvloop
import asyncio

# Set uvloop as default event loop policy

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Now all async operations use uvloop
```

### Method 1: Uvicorn with UVLoop

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --loop uvloop
```

#### Method 2: Production Setup

```bash
# Single worker (recommended for async apps)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop --reload

# Multiple workers (only if needed)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --reload


# Gunicorn with workers for Production
gunicorn main:app --workers 4 --worker-class uvicorn_worker.UvicornWorker 
 --bind 0.0.0.0:8000 --preload --max-requests 1000 --max-requests-jitter 100
 --timeout 30 --keep-alive 5 --worker-tmp-dir /dev/shm


```

##### Gunicorn Key Configuration Options

**Worker Configuration:**

- `-w` or `--workers`: Number of worker processes (typically 2-4 per CPU core)
- `-k uvicorn.workers.UvicornWorker`: Specifies Uvicorn as the worker class
- `--worker-connections`: Max simultaneous connections per worker (default 1000)

**Binding and Network:**

- `-b` or `--bind`: Host and port binding (e.g., `0.0.0.0:8000`)
- `--worker-tmp-dir`: Use memory-mapped files for better performance

**Process Management:**

- `--preload`: Preload application code before forking workers (saves memory)
- `--max-requests`: Restart workers after handling N requests (prevents memory leaks)
- `--max-requests-jitter`: Add randomness to max-requests to avoid simultaneous restarts
- `--timeout`: Worker timeout in seconds
- `--keep-alive`: Keep-alive connections timeout
  
  

---

## Monitoring Connection Pool

### Check Pool Statistics

```bash
curl http://localhost:8000/connection-stats
```

Response

```json
{
  "success": true,
  "connection_pool_stats": {
    "current_connections": 25,
    "available_connections": 75,
    "total_created": 100,
    "active_connections": 25,
    "pool_config": {
      "max_pool_size": 100,
      "min_pool_size": 10,
      "max_idle_time_ms": 30000
    }
  }
}
```

Health Check with Pool Info

```bash
curl http://localhost:8000/health
```

MongoDB Connection Pool Sizing

```python
# For high-traffic applications
MAX_POOL_SIZE = 200
MIN_POOL_SIZE = 20

# For low-traffic applications  
MAX_POOL_SIZE = 50
MIN_POOL_SIZE = 5

# Rule of thumb: Start with 100 max, 10 min
# Monitor and adjust based on usage patterns
```

Timeout Configuration

```python
# Aggressive timeouts for fast failure
CONNECT_TIMEOUT_MS = 2000      # 2 seconds
SOCKET_TIMEOUT_MS = 5000       # 5 seconds
SERVER_SELECTION_TIMEOUT_MS = 3000  # 3 seconds

# Conservative timeouts for reliability
CONNECT_TIMEOUT_MS = 10000     # 10 seconds
SOCKET_TIMEOUT_MS = 30000      # 30 seconds
SERVER_SELECTION_TIMEOUT_MS = 10000  # 10 seconds
```

### 1. Connection Pool Management

- Use singleton pattern for database manager
- Initialize pool once at startup
- Properly close pool at shutdown
- Monitor pool statistics regularly
- 
  
   #2. Error Handling

#### 2. Error Handling

```python
try:
    result = await collection.find_one({"_id": user_id})
except ServerSelectionTimeoutError:
    # MongoDB server unreachable
    logger.error("Database server unreachable")
    raise HTTPException(status_code=503, detail="Database unavailable")
except PyMongoError as e:
    # Other MongoDB errors
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database error")
```

#### 3. Resource Cleanup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.connect()
    try:
        yield
    finally:
        # Cleanup
        await db_manager.disconnect()
```



---



## Docker Container Based Deployment Configuration

##### Docker Configuration

```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Run with uvloop
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
```

##### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    spec:
      containers:
      - name: fastapi-app
        image: your-app:latest
        env:
        - name: MONGODB_URL
          value: "mongodb://mongo-service:27017"
        - name: MAX_POOL_SIZE
          value: "100"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi" 
            cpu: "500m"
```

---

## Monitoring and Logging

##### Key Metrics to Monitor

- Connection pool utilization
- Query execution times
- Error rates
- Memory usage
- CPU usage

##### Log Analysis

```bash
# Monitor connection pool usage
grep "connection pool" api.log

# Monitor slow queries
grep "Execution time" api.log | awk '$NF > 1.0'

# Monitor errors
grep "ERROR" api.log
```


