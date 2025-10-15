# Caddy Setup and User Guide

Caddy is a modern, open-source web server written in Go. It's particularly popular for reverse proxying because of its **automatic HTTPS** capabilities and simple configuration syntax. Unlike traditional servers like Nginx or Apache, Caddy automatically obtains and renews SSL/TLS certificates from Let's Encrypt without any configuration.

## Key Features

- **Automatic HTTPS**: Certificates are obtained, installed, and renewed automatically
- **Simple Configuration**: Human-readable Caddyfile syntax
- **HTTP/2 and HTTP/3**: Built-in support for modern protocols
- **Reverse Proxy**: Easy to configure for multiple backend services
- **Zero Downtime Reloads**: Configuration changes apply without interrupting connections
- **Security by Default**: Secure TLS settings out of the box



### Caddy reverse proxy features

> Load Balancing (multiple policies)
> 
> Active & Passive Health Checks
> 
> Header Manipulation
> 
> Retries
> 
> Buffering
> 
> Streaming
> 
> WebSocket & HTTP/2/3 Support
> 
> Response Interception

Caddy combines TLS termination + proxy + LB



### Load Balancing Policy

> random
> 
> round_robin
> 
> least_conn
> 
> first
> 
> ip_hash
> 
> cookie
> 
> uri_hash
> 
> header



### Health checks

> Active: configurable interval, path, port
> 
> Passive: failed proxied responses can reduce the weight/availability of an upstream
> 
> **Passive checks** — Caddy observes proxy traffic and marks an upstream unhealthy if requests to it fail (timeouts, 5xx, connection errors)
> 
>  health_passive_fail_duration 30s



### Basic Caddy Commands

##### Basic Command to start Caddy Server from the shell

```bash
# Start Caddy Server in Normal Mode
caddy run --config /path/to/Caddyfile --adapter caddyfile

# Start Caddy Server in Debug Mode
caddy run --config /etc/caddy/Caddyfile --watch
```

✅ What this does:

- `run` starts the Caddy server in the foreground (logs visible in terminal).

- `--config` points to your Caddyfile.

- `--adapter caddyfile` tells Caddy to interpret the file as a **Caddyfile** (not JSON).



##### Validate Caddyfile before running

```bash
caddy validate --config /path/to/Caddyfile --adapter caddyfile
```

##### RUN as a background service (systemd)

```bash
# To check status
sudo systemctl status caddy

# Start and Stop Caddy using systemctl
sudo systemctl daemon-reload
sudo systemctl stop caddy
sudo systemctl restart caddy

# View Logs
sudo journalctl -u caddy -f

# Enable Caddy on Boot
sudo systemctl enable caddy

# Graceful reload of Caddyfile without downtime
caddy reload --config /path/to/Caddyfile --adapter caddyfile

# Override with your own Caddyfile
sudo cp /path/to/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy

# Check port bindings
sudo netstat -tlnp | grep caddy
# or
sudo ss -tlnp | grep caddy
```

