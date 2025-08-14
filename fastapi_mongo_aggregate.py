import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional

import uvloop  # High-performance event loop
from fastapi import FastAPI, HTTPException, status, Query, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from bson import ObjectId, json_util
import json

# Set uvloop as the default event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MongoDB Configuration
class MongoConfig:
    def __init__(self):
        self.MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "your_database")
        
        # Connection Pool Settings
        self.MAX_POOL_SIZE = int(os.getenv("MAX_POOL_SIZE", "100"))  # Max connections in pool
        self.MIN_POOL_SIZE = int(os.getenv("MIN_POOL_SIZE", "10"))   # Min connections maintained
        self.MAX_IDLE_TIME_MS = int(os.getenv("MAX_IDLE_TIME_MS", "30000"))  # 30 seconds
        self.CONNECT_TIMEOUT_MS = int(os.getenv("CONNECT_TIMEOUT_MS", "5000"))  # 5 seconds
        self.SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("SERVER_SELECTION_TIMEOUT_MS", "5000"))
        self.SOCKET_TIMEOUT_MS = int(os.getenv("SOCKET_TIMEOUT_MS", "10000"))  # 10 seconds
        self.HEARTBEAT_FREQUENCY_MS = int(os.getenv("HEARTBEAT_FREQUENCY_MS", "10000"))  # 10 seconds
        
        # Connection pool monitoring
        self.WAIT_QUEUE_TIMEOUT_MS = int(os.getenv("WAIT_QUEUE_TIMEOUT_MS", "5000"))
        self.WAIT_QUEUE_MULTIPLE = int(os.getenv("WAIT_QUEUE_MULTIPLE", "5"))

config = MongoConfig()

class DatabaseManager:
    """Singleton database manager with advanced connection pooling"""
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Initialize connection pool with advanced settings"""
        if self._client is None:
            try:
                # Advanced connection pool configuration
                self._client = AsyncIOMotorClient(
                    config.MONGODB_URL,
                    
                    # Connection Pool Settings
                    maxPoolSize=config.MAX_POOL_SIZE,           # Maximum connections
                    minPoolSize=config.MIN_POOL_SIZE,           # Minimum connections maintained
                    maxIdleTimeMS=config.MAX_IDLE_TIME_MS,      # Close idle connections after 30s
                    
                    # Timeout Settings
                    connectTimeoutMS=config.CONNECT_TIMEOUT_MS,           # Connection timeout
                    serverSelectionTimeoutMS=config.SERVER_SELECTION_TIMEOUT_MS,  # Server selection timeout
                    socketTimeoutMS=config.SOCKET_TIMEOUT_MS,             # Socket timeout
                    heartbeatFrequencyMS=config.HEARTBEAT_FREQUENCY_MS,   # Heartbeat frequency
                    
                    # Wait Queue Settings (for connection pool)
                    waitQueueTimeoutMS=config.WAIT_QUEUE_TIMEOUT_MS,      # Wait for connection from pool
                    waitQueueMultiple=config.WAIT_QUEUE_MULTIPLE,         # Queue size multiplier
                    
                    # Replica Set Settings (if using replica sets)
                    retryWrites=True,                           # Retry failed writes
                    retryReads=True,                           # Retry failed reads
                    
                    # Additional Performance Settings
                    compressors="snappy,zlib,zstd",            # Compression
                    zlibCompressionLevel=6,                    # Compression level
                    
                    # Connection Monitoring
                    appname="FastAPI-UserService",             # App identifier
                    
                    # Read/Write Concerns (adjust based on needs)
                    # readConcern={"level": "majority"},      # Uncomment for stronger consistency
                    # writeConcern={"w": "majority"},         # Uncomment for stronger durability
                )
                
                self._db = self._client[config.DATABASE_NAME]
                
                # Test connection and log pool info
                await self._client.admin.command('ping')
                
                # Log connection pool configuration
                logger.info(f"MongoDB connection pool initialized:")
                logger.info(f"  - Database: {config.DATABASE_NAME}")
                logger.info(f"  - Max Pool Size: {config.MAX_POOL_SIZE}")
                logger.info(f"  - Min Pool Size: {config.MIN_POOL_SIZE}")
                logger.info(f"  - Max Idle Time: {config.MAX_IDLE_TIME_MS}ms")
                logger.info(f"  - Connection Timeout: {config.CONNECT_TIMEOUT_MS}ms")
                
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB connection pool: {str(e)}")
                raise
    
    async def disconnect(self):
        """Properly close connection pool"""
        if self._client:
            # Log connection pool stats before closing
            try:
                pool_stats = await self.get_connection_pool_stats()
                logger.info(f"Closing connection pool. Final stats: {pool_stats}")
            except Exception as e:
                logger.warning(f"Could not get final pool stats: {e}")
            
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection pool closed")
    
    async def get_connection_pool_stats(self) -> Dict:
        """Get connection pool statistics"""
        try:
            if self._client:
                # Get server info and pool stats
                server_info = await self._client.admin.command('serverStatus')
                
                # Extract connection info from server status
                connections = server_info.get('connections', {})
                
                stats = {
                    "current_connections": connections.get('current', 0),
                    "available_connections": connections.get('available', 0),
                    "total_created": connections.get('totalCreated', 0),
                    "active_connections": connections.get('active', 0),
                    "pool_config": {
                        "max_pool_size": config.MAX_POOL_SIZE,
                        "min_pool_size": config.MIN_POOL_SIZE,
                        "max_idle_time_ms": config.MAX_IDLE_TIME_MS
                    }
                }
                return stats
            else:
                return {"error": "No active connection"}
        except Exception as e:
            logger.error(f"Error getting connection pool stats: {str(e)}")
            return {"error": str(e)}
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client (connection pool)"""
        if self._client is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._client
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Get a collection instance with connection reuse"""
        return self.database[collection_name]

# Global database manager instance
db_manager = DatabaseManager()

# Lifespan context manager for proper startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper connection handling"""
    # Startup
    logger.info("Starting FastAPI application with uvloop...")
    logger.info(f"Event loop: {type(asyncio.get_event_loop())}")
    
    try:
        await db_manager.connect()
        logger.info("Database connection pool initialized successfully")
        yield
    finally:
        # Shutdown
        logger.info("Shutting down FastAPI application...")
        await db_manager.disconnect()

