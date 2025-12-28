"""
MCS-IOT 依赖注入模块 (Dependency Injection)

该文件负责维护全局的资源连接池，并为 FastAPI 提供依赖注入函数。
主要功能：
1. 管理 Redis (aioredis) 和 PostgreSQL (asyncpg) 的连接池单例。
2. 提供 get_redis 和 get_db 函数，供 API 路由层注入使用。
"""
from typing import Optional
import redis.asyncio as aioredis
import asyncpg

# Global pools
redis_pool: Optional[aioredis.Redis] = None
db_pool: Optional[asyncpg.Pool] = None

async def get_redis() -> aioredis.Redis:
    return redis_pool

async def get_db() -> asyncpg.Pool:
    return db_pool
