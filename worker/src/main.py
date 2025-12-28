"""
MCS-IOT 后台工作程序总控 (Worker Main Entry)

该文件是后台 Worker 进程的启动入口，负责协调数据采集、处理、报警及定时任务。
主要功能包括：
1. 初始化 Redis 连接及持久化存储 (Storage)。
2. 实例化并配置各核心组件：校准器 (Calibrator)、报警中心 (AlarmCenter)、授权守卫 (LicenseGuard) 等。
3. 启动定时任务调度器 (Scheduler)，处理数据归档、设备在线检查等周期性逻辑。
4. 建立 MQTT 连接，并建立同步消息回调与异步逻辑处理 (Processor) 之间的桥梁。
5. 实现服务的优雅停机 (Graceful Shutdown)，确保资源在退出前正确释放。

结构：
- main: 异步主函数，按顺序执行各组件的启动与依赖注入。
- on_mqtt_message: 消息中转回调，将 MQTT 线程捕获的数据安全传递至异步事件循环处理。
- 信号处理: 监听系统信号并触发退出流程。
"""
import asyncio
import os
import signal
import sys
import logging
import redis.asyncio as aioredis
import json
from dotenv import load_dotenv

# Load Modules
from mqtt_client import MQTTClient
from storage import Storage
from calibrator import Calibrator
from processor import Processor
from alarm import AlarmCenter
from license import LicenseGuard
from scheduler import Scheduler

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Worker")

async def main():
    logger.info("MCS-IoT Worker Starting...")
    
    # 1. Initialize Redis
    redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379"
    try:
        redis = await aioredis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Redis Connection Failed: {e}")
        return

    # 2. Initialize DB Storage
    storage = Storage()
    await storage.connect()

    # 3. Initialize Calibrator
    calib = Calibrator(redis)

    # 4. Initialize Alarm Center
    alarm = AlarmCenter(redis, storage)

    # 5. Initialize License Guard
    license_guard = LicenseGuard(redis)
    if not await license_guard.startup_check():
        logger.error("License check failed! System may be locked.")
        # In production, you might want to exit here
        # For dev, we continue with DEV_MODE=true

    # 6. Initialize Scheduler (定时任务)
    scheduler = Scheduler(redis, storage.pool)
    scheduler.set_alarm_center(alarm)
    await scheduler.start()
    logger.info("Scheduler started")

    # 7. Initialize Processor
    processor = Processor(calib, storage, redis, alarm)

    # 8. Initialize MQTT
    # Since MQTT Client (Sync/Threaded) needs to call Async Processor, 
    # we need to bridge them.
    loop = asyncio.get_running_loop()

    def on_mqtt_message(client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        # Schedule the async processing in the main loop
        asyncio.run_coroutine_threadsafe(processor.process_message(topic, payload), loop)
        # Update last message time for health check
        import time
        asyncio.run_coroutine_threadsafe(
            redis.set("mqtt:last_message_time", str(time.time())), 
            loop
        )

    mqtt_client = MQTTClient(on_mqtt_message, redis_client=redis)
    mqtt_client.start()

    # Graceful Shutdown
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received...")
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    # Wait for stop signal
    await stop_event.wait()

    # Cleanup
    logger.info("Shutting down...")
    await scheduler.stop()
    mqtt_client.stop()
    await storage.close()
    await redis.close()
    logger.info("Bye.")

if __name__ == "__main__":
    load_dotenv()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
