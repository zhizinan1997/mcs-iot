import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class Processor:
    def __init__(self, calibrator, storage, redis, alarm=None):
        self.calib = calibrator
        self.storage = storage
        self.redis = redis
        self.alarm = alarm

    async def process_message(self, topic, payload_str):
        try:
            # Parse Topic
            # mcs/{sn}/up
            parts = topic.split('/')
            if len(parts) < 3:
                return
            
            msg_type = parts[2]
            sn = parts[1]
            
            payload = json.loads(payload_str)
            
            if msg_type == 'up':
                await self.handle_uplink(sn, payload)
            elif msg_type == 'status':
                await self.handle_status(sn, payload)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {topic}: {payload_str}")
        except Exception as e:
            logger.error(f"Processing Error ({topic}): {e}")

    async def handle_uplink(self, sn, data):
        # 1. Update Last Seen in Redis
        # Key: "online:{sn}" -> TTL 60s
        await self.redis.setex(f"online:{sn}", 60, "1")
        
        # 2. Calculate Concentration
        v_raw = float(data.get('v_raw', 0))
        temp = float(data.get('temp', 25))
        
        ppm = await self.calib.calculate(sn, v_raw, temp)
        
        # 3. Store to DB
        await self.storage.save_sensor_data(sn, data, ppm)
        
        # 4. Cache Realtime Data for Dashboard
        # Key: "realtime:{sn}" -> Hash
        rt_data = {
            "ppm": ppm,
            "temp": temp,
            "humi": data.get('humi'),
            "bat": data.get('bat'),
            "rssi": data.get('rssi'),
            "ts": int(data.get('ts'))
        }
        await self.redis.hset(f"realtime:{sn}", mapping=rt_data)
        
        # 5. Check Alarm
        if self.alarm:
            await self.alarm.check_and_alert(sn, ppm, temp)
        
        logger.info(f"[{sn}] v={v_raw}, ppm={ppm} (Saved)")

    async def handle_status(self, sn, data):
        # Handle LWT or Status messages if any
        pass
