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

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db = Depends(get_db), redis = Depends(get_redis)):
    async with db.acquire() as conn:
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM devices d
            LEFT JOIN instruments i ON d.instrument_id = i.id
            WHERE i.id IS NULL OR i.is_displayed = TRUE
        """)
        online_count = await conn.fetchval("""
            SELECT COUNT(*) FROM devices d
            LEFT JOIN instruments i ON d.instrument_id = i.id
            WHERE d.status = 'online' AND (i.id IS NULL OR i.is_displayed = TRUE)
        """)
        alarms_today = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
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
        alarms_today=alarms_today or 0
    )

@router.get("/realtime", response_model=List[DeviceRealtime])
async def get_realtime_data(db = Depends(get_db), redis = Depends(get_redis)):
    devices = []
    
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT d.sn, d.name,
                   i.name as instrument_name, i.color as instrument_color
            FROM devices d
            LEFT JOIN instruments i ON d.instrument_id = i.id
            WHERE i.id IS NULL OR i.is_displayed = TRUE
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
            instrument_name=row['instrument_name'],
            instrument_color=row['instrument_color']
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
                rows = await conn.fetch("SELECT sn, name FROM devices")
            
            for row in rows:
                sn = row['sn']
                rt_data = await redis.hgetall(f"realtime:{sn}")
                is_online = await redis.exists(f"online:{sn}")
                
                devices.append({
                    "sn": sn,
                    "name": row['name'],
                    "ppm": float(rt_data.get('ppm')) if rt_data.get('ppm') else None,
                    "temp": float(rt_data.get('temp')) if rt_data.get('temp') else None,
                    "status": "online" if is_online else "offline"
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
