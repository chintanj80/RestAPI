# FastAPI Service - Performance Improvement

## key strategies to improve FastAPI microservice performance:

## Async Programming

Use async/await patterns throughout your application. FastAPI is built on async foundations, so leverage this fully:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # Use async database calls
    result = await database.fetch_one(query)
    return result
```

## Database Optimization

- **Connection pooling**: Use async database drivers like `asyncpg` for PostgreSQL or `aiomysql` for MySQL
- **Query optimization**: Add proper indexes, avoid N+1 queries, use database-specific optimizations
- **Connection limits**: Configure appropriate pool sizes based on your database capacity

## Caching Strategies

- **In-memory caching**: Use Redis for frequently accessed data
- **Response caching**: Cache API responses for read-heavy endpoints
- **Database query caching**: Cache expensive database queries
- **HTTP caching headers**: Set appropriate cache headers for client-side caching

## Request/Response Optimization

- **Pydantic model optimization**: Use `model_validate` instead of parsing from dict when possible
- **Response models**: Use specific response models instead of returning full objects
- **Streaming responses**: For large payloads, use `StreamingResponse`
- **Compression**: Enable gzip compression in your reverse proxy

## Concurrency and Scalability

- **Worker processes**: Run multiple Uvicorn workers with Gunicorn
- **Load balancing**: Use nginx or similar for load distribution
- **Background tasks**: Use FastAPI's background tasks for non-blocking operations
- **Task queues**: Implement Celery or similar for heavy processing

## Resource Management

- **Memory profiling**: Monitor memory usage and optimize data structures
- **Connection limits**: Set appropriate limits for external API calls
- **Timeouts**: Implement proper timeouts for all external dependencies
- **Circuit breakers**: Add circuit breakers for external service calls

## Deployment Optimizations

- **Docker optimization**: Use multi-stage builds and minimal base images
- **Container resources**: Set appropriate CPU and memory limits
- **Health checks**: Implement proper health check endpoints
- **Graceful shutdowns**: Handle shutdown signals properly

## Monitoring and Profiling

- **APM tools**: Use tools like New Relic, DataDog, or Prometheus
- **Logging**: Implement structured logging with appropriate levels
- **Metrics**: Track key performance indicators (response time, throughput, error rates)
- **Profiling**: Use tools like `py-spy` or `cProfile` to identify bottlenecks

The most impactful improvements typically come from proper async implementation, database optimization, and strategic caching. Start with profiling your current application to identify the biggest bottlenecks before implementing optimizations.

## Python Dictionary Cache

Simple in-memory cache using a dictionary:

```python
from fastapi import FastAPI
import time
from typing import Optional

app = FastAPI()
cache = {}
CACHE_TTL = 300  # 5 minutes

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    cache_key = f"user_{user_id}"
    
    # Check cache first
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
    
    # Fetch from database if not cached or expired
    user_data = await fetch_user_from_db(user_id)
    
    # Store in cache
    cache[cache_key] = (user_data, time.time())
    return user_data
```

## LRU Cache with functools

For simple function caching:

```python
from functools import lru_cache
from fastapi import FastAPI

app = FastAPI()

@lru_cache(maxsize=100)
def get_expensive_calculation(param: str) -> dict:
    # Expensive operation here
    result = perform_heavy_computation(param)
    return result

@app.get("/calculate/{param}")
async def calculate(param: str):
    return get_expensive_calculation(param)
```

## Custom Cache Class

More sophisticated caching with TTL and size limits:

```python
import time
from typing import Any, Optional
from collections import OrderedDict

class MemoryCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        value, expiry = self.cache[key]
        if time.time() > expiry:
            del self.cache[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
        self.cache.move_to_end(key)
        
        # Remove oldest items if cache is full
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

# Usage
cache = MemoryCache(max_size=500, default_ttl=600)

@app.get("/products/{product_id}")
async def get_product(product_id: int):
    cache_key = f"product_{product_id}"
    
    # Try cache first
    cached_product = cache.get(cache_key)
    if cached_product:
        return cached_product
    
    # Fetch from database
    product = await fetch_product_from_db(product_id)
    
    # Cache the result
    cache.set(cache_key, product, ttl=300)
    return product
```

## Redis for Distributed Caching

For production applications, Redis is often better:

```python
import redis
import json
from fastapi import FastAPI

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    cache_key = f"item_{item_id}"
    
    # Try Redis cache
    cached_item = redis_client.get(cache_key)
    if cached_item:
        return json.loads(cached_item)
    
    # Fetch from database
    item = await fetch_item_from_db(item_id)
    
    # Cache in Redis with 10-minute expiry
    redis_client.setex(cache_key, 600, json.dumps(item))
    return item
```

## Cache Decorator

Create a reusable caching decorator:

```python
import asyncio
from functools import wraps
from typing import Callable, Any

def cache_response(ttl: int = 300):
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return result
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Store in cache
            cache[cache_key] = (result, time.time())
            return result
        
        return wrapper
    return decorator

# Usage
@app.get("/reports/{report_id}")
@cache_response(ttl=600)  # Cache for 10 minutes
async def get_report(report_id: int):
    return await generate_expensive_report(report_id)
```

## Best Practices

**Cache Invalidation**: Implement cache clearing when data changes:

```python
@app.put("/users/{user_id}")
async def update_user(user_id: int, user_data: dict):
    # Update database
    await update_user_in_db(user_id, user_data)
    
    # Invalidate cache
    cache_key = f"user_{user_id}"
    if cache_key in cache:
        del cache[cache_key]
    
    return {"status": "updated"}
```

**Memory Management**: Monitor cache size and implement cleanup:

```python
import psutil

def cleanup_cache_if_needed():
    memory_usage = psutil.virtual_memory().percent
    if memory_usage > 80:  # If memory usage > 80%
        cache.clear()  # Clear cache to free memory
```

**Cache Warming**: Pre-populate frequently accessed data:

```python
@app.on_event("startup")
async def warm_cache():
    popular_items = await get_popular_items()
    for item in popular_items:
        cache[f"item_{item.id}"] = (item, time.time())
```

In-memory caching can significantly improve API response times, especially for data that doesn't change frequently. Choose the approach based on your application's complexity and scalability requirements.


