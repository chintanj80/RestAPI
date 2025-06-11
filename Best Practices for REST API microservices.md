# Project Structure

## Key Components:

**🔐 Security Features:**

- JWT authentication with scoped permissions
- SSL/TLS enforcement with modern ciphers
- Security headers (HSTS, XSS protection, etc.)
- Rate limiting and DDoS protection
- Input validation and sanitization

**📊 Detailed Loguru Logging:**

- JSON structured logging for easy parsing
- Request/response logging with unique IDs
- Log rotation and compression
- Separate error logs
- Service-specific log contexts

**🚀 High Availability:**

- Multiple service instances across nodes
- Load balancing with Nginx/Kubernetes
- Health checks and auto-healing
- Horizontal Pod Autoscaling
- Circuit breaker patterns

**🐳 Orchestration:**

- Docker containerization
- Kubernetes deployments with HPA
- Docker Compose for development
- Service discovery and networking



### Key Benefits:

1. **Observability**: Every request is logged with context
2. **Security**: Multiple layers of protection
3. **Maintainability**: Shared code reduces duplication
4. **Performance**: Efficient middleware stack
5. **Compliance**: Security headers meet modern standards

This foundation ensures all services have consistent logging, security, and request handling patterns.



## Project Structure

### 1. Project Structure and Shared Components

The project follows a well-organized microservices architecture pattern:

microservices-project/
├── services/           # Individual microservices
├── shared/services            # Common code shared across services
├── orchestration/     # Deployment configurations
├── nginx/            # Load balancer configuration
├── monitoring/       # Observability tools
└── scripts/          # Automation scripts

This structure provides:

- **Separation of Concerns**: Each service is independent
- **Code Reusability**: Shared components avoid duplication
- **Easy Maintenance**: Clear organization for different aspects
- **Scalability**: Easy to add new services

microservices-project/
├── services/
│   ├── user-service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── routes.py
│   │   │   ├── auth.py
│   │   │   └── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── product-service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── routes.py
│   │   │   ├── auth.py
│   │   │   └── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── shared/
│       ├── __init__.py
│       ├── logging_config.py
│       ├── security.py
│       └── middleware.py
├── orchestration/
│   ├── docker-compose.yml
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── user-service-deployment.yaml
│   │   ├── product-service-deployment.yaml
│   │   ├── ingress.yaml
│   │   └── configmap.yaml
├── nginx/
│   ├── nginx.conf
│   └── ssl/
├── monitoring/
│   ├── prometheus.yml
│   └── grafana-dashboard.json
└── scripts/
    ├── generate_certs.sh
    └── deploy.sh

## FastAPI Service - Logging

**logging_config.py** - Centralized Logging System:

- **LoguruInterceptHandler**: Intercepts Python's standard logging and redirects to Loguru
- **JSON Structured Logging**: All logs are in JSON format for easy parsing by log aggregators
- **Multiple Handlers**: Console output, file logging, and error-specific logs
- **Log Rotation**: Automatic file rotation based on size (100MB) with 30-day retention
- **Compression**: Old logs are gzipped to save space
- **Service Context**: Each log entry includes service name, timestamp, and request details

```python
from loguru import logger
import sys
import json
from datetime import datetime
from typing import Dict, Any
import os

class LoguruInterceptHandler:
    """Intercept standard logging and redirect to loguru"""
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename.endswith("logging/__init__.py"):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging(service_name: str, log_level: str = "INFO"):
    """Configure loguru logging for the service"""
    
    # Remove default handler
    logger.remove()
    
    # JSON formatter for structured logging
    def json_formatter(record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service_name,
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "thread": record["thread"].name,
            "process": record["process"].name
        }
        
        # Add extra fields if present
        if record["extra"]:
            log_record.update(record["extra"])
            
        return json.dumps(log_record)
    
    # Console handler with JSON format
    logger.add(
        sys.stdout,
        format=json_formatter,
        level=log_level,
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler for persistent logs
    logger.add(
        f"/var/log/{service_name}.log",
        format=json_formatter,
        level=log_level,
        rotation="100 MB",
        retention="30 days",
        compression="gzip",
        enqueue=True
    )
    
    # Error file handler
    logger.add(
        f"/var/log/{service_name}_errors.log",
        format=json_formatter,
        level="ERROR",
        rotation="50 MB",
        retention="90 days",
        compression="gzip",
        enqueue=True
    )
    
    return logger

def get_logger():
    """Get configured logger instance"""
    return logger
```

### FastAPI Service - Security

**security.py** - Authentication & Authorization:

- **JWT Token Management**: Creates and validates JSON Web Tokens
- **Password Hashing**: Uses bcrypt for secure password storage
- **Scoped Permissions**: Role-based access control with granular permissions
- **Token Expiration**: Configurable token lifetime with automatic expiry
- **Security Dependencies**: FastAPI dependencies for protecting endpoints

