"""
MCS-IOT 数据导出模块 (Data Export)

该文件负责将系统中的传感器历史数据及报警记录导出为标准格式文件（如 CSV），方便用户进行离线分析或报表制作。
主要功能包括：
1. 提供传感器数据的导出接口，支持按 SN、时间范围进行筛选，并自动处理物理量转换及格式化。
2. 提供报警日志的导出接口，支持按设备、报警类型及日期范围进行过滤。
3. 采用 StreamingResponse 流式相应，支持大规模数据导出时减少内存占用。
4. 自动生成规范的文件命名，包含导出内容的描述及时间范围。

结构：
- export_sensor_data: 传感器数据导出逻辑，包含表头定义及时序数据获取。
- export_alarms: 报警记录导出逻辑，关联设备名称并导出报警详情。
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from typing import Optional
import csv
import io
import asyncpg

router = APIRouter()

async def get_db():
    from .main import db_pool
    return db_pool


@router.get("/sensor-data")
async def export_sensor_data(
    sn: Optional[str] = Query(None, description="设备序列号，不填则导出所有"),
    start: Optional[str] = Query(None, description="开始时间 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束时间 YYYY-MM-DD"),
    format: str = Query("csv", description="导出格式: csv 或 excel"),
    db: asyncpg.Pool = Depends(get_db)
):
    """
    导出传感器历史数据
    """
    # 默认导出最近7天
    if not end:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end, "%Y-%m-%d")
    
    if not start:
        start_date = end_date - timedelta(days=7)
    else:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    
    # 构建查询
    query = """
        SELECT time, sn, v_raw, ppm, temp, humi, bat, rssi, seq
        FROM sensor_data
        WHERE time >= $1 AND time <= $2
    """
    params = [start_date, end_date]
    
    if sn:
        query += " AND sn = $3"
        params.append(sn)
    
    query += " ORDER BY time DESC LIMIT 100000"  # 限制导出行数
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    if not rows:
        raise HTTPException(status_code=404, detail="No data found for the specified criteria")
    
    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(["时间", "设备SN", "原始电压(mV)", "浓度(ppm)", "温度(℃)", "湿度(%)", "电量(%)", "信号(dBm)", "包序号"])
    
    # 写入数据
    for row in rows:
        writer.writerow([
            row['time'].strftime("%Y-%m-%d %H:%M:%S"),
            row['sn'],
            row['v_raw'],
            round(row['ppm'], 2) if row['ppm'] else '',
            row['temp'],
            row['humi'],
            row['bat'],
            row['rssi'],
            row['seq']
        ])
    
    output.seek(0)
    
    # 文件名
    filename = f"sensor_data_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    if sn:
        filename += f"_{sn}"
    filename += ".csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/alarms")
async def export_alarms(
    sn: Optional[str] = Query(None, description="设备序列号"),
    alarm_type: Optional[str] = Query(None, description="报警类型: HIGH/LOW/OFFLINE/LOW_BAT"),
    start: Optional[str] = Query(None, description="开始时间 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束时间 YYYY-MM-DD"),
    db: asyncpg.Pool = Depends(get_db)
):
    """
    导出报警记录
    """
    # 默认导出最近30天
    if not end:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end, "%Y-%m-%d")
    
    if not start:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    
    # 构建查询
    query = """
        SELECT a.id, a.sn, d.name as device_name, a.type, a.value, a.threshold, 
               a.triggered_at, a.notified, a.ack_at, a.ack_by
        FROM alarm_logs a
        LEFT JOIN devices d ON a.sn = d.sn
        WHERE a.triggered_at >= $1 AND a.triggered_at <= $2
    """
    params = [start_date, end_date]
    param_idx = 3
    
    if sn:
        query += f" AND a.sn = ${param_idx}"
        params.append(sn)
        param_idx += 1
    
    if alarm_type:
        query += f" AND a.type = ${param_idx}"
        params.append(alarm_type)
        param_idx += 1
    
    query += " ORDER BY a.triggered_at DESC LIMIT 10000"
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    if not rows:
        raise HTTPException(status_code=404, detail="No alarms found")
    
    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(["ID", "设备SN", "设备名称", "报警类型", "触发值", "阈值", "触发时间", "已通知", "确认时间", "确认人"])
    
    # 写入数据
    for row in rows:
        writer.writerow([
            row['id'],
            row['sn'],
            row['device_name'] or row['sn'],
            row['type'],
            round(row['value'], 2) if row['value'] else '',
            round(row['threshold'], 2) if row['threshold'] else '',
            row['triggered_at'].strftime("%Y-%m-%d %H:%M:%S") if row['triggered_at'] else '',
            "是" if row['notified'] else "否",
            row['ack_at'].strftime("%Y-%m-%d %H:%M:%S") if row['ack_at'] else '',
            row['ack_by'] or ''
        ])
    
    output.seek(0)
    
    filename = f"alarms_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
