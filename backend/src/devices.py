from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

router = APIRouter()

# Models
class DeviceBase(BaseModel):
    sn: str
    name: Optional[str] = None
    model: Optional[str] = None
    high_limit: float = 1000.0
    low_limit: Optional[float] = None
    k_val: float = 1.0
    b_val: float = 0.0
    t_coef: float = 0.0

    instrument_id: Optional[int] = None
    sensor_order: int = 0

class DeviceResponse(DeviceBase):
    status: str = "offline"
    last_seen: Optional[datetime] = None
    last_ppm: Optional[float] = None
    battery: Optional[int] = None  # 电池百分比
    rssi: Optional[int] = None     # 信号强度 (dBm)
    network: Optional[str] = None  # 网络类型 (4G, WiFi等)
    network: Optional[str] = None  # 网络类型 (4G, WiFi等)
    instrument_name: Optional[str] = None  # 仪表名称
    instrument_color: Optional[str] = None  # 仪表颜色

class DeviceList(BaseModel):
    total: int
    data: List[DeviceResponse]

class DeviceCommand(BaseModel):
    cmd: str  # debug, calib, reboot, ota
    params: Optional[dict] = None

# Dependency injection placeholders (will be set by main.py)
async def get_db():
    from .main import db_pool
    return db_pool

async def get_redis():
    from .main import redis_pool
    return redis_pool

@router.get("", response_model=DeviceList)
async def list_devices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db = Depends(get_db),
    redis = Depends(get_redis)
):
    offset = (page - 1) * size
    
    # Get devices from DB with zone and instrument info
    async with db.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM devices")
        rows = await conn.fetch(
            """SELECT d.sn, d.name, d.model, d.high_limit, d.low_limit, d.calib_k, d.calib_b, 
                      d.calib_t_comp, d.status, d.last_seen,
                      d.instrument_id, d.sensor_order, i.name as instrument_name, i.color as instrument_color
               FROM devices d 
               LEFT JOIN instruments i ON d.instrument_id = i.id
               ORDER BY COALESCE(i.sort_order, 999999), i.name NULLS LAST, d.sensor_order, d.sn 
               LIMIT $1 OFFSET $2""",
            size, offset
        )
    
    devices = []
    for row in rows:
        # Get realtime data from Redis
        rt_data = await redis.hgetall(f"realtime:{row['sn']}")
        is_online = await redis.exists(f"online:{row['sn']}")
        
        devices.append(DeviceResponse(
            sn=row['sn'],
            name=row['name'],
            model=row['model'],
            high_limit=row['high_limit'] or 1000,
            low_limit=row['low_limit'],
            k_val=row['calib_k'] or 1.0,
            b_val=row['calib_b'] or 0.0,
            t_coef=row['calib_t_comp'] or 0.0,

            instrument_id=row['instrument_id'],
            sensor_order=row['sensor_order'] or 0,
            instrument_name=row['instrument_name'],
            instrument_color=row['instrument_color'],
            status="online" if is_online else "offline",
            last_seen=row['last_seen'],
            last_ppm=float(rt_data.get('ppm')) if rt_data.get('ppm') else None,
            battery=int(rt_data.get('bat')) if rt_data.get('bat') else None,
            rssi=int(rt_data.get('rssi')) if rt_data.get('rssi') else None,
            network=rt_data.get('net') if rt_data.get('net') else None
        ))
    
    return DeviceList(total=total, data=devices)

@router.get("/{sn}", response_model=DeviceResponse)
async def get_device(sn: str, db = Depends(get_db), redis = Depends(get_redis)):
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM devices WHERE sn = $1", sn)
    
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    
    rt_data = await redis.hgetall(f"realtime:{sn}")
    is_online = await redis.exists(f"online:{sn}")
    
    return DeviceResponse(
        sn=row['sn'],
        name=row['name'],
        model=row['model'],
        high_limit=row['high_limit'] or 1000,
        low_limit=row['low_limit'],
        k_val=row['calib_k'] or 1.0,
        b_val=row['calib_b'] or 0.0,
        t_coef=row['calib_t_comp'] or 0.0,
        status="online" if is_online else "offline",
        last_seen=row['last_seen'],
        last_ppm=float(rt_data.get('ppm')) if rt_data.get('ppm') else None,
        battery=int(rt_data.get('bat')) if rt_data.get('bat') else None,
        rssi=int(rt_data.get('rssi')) if rt_data.get('rssi') else None,
        network=rt_data.get('net') if rt_data.get('net') else None
    )

