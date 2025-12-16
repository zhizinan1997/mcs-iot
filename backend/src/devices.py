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

class DeviceResponse(DeviceBase):
    status: str = "offline"
    last_seen: Optional[datetime] = None
    last_ppm: Optional[float] = None

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
    
    # Get devices from DB
    async with db.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM devices")
        rows = await conn.fetch(
            "SELECT sn, name, model, high_limit, low_limit, k_val, b_val, t_coef, status, last_seen FROM devices ORDER BY sn LIMIT $1 OFFSET $2",
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
            k_val=row['k_val'] or 1.0,
            b_val=row['b_val'] or 0.0,
            t_coef=row['t_coef'] or 0.0,
            status="online" if is_online else "offline",
            last_seen=row['last_seen'],
            last_ppm=float(rt_data.get('ppm')) if rt_data.get('ppm') else None
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
        k_val=row['k_val'] or 1.0,
        b_val=row['b_val'] or 0.0,
        t_coef=row['t_coef'] or 0.0,
        status="online" if is_online else "offline",
        last_seen=row['last_seen'],
        last_ppm=float(rt_data.get('ppm')) if rt_data.get('ppm') else None
    )

@router.post("")
async def create_device(device: DeviceBase, db = Depends(get_db)):
    async with db.acquire() as conn:
        try:
            await conn.execute(
                """INSERT INTO devices (sn, name, model, high_limit, low_limit, k_val, b_val, t_coef) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                device.sn, device.name, device.model, device.high_limit, device.low_limit,
                device.k_val, device.b_val, device.t_coef
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Device created", "sn": device.sn}

@router.put("/{sn}")
async def update_device(sn: str, device: DeviceBase, db = Depends(get_db), redis = Depends(get_redis)):
    async with db.acquire() as conn:
        result = await conn.execute(
            """UPDATE devices SET name=$2, model=$3, high_limit=$4, low_limit=$5, 
               k_val=$6, b_val=$7, t_coef=$8 WHERE sn=$1""",
            sn, device.name, device.model, device.high_limit, device.low_limit,
            device.k_val, device.b_val, device.t_coef
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
    start: datetime = Query(None),
    end: datetime = Query(None),
    interval: str = Query("1m"),
    db = Depends(get_db)
):
    # Default to last 1 hour
    if not end:
        end = datetime.now()
    if not start:
        start = end - timedelta(hours=1)
    
    async with db.acquire() as conn:
        rows = await conn.fetch(
            """SELECT time_bucket($1::interval, time) AS bucket, 
                      AVG(ppm) as ppm, AVG(temp) as temp
               FROM sensor_data 
               WHERE sn = $2 AND time BETWEEN $3 AND $4
               GROUP BY bucket ORDER BY bucket""",
            interval, sn, start, end
        )
    
    return {
        "sn": sn,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "interval": interval,
        "points": [{"ts": r['bucket'].isoformat(), "ppm": r['ppm'], "temp": r['temp']} for r in rows]
    }

from datetime import timedelta
