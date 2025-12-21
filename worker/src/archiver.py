"""
数据归档模块 v2.0
- 本地保留 N 天数据
- 每天 0 点备份 N 天前的数据到 R2
- 验证上传成功后删除本地旧数据
- R2 过期文件自动清理
- 存储空间监控
"""
import asyncio
import gzip
import csv
import io
import os
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class Archiver:
    """数据归档器"""
    
    def __init__(self, db_pool, redis):
        self.db_pool = db_pool
        self.redis = redis
        self.config = None
        self._s3_client = None
    
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
                    "local_retention_days": 3,
                    "r2_retention_days": 30,
                    "r2_account_id": "",
                    "r2_bucket": "",
                    "r2_access_key": "",
                    "r2_secret_key": ""
                }
        except Exception as e:
            logger.error(f"Failed to load archive config: {e}")
            self.config = {"enabled": False}
    
    def _get_s3_client(self):
        """获取 S3 客户端 (缓存)"""
        if self._s3_client:
            return self._s3_client
        
        try:
            import boto3
            from botocore.config import Config as BotoConfig
            # 根据 account_id 构建 endpoint URL
            account_id = self.config.get('r2_account_id', '').strip()
            if not account_id:
                logger.warning("R2 account_id not configured")
                return None
            
            endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
            
            self._s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=self.config['r2_access_key'],
                aws_secret_access_key=self.config['r2_secret_key'],
                config=BotoConfig(
                    signature_version='s3v4',
                    retries={'max_attempts': 3, 'mode': 'standard'}
                ),
                region_name='auto'  # Required for Cloudflare R2
            )
            return self._s3_client
        except ImportError:
            logger.warning("boto3 not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to create S3 client: {e}")
            return None
    
    async def run_daily_archive(self) -> Dict[str, Any]:
        """
        每日归档任务 (在 00:00 执行)
        1. 备份 local_retention_days 天前的数据到 R2
        2. 删除数据库中超过 local_retention_days 天的数据
        3. 清理 R2 中超过 r2_retention_days 天的备份
        """
        await self.load_config()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "archive_result": None,
            "cleanup_result": None,
            "r2_cleanup_result": None
        }
        
        if not self.config.get("enabled"):
            result["status"] = "disabled"
            result["message"] = "归档功能未启用"
            return result
        
        local_retention = self.config.get("local_retention_days", 3)
        r2_retention = self.config.get("r2_retention_days", 30)
        
        # Step 1: 备份 local_retention 天前的数据
        target_date = (datetime.now() - timedelta(days=local_retention)).date()
        archive_result = await self.archive_day(target_date)
        result["archive_result"] = archive_result
        
        # Step 2: 如果备份成功，删除所有超过 local_retention 天的数据
        if archive_result.get("status") in ["success", "empty"]:
            cleanup_result = await self.cleanup_old_data(local_retention)
            result["cleanup_result"] = cleanup_result
        else:
            result["cleanup_result"] = {"status": "skipped", "message": "备份未成功，跳过清理"}
        
        # Step 3: 清理 R2 中过期的备份
        if self.config.get("r2_account_id"):
            r2_cleanup = await self.cleanup_r2_old_backups(r2_retention)
            result["r2_cleanup_result"] = r2_cleanup
        
        result["status"] = "completed"
        logger.info(f"Daily archive completed: {result}")
        return result
    
    async def archive_day(self, target_date: date) -> Dict[str, Any]:
        """
        归档指定日期的数据到 R2
        1. 查询数据
        2. 导出为 CSV.GZ
        3. 上传到 R2
        4. 验证上传
        5. 记录归档日志
        """
        result = {
            "date": str(target_date),
            "status": "pending",
            "row_count": 0,
            "file_size": 0
        }
        
        try:
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
                logger.info(f"No data to archive for {target_date}")
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
            
            if self.config.get("r2_account_id"):
                upload_success = await self._upload_to_r2(gzipped, r2_path)
                if not upload_success:
                    result["status"] = "upload_failed"
                    result["message"] = "上传 R2 失败"
                    return result
                
                # Step 4: 验证上传
                verify_success = await self._verify_r2_upload(r2_path, len(gzipped))
                if not verify_success:
                    result["status"] = "verify_failed"
                    result["message"] = "R2 上传验证失败"
                    return result
            else:
                # 没有配置 R2，保存到本地
                local_path = f"/tmp/mcs_archive/{r2_path}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(gzipped)
                r2_path = local_path
            
            # Step 5: 记录归档日志
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO archive_logs (archive_date, file_name, file_size, row_count, r2_path, status)
                    VALUES ($1, $2, $3, $4, $5, 'uploaded')
                    ON CONFLICT (archive_date) DO UPDATE SET 
                        file_name = EXCLUDED.file_name,
                        file_size = EXCLUDED.file_size,
                        row_count = EXCLUDED.row_count,
                        r2_path = EXCLUDED.r2_path,
                        status = EXCLUDED.status
                """, target_date, file_name, result["file_size"], result["row_count"], r2_path)
            
            result["status"] = "success"
            result["r2_path"] = r2_path
            logger.info(f"Archive completed for {target_date}: {result['row_count']} rows, {result['file_size']} bytes")
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"Archive failed for {target_date}: {e}")
        
        return result
    
    async def cleanup_old_data(self, retention_days: int) -> Dict[str, Any]:
        """删除数据库中超过保留期限的传感器数据"""
        result = {"status": "pending", "deleted_rows": 0}
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).date()
            
            async with self.db_pool.acquire() as conn:
                # 先统计要删除的行数
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM sensor_data
                    WHERE time::date < $1
                """, cutoff_date)
                
                if count == 0:
                    result["status"] = "empty"
                    result["message"] = "没有需要删除的旧数据"
                    return result
                
                # 删除旧数据
                deleted = await conn.execute("""
                    DELETE FROM sensor_data
                    WHERE time::date < $1
                """, cutoff_date)
                
                result["deleted_rows"] = count
                result["cutoff_date"] = str(cutoff_date)
                result["status"] = "success"
                logger.info(f"Cleaned up {count} rows older than {cutoff_date}")
                
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"Cleanup failed: {e}")
        
        return result
    
    async def cleanup_r2_old_backups(self, retention_days: int) -> Dict[str, Any]:
        """清理 R2 中超过保留期限的备份文件"""
        result = {"status": "pending", "deleted_files": 0, "deleted_files_list": []}
        
        try:
            s3 = self._get_s3_client()
            if not s3:
                result["status"] = "skipped"
                result["message"] = "S3 客户端不可用"
                return result
            
            bucket = self.config['r2_bucket']
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 列出所有归档文件
            paginator = s3.get_paginator('list_objects_v2')
            deleted_count = 0
            deleted_files = []
            
            for page in paginator.paginate(Bucket=bucket, Prefix='archive/'):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    last_modified = obj['LastModified']
                    
                    # 检查文件是否过期
                    if last_modified.replace(tzinfo=None) < cutoff_date:
                        s3.delete_object(Bucket=bucket, Key=key)
                        deleted_count += 1
                        deleted_files.append(key)
                        logger.info(f"Deleted old backup: {key}")
            
            result["deleted_files"] = deleted_count
            result["deleted_files_list"] = deleted_files[:10]  # 只返回前10个
            result["status"] = "success"
            logger.info(f"R2 cleanup completed: deleted {deleted_count} files")
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"R2 cleanup failed: {e}")
        
        return result
    
    async def _upload_to_r2(self, data: bytes, path: str) -> bool:
        """上传到 Cloudflare R2 (S3 兼容)"""
        try:
            s3 = self._get_s3_client()
            if not s3:
                return False
            
            s3.put_object(
                Bucket=self.config['r2_bucket'],
                Key=path,
                Body=data,
                ContentType='application/gzip'
            )
            
            logger.info(f"Uploaded to R2: {path}")
            return True
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return False
    
    async def _verify_r2_upload(self, path: str, expected_size: int) -> bool:
        """验证 R2 上传是否成功"""
        try:
            s3 = self._get_s3_client()
            if not s3:
                return False
            
            response = s3.head_object(
                Bucket=self.config['r2_bucket'],
                Key=path
            )
            
            actual_size = response.get('ContentLength', 0)
            if actual_size == expected_size:
                logger.info(f"R2 upload verified: {path} ({actual_size} bytes)")
                return True
            else:
                logger.warning(f"R2 size mismatch: expected {expected_size}, got {actual_size}")
                return False
        except Exception as e:
            logger.error(f"R2 verification failed: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储空间统计"""
        stats = {
            "local_db": {"size_bytes": 0, "size_human": "0 B", "row_count": 0},
            "r2": {"size_bytes": 0, "size_human": "0 B", "file_count": 0}
        }
        
        # 获取本地数据库大小
        try:
            async with self.db_pool.acquire() as conn:
                # sensor_data 表大小
                size_result = await conn.fetchrow("""
                    SELECT pg_total_relation_size('sensor_data') as size,
                           (SELECT COUNT(*) FROM sensor_data) as count
                """)
                if size_result:
                    stats["local_db"]["size_bytes"] = size_result['size'] or 0
                    stats["local_db"]["size_human"] = self._format_size(size_result['size'] or 0)
                    stats["local_db"]["row_count"] = size_result['count'] or 0
        except Exception as e:
            logger.error(f"Failed to get local DB stats: {e}")
            stats["local_db"]["error"] = str(e)
        
        # 获取 R2 存储大小
        await self.load_config()
        if self.config.get("r2_account_id"):
            try:
                s3 = self._get_s3_client()
                if s3:
                    bucket = self.config['r2_bucket']
                    total_size = 0
                    file_count = 0
                    
                    paginator = s3.get_paginator('list_objects_v2')
                    for page in paginator.paginate(Bucket=bucket, Prefix='archive/'):
                        for obj in page.get('Contents', []):
                            total_size += obj.get('Size', 0)
                            file_count += 1
                    
                    stats["r2"]["size_bytes"] = total_size
                    stats["r2"]["size_human"] = self._format_size(total_size)
                    stats["r2"]["file_count"] = file_count
            except Exception as e:
                logger.error(f"Failed to get R2 stats: {e}")
                stats["r2"]["error"] = str(e)
        else:
            stats["r2"]["message"] = "R2 未配置"
        
        return stats
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


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
        result = await archiver.run_daily_archive()
        logger.info(f"Archive result: {result}")
        return result
    finally:
        await redis.close()
        await db_pool.close()


if __name__ == "__main__":
    # 手动运行测试
    asyncio.run(run_archive())
