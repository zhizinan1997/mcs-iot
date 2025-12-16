import logging
import redis.asyncio as aioredis
import json
import os

logger = logging.getLogger(__name__)

class Calibrator:
    def __init__(self, redis_pool):
        self.redis = redis_pool
        self.default_params = {
            "k": 1.0,
            "b": 0.0,
            "t_coef": 0.0 # No temp compensation by default
        }

    async def get_params(self, sn):
        # 1. Try Redis Cache
        # Key: "calib:{sn}" -> Hash: {k, b, t_coef}
        cache_key = f"calib:{sn}"
        try:
            params = await self.redis.hgetall(cache_key)
            if params:
                return {
                    "k": float(params.get("k", 1.0)),
                    "b": float(params.get("b", 0.0)),
                    "t_coef": float(params.get("t_coef", 0.0))
                }
        except Exception as e:
            logger.error(f"Redis Error in Calibrator: {e}")
        
        # 2. Redis Miss -> Return default (In prod, fetch from DB here or let periodic sync handle it)
        # For simplicity in this phase, we use defaults if not cached.
        # Ideally, there should be a background task syncing DB->Redis
        return self.default_params

    async def calculate(self, sn, v_raw, temp):
        params = await self.get_params(sn)
        k = params["k"]
        b = params["b"]
        t_coef = params["t_coef"]
        
        # Formula: Conc = k * v_raw + b + t_coef * (temp - 25)
        # 25 is the reference temperature
        t_comp = t_coef * (temp - 25.0)
        
        ppm = (k * v_raw) + b + t_comp
        
        # Boundary checks
        if ppm < 0:
            ppm = 0.0
        
        # Optional: Cap max value to avoid insane glitches
        if ppm > 50000:
            logger.warning(f"Abnormal High PPM for {sn}: {ppm}")
        
        return round(ppm, 2)