# Initialize FastAPI with lifespan management
app = FastAPI(
    title="High-Performance User API",
    description="FastAPI with advanced MongoDB connection pooling and uvloop",
    version="2.0.0",
    lifespan=lifespan
)

# Dependency to get database connection
async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database connection from pool"""
    return db_manager.database

def serialize_mongo_document(doc):
    """Convert MongoDB document to JSON serializable format"""
    return json.loads(json_util.dumps(doc))

def build_user_aggregation_pipeline(user_id: str, include_orders: bool = True) -> List[Dict]:
    """Build optimized aggregation pipeline"""
    try:
        object_id = ObjectId(user_id)
    except:
        object_id = user_id

    pipeline = [
        {
            "$match": {
                "_id": object_id
            }
        },
        {
            "$lookup": {
                "from": "profiles",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "profile",
                "pipeline": [
                    {
                        "$project": {
                            "first_name": 1,
                            "last_name": 1,
                            "phone": 1,
                            "address": 1
                        }
                    }
                ]
            }
        }
    ]
    
    if include_orders:
        pipeline.append({
            "$lookup": {
                "from": "orders",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "orders",
                "pipeline": [
                    {"$sort": {"created_at": -1}},
                    {"$limit": 10},
                    {
                        "$project": {
                            "amount": 1,
                            "status": 1,
                            "created_at": 1,
                            "product_name": 1
                        }
                    }
                ]
            }
        })
    
    pipeline.extend([
        {
            "$addFields": {
                "profile": {"$arrayElemAt": ["$profile", 0]},
                "total_orders": {"$size": "$orders"} if include_orders else 0,
                "total_spent": {"$sum": "$orders.amount"} if include_orders else 0
            }
        },
        {
            "$project": {
                "_id": 1,
                "username": 1,
                "email": 1,
                "created_at": 1,
                "last_login": 1,
                "profile.first_name": 1,
                "profile.last_name": 1,
                "profile.phone": 1,
                "profile.address": 1,
                "total_orders": 1,
                "total_spent": 1,
                "recent_orders": {"$slice": ["$orders", 3]} if include_orders else []
            }
        }
    ])
    
    return pipeline

@app.get("/get-user/{user_id}")
async def get_user(
    user_id: str,
    include_orders: bool = Query(True, description="Include order information"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get user data using connection pool"""
    start_time = time.time()
    username = None
    doc_count = 0
    
    try:
        # Get collection from connection pool
        collection = db_manager.get_collection("users")
        
        pipeline = build_user_aggregation_pipeline(user_id, include_orders)
        
        # Execute aggregation using connection from pool
        cursor = collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        doc_count = len(result)
        
        if not result:
            logger.warning(f"User not found: {user_id}, Documents returned: {doc_count}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        user_data = result[0]
        username = user_data.get('username', 'Unknown')
        
        execution_time = time.time() - start_time
        logger.info(
            f"User retrieved - ID: {user_id}, Username: {username}, "
            f"Documents: {doc_count}, Execution time: {execution_time:.3f}s"
        )
        
        serialized_data = serialize_mongo_document(user_data)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": serialized_data,
                "metadata": {
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "connection_reused": True
                }
            }
        )
        
    except PyMongoError as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Database error for user {user_id} - Username: {username}, "
            f"Documents: {doc_count}, Error: {str(e)}, Time: {execution_time:.3f}s"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Unexpected error for user {user_id} - Username: {username}, "
            f"Documents: {doc_count}, Error: {str(e)}, Time: {execution_time:.3f}s"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/connection-stats")
async def get_connection_stats():
    """Get current connection pool statistics"""
    try:
        stats = await db_manager.get_connection_pool_stats()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "connection_pool_stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error getting connection stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting connection stats: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Enhanced health check with connection pool info"""
    try:
        # Test database connection
        await db_manager.client.admin.command('ping')
        
        # Get connection pool stats
        pool_stats = await db_manager.get_connection_pool_stats()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "database": "connected",
                "event_loop": str(type(asyncio.get_event_loop())),
                "connection_pool": pool_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Run with uvloop optimization
if __name__ == "__main__":
    import uvicorn
    
    # Run with uvloop for maximum performance
    uvicorn.run(
        "main:app",  # Replace 'main' with your filename
        host="0.0.0.0",
        port=8000,
        workers=1,  # Use 1 worker with async
        loop="uvloop",  # Use uvloop event loop
        access_log=True,
        reload=False,  # Disable in production
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )