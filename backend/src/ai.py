from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import time
import datetime
from typing import Optional, List
import aiohttp
import asyncpg
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_redis():
    from .main import redis_pool
    return redis_pool

async def get_db():
    from .main import db_pool
    return db_pool

class AISummaryResponse(BaseModel):
    content: str
    timestamp: float
    time_range: str

CHECKPOINTS = [
    datetime.time(8, 0),
    datetime.time(12, 0),
    datetime.time(17, 0),
    datetime.time(20, 0)
]

def get_latest_checkpoint():
    now = datetime.datetime.now()
    current_time = now.time()
    
    sorted_cps = sorted(CHECKPOINTS)
    
    latest_cp = None
    for cp in sorted_cps:
        if current_time >= cp:
            latest_cp = cp
        else:
            break
            
    if latest_cp:
        return datetime.datetime.combine(now.date(), latest_cp)
    else:
        # Before 8am today, return yesterday's last checkpoint
        return datetime.datetime.combine(now.date() - datetime.timedelta(days=1), sorted_cps[-1])

def get_previous_checkpoint(dt: datetime.datetime):
    t = dt.time()
    d = dt.date()
    
    # 8:00 covers 00:00 - 08:00
    # 12:00 covers 08:00 - 12:00
    # 17:00 covers 12:00 - 17:00
    # 20:00 covers 17:00 - 20:00
    
    if t >= datetime.time(20, 0):
        start = datetime.datetime.combine(d, datetime.time(17, 0))
    elif t >= datetime.time(17, 0):
        start = datetime.datetime.combine(d, datetime.time(12, 0))
    elif t >= datetime.time(12, 0):
        start = datetime.datetime.combine(d, datetime.time(8, 0))
    elif t >= datetime.time(8, 0):
        start = datetime.datetime.combine(d, datetime.time(0, 0))
    else:
        # Should not happen if passed from get_latest_checkpoint
        return None
    return start

async def call_openai(config, prompt):
    base_url = config.get("api_url", "https://api.openai.com/v1").rstrip('/')
    if not base_url.endswith("/v1"):
         # Some users might put base url without v1, try to handle
         pass 
         
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config.get("model", "gpt-3.5-turbo"),
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, timeout=30) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"API Error {resp.status}: {text}")
            result = await resp.json()
            return result['choices'][0]['message']['content']

@router.get("/summary", response_model=AISummaryResponse)
async def get_ai_summary(redis = Depends(get_redis), db = Depends(get_db)):
    latest_cp_dt = get_latest_checkpoint()
    
    cached_ts = await redis.get("ai:summary:timestamp")
    cached_content = await redis.get("ai:summary:content")
    cached_range = await redis.get("ai:summary:range")
    
    need_generate = False
    if not cached_ts or not cached_content:
        need_generate = True
    else:
        # Check if cache is from the current checkpoint cycle
        # If cache time is >= latest_cp_dt, it means it was generated AFTER the checkpoint time
        # so it's fresh for this slot.
        last_gen_time = datetime.datetime.fromtimestamp(float(cached_ts))
        if last_gen_time < latest_cp_dt:
            need_generate = True
            
    if not need_generate:
        return AISummaryResponse(
            content=cached_content,
            timestamp=float(cached_ts),
            time_range=cached_range or ""
        )
        
    # Generate
    start_dt = get_previous_checkpoint(latest_cp_dt)
    if not start_dt:
        # Fallback if weird time
        if cached_content:
             return AISummaryResponse(content=cached_content, timestamp=float(cached_ts), time_range=cached_range or "")
        return AISummaryResponse(content="等待初次分析...", timestamp=time.time(), time_range="")

    end_dt = latest_cp_dt
    
    # DB Queries
    async with db.acquire() as conn:
        # Alarm count
        rows = await conn.fetch("SELECT count(*) as count FROM alarm_logs WHERE triggered_at >= $1 AND triggered_at < $2", start_dt, end_dt)
        alarm_count = rows[0]['count']
        
        # Distinct instruments
        inst_rows = await conn.fetch("""
            SELECT count(DISTINCT d.instrument_id) as count
            FROM alarm_logs a
            JOIN devices d ON a.sn = d.sn
            WHERE a.triggered_at >= $1 AND a.triggered_at < $2
        """, start_dt, end_dt)
        inst_count = inst_rows[0]['count']
        
        # Details
        details = await conn.fetch("""
            SELECT a.triggered_at as time, d.name, a.value, d.unit
            FROM alarm_logs a
            JOIN devices d ON a.sn = d.sn
            WHERE a.triggered_at >= $1 AND a.triggered_at < $2
            ORDER BY a.triggered_at DESC
            LIMIT 10
        """, start_dt, end_dt)

    time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    
    alarm_desc = ""
    if not details:
        alarm_desc = "无报警记录"
    else:
        for r in details:
            t_str = r['time'].strftime('%H:%M:%S')
            alarm_desc += f"- {t_str} {r['name']} 报警值:{r['value']}{r['unit']}\n"
            
    prompt = f"""
你是一个部署在物联网气体环境监测平台中的 AI 助手，今日【{time_str}】内平台收到【{alarm_count}】次传感器报警，涉及到 {inst_count} 台仪表。
具体的报警信息包括（仅列出部分）：
{alarm_desc}

请你用简单的话语总结这段时间的平台运行状况，我将显示在监测大屏上，请直接输出内容，一句多余的话都不要说。
"""

    ai_config_json = await redis.get("config:ai")
    if not ai_config_json:
         return AISummaryResponse(content="请在管理后台配置 AI 接口信息", timestamp=time.time(), time_range="")
    
    ai_config = json.loads(ai_config_json)
    if not ai_config.get("api_key"):
        return AISummaryResponse(content="AI API Key 未配置", timestamp=time.time(), time_range="")
        
    try:
        content = await call_openai(ai_config, prompt)
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        return AISummaryResponse(content=f"AI 分析服务暂不可用: {str(e)}", timestamp=time.time(), time_range="")
        
    # Save
    ts = datetime.datetime.now().timestamp()
    await redis.set("ai:summary:content", content)
    await redis.set("ai:summary:timestamp", str(ts))
    await redis.set("ai:summary:range", time_str)
    
    return AISummaryResponse(content=content, timestamp=ts, time_range=time_str)
