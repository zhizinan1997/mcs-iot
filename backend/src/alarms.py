"""
MCS-IOT 报警日志模块 (Alarm Logging)

该文件负责系统报警记录的查询、确认及统计分析。
主要功能包括：
1. 分页查询报警日志，支持按 SN、报警类型、状态进行过滤。
2. 关联查询设备及仪表信息，丰富报警记录的展示。
3. 提供报警确认 (ACK) 功能，支持单个确认及一键全部确认。
4. 统计报警概览，包括今日报警总数、近一周报警总数及各类型报警分布。

结构：
- AlarmLog / AlarmList: 报警数据的标准交换模型。
- list_alarms: 多条件分页查询逻辑。
- acknowledge Handlers: 处理报警的人工确认逻辑。
- get_alarm_stats: 统计分析逻辑。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()

class AlarmLog(BaseModel):
    id: int
    time: datetime
    sn: str
    device_name: Optional[str] = None
    instrument_name: Optional[str] = None
    instrument_color: Optional[str] = None
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
            f"""SELECT a.id, a.triggered_at as time, a.sn, d.name as device_name,
                       i.name as instrument_name, i.color as instrument_color,
                       a.type, a.value, a.threshold, a.status, a.notified 
                FROM alarm_logs a
                LEFT JOIN devices d ON a.sn = d.sn
                LEFT JOIN instruments i ON d.instrument_id = i.id
                WHERE {where_sql} 
                ORDER BY a.triggered_at DESC LIMIT ${param_idx} OFFSET ${param_idx+1}""",
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

@router.post("/ack-all")
async def acknowledge_all_alarms(db = Depends(get_db)):
    """Acknowledge all active alarms at once"""
    async with db.acquire() as conn:
        result = await conn.execute(
            "UPDATE alarm_logs SET status = 'ack' WHERE status = 'active'"
        )
        # Get count of updated rows
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE status = 'ack' AND ack_at IS NULL"
        )
    return {"message": "All alarms acknowledged", "count": count or 0}

@router.get("/stats/summary")
async def get_alarm_stats(db = Depends(get_db)):
    async with db.acquire() as conn:
        today_count = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
        )
        week_count = await conn.fetchval(
            "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE - INTERVAL '7 days'"
        )
        by_type = await conn.fetch(
            "SELECT type, COUNT(*) as count FROM alarm_logs WHERE triggered_at >= CURRENT_DATE GROUP BY type"
        )
    
    return {
        "today": today_count,
        "week": week_count,
        "by_type": {r['type']: r['count'] for r in by_type}
    }