##### Caddy Service File for systemctl

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/caddy run --environ --config /path/to/Caddyfile --adapter caddyfile
```

### Caddyfile

reverse_proxy block - Basic

1. Simple TLS + proxy 

```css
example.com {
    reverse_proxy 127.0.0.1:8080
}
```

2. Load Balancing with least_conn + retries + headers
   
   ```
   myapp.example.com {
      reverse_proxy / 10.0.1.10:8080 10.0.1.11:8080 {
       lb_policy least_conn
       lb_retries 2
       header_up X-Forwarded-Proto {scheme}
       header_up X-Real-IP {remote}
       health_interval 15s
       health_path /healthz
     }   
   }
   ```

3. Path-based routing (three distint REST services)
   
   ```css
   hostname_a:12121 {
     # Optional: enable access logs
     log {
       output file /var/log/caddy/hostname_a-12121.access.log
       format single_field common_log
     }
   
     # Route /svc1 -> local port 51515
     handle_path /svc1/* {
       reverse_proxy 127.0.0.1:51515 {
         # optional tuning
         lb_policy round_robin
         health_interval 10s
         health_path /health
         header_up X-Forwarded-For {remote}
         header_up X-Forwarded-Proto {scheme}
       }
     }
   
     # Route /svc2 -> local port 51512
     handle_path /svc2/* {
       reverse_proxy 127.0.0.1:51512 {
         health_interval 10s
         health_path /health
         header_up X-Forwarded-For {remote}
       }
     }
   
     # Route /svc3 -> local port 51513
     handle_path /svc3/* {
       reverse_proxy 127.0.0.1:51513 {
         health_interval 10s
         health_path /health
         header_up X-Forwarded-For {remote}
       }
     }
   
     # Optional: default handler for root or unknown paths
     handle {
       respond "Service not found" 404
     }
   }
   
   ```
   
   4. Single entry + three upstreams (load-balanced replicas)

```css
hostname_a:12121 {
  log {
    output file /var/log/caddy/myapi.access.log
  }

  reverse_proxy /api/* \
        127.0.0.1:51515 \
        127.0.0.1:51512 \
        127.0.0.1:51513 {
    lb_policy round_robin
    lb_try_duration 3s     # how long to try an upstream before moving on
    lb_retries 2
    health_uri /health
    health_interval 10s
    health_passive_fail_duration 30s
    header_up X-Forwarded-For {remote}
    header_up X-Forwarded-Proto {scheme}
  }

  handle {
    respond "Not found" 404
  }
}

```

5. Complete minimal Caddyfile (path + TLS via provided certs)

```css
hostname_a:12121 {
  tls /etc/caddy/certs/fullchain.pem /etc/caddy/certs/privkey.pem

  handle_path /svc1/* {
    reverse_proxy 127.0.0.1:51515 {
      health_interval 10s
      health_path /health
    }
  }
  handle_path /svc2/* {
    reverse_proxy 127.0.0.1:51512
  }
  handle_path /svc3/* {
    reverse_proxy 127.0.0.1:51513
  }

  handle {
    respond "Not found" 404
  }
}

```

6. Sticky Sessions (affinity)

```css
reverse_proxy /api/* 127.0.0.1:51515 127.0.0.1:51512 127.0.0.1:51513 {
  lb_policy cookie lb_session {
    fallback round_robin
    max_age 86400
  }
}

```

7. Simple TLS Configuration with custom certs
   
   ```css
   yourdomain.local {
       tls /path/to/certificate.crt /path/to/private.key
       
       reverse_proxy localhost:8080
   }
   
   
   # Complete Example
   api.internal.company.com {
       tls /etc/caddy/certs/api.crt /etc/caddy/certs/api.key
       
       reverse_proxy localhost:8080
   }
   
   api2.internal.company.com {
       tls /etc/caddy/certs/api2.crt /etc/caddy/certs/api2.key
       
       reverse_proxy localhost:8081
   }
   
   
   ## Method 2: With CA Certificate Chain
   
   If you need to include the full certificate chain (common with internal CAs):
   ```
   yourdomain.local {
       tls /path/to/fullchain.crt /path/to/private.key
       
       reverse_proxy localhost:8080
   }
   ```

8. Multiple upstream endpoints for a single client endpoint with custom certs
   
   ```css
   /* High Availability */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       reverse_proxy localhost:8080 localhost:8081 {
           lb_policy least_conn
           
           # Health checks - crucial for HA
           health_uri /health
           health_interval 10s
           health_timeout 5s
           health_status 200
           
           # Retry failed requests on other backend
           fail_duration 30s
           max_fails 3
           unhealthy_status 500 502 503 504
       }
   }
   
   
   /* Stateful APIs */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       reverse_proxy localhost:8080 localhost:8081 {
           lb_policy ip_hash
           
           health_uri /health
           health_interval 15s
       }
   }
   
   
   /* Cookie-Based Session Affinity */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       reverse_proxy localhost:8080 localhost:8081 {
           lb_policy cookie lb_session
           
           # Cookie settings
           lb_try_duration 5m
           lb_try_interval 250ms
           
           health_uri /health
           health_interval 10s
       }
   }
   
   
   /* Weighted Load Balancing */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       reverse_proxy {
           to localhost:8080
           to localhost:8081
           
           lb_policy weighted_round_robin
           lb_try_duration 5s
           
           # Not directly supported in Caddyfile for weights
           # Use multiple entries for simple weighting:
           # This gives 8080 twice the traffic of 8081
       }
   }
   
   /* Alternative for 2:1 ratio */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       reverse_proxy localhost:8080 localhost:8080 localhost:8081 {
           lb_policy round_robin
           health_uri /health
       }
   }
   
   /* Complete Production Example */
   {
       email admin@company.com
       admin off
   }
   
   api.internal.company.com {
       # Custom SSL certificate
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key {
           protocols tls1.2 tls1.3
       }
       
       # Logging
       log {
           output file /var/log/caddy/api.log {
               roll_size 100mb
               roll_keep 5
           }
           format json
           level INFO
       }
       
       # CORS
       @cors_preflight method OPTIONS
       handle @cors_preflight {
           header Access-Control-Allow-Origin "https://app.internal.company.com"
           header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
           header Access-Control-Allow-Headers "Content-Type, Authorization"
           header Access-Control-Max-Age "3600"
           respond "" 204
       }
       
       header Access-Control-Allow-Origin "https://app.internal.company.com"
       
       # Load balanced reverse proxy
       reverse_proxy localhost:8080 localhost:8081 {
           # Use least connections for optimal distribution
           lb_policy least_conn
           
           # Health checks
           health_uri /health
           health_interval 10s
           health_timeout 5s
           health_status 200
           
           # Failure handling
           fail_duration 30s
           max_fails 3
           unhealthy_status 500 502 503 504
           
           # Retry configuration
           lb_try_duration 10s
           lb_try_interval 250ms
           
           # Headers to pass to backend
           header_up X-Real-IP {remote_host}
           header_up X-Forwarded-For {remote_host}
           header_up X-Forwarded-Proto {scheme}
           header_up X-Forwarded-Host {host}
           
           # Timeouts
           transport http {
               dial_timeout 10s
               response_header_timeout 20s
               read_timeout 60s
               write_timeout 60s
               keepalive 120s
           }
       }
   }
   
   
   /* Multiple Service Groups with Load Balancing */
   api.internal.company.com {
       tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
       
       # User service - 2 instances
       handle /api/users/\* {
           uri strip_prefix /api/users
           reverse_proxy localhost:8080 localhost:8081 {
               lb_policy least_conn
               health_uri /health
               health_interval 15s
           }
       }
       
       # Product service - 2 instances
       handle /api/products/\* {
           uri strip_prefix /api/products
           reverse_proxy localhost:8090 localhost:8091 {
               lb_policy round_robin
               health_uri /health
               health_interval 15s
           }
       }
       
       # Order service - 2 instances with session affinity
       handle /api/orders/\* {
           uri strip_prefix /api/orders
           reverse_proxy localhost:8100 localhost:8101 {
               lb_policy ip_hash
               health_uri /health
               health_interval 15s
           }
       }
       
       handle {
           respond "API Gateway - Service not found" 404
       }
   }
   
   
   /*  Health Check Configuration Details */
   
   /* Basic Health Check */
   reverse_proxy localhost:8080 localhost:8081 {
       health_uri /health
       health_interval 10s
       health_timeout 5s
       health_status 200
   }
   
   
   /* Advanced Health Check */
   reverse_proxy localhost:8080 localhost:8081 {
       # Multiple status codes considered healthy
       health_status 200 204
       
       # Check every 10 seconds
       health_interval 10s
       
       # Timeout after 5 seconds
       health_timeout 5s
       
       # Custom health check path
       health_uri /api/health
       
       # Optional: Send specific headers with health check
       health_headers {
           Authorization "Bearer health-check-token"
       }
       
       # Optional: Expect specific response body
       health_body "OK"
   }
   
   
   /* Passive Health Checks */
   reverse_proxy localhost:8080 localhost:8081 {
       # Mark unhealthy after 3 failures
       max_fails 3
       
       # Keep marked unhealthy for 30 seconds
       fail_duration 30s
       
       # Which status codes indicate failure
       unhealthy_status 500 502 503 504
       
       # Still do active health checks
       health_uri /health
       health_interval 10s
   }
   ```

9. Add headers to identify the client, backend:
   
   ```css
   reverse_proxy localhost:8080 localhost:8081 {
       lb_policy round_robin
       
       # Add header showing which backend responded
       header_down X-Served-By "backend-{upstream_hostport}"
       
       health_uri /health
   }
   ```

10. Authenticate against FedSSO in Caddy
    
    ```css
    api.internal.company.com {
        tls /etc/caddy/certs/api/fullchain.crt /etc/caddy/certs/api/private.key
        
        # Forward auth to your authentication service
        forward_auth localhost:9000 {
            uri /validate
            copy_headers Authorization X-Client-ID X-Client-Token
        }
        
        # Load balanced backend
        reverse_proxy localhost:8080 localhost:8081 {
            lb_policy least_conn
            health_uri /health
            health_interval 10s
        }
    }
    ```

Auth Service for validating FedSSO using FastAPI in Python

```python
"""
FastAPI Authentication Service for FedSSO
Validates client credentials and caches results for 60 minutes
"""

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
import httpx
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FEDSSO_VALIDATE_URL = "https://fedsso.example.gov/api/validate"
FEDSSO_TIMEOUT = 10.0  # seconds
CACHE_TTL_MINUTES = 60
CACHE_CLEANUP_INTERVAL = 300  # Clean expired entries every 5 minutes