@router.post("")
async def create_device(device: DeviceBase, db = Depends(get_db)):
    async with db.acquire() as conn:
        try:
            await conn.execute(
                """INSERT INTO devices (sn, name, model, high_limit, low_limit, calib_k, calib_b, calib_t_comp, instrument_id, sensor_order) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                device.sn, device.name, device.model, device.high_limit, device.low_limit,
                device.k_val, device.b_val, device.t_coef, device.instrument_id, device.sensor_order
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Device created", "sn": device.sn}

@router.put("/{sn}")
async def update_device(sn: str, device: DeviceBase, db = Depends(get_db), redis = Depends(get_redis)):
    async with db.acquire() as conn:
        result = await conn.execute(
            """UPDATE devices SET name=$2, model=$3, high_limit=$4, low_limit=$5, 
               calib_k=$6, calib_b=$7, calib_t_comp=$8, instrument_id=$9, sensor_order=$10 WHERE sn=$1""",
            sn, device.name, device.model, device.high_limit, device.low_limit,
            device.k_val, device.b_val, device.t_coef, device.instrument_id, device.sensor_order
        )
    
    # Update Redis cache for calibration params
    await redis.hset(f"calib:{sn}", mapping={
        "k": device.k_val,
        "b": device.b_val,
        "t_coef": device.t_coef
    })
    await redis.hset(f"device:{sn}", mapping={
        "name": device.name or sn,
        "high_limit": device.high_limit,
        "low_limit": device.low_limit or ""
    })
    
    return {"message": "Device updated", "sn": sn}

@router.delete("/{sn}")
async def delete_device(sn: str, db = Depends(get_db)):
    async with db.acquire() as conn:
        await conn.execute("DELETE FROM devices WHERE sn = $1", sn)
    return {"message": "Device deleted", "sn": sn}

@router.get("/{sn}/history")
async def get_device_history(
    sn: str,
    hours: int = Query(1, ge=1, le=72),  # 1-72 hours
    db = Depends(get_db)
):
    """Get device history data for charts
    
    Args:
        sn: Device serial number
        hours: Time range in hours (1, 3, 24, 72)
    """
    end = datetime.now()
    start = end - timedelta(hours=hours)
    
    # Choose interval based on time range
    if hours <= 1:
        interval = timedelta(minutes=1)
    elif hours <= 3:
        interval = timedelta(minutes=2)
    elif hours <= 24:
        interval = timedelta(minutes=10)
    else:
        interval = timedelta(minutes=30)
    
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT time_bucket($1, time) AS bucket, 
                      AVG(ppm) as ppm, AVG(temp) as temp, AVG(humi) as humi
               FROM sensor_data 
               WHERE sn = $2 AND time BETWEEN $3 AND $4
               GROUP BY bucket ORDER BY bucket""",
            interval, sn, start, end
        )
        
        # Also get alarms in this period
        alarms = await conn.fetch(
            """SELECT triggered_at, type, value 
               FROM alarm_logs 
               WHERE sn = $1 AND triggered_at BETWEEN $2 AND $3
               ORDER BY triggered_at""",
            sn, start, end
        )
    
    return {
        "sn": sn,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "hours": hours,
        "points": [
            {
                "ts": r['bucket'].isoformat(), 
                "ppm": round(r['ppm'], 2) if r['ppm'] else None, 
                "temp": round(r['temp'], 1) if r['temp'] else None,
                "humi": round(r['humi'], 1) if r['humi'] else None
            } 
            for r in rows
        ],
        "alarms": [
            {
                "ts": a['triggered_at'].isoformat(),
                "type": a['type'],
                "value": a['value']
            }
            for a in alarms
        ]
    }

from datetime import timedelta
