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
        asyncio.run_coroutine_threadsafe(
            redis.set("mqtt:last_message_time", str(asyncio.get_event_loop().time())), 
            loop
        )

    mqtt_client = MQTTClient(on_mqtt_message)
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
