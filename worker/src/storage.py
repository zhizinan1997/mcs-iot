"""
MCS-IOT 数据库存储接口 (Storage Infrastructure)

该文件封装了后台 Worker 与时序数据库 (TimescaleDB) 之间的底层交互逻辑。
主要功能包括：
1. 维护异步数据库连接池 (asyncpg)，并实现针对容器启动环境的重试连接机制。
2. 实现传感器海量时序数据的并发保存。
3. 动态维护设备元数据：在收到上报时自动注册新设备 (Upsert) 并实时更新其最后活跃时间。
4. 提供设备状态转场的持久化操作（如标记离线）。

结构：
- Storage: 核心持久化类。
- connect: 健壮的连接初始化逻辑。
- save_sensor_data: 传感器采集值的高效保存逻辑。
- upsert_device / set_device_offline: 设备生命周期管理相关的 SQL 封装。
"""
import asyncpg
import logging
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        self.pool = None
        self.dsn = f"postgres://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASS','password')}@{os.getenv('DB_HOST','timescaledb')}:{os.getenv('DB_PORT',5432)}/{os.getenv('DB_NAME','mcs_iot')}"

    async def connect(self):
        try:
            # Wait for DB to be potentially ready
            for i in range(5):
                try:
                    self.pool = await asyncpg.create_pool(self.dsn, min_size=5, max_size=20)
                    logger.info("Connected to TimescaleDB")
                    return
                except Exception as e:
                    logger.warning(f"DB Connect failed ({e}), retrying in 3s...")
                    time.sleep(3)
            logger.error("Could not connect to Database after retries.")
        except Exception as e:
            logger.error(f"Fatal DB Error: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def save_sensor_data(self, sn, data, ppm):
        if not self.pool:
            logger.error("DB Pool not initialized")
            return

        ts = datetime.fromtimestamp(data['ts'])
        
        # 1. 自动注册/更新设备 (upsert)
        await self.upsert_device(sn, ts)
        
        # 2. 保存传感器数据
        sql = """
            INSERT INTO sensor_data 
            (time, sn, v_raw, ppm, temp, humi, bat, rssi, err_code, seq)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, 
                    ts, sn, 
                    float(data['v_raw']), ppm, 
                    float(data['temp']), float(data['humi']),
                    int(data['bat']), int(data['rssi']), 
                    int(data.get('err', 0)), int(data['seq'])
                )
        except Exception as e:
            logger.error(f"Insert Error: {e}")

    async def upsert_device(self, sn: str, last_seen: datetime):
        """自动注册设备并更新状态为 online"""
        if not self.pool:
            return
        
        sql = """
            INSERT INTO devices (sn, name, status, last_seen)
            VALUES ($1, $2, 'online', $3)
            ON CONFLICT (sn) 
            DO UPDATE SET status = 'online', last_seen = $3
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, sn, sn, last_seen)
        except Exception as e:
            logger.error(f"Upsert device error: {e}")

    async def set_device_offline(self, sn: str):
        """将设备标记为离线"""
        if not self.pool:
            return
        
        sql = "UPDATE devices SET status = 'offline' WHERE sn = $1"
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, sn)
        except Exception as e:
            logger.error(f"Set device offline error: {e}")
