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
from .export import router as export_router
from .commands import router as commands_router
from .mqtt import router as mqtt_router

from .instruments import router as instruments_router
from .uploads import router as uploads_router
from .ai import router as ai_router

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
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(commands_router, prefix="/api/commands", tags=["Commands"])
app.include_router(mqtt_router, prefix="/api/config", tags=["MQTT"])

app.include_router(instruments_router, prefix="/api/instruments", tags=["Instruments"])
app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])

@app.get("/api/health")
async def health_check():
    """
    系统健康检查端点
    返回所有组件的状态和系统指标
    """
    import time
    import json
    
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {},
        "metrics": {}
    }
    
    # 检查数据库
    if db_pool:
        try:
            start = time.time()
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            latency = int((time.time() - start) * 1000)
            health["components"]["database"] = {"status": "up", "latency_ms": latency}
        except Exception as e:
            health["components"]["database"] = {"status": "down", "error": str(e)}
            health["status"] = "unhealthy"
    else:
        health["components"]["database"] = {"status": "down", "error": "No pool"}
        health["status"] = "unhealthy"
    
    # 检查 Redis
    if redis_pool:
        try:
            start = time.time()
            await redis_pool.ping()
            latency = int((time.time() - start) * 1000)
            health["components"]["redis"] = {"status": "up", "latency_ms": latency}
        except Exception as e:
            health["components"]["redis"] = {"status": "down", "error": str(e)}
            health["status"] = "unhealthy"
    else:
        health["components"]["redis"] = {"status": "down", "error": "No pool"}
        health["status"] = "unhealthy"
    
    # 获取 Worker 健康状态 (从 Redis)
    try:
        worker_health = await redis_pool.get("system:health")
        if worker_health:
            worker_data = json.loads(worker_health)
            health["components"]["worker"] = {"status": worker_data.get("status", "unknown")}
            if "components" in worker_data and "mqtt" in worker_data["components"]:
                health["components"]["mqtt"] = worker_data["components"]["mqtt"]
        else:
            health["components"]["worker"] = {"status": "unknown"}
    except:
        health["components"]["worker"] = {"status": "unknown"}
    
    # 获取授权状态
    try:
        license_status = await redis_pool.get("license:status")
        if license_status:
            health["components"]["license"] = {"status": license_status}
        else:
            health["components"]["license"] = {"status": "unknown"}
    except:
        health["components"]["license"] = {"status": "unknown"}
    
    # 获取统计指标
    try:
        stats = await redis_pool.hgetall("stats:devices")
        if stats:
            health["metrics"]["devices_online"] = int(stats.get("online", 0))
            health["metrics"]["devices_offline"] = int(stats.get("offline", 0))
            health["metrics"]["devices_total"] = int(stats.get("total", 0))
        
        # 今日报警数
        if db_pool:
            async with db_pool.acquire() as conn:
                today_alarms = await conn.fetchval(
                    "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
                )
                health["metrics"]["alarms_today"] = today_alarms or 0
    except Exception as e:
        logger.warning(f"Failed to get metrics: {e}")
    
    return health
