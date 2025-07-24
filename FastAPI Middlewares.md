# FastAPI Middlewares

### Request Logging Middleware

> Logs
>  every incoming HTTP request and outgoing response, helping you trace 
> errors, analyze traffic, and monitor system behavior in real time.

- **Debugging**: Understand exactly what the client sent and what the API responded with.
- **Monitoring**: Track response times, endpoints usage, and traffic patterns.
- **Security auditing**: Identify suspicious activity or unexpected usage.
- **Troubleshooting**: Quickly spot failed requests or long-running endpoints.

##### Basic Implementation Using `BaseHTTPMiddleware`

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        logger.info(f"➡️ {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        process_time = round((time.time() - start_time) * 1000, 2)
        
        # Log response status and duration
        logger.info(f"⬅️ {request.method} {request.url.path} - {response.status_code} ({process_time} ms)")
        
        return response

# Add to app
app.add_middleware(LoggingMiddleware)

@app.get("/hello")
async def hello():
    return {"message": "Hello, world!"}
```

Example Log Output

<div>
➡️ GET /hello
</p>
⬅️ GET /hello - 200 (1.43 ms)
</div>

### # **BaseHTTPMiddleware (Built-in)**

Use this when you want full control over what happens before and after every request in your FastAPI app.

`BaseHTTPMiddleware` is part of **Starlette**, the ASGI toolkit that FastAPI is built on top of.

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 🔹 Before request
        print(f"Request URL: {request.url}")
        
        # Call the next middleware or route
        response = await call_next(request)
        
        # 🔹 After response
        response.headers["X-Custom-Header"] = "MyValue"
        return response

# Add middleware to app
app.add_middleware(CustomHeaderMiddleware)

@app.get("/")
async def read_main():
    return {"message": "Hello World"}
```

### # **CORS Middleware**

> CORS
>  (Cross-Origin Resource Sharing) is a mechanism that allows your 
> frontend JavaScript app (on one domain) to securely interact with your 
> FastAPI backend (on another domain).

By default, **browsers block requests made from a frontend domain (like** `http://localhost:3000`**) to a backend domain (like** `http://localhost:8000`**)** due to security reasons (Same-Origin Policy).

This becomes a problem in almost every real-world app where:

- You build a frontend in React, Vue, or Angular
- Your API runs on a different domain, subdomain, or port
- You want them to talk to each other

##### FastAPI’s Solution: `CORSMiddleware`

FastAPI (via Starlette) provides a built-in CORS middleware that makes this **super easy to configure**.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allowed origins (can be specific URLs or wildcards)
origins = [
    "http://localhost",
    "http://localhost:3000",  # your frontend dev server
    "https://yourfrontenddomain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # allowed frontend origins
    allow_credentials=True,            # allow cookies, headers, sessions
    allow_methods=["*"],               # allow all HTTP methods
    allow_headers=["*"],               # allow all headers
)
```

CORS is one of those things that **just works** once it’s configured properly — but can cause major headaches when it’s not.

**Set it up early, test it often, and keep it tight in production.**

### # **Session Middleware (Starlette)**

> SessionMiddleware
>  allows you to store user-specific data on the server (like login state,
>  user preferences, or cart items) while tracking users via signed 
> cookies.

Even though modern APIs often use JWTs or OAuth for stateless auth, **sessions still make sense when**:

- You’re building **form-based authentication**
- You want **user sessions stored securely on the server**
- You’re working on **admin dashboards** or **legacy-style web apps**
- You want to avoid exposing sensitive data in tokens

##### Basic Setup in FastAPI

```python
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="super-secret-key",  # 🔐 used for signing the cookie
    session_cookie="myapp_session", # optional: custom cookie name
    max_age=86400                   # optional: cookie expiration in seconds (1 day)
)

@app.get("/set-session")
async def set_session(request: Request):
    request.session["username"] = "aashish"
    return {"message": "Session set"}

@app.get("/get-session")
async def get_session(request: Request):
    username = request.session.get("username", "Guest")
    return {"username": username}
```

##### Example Use Case: Login System

```python
@app.post("/login")
async def login(request: Request):
    # Assume user is authenticated
    request.session["user_id"] = "12345"
    return {"message": "Logged in"}

@app.get("/me")
async def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return {"message": "Not logged in"}
    return {"user_id": user_id}
```

If you’re building a **stateful web application** in FastAPI — and you want simple, secure user session management without extra infrastructure — **SessionMiddleware is the perfect fit**.

Fast, simple, and zero dependencies beyond FastAPI and Starlette.

### # **Cache Middleware**

> Use caching to reduce redundant processing and database queries — speeding up your FastAPI endpoints dramatically.

Imagine you have:

- A product listing endpoint that doesn’t change every second
- A public API serving weather or stock info
- A report-heavy dashboard querying huge datasets

Instead of recalculating the response every time, you **store and reuse** it — cutting latency and server load.

##### Install FastAPI Cache



```python
pip install fastapi-cache2[redis]
```

##### Basic Setup with Redis

```python
from fastapi import FastAPI
from fastapi_cache2 import FastAPICache
from fastapi_cache2.backends.redis import RedisBackend
import redis.asyncio as redis

app = FastAPI()

@app.on_event("startup")
async def startup():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")
```

##### Add Caching to Endpoints

```python
from fastapi_cache2.decorator import cache

@app.get("/products")
@cache(expire=60)  # cache for 60 seconds
async def get_products():
    # Simulate DB or computation
    await asyncio.sleep(1)
    return {"products": ["Laptop", "Phone", "Tablet"]}
```

Now repeated calls within 60 seconds return **instantly**.

##### Output Comparison

First request:

<div>
GET /products 
</p> 
⏱️ Took 1000ms
</div>

Second request:

<div>
GET /products  
</p>
⚡ Took ~1ms (from cache)
</div>

##### Advanced Options

@cache(expire=300, namespace="reports", key_builder=my_custom_key_func)

- `expire`: TTL in seconds
- `namespace`: Logical grouping of cache entries
- `key_builder`: Custom cache key function

You can even **invalidate the cache** manually if needed:

await FastAPICache.clear(namespace="reports")

In the world of APIs, **speed is user experience.**

By caching even a handful of high-traffic endpoints, you can cut latency, save compute, and scale effortlessly.

### # **Request ID Middleware**

Automatically attach a unique ID to every incoming request — and use it to trace 
logs, debug errors, and correlate services in distributed systems.

##### Step 1: Install `python-uuid` (Optional)

FastAPI doesn’t need external packages for UUIDs, but you can use `ulid-py` or `uuid` from the standard lib.

<div>
pip install ulid-py  # (optional)
</div>

##### Step 2: Custom Middleware for Request IDs

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id  # store it in request context

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id  # propagate to response
        return response
```

##### Step 3: Add to Your FastAPI App

```python
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(RequestIDMiddleware)
```

Now every request has a unique ID — either provided by the client (`X-Request-ID`) or generated server-side.

##### Step 4: Use in Logs or Debugging

```python
from fastapi import Request

@app.get("/debug")
async def debug(request: Request):
    print(f"Request ID: {request.state.request_id}")
    return {"request_id": request.state.request_id}
```

Logs now contain context like:

<div>
[INFO] [Request ID: 5a02a3fd-21a1-4ccf-a91f-d82143e3a00c] GET /debug
</div>

If you’ve ever struggled to debug “that one weird bug in production,”  
**Request ID Middleware is your secret weapon.**

It’s small, simple, and makes observability 10x better — especially in distributed or containerized environments.


