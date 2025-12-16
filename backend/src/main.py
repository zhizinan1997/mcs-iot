from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
import asyncpg
import os
import logging

from .auth import router as auth_router
from .devices import router as devices_router
from .alarms import router as alarms_router
from .config import router as config_router
from .dashboard import router as dashboard_router

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connections
redis_pool = None
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool, db_pool
    
    # Startup
    logger.info("Starting Backend API...")
    
    # Redis
    redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379"
    redis_pool = await aioredis.from_url(redis_url, decode_responses=True)
    logger.info("Connected to Redis")
    
    # Database
    db_dsn = f"postgres://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASS','password')}@{os.getenv('DB_HOST','timescaledb')}:5432/{os.getenv('DB_NAME','mcs_iot')}"
    db_pool = await asyncpg.create_pool(db_dsn, min_size=5, max_size=20)
    logger.info("Connected to Database")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await redis_pool.close()
    await db_pool.close()

app = FastAPI(
    title="MCS-IoT Admin API",
    description="Management API for MCS-IoT Gas Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get Redis
async def get_redis():
    return redis_pool

# Dependency to get DB
async def get_db():
    return db_pool

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(devices_router, prefix="/api/devices", tags=["Devices"])
app.include_router(alarms_router, prefix="/api/alarms", tags=["Alarms"])
app.include_router(config_router, prefix="/api/config", tags=["Config"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "database": "up" if db_pool else "down",
            "redis": "up" if redis_pool else "down"
        }
    }