# In-memory cache
# In production, consider using Redis for distributed caching
class TokenCache:
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, dict] = {}
        self.ttl_minutes = ttl_minutes
        self.lock = asyncio.Lock()
    
    def _generate_key(self, client_id: str, client_token: str) -> str:
        """Generate a secure cache key from credentials"""
        combined = f"{client_id}:{client_token}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def get(self, client_id: str, client_token: str) -> Optional[dict]:
        """Get cached validation result if not expired"""
        async with self.lock:
            cache_key = self._generate_key(client_id, client_token)
            
            if cache_key not in self.cache:
                return None
            
            cached_data = self.cache[cache_key]
            expires_at = cached_data['expires_at']
            
            # Check if expired
            if datetime.utcnow() > expires_at:
                logger.info(f"Cache expired for client: {client_id}")
                del self.cache[cache_key]
                return None
            
            logger.info(f"Cache hit for client: {client_id}")
            return cached_data
    
    async def set(self, client_id: str, client_token: str, data: dict):
        """Cache validation result with TTL"""
        async with self.lock:
            cache_key = self._generate_key(client_id, client_token)
            expires_at = datetime.utcnow() + timedelta(minutes=self.ttl_minutes)
            
            self.cache[cache_key] = {
                'client_id': client_id,
                'data': data,
                'cached_at': datetime.utcnow(),
                'expires_at': expires_at
            }
            
            logger.info(f"Cached validation for client: {client_id}, expires at: {expires_at}")
    
    async def invalidate(self, client_id: str, client_token: str):
        """Manually invalidate a cache entry"""
        async with self.lock:
            cache_key = self._generate_key(client_id, client_token)
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.info(f"Invalidated cache for client: {client_id}")
    
    async def cleanup_expired(self):
        """Remove expired entries from cache"""
        async with self.lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, value in self.cache.items()
                if value['expires_at'] < now
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def get_stats(self) -> dict:
        """Get cache statistics"""
        async with self.lock:
            total_entries = len(self.cache)
            now = datetime.utcnow()
            valid_entries = sum(
                1 for value in self.cache.values()
                if value['expires_at'] > now
            )
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': total_entries - valid_entries
            }


