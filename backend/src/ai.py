"""
MCS-IOT AI 智能分析模块 (AI Analysis & Summary)

该文件利用大语言模型 (LLM) 对平台的运行状况进行定时总结，以便在大屏等界面展示直观的分析报告。
主要功能包括：
1. 实现“检查点 (Checkpoint)”机制，确保 AI 总结与特定的时间段（如早班、午间、晚班）匹配。
2. 自动从数据库抓取指定时间范围内的报警频次、涉及仪器及报警明细。
3. 调用 OpenAI 兼容接口，根据预设 Prompt 生成简洁的运行总结。
4. 提供缓存机制（Redis），减少冗余的 API 调用，并在数据陈旧或时间跨度变化时自动重新生成。

结构：
- Checkpoint Logic: get_latest_checkpoint 等函数用于计算当前所属的时间窗口。
- call_openai: 封装异步 HTTP 调用 LLM 的逻辑。
- get_ai_summary: 核心 API，处理“查询缓存 -> 逻辑判断 -> 取数分析 -> 调用 AI -> 更新缓存”的全流程。
"""
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

# 默认间隔小时数（如未配置）
DEFAULT_INTERVAL_HOURS = 4

def generate_checkpoints_from_interval(interval_hours: int) -> list:
    """
    根据间隔小时数生成检查点列表，以0点为起点
    例如 interval_hours=4 生成 [00:00, 04:00, 08:00, 12:00, 16:00, 20:00]
    """
    checkpoints = []
    hour = 0
    while hour < 24:
        checkpoints.append(datetime.time(hour, 0))
        hour += interval_hours
    return checkpoints

def get_latest_checkpoint_dynamic(interval_hours: int):
    """
    根据动态间隔获取最近的检查点时间
    检查点基于整点北京时间计算，从 00:00 开始
    """
    now = datetime.datetime.now()
    current_time = now.time()
    
    checkpoints = generate_checkpoints_from_interval(interval_hours)
    sorted_cps = sorted(checkpoints)
    
    latest_cp = None
    for cp in sorted_cps:
        if current_time >= cp:
            latest_cp = cp
        else:
            break
            
    if latest_cp:
        return datetime.datetime.combine(now.date(), latest_cp)
    else:
        # 在今日第一个检查点之前，返回昨日最后一个检查点
        return datetime.datetime.combine(now.date() - datetime.timedelta(days=1), sorted_cps[-1])

def get_previous_checkpoint_dynamic(dt: datetime.datetime, interval_hours: int):
    """
    获取指定检查点的上一个检查点时间（即当前时段的起始时间）
    """
    t = dt.time()
    d = dt.date()
    
    checkpoints = generate_checkpoints_from_interval(interval_hours)
    sorted_cps = sorted(checkpoints)
    
    # 找到 dt 对应的检查点在列表中的位置
    current_idx = None
    for i, cp in enumerate(sorted_cps):
        if t >= cp:
            current_idx = i
    
    if current_idx is None:
        # 不应该发生
        return None
    
    if current_idx == 0:
        # 第一个检查点（如 00:00），其开始时间是昨天的最后一个检查点
        prev_cp = sorted_cps[-1]
        return datetime.datetime.combine(d - datetime.timedelta(days=1), prev_cp)
    else:
        # 上一个检查点
        prev_cp = sorted_cps[current_idx - 1]
        return datetime.datetime.combine(d, prev_cp)

async def call_openai(config, prompt):
    # 固定使用元芯 AI API 地址
    base_url = "https://newapi2.zhizinan.top/v1"
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
    # 从配置读取间隔小时数
    ai_config_json = await redis.get("config:ai")
    interval_hours = DEFAULT_INTERVAL_HOURS
    if ai_config_json:
        ai_config = json.loads(ai_config_json)
        interval_hours = ai_config.get("interval_hours", DEFAULT_INTERVAL_HOURS)
    
    # 获取当前时段的检查点
    latest_cp_dt = get_latest_checkpoint_dynamic(interval_hours)
    
    cached_ts = await redis.get("ai:summary:timestamp")
    cached_content = await redis.get("ai:summary:content")
    cached_range = await redis.get("ai:summary:range")
    
    need_generate = False
    if not cached_ts or not cached_content:
        need_generate = True
    else:
        # 检查缓存是否属于当前周期
        # 如果缓存时间 >= 最新检查点时间，说明是当前时段生成的
        last_gen_time = datetime.datetime.fromtimestamp(float(cached_ts))
        if last_gen_time < latest_cp_dt:
            need_generate = True
            
    if not need_generate:
        return AISummaryResponse(
            content=cached_content,
            timestamp=float(cached_ts),
            time_range=cached_range or ""
        )
        
    # 生成新的总结
    start_dt = get_previous_checkpoint_dynamic(latest_cp_dt, interval_hours)
    if not start_dt:
        # 异常情况降级处理
        if cached_content:
             return AISummaryResponse(content=cached_content, timestamp=float(cached_ts), time_range=cached_range or "")
        return AISummaryResponse(content="等待初次分析...", timestamp=time.time(), time_range="")

    end_dt = latest_cp_dt
    
    # 查询数据库获取报警统计
    async with db.acquire() as conn:
        # 报警次数
        rows = await conn.fetch("SELECT count(*) as count FROM alarm_logs WHERE triggered_at >= $1 AND triggered_at < $2", start_dt, end_dt)
        alarm_count = rows[0]['count']
        
        # 涉及的仪表数量
        inst_rows = await conn.fetch("""
            SELECT count(DISTINCT d.instrument_id) as count
            FROM alarm_logs a
            JOIN devices d ON a.sn = d.sn
            WHERE a.triggered_at >= $1 AND a.triggered_at < $2
        """, start_dt, end_dt)
        inst_count = inst_rows[0]['count']
        
        # 报警详情（最多10条）
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
        
    # 保存到 Redis 缓存
    ts = datetime.datetime.now().timestamp()
    await redis.set("ai:summary:content", content)
    await redis.set("ai:summary:timestamp", str(ts))
    await redis.set("ai:summary:range", time_str)
    
    # 保存到数据库历史记录
    try:
        async with db.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_summary_logs (time_range, content, alarm_count, instrument_count)
                VALUES ($1, $2, $3, $4)
            """, time_str, content, alarm_count, inst_count)
    except Exception as e:
        # 历史记录保存失败不影响主流程
        logger.warning(f"Failed to save AI summary history: {e}")
    
    return AISummaryResponse(content=content, timestamp=ts, time_range=time_str)
