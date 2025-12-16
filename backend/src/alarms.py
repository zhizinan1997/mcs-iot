from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()

class AlarmLog(BaseModel):
    id: int
    time: datetime
    sn: str
    type: str
    value: float
    threshold: float
    status: str
    notified: bool

class AlarmList(BaseModel):
    total: int
    data: List[AlarmLog]

async def get_db():
    from .main import db_pool
    return db_pool

@router.get("", response_model=AlarmList)
async def list_alarms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sn: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db = Depends(get_db)
):
    offset = (page - 1) * size
    
    # Build query
    where_clauses = []
    params = []
    param_idx = 1
    
    if sn:
        where_clauses.append(f"sn = ${param_idx}")
        params.append(sn)
        param_idx += 1
    if type:
        where_clauses.append(f"type = ${param_idx}")
        params.append(type)
        param_idx += 1
    if status:
        where_clauses.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    async with db.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM alarm_logs WHERE {where_sql}", *params)
        
        params.extend([size, offset])
        rows = await conn.fetch(
            f"""SELECT id, time, sn, type, value, threshold, status, notified 
                FROM alarm_logs WHERE {where_sql} 
                ORDER BY time DESC LIMIT ${param_idx} OFFSET ${param_idx+1}""",
            *params
        )
    
    return AlarmList(
        total=total,
        data=[AlarmLog(**dict(r)) for r in rows]
    )

@router.get("/{alarm_id}", response_model=AlarmLog)
async def get_alarm(alarm_id: int, db = Depends(get_db)):
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM alarm_logs WHERE id = $1", alarm_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    return AlarmLog(**dict(row))

@router.post("/{alarm_id}/ack")
async def acknowledge_alarm(alarm_id: int, db = Depends(get_db)):
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE alarm_logs SET status = 'ack' WHERE id = $1",
            alarm_id
        )
    return {"message": "Alarm acknowledged", "id": alarm_id}

@router.get("/stats/summary")
async def get_alarm_stats(db = Depends(get_db)):
    async with db.acquire() as conn:
        today_count = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE time >= CURRENT_DATE"
        )
        week_count = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE time >= CURRENT_DATE - INTERVAL '7 days'"
        )
        by_type = await conn.fetch(
            "SELECT type, COUNT(*) as count FROM alarm_logs WHERE time >= CURRENT_DATE GROUP BY type"
        )
    
    return {
        "today": today_count,
        "week": week_count,
        "by_type": {r['type']: r['count'] for r in by_type}
    }
