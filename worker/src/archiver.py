"""
数据归档模块
- CSV 导出
- R2/S3 上传
- 本地数据清理
"""
import asyncio
import gzip
import csv
import io
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class Archiver:
    """数据归档器"""
    
    def __init__(self, db_pool, redis):
        self.db_pool = db_pool
        self.redis = redis
        self.config = None
    
    async def load_config(self):
        """加载归档配置"""
        try:
            import json
            config_str = await self.redis.get("config:archive")
            if config_str:
                self.config = json.loads(config_str)
            else:
                self.config = {
                    "enabled": False,
                    "retention_days": 3,
                    "r2_endpoint": "",
                    "r2_bucket": "",
                    "r2_access_key": "",
                    "r2_secret_key": ""
                }
        except Exception as e:
            logger.error(f"Failed to load archive config: {e}")
            self.config = {"enabled": False}
    
    async def archive_day(self, target_date: datetime.date) -> dict:
        """
        归档指定日期的数据
        1. 查询数据
        2. 导出为 CSV.GZ
        3. 上传到 R2
        4. 删除本地数据
        5. 记录归档日志
        """
        result = {
            "date": str(target_date),
            "status": "pending",
            "row_count": 0,
            "file_size": 0
        }
        
        try:
            await self.load_config()
            
            if not self.config.get("enabled"):
                result["status"] = "skipped"
                result["message"] = "Archive disabled"
                return result
            
            # Step 1: 查询数据
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT time, sn, v_raw, ppm, temp, humi, bat, rssi, seq
                    FROM sensor_data
                    WHERE time::date = $1
                    ORDER BY time
                """, target_date)
            
            if not rows:
                result["status"] = "empty"
                result["message"] = f"No data for {target_date}"
                return result
            
            result["row_count"] = len(rows)
            
            # Step 2: 生成 CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["time", "sn", "v_raw", "ppm", "temp", "humi", "bat", "rssi", "seq"])
            
            for row in rows:
                writer.writerow([
                    row['time'].isoformat(),
                    row['sn'],
                    row['v_raw'],
                    row['ppm'],
                    row['temp'],
                    row['humi'],
                    row['bat'],
                    row['rssi'],
                    row['seq']
                ])
            
            # 压缩
            csv_content = csv_buffer.getvalue().encode('utf-8')
            gzipped = gzip.compress(csv_content)
            result["file_size"] = len(gzipped)
            
            # Step 3: 上传到 R2
            file_name = f"sensor_data_{target_date.strftime('%Y%m%d')}.csv.gz"
            r2_path = f"archive/{target_date.year}/{target_date.month:02d}/{file_name}"
            
            if self.config.get("r2_endpoint"):
                upload_success = await self._upload_to_r2(gzipped, r2_path)
                if not upload_success:
                    result["status"] = "upload_failed"
                    return result
            else:
                # 没有配置 R2，保存到本地
                local_path = f"/tmp/mcs_archive/{r2_path}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(gzipped)
                r2_path = local_path
            
            # Step 4: 删除本地数据
            async with self.db_pool.acquire() as conn:
                deleted = await conn.execute("""
                    DELETE FROM sensor_data
                    WHERE time::date = $1
                """, target_date)
                logger.info(f"Deleted {deleted} rows for {target_date}")
            
            # Step 5: 记录归档日志
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO archive_logs (archive_date, file_name, file_size, row_count, r2_path, status)
                    VALUES ($1, $2, $3, $4, $5, 'uploaded')
                """, target_date, file_name, result["file_size"], result["row_count"], r2_path)
            
            result["status"] = "success"
            result["r2_path"] = r2_path
            logger.info(f"Archive completed for {target_date}: {result['row_count']} rows, {result['file_size']} bytes")
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"Archive failed for {target_date}: {e}")
        
        return result
    
    async def _upload_to_r2(self, data: bytes, path: str) -> bool:
        """上传到 Cloudflare R2 (S3 兼容)"""
        try:
            import boto3
            from botocore.config import Config
            
            s3 = boto3.client(
                's3',
                endpoint_url=self.config['r2_endpoint'],
                aws_access_key_id=self.config['r2_access_key'],
                aws_secret_access_key=self.config['r2_secret_key'],
                config=Config(signature_version='s3v4')
            )
            
            s3.put_object(
                Bucket=self.config['r2_bucket'],
                Key=path,
                Body=data,
                ContentType='application/gzip'
            )
            
            return True
        except ImportError:
            logger.warning("boto3 not installed, skipping R2 upload")
            return False
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return False


async def run_archive():
    """运行归档任务 (由 scheduler 调用)"""
    import redis.asyncio as aioredis
    import asyncpg
    
    # 连接数据库和 Redis
    redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379"
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    
    db_dsn = f"postgres://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASS','password')}@{os.getenv('DB_HOST','timescaledb')}:5432/{os.getenv('DB_NAME','mcs_iot')}"
    db_pool = await asyncpg.create_pool(db_dsn)
    
    try:
        archiver = Archiver(db_pool, redis)
        await archiver.load_config()
        
        retention_days = archiver.config.get("retention_days", 3)
        target_date = (datetime.now() - timedelta(days=retention_days)).date()
        
        result = await archiver.archive_day(target_date)
        logger.info(f"Archive result: {result}")
        
    finally:
        await redis.close()
        await db_pool.close()


if __name__ == "__main__":
    # 手动运行测试
    asyncio.run(run_archive())
