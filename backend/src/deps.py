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
