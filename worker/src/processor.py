"""
MCS-IOT 消息处理器 (Message Processor)

该文件负责解析来自 MQTT 的原始报文，并驱动业务逻辑。
主要功能包括：
1. 路由解析：根据 MQTT Topic (如 mcs/{sn}/up) 区分数据上报及状态上报。
2. 状态维护：收到任何上报时，更新设备在 Redis 中的在线标记及 TTL。
3. 数据加工：整合校准算法 (Calibrator)，将原始电压值转为 ppm 浓度值。
4. 资源同步：将加工后的数据同步持久化到数据库 (Storage) 并缓存实时数据供大屏使用 (Redis Hash)。
5. 报警触发：完成数据处理后，调起报警中心 (AlarmCenter) 进行阈值判定。

结构：
- Processor: 核心类，持有了校准、存储、缓存及报警的引用。
- process_message: 入口函数，处理 JSON 解析及路由分发。
- handle_uplink: 核心逻辑函数，处理传感器上报数据的完整流水线。
"""
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
        # Key: "online:{sn}" -> TTL 90s (设备每10秒上报一次，90秒无数据判定离线)
        await self.redis.setex(f"online:{sn}", 90, "1")
        
        # 2. Calculate Concentration
        v_raw = float(data.get('v_raw', 0))
        temp = float(data.get('temp', 25))
        bat = int(data.get('bat', 100))
        
        ppm = await self.calib.calculate(sn, v_raw, temp)
        
        # 3. Store to DB
        await self.storage.save_sensor_data(sn, data, ppm)
        
        # 4. Cache Realtime Data for Dashboard
        # Key: "realtime:{sn}" -> Hash
        rt_data = {
            "ppm": str(ppm),
            "temp": str(temp),
            "humi": str(data.get('humi', 0)),
            "bat": str(bat),
            "rssi": str(data.get('rssi', 0)),
            "net": str(data.get('net', '')),
            "ts": str(int(data.get('ts', 0)))
        }
        await self.redis.hset(f"realtime:{sn}", mapping=rt_data)
        
        # 5. Check Alarm (包含浓度、低电量、弱信号)
        if self.alarm:
            rssi = int(data.get('rssi', 0)) if data.get('rssi') else None
            network = data.get('net', '')
            await self.alarm.check_and_alert(sn, ppm, temp, bat, rssi=rssi, network=network)
        
        logger.info(f"[{sn}] v={v_raw:.1f}, ppm={ppm:.2f}, bat={bat}% (Saved)")

    async def handle_status(self, sn, data):
        # Handle LWT or Status messages if any
        pass
