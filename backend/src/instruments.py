from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()

# Models
class InstrumentBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#409eff"
    sort_order: int = 0

    is_displayed: bool = True

class InstrumentResponse(InstrumentBase):
    id: int
    sensor_count: int = 0
    alarms_today: int = 0
    alarms_unhandled: int = 0
    is_displayed: bool = True
    pos_x: float = 50.0
    pos_y: float = 50.0
    created_at: Optional[datetime] = None

class InstrumentList(BaseModel):
    total: int
    data: List[InstrumentResponse]

# Dependency injection
async def get_db():
    from .main import db_pool
    return db_pool

@router.get("", response_model=InstrumentList)
async def list_instruments(db = Depends(get_db)):
    """获取所有仪表"""
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT i.*, 
                   COALESCE((SELECT COUNT(*) FROM devices d WHERE d.instrument_id = i.id), 0) as sensor_count,
                   COALESCE((
                       SELECT COUNT(*) 
                       FROM alarm_logs a 
                       JOIN devices d ON a.sn = d.sn 
                       WHERE d.instrument_id = i.id AND a.triggered_at >= CURRENT_DATE
                   ), 0) as alarms_today,
                   COALESCE((
                       SELECT COUNT(*) 
                       FROM alarm_logs a 
                       JOIN devices d ON a.sn = d.sn 
                       WHERE d.instrument_id = i.id AND a.status != 'ack'
                   ), 0) as alarms_unhandled
            FROM instruments i 
            ORDER BY i.sort_order, i.id
        """)
        total = len(rows)
    
    return InstrumentList(
        total=total,
        data=[
            InstrumentResponse(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                color=row['color'] or '#409eff',
                sort_order=row['sort_order'],
                is_displayed=row['is_displayed'],
                pos_x=row.get('pos_x', 50.0) or 50.0,
                pos_y=row.get('pos_y', 50.0) or 50.0,
                sensor_count=row['sensor_count'],
                alarms_today=row['alarms_today'],
                alarms_unhandled=row['alarms_unhandled'],
                created_at=row['created_at']
            )
            for row in rows
        ]
    )

@router.get("/{instrument_id}", response_model=InstrumentResponse)
async def get_instrument(instrument_id: int, db = Depends(get_db)):
    """获取单个仪表详情"""
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT i.*, 
                   COALESCE((SELECT COUNT(*) FROM devices d WHERE d.instrument_id = i.id), 0) as sensor_count,
                   COALESCE((
                       SELECT COUNT(*) 
                       FROM alarm_logs a 
                       JOIN devices d ON a.sn = d.sn 
                       WHERE d.instrument_id = i.id AND a.triggered_at >= CURRENT_DATE
                   ), 0) as alarms_today,
                   COALESCE((
                       SELECT COUNT(*) 
                       FROM alarm_logs a 
                       JOIN devices d ON a.sn = d.sn 
                       WHERE d.instrument_id = i.id AND a.status != 'ack'
                   ), 0) as alarms_unhandled
            FROM instruments i 
            WHERE i.id = $1
        """, instrument_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    return InstrumentResponse(
        id=row['id'],
        name=row['name'],
        description=row['description'],
        color=row['color'] or '#409eff',
        sort_order=row['sort_order'],
        is_displayed=row['is_displayed'],
        pos_x=row.get('pos_x', 50.0) or 50.0,
        pos_y=row.get('pos_y', 50.0) or 50.0,
        sensor_count=row['sensor_count'],
        alarms_today=row['alarms_today'],
        alarms_unhandled=row['alarms_unhandled'],
        created_at=row['created_at']
    )

@router.post("", response_model=InstrumentResponse)
async def create_instrument(instrument: InstrumentBase, db = Depends(get_db)):
    """创建仪表"""
    async with db.acquire() as conn:
        try:
            row = await conn.fetchrow("""
                INSERT INTO instruments (name, description, color, sort_order, is_displayed)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, name, description, color, sort_order, is_displayed, created_at
            """, instrument.name, instrument.description, instrument.color, instrument.sort_order, instrument.is_displayed)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return InstrumentResponse(
        id=row['id'],
        name=row['name'],
        description=row['description'],
        color=row['color'] or '#409eff',
        sort_order=row['sort_order'],
        is_displayed=row['is_displayed'],
        sensor_count=0,
        created_at=row['created_at']
    )