```python
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import secrets
import os

security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class SecurityManager:
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current authenticated user from JWT token"""
    try:
        payload = SecurityManager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return {"user_id": user_id, "scopes": payload.get("scopes", [])}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

def require_scopes(required_scopes: list):
    """Dependency to check required scopes"""
    def scope_checker(current_user: dict = Depends(get_current_user)):
        user_scopes = current_user.get("scopes", [])
        for scope in required_scopes:
            if scope not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        return current_user
    return scope_checker
```

## FastAPI - Middleware

- **LoggingMiddleware**: Tracks every request with unique IDs, measures response times
- **SecurityHeadersMiddleware**: Adds security headers to prevent common attacks
- **CORS Configuration**: Cross-origin request handling for web applications
- **HTTPS Enforcement**: Redirects HTTP to HTTPS in production
- **Trusted Hosts**: Prevents host header injection attacks

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
import time
import uuid
from loguru import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent", ""),
                "content_length": request.headers.get("content-length", 0)
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.4f}s",
                    "response_size": response.headers.get("content-length", 0)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "process_time": f"{process_time:.4f}s"
                }
            )
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

def setup_middleware(app):
    """Configure all middleware for the application"""
    
    # HTTPS redirect (only in production)
    if os.getenv("ENVIRONMENT") == "production":
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Trusted hosts
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Custom security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    app.add_middleware(LoggingMiddleware)
```

## FastAPI Service - User Service Implementation

### services/user-service/app/config.py

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    service_name: str = "user-service"
    version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://user:password@localhost/userdb"
    
    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    
    # CORS
    cors_origins: List[str] = ["https://yourdomain.com"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### services/user-service/app/models.py

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str
```

### services/user-service/app/routes.py

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from loguru import logger
from .models import UserCreate, UserResponse, UserUpdate, Token, LoginRequest
from ..shared.security import SecurityManager, get_current_user, require_scopes
from ..shared.logging_config import get_logger

router = APIRouter(prefix="/api/v1", tags=["users"])
log = get_logger()

# Mock database - replace with actual database operations
users_db = {}
user_id_counter = 1

@router.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Authenticate user and return JWT token"""
    log.info("User login attempt", extra={"username": login_data.username})
    
    # Mock authentication - replace with actual user verification
    user = users_db.get(login_data.username)
    if not user or not SecurityManager.verify_password(login_data.password, user["password"]):
        log.warning("Failed login attempt", extra={"username": login_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token = SecurityManager.create_access_token(
        data={"sub": str(user["id"]), "scopes": user.get("scopes", ["user:read"])}
    )
    
    log.info("User logged in successfully", extra={"user_id": user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, current_user: dict = Depends(require_scopes(["user:write"]))):
    """Create a new user"""
    global user_id_counter
    
    log.info("Creating new user", extra={"email": user.email, "username": user.username})
    
    # Check if user already exists
    if user.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Hash password and create user
    hashed_password = SecurityManager.hash_password(user.password)
    new_user = {
        "id": user_id_counter,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "password": hashed_password,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "scopes": ["user:read"]
    }
    
    users_db[user.username] = new_user
    user_id_counter += 1
    
    log.info("User created successfully", extra={"user_id": new_user["id"]})
    return UserResponse(**new_user)

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    user_id = current_user["user_id"]
    log.info("Fetching user profile", extra={"user_id": user_id})
    
    # Find user by ID - replace with actual database query
    user = next((u for u in users_db.values() if u["id"] == int(user_id)), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: dict = Depends(require_scopes(["user:read"]))
):
    """List all users (admin only)"""
    log.info("Listing users", extra={"skip": skip, "limit": limit})
    
    users = list(users_db.values())[skip:skip + limit]
    return [UserResponse(**user) for user in users]

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "user-service", "timestamp": datetime.utcnow()}
```

### services/user-service/app/main.py

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from .config import settings
from .routes import router
from ..shared.logging_config import setup_logging
from ..shared.middleware import setup_middleware

# Setup logging
logger = setup_logging(settings.service_name, settings.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting user service", extra={"version": settings.version})
    yield
    logger.info("Shutting down user service")

# Create FastAPI app
app = FastAPI(
    title="User Service",
    description="Microservice for user management",
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        ssl_keyfile="/etc/ssl/private/key.pem" if os.path.exists("/etc/ssl/private/key.pem") else None,
        ssl_certfile="/etc/ssl/certs/cert.pem" if os.path.exists("/etc/ssl/certs/cert.pem") else None,
        log_config=None  # Disable uvicorn's default logging
    )
```