# Initialize cache
token_cache = TokenCache(ttl_minutes=CACHE_TTL_MINUTES)


async def cleanup_task():
    """Background task to periodically clean expired cache entries"""
    while True:
        await asyncio.sleep(CACHE_CLEANUP_INTERVAL)
        try:
            await token_cache.cleanup_expired()
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - start/stop background tasks"""
    # Startup
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    logger.info("Started cache cleanup background task")
    
    yield
    
    # Shutdown
    cleanup_task_handle.cancel()
    try:
        await cleanup_task_handle
    except asyncio.CancelledError:
        pass
    logger.info("Stopped cache cleanup background task")


# Initialize FastAPI app
app = FastAPI(
    title="FedSSO Authentication Service",
    description="Validates client credentials against FedSSO with caching",
    version="1.0.0",
    lifespan=lifespan
)


async def validate_with_fedsso(client_id: str, client_token: str) -> tuple[bool, Optional[dict]]:
    """
    Validate credentials against FedSSO API
    
    Returns:
        tuple: (is_valid, response_data)
    """
    try:
        async with httpx.AsyncClient(timeout=FEDSSO_TIMEOUT) as client:
            response = await client.post(
                FEDSSO_VALIDATE_URL,
                json={
                    "client_id": client_id,
                    "client_token": client_token
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            logger.info(f"FedSSO response status: {response.status_code} for client: {client_id}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Assuming FedSSO returns something like: {"valid": true, "user_id": "...", ...}
                    is_valid = data.get('valid', False)
                    return is_valid, data if is_valid else None
                except Exception as e:
                    logger.error(f"Error parsing FedSSO response: {e}")
                    return False, None
            else:
                logger.warning(f"FedSSO returned non-200 status: {response.status_code}")
                return False, None
                
    except httpx.TimeoutException:
        logger.error(f"Timeout validating with FedSSO for client: {client_id}")
        return False, None
    except httpx.RequestError as e:
        logger.error(f"Request error validating with FedSSO: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error validating with FedSSO: {e}")
        return False, None


@app.api_route("/validate", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def validate(request: Request):
    """
    Validate authentication credentials
    
    Expected headers:
    - X-Client-ID: Client identifier
    - X-Client-Token: Client authentication token
    
    Returns:
    - 200: Valid credentials
    - 401: Invalid credentials
    - 503: Service unavailable (FedSSO error)
    """
    # Extract credentials from headers
    client_id = request.headers.get('x-client-id') or request.headers.get('X-Client-ID')
    client_token = request.headers.get('x-client-token') or request.headers.get('X-Client-Token')
    
    # Log request details
    logger.info(f"Validation request from {request.client.host} - Method: {request.method}")
    
    if not client_id or not client_token:
        logger.warning(f"Missing credentials from {request.client.host}")
        return Response(
            content="Missing X-Client-ID or X-Client-Token header",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check cache first
    cached_result = await token_cache.get(client_id, client_token)
    
    if cached_result:
        logger.info(f"Using cached validation for client: {client_id}")
        return Response(status_code=status.HTTP_200_OK)
    
    # Not in cache, validate with FedSSO
    logger.info(f"Validating with FedSSO for client: {client_id}")
    is_valid, fedsso_data = await validate_with_fedsso(client_id, client_token)
    
    if is_valid:
        # Cache the successful validation
        await token_cache.set(client_id, client_token, fedsso_data)
        logger.info(f"Successful authentication for client: {client_id}")
        return Response(status_code=status.HTTP_200_OK)
    elif fedsso_data is None:
        # FedSSO service error (timeout, connection error, etc.)
        logger.error(f"FedSSO service unavailable for client: {client_id}")
        return Response(
            content="Authentication service unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    else:
        # Invalid credentials
        logger.warning(f"Invalid credentials for client: {client_id}")
        return Response(
            content="Invalid credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


@app.post("/invalidate")
async def invalidate_cache(request: Request):
    """
    Manually invalidate cache for specific credentials
    Useful for forced re-authentication
    
    Request body:
    {
        "client_id": "...",
        "client_token": "..."
    }
    """
    try:
        data = await request.json()
        client_id = data.get('client_id')
        client_token = data.get('client_token')
        
        if not client_id or not client_token:
            return JSONResponse(
                content={"error": "Missing client_id or client_token"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        await token_cache.invalidate(client_id, client_token)
        
        return JSONResponse(
            content={"message": f"Cache invalidated for client: {client_id}"},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "fedsso-auth-service",
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status.HTTP_200_OK
    )


@app.get("/stats")
async def get_stats():
    """Get cache statistics"""
    cache_stats = await token_cache.get_stats()
    
    return JSONResponse(
        content={
            "service": "fedsso-auth-service",
            "cache": {
                "ttl_minutes": CACHE_TTL_MINUTES,
                **cache_stats
            },
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status.HTTP_200_OK
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        content={
            "service": "FedSSO Authentication Service",
            "version": "1.0.0",
            "endpoints": {
                "/validate": "Validate client credentials (all HTTP methods)",
                "/invalidate": "Manually invalidate cache (POST)",
                "/health": "Health check",
                "/stats": "Cache statistics"
            }
        },
        status_code=status.HTTP_200_OK
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        log_level="info",
        access_log=True
    )
```

Requirements.txt for the service

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
python-multipart==0.0.6
```

Important settings to Configure the Service

```
FEDSSO_VALIDATE_URL = "https://your-actual-fedsso-endpoint.gov/api/validate"
You can also adjust these settings:

FEDSSO_TIMEOUT: Timeout for FedSSO API calls (default: 10 seconds)
CACHE_TTL_MINUTES: Cache duration (default: 60 minutes)
CACHE_CLEANUP_INTERVAL: How often to clean expired cache entries (default: 5 minutes)

# Sample
FEDSSO_VALIDATE_URL=https://fedsso.example.gov/api/validate
FEDSSO_TIMEOUT=10.0
CACHE_TTL_MINUTES=60
LOG_LEVEL=INFO
```

Manage auth service using Systemd in Linux

```
# Copy service file
sudo cp fedsso-auth.service /etc/systemd/system/

# Set proper ownership
sudo chown www-data:www-data /opt/fedsso-auth
sudo chown -R www-data:www-data /opt/fedsso-auth/venv

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable fedsso-auth
sudo systemctl start fedsso-auth

# Check status
sudo systemctl status fedsso-auth
```

Simpler version of the FedSSO authentication API

```
"""
Simple FastAPI Authentication Service for FedSSO
Development version - validates client credentials against FedSSO
"""

from fastapi import FastAPI, Request, Response, status
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FEDSSO_VALIDATE_URL = "https://fedsso.example.gov/api/validate"
FEDSSO_TIMEOUT = 10.0

# Initialize FastAPI app
app = FastAPI(title="FedSSO Auth Service")


async def validate_with_fedsso(client_id: str, client_token: str) -> bool:
    """Validate credentials against FedSSO API"""
    try:
        async with httpx.AsyncClient(timeout=FEDSSO_TIMEOUT) as client:
            response = await client.post(
                FEDSSO_VALIDATE_URL,
                json={
                    "client_id": client_id,
                    "client_token": client_token
                },
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"FedSSO response: {response.status_code} for client: {client_id}")
            
            if response.status_code == 200:
                data = response.json()
                return data.get('valid', False)
            
            return False
                
    except Exception as e:
        logger.error(f"Error validating with FedSSO: {e}")
        return False


@app.api_route("/validate", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def validate(request: Request):
    """
    Validate authentication credentials
    
    Expected headers:
    - X-Client-ID: Client identifier
    - X-Client-Token: Client authentication token
    """
    # Extract credentials from headers
    client_id = request.headers.get('x-client-id')
    client_token = request.headers.get('x-client-token')
    
    if not client_id or not client_token:
        logger.warning("Missing credentials")
        return Response(
            content="Missing credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Validate with FedSSO
    is_valid = await validate_with_fedsso(client_id, client_token)
    
    if is_valid:
        logger.info(f"Valid credentials for client: {client_id}")
        return Response(status_code=status.HTTP_200_OK)
    else:
        logger.warning(f"Invalid credentials for client: {client_id}")
        return Response(
            content="Invalid credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
```