@router.put("/{instrument_id}", response_model=InstrumentResponse)
async def update_instrument(instrument_id: int, instrument: InstrumentBase, db = Depends(get_db)):
    """更新仪表"""
    async with db.acquire() as conn:
        result = await conn.execute("""
            UPDATE instruments SET name=$2, description=$3, color=$4, sort_order=$5, is_displayed=$6
            WHERE id=$1
        """, instrument_id, instrument.name, instrument.description, instrument.color, instrument.sort_order, instrument.is_displayed)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Instrument not found")
        
        # Get updated instrument
        row = await conn.fetchrow("""
            SELECT i.*, 
                   COALESCE((SELECT COUNT(*) FROM devices d WHERE d.instrument_id = i.id), 0) as sensor_count
            FROM instruments i 
            WHERE i.id = $1
        """, instrument_id)
    
    return InstrumentResponse(
        id=row['id'],
        name=row['name'],
        description=row['description'],
        color=row['color'] or '#409eff',
        sort_order=row['sort_order'],
        sensor_count=row['sensor_count'],
        is_displayed=row['is_displayed'],
        created_at=row['created_at']
    )

@router.delete("/{instrument_id}")
async def delete_instrument(instrument_id: int, db = Depends(get_db)):
    """删除仪表"""
    async with db.acquire() as conn:
        # First, clear instrument_id from devices
        await conn.execute("UPDATE devices SET instrument_id = NULL WHERE instrument_id = $1", instrument_id)
        # Then delete the instrument
        result = await conn.execute("DELETE FROM instruments WHERE id = $1", instrument_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Instrument not found")
    
    return {"message": "Instrument deleted", "id": instrument_id}


class PositionUpdate(BaseModel):
    pos_x: float
    pos_y: float


@router.patch("/{instrument_id}/position")
async def update_instrument_position(instrument_id: int, position: PositionUpdate, db = Depends(get_db)):
    """更新仪表在大屏上的位置"""
    async with db.acquire() as conn:
        result = await conn.execute("""
            UPDATE instruments SET pos_x=$2, pos_y=$3
            WHERE id=$1
        """, instrument_id, position.pos_x, position.pos_y)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Instrument not found")
    
    return {"message": "Position updated", "id": instrument_id, "pos_x": position.pos_x, "pos_y": position.pos_y}

from datetime import datetime, timedelta

@router.get("/{instrument_id}/history")
async def get_instrument_history(
    instrument_id: int,
    hours: int = Query(1, ge=1, le=72),
    db = Depends(get_db)
):
    """获取仪表下所有传感器的历史数据"""
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
        # 1. Get all devices for this instrument
        devices = await conn.fetch("""
            SELECT sn, name, sensor_type, unit 
            FROM devices 
            WHERE instrument_id = $1
            ORDER BY sensor_order, sn
        """, instrument_id)
        
        if not devices:
            return {"instrument_id": instrument_id, "series": []}
            
        series = []
        for dev in devices:
            # 2. Get history for each device
            rows = await conn.fetch(
                """SELECT time_bucket($1, time) AS bucket, 
                          AVG(ppm) as ppm
                   FROM sensor_data 
                   WHERE sn = $2 AND time BETWEEN $3 AND $4
                   GROUP BY bucket ORDER BY bucket""",
                interval, dev['sn'], start, end
            )
            
            # Format data points: [timestamp_ms, value]
            points = []
            for r in rows:
                if r['bucket']:
                    points.append([r['bucket'].timestamp() * 1000, round(r['ppm'], 2)])
            
            series.append({
                "sn": dev['sn'],
                "name": dev['name'],
                "sensor_type": dev['sensor_type'],
                "unit": dev['unit'],
                "data": points
            })
            
    return {
        "instrument_id": instrument_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "series": series
    }
