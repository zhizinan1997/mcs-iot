"""
MCS-IOT 定时任务调度器 (Task Scheduler)

该文件负责驱动系统中所有非触发式的后台任务，确保系统的自我维护与状态同步。
主要调度任务包括：
1. 设备离线检测 (每分钟)：扫描超时的设备并自动切换状态、发出报警。
2. 系统健康报表 (每5分钟)：汇总各组件状态并更新至 Redis 供前端实时查询。
3. 历史数据归档 (每日凌晨2点)：触发数据的云端备份与本地清理，释放存储空间。
4. 商业授权巡检 (每日凌晨3点)：定期在线核验授权合法性。
5. 数据库自动优化 (每日凌晨4点)：执行 VACUUM ANALYZE，保持数据库在高吞吐下的查询性能。

结构：
- Scheduler: 核心类，封装了基于 asyncio 的循环任务控制。
- _run_every / _run_at_time: 基础的任务循环原语，支持间隔运行及定时运行。
- Task Implementations: 各个具体业务任务的实现函数。
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Callable, Optional
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class Scheduler:
    """异步定时任务调度器"""
    
    def __init__(self, redis_client: aioredis.Redis, db_pool):
        self.redis = redis_client
        self.db_pool = db_pool
        self.tasks = []
        self.running = False
        self.alarm_center = None  # 延迟注入
    
    def set_alarm_center(self, alarm_center):
        """注入报警中心实例"""
        self.alarm_center = alarm_center
    
    async def start(self):
        """启动所有定时任务"""
        self.running = True
        logger.info("定时任务调度器已启动")
        
        # 创建定时任务
        self.tasks = [
            asyncio.create_task(self._run_every(60, self.check_device_offline, "设备离线检测")),
            asyncio.create_task(self._run_every(300, self.health_check, "健康检查")),
            asyncio.create_task(self._run_at_time(time(2, 0), self.run_archive, "数据归档")),
            asyncio.create_task(self._run_at_time(time(3, 0), self.run_license_check, "授权校验")),
            asyncio.create_task(self._run_at_time(time(4, 0), self.run_db_optimize, "数据库优化")),
        ]
    
    async def stop(self):
        """停止所有定时任务"""
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("定时任务调度器已停止")
    
    async def _run_every(self, interval_seconds: int, func: Callable, name: str):
        """按固定间隔运行任务"""
        while self.running:
            try:
                await func()
            except Exception as e:
                logger.error(f"定时任务 [{name}] 执行失败: {e}")
            await asyncio.sleep(interval_seconds)
    
    async def _run_at_time(self, target_time: time, func: Callable, name: str):
        """在每天指定时间运行任务"""
        while self.running:
            now = datetime.now()
            target = datetime.combine(now.date(), target_time)
            
            # 如果今天的目标时间已过，则等到明天
            if now.time() >= target_time:
                target = datetime.combine(now.date(), target_time)
                target = target.replace(day=target.day + 1)
            
            wait_seconds = (target - now).total_seconds()
            logger.debug(f"任务 [{name}] 将在 {wait_seconds:.0f} 秒后执行")
            
            await asyncio.sleep(wait_seconds)
            
            if self.running:
                try:
                    logger.info(f"开始执行定时任务: {name}")
                    await func()
                    logger.info(f"定时任务 [{name}] 执行完成")
                except Exception as e:
                    logger.error(f"定时任务 [{name}] 执行失败: {e}")
    
    # ==================== 任务实现 ====================
    
    async def check_device_offline(self):
        """
        检测设备离线状态
        - 扫描所有设备
        - 检查 Redis 中的 online:{sn} 键
        - 如果键不存在且设备之前在线，则标记为离线并触发报警
        """
        async with self.db_pool.acquire() as conn:
            # 获取所有设备
            devices = await conn.fetch(
                "SELECT sn, status FROM devices"
            )
            
            offline_count = 0
            online_count = 0
            
            for device in devices:
                sn = device['sn']
                current_status = device['status']
                
                # 检查 Redis 中的在线标记
                is_online = await self.redis.exists(f"online:{sn}")
                
                if is_online:
                    online_count += 1
                    if current_status != 'online':
                        # 设备上线，更新状态
                        await conn.execute(
                            "UPDATE devices SET status = 'online' WHERE sn = $1",
                            sn
                        )
                else:
                    offline_count += 1
                    if current_status == 'online':
                        # 设备离线，更新状态并触发报警
                        await conn.execute(
                            "UPDATE devices SET status = 'offline' WHERE sn = $1",
                            sn
                        )
                        
                        # 触发离线报警
                        if self.alarm_center:
                            await self.alarm_center.process_alarm(
                                sn=sn,
                                alarm_type="OFFLINE",
                                value=0,
                                threshold=0,
                                message=f"设备 {sn} 已离线"
                            )
                        
                        logger.warning(f"设备 {sn} 已离线")
            
            # 更新 Redis 中的统计信息
            await self.redis.hset("stats:devices", mapping={
                "online": online_count,
                "offline": offline_count,
                "total": len(devices)
            })
    
    async def health_check(self):
        """
        系统健康检查
        - 检查数据库连接
        - 检查 Redis 连接
        - 检查 MQTT 连接 (通过检查最近消息时间)
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 检查数据库
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health["components"]["database"] = {"status": "up"}
        except Exception as e:
            health["components"]["database"] = {"status": "down", "error": str(e)}
            health["status"] = "unhealthy"
        
        # 检查 Redis
        try:
            await self.redis.ping()
            health["components"]["redis"] = {"status": "up"}
        except Exception as e:
            health["components"]["redis"] = {"status": "down", "error": str(e)}
            health["status"] = "unhealthy"
        
        # 检查 MQTT (通过最后消息时间)
        last_msg_time = await self.redis.get("mqtt:last_message_time")
        if last_msg_time:
            last_time = float(last_msg_time)
            age = datetime.now().timestamp() - last_time
            if age < 120:  # 2分钟内有消息
                health["components"]["mqtt"] = {"status": "up", "last_message_age_sec": int(age)}
            else:
                health["components"]["mqtt"] = {"status": "warning", "last_message_age_sec": int(age)}
        else:
            health["components"]["mqtt"] = {"status": "unknown"}
        
        # 存储健康状态到 Redis
        import json
        await self.redis.set("system:health", json.dumps(health), ex=600)
        
        if health["status"] != "healthy":
            logger.warning(f"系统健康检查异常: {health}")
    
    async def run_archive(self):
        """执行数据归档任务"""
        try:
            from archiver import run_archive
            await run_archive()
        except ImportError:
            logger.warning("归档模块未加载")
        except Exception as e:
            logger.error(f"数据归档失败: {e}")
    
    async def run_license_check(self):
        """执行授权校验"""
        try:
            from license import LicenseGuard
            guard = LicenseGuard(self.redis)
            await guard.verify()
        except Exception as e:
            logger.error(f"授权校验失败: {e}")
    
    async def run_db_optimize(self):
        """执行数据库优化"""
        try:
            async with self.db_pool.acquire() as conn:
                # VACUUM ANALYZE 主要表
                await conn.execute("VACUUM ANALYZE sensor_data")
                await conn.execute("VACUUM ANALYZE alarm_logs")
                await conn.execute("VACUUM ANALYZE devices")
                logger.info("数据库优化完成")
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
