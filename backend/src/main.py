"""
MCS-IOT 后端主程序 (Main Entry Point)

该文件是 FastAPI 后端服务的入口点。
主要功能包括：
1. 初始化 FastAPI 应用实例。
2. 配置跨域资源共享 (CORS)。
3. 管理应用生命周期事件 (Lifespan)，包括 Redis 和 数据库 (TimescaleDB) 线程池的启动与关闭。
4. 自动执行数据库迁移和授权系统初始化。
5. 注册所有子模块的 API 路由。
6. 提供全局健康检查接口 (/api/health)。

结构：
- lifespan: 异步上下文管理器，处理服务启停逻辑。
- app: FastAPI 实例，配置路由和中间件。
- health_check: 系统监控接口，返回各组件及业务指标状态。
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
import asyncpg
import os
import logging
from . import deps

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
from .health import router as health_router
from .logs import router as logs_router
from .users import router as users_router

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _migrate_archive_config_on_startup(redis):
    """
    容器启动时自动迁移归档配置
    将旧版 r2_* 字段迁移到新版统一字段格式
    """
    import json
    import re
    
    config_str = await redis.get("config:archive")
    if not config_str:
        return  # No config to migrate
    
    config = json.loads(config_str)
    migrated = False
    
    # Step 1: 从 r2_endpoint 提取 account_id
    if config.get("r2_endpoint") and not config.get("r2_account_id"):
        endpoint = config.get("r2_endpoint", "")
        match = re.search(r'https?://([a-zA-Z0-9]+)\.r2\.cloudflarestorage\.com', endpoint)
        if match:
            config["r2_account_id"] = match.group(1)
        config.pop("r2_endpoint", None)
        migrated = True
    
    # Step 2: 从 r2_* 字段迁移到新版统一字段
    if config.get("r2_account_id") and not config.get("account_id"):
        config["provider"] = "cloudflare"
        config["account_id"] = config.get("r2_account_id", "")
        config["bucket"] = config.get("r2_bucket", "")
        config["access_key"] = config.get("r2_access_key", "")
        config["secret_key"] = config.get("r2_secret_key", "")
        config["cloud_retention_days"] = config.get("r2_retention_days", 30)
        config["region"] = ""  # Cloudflare R2 doesn't need region
        migrated = True
    
    if migrated:
        await redis.set("config:archive", json.dumps(config))
        logger.info("Archive config migrated from old r2_* format to new unified format")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Backend API...")
    
    # Redis
    redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379"
    deps.redis_pool = await aioredis.from_url(redis_url, decode_responses=True)
    logger.info("Connected to Redis")
    
    # Database
    db_dsn = f"postgres://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASS','password')}@{os.getenv('DB_HOST','timescaledb')}:5432/{os.getenv('DB_NAME','mcs_iot')}"
    deps.db_pool = await asyncpg.create_pool(db_dsn, min_size=5, max_size=20)
    logger.info("Connected to Database")
    
    # 自动执行数据库迁移 (确保 Schema 更新)
    try:
        from .migrations import run_migrations
        await run_migrations(deps.db_pool)
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
    
    # Initialize License Manager
    try:
        from .license import init_license_manager
        license_mgr = await init_license_manager(deps.redis_pool)
        logger.info(f"License initialized - Device ID: {license_mgr.get_device_id()}")
    except Exception as e:
        logger.warning(f"License initialization failed: {e}")
    
    # Auto-migrate archive config from old format to new format
    try:
        await _migrate_archive_config_on_startup(deps.redis_pool)
    except Exception as e:
        logger.warning(f"Archive config migration failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if deps.redis_pool:
        await deps.redis_pool.close()
    if deps.db_pool:
        await deps.db_pool.close()

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

# Dependencies (re-exported from deps)
from .deps import get_redis, get_db

# Backward compatibility: Allow other modules to import db_pool/redis_pool from main
# These are now managed in deps module
def __getattr__(name):
    if name == 'db_pool':
        return deps.db_pool
    if name == 'redis_pool':
        return deps.redis_pool
    raise AttributeError(f"module 'src.main' has no attribute '{name}'")

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
app.include_router(health_router, prefix="/api/health-check", tags=["HealthCheck"])
app.include_router(logs_router, prefix="/api", tags=["Logs"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])

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
    if deps.db_pool:
        try:
            start = time.time()
            async with deps.db_pool.acquire() as conn:
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
    if deps.redis_pool:
        try:
            start = time.time()
            await deps.redis_pool.ping()
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
        worker_health = await deps.redis_pool.get("system:health")
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
        license_status = await deps.redis_pool.get("license:status")
        if license_status:
            health["components"]["license"] = {"status": license_status}
        else:
            health["components"]["license"] = {"status": "unknown"}
    except:
        health["components"]["license"] = {"status": "unknown"}
    
    # 获取统计指标
    try:
        stats = await deps.redis_pool.hgetall("stats:devices")
        if stats:
            health["metrics"]["devices_online"] = int(stats.get("online", 0))
            health["metrics"]["devices_offline"] = int(stats.get("offline", 0))
            health["metrics"]["devices_total"] = int(stats.get("total", 0))
        
        # 今日报警数
        if deps.db_pool:
            async with deps.db_pool.acquire() as conn:
                today_alarms = await conn.fetchval(
                    "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
                )
                health["metrics"]["alarms_today"] = today_alarms or 0
    except Exception as e:
        logger.warning(f"Failed to get metrics: {e}")
    
    return health
