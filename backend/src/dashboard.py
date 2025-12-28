"""
MCS-IOT 大屏与仪表盘数据模块 (Dashboard & Real-time Data)

该文件负责为监控前端提供高度聚合的系统概览数据及低延迟的实时状态流。
主要功能包括：
1. 统计全系统的设备在线状态、今日报警及确认情况。
2. 提供所有设备的最新实时监测数据（PPM、温度、电量、信号等），并关联所属仪表信息。
3. 通过 WebSocket (WS) 协议向前端实时推送数据更新，实现无刷新同步。
4. 提供设备布局坐标的管理接口，支持在大屏上拖拽保存设备位置。

结构：
- ConnectionManager: 管理 WebSocket 连接的生命周期及消息广播。
- get_dashboard_stats: 聚合统计逻辑，用于仪表盘卡片展示。
- get_realtime_data: 实时数据快照获取逻辑。
- websocket_endpoint: WS 服务端实现，每秒定时推送最新传感器状态。
- update_device_positions: 布局管理逻辑，将位置信息持久化至 Redis。
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import json

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

async def get_redis():
    from .main import redis_pool
    return redis_pool

async def get_db():
    from .main import db_pool
    return db_pool

class DashboardStats(BaseModel):
    devices_total: int
    devices_online: int
    devices_offline: int
    devices_alarm: int
    alarms_today: int
    alarms_confirmed_today: int

class DeviceRealtime(BaseModel):
    sn: str
    name: Optional[str]
    ppm: Optional[float]
    temp: Optional[float]
    status: str
    position_x: Optional[float]
    position_y: Optional[float]
    battery: Optional[int] = None
    rssi: Optional[int] = None
    network: Optional[str] = None
    instrument_name: Optional[str] = None
    instrument_color: Optional[str] = None
    instrument_id: Optional[int] = None
    unit: str = "ppm"
    sensor_type: Optional[str] = None

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db = Depends(get_db), redis = Depends(get_redis)):
    async with db.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM devices")
        online_count = await conn.fetchval(
            "SELECT COUNT(*) FROM devices WHERE status = 'online'"
        )
        alarms_today = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
        )
        alarms_confirmed_today = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE AND status = 'ack'"
        )
        # 报警中的设备数 (今日有未确认报警)
        devices_alarm = await conn.fetchval("""
            SELECT COUNT(DISTINCT sn) FROM alarm_logs 
            WHERE triggered_at >= CURRENT_DATE
        """)
    
    return DashboardStats(
        devices_total=total or 0,
        devices_online=online_count or 0,
        devices_offline=(total or 0) - (online_count or 0),
        devices_alarm=devices_alarm or 0,
        alarms_today=alarms_today or 0,
        alarms_confirmed_today=alarms_confirmed_today or 0
    )

@router.get("/realtime", response_model=List[DeviceRealtime])
async def get_realtime_data(db = Depends(get_db), redis = Depends(get_redis)):
    devices = []
    
    async with db.acquire() as conn:
        # JOIN instruments 表获取仪表名称和颜色
        rows = await conn.fetch("""
            SELECT d.sn, d.name, d.instrument_id, d.unit, d.sensor_type,
                   i.name as instrument_name, i.color as instrument_color
            FROM devices d
            LEFT JOIN instruments i ON d.instrument_id = i.id
        """)
    
    for row in rows:
        sn = row['sn']
        rt_data = await redis.hgetall(f"realtime:{sn}")
        is_online = await redis.exists(f"online:{sn}")
        pos_data = await redis.hgetall(f"position:{sn}")
        
        devices.append(DeviceRealtime(
            sn=sn,
            name=row['name'],
            ppm=float(rt_data.get('ppm')) if rt_data.get('ppm') else None,
            temp=float(rt_data.get('temp')) if rt_data.get('temp') else None,
            status="online" if is_online else "offline",
            position_x=float(pos_data.get('x')) if pos_data.get('x') else None,
            position_y=float(pos_data.get('y')) if pos_data.get('y') else None,
            battery=int(rt_data.get('bat')) if rt_data.get('bat') else None,
            rssi=int(rt_data.get('rssi')) if rt_data.get('rssi') else None,
            network=rt_data.get('net') if rt_data.get('net') else None,
            instrument_id=row['instrument_id'],
            instrument_name=row['instrument_name'],
            instrument_color=row['instrument_color'],
            unit=row['unit'] or "ppm",
            sensor_type=row['sensor_type']
        ))
    
    return devices

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Get redis connection
    from .main import redis_pool
    redis = redis_pool
    
    try:
        while True:
            # Push realtime data every second
            devices = []
            
            # Get all device SNs (simplified)
            # In production, maintain a set of registered devices
            async with (await get_db()).acquire() as conn:
                rows = await conn.fetch("SELECT sn, name, unit, sensor_type, instrument_id FROM devices")
            
            for row in rows:
                sn = row['sn']
                rt_data = await redis.hgetall(f"realtime:{sn}")
                is_online = await redis.exists(f"online:{sn}")
                
                devices.append({
                    "sn": sn,
                    "name": row['name'],
                    "ppm": float(rt_data.get('ppm')) if rt_data.get('ppm') else None,
                    "temp": float(rt_data.get('temp')) if rt_data.get('temp') else None,
                    "status": "online" if is_online else "offline",
                    "unit": row['unit'],
                    "sensor_type": row['sensor_type'],
                    "instrument_id": row['instrument_id']
                })
            
            await websocket.send_json({
                "type": "realtime",
                "data": devices
            })
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/devices/positions")
async def update_device_positions(positions: Dict[str, Dict[str, float]], redis = Depends(get_redis)):
    """Update device positions for dashboard layout"""
    for sn, pos in positions.items():
        await redis.hset(f"position:{sn}", mapping={
            "x": pos.get("x", 0),
            "y": pos.get("y", 0)
        })
    return {"message": "Positions updated"}
