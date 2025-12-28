"""
MCS-IOT 设备下行命令控制模块 (Device Control Commands)

该文件负责向物联网设备发送下行控制指令，通过 MQTT 协议实现远程配置与管理。
主要功能包括：
1. 调试模式控制：允许管理员暂时提升设备的监测频率以便进行故障排查。
2. 校准参数下发：将服务器端的标定参数（k/b 值及温度补偿）远程同步至设备端固件。
3. 远程运维支持：实现设备的远程重启、OTA 固件升级等高级运维指令。
4. 广播能力：支持向所有在线设备同步下达特定指令。

结构：
- MQTT Connection Logic: get_mqtt_client 实现后端的实时命令推送能力。
- Command Models: DebugCommand, CalibCommand 等封装了各种指令的具体参数。
- API Handlers: /{sn}/debug, /{sn}/calibrate 等接口，处理“校验权限 -> 更新本地 DB/Redis -> 推送 MQTT 消息”的闭环流程。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
import json
import os
import paho.mqtt.client as mqtt
import asyncpg
import redis.asyncio as aioredis

router = APIRouter()

# MQTT 客户端 (用于下行命令)
mqtt_client = None

def get_mqtt_client():
    global mqtt_client
    if mqtt_client is None or not mqtt_client.is_connected():
        mqtt_client = mqtt.Client()
        mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
        mqtt_user = os.getenv("MQTT_USER", "worker")
        mqtt_pass = os.getenv("MQTT_PASS", "worker123")
        mqtt_client.username_pw_set(mqtt_user, mqtt_pass)
        mqtt_client.connect(mqtt_host, 1883, 60)
        mqtt_client.loop_start()
    return mqtt_client

async def get_db():
    from .main import db_pool
    return db_pool

async def get_redis():
    from .main import redis_pool
    return redis_pool


class DebugCommand(BaseModel):
    """调试模式命令"""
    duration: int = 600  # 持续时间(秒)，默认10分钟


class CalibCommand(BaseModel):
    """校准参数更新"""
    k: float  # 斜率
    b: float  # 截距
    t_ref: Optional[float] = 25.0  # 参考温度
    t_comp: Optional[float] = 0.1  # 温度补偿系数


class RebootCommand(BaseModel):
    """重启命令"""
    delay: int = 5  # 延迟秒数


class OtaCommand(BaseModel):
    """OTA升级命令"""
    url: str  # 固件下载地址
    md5: str  # 固件MD5校验


@router.post("/{sn}/debug")
async def send_debug_command(
    sn: str,
    cmd: DebugCommand,
    db: asyncpg.Pool = Depends(get_db)
):
    """
    切换设备到调试模式
    调试模式下采集频率从10秒降到1秒
    """
    # 检查设备是否存在
    async with db.acquire() as conn:
        device = await conn.fetchrow("SELECT sn, name FROM devices WHERE sn = $1", sn)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {sn} not found")
    
    # 发送MQTT命令
    topic = f"mcs/{sn}/cmd"
    payload = json.dumps({
        "cmd": "debug",
        "duration": min(cmd.duration, 600)  # 最长10分钟
    })
    
    try:
        client = get_mqtt_client()
        result = client.publish(topic, payload)
        if result.rc == 0:
            return {"success": True, "message": f"Debug command sent to {sn}", "duration": cmd.duration}
        else:
            raise HTTPException(status_code=500, detail="MQTT publish failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.post("/{sn}/calibrate")
async def send_calib_command(
    sn: str,
    cmd: CalibCommand,
    db: asyncpg.Pool = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    更新设备校准参数
    同时更新设备端和服务器端的校准参数
    """
    # 检查设备是否存在
    async with db.acquire() as conn:
        device = await conn.fetchrow("SELECT sn FROM devices WHERE sn = $1", sn)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {sn} not found")
        
        # 更新数据库中的校准参数
        await conn.execute("""
            UPDATE devices 
            SET calib_k = $1, calib_b = $2, calib_t_ref = $3, calib_t_comp = $4
            WHERE sn = $5
        """, cmd.k, cmd.b, cmd.t_ref, cmd.t_comp, sn)
    
    # 更新 Redis 缓存
    await redis.hset(f"calib:{sn}", mapping={
        "k": str(cmd.k),
        "b": str(cmd.b),
        "t_ref": str(cmd.t_ref),
        "t_comp": str(cmd.t_comp)
    })
    
    # 发送MQTT命令到设备
    topic = f"mcs/{sn}/cmd"
    payload = json.dumps({
        "cmd": "calib",
        "k": cmd.k,
        "b": cmd.b,
        "t_comp": cmd.t_comp
    })
    
    try:
        client = get_mqtt_client()
        client.publish(topic, payload)
        return {
            "success": True, 
            "message": f"Calibration updated for {sn}",
            "params": {"k": cmd.k, "b": cmd.b, "t_ref": cmd.t_ref, "t_comp": cmd.t_comp}
        }
    except Exception as e:
        # 数据库已更新，只是设备端可能未收到
        return {
            "success": True,
            "warning": f"Database updated but device command may have failed: {str(e)}",
            "params": {"k": cmd.k, "b": cmd.b, "t_ref": cmd.t_ref, "t_comp": cmd.t_comp}
        }


@router.post("/{sn}/reboot")
async def send_reboot_command(
    sn: str,
    cmd: RebootCommand,
    db: asyncpg.Pool = Depends(get_db)
):
    """
    远程重启设备
    """
    # 检查设备是否存在
    async with db.acquire() as conn:
        device = await conn.fetchrow("SELECT sn FROM devices WHERE sn = $1", sn)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {sn} not found")
    
    # 发送MQTT命令
    topic = f"mcs/{sn}/cmd"
    payload = json.dumps({
        "cmd": "reboot",
        "delay": cmd.delay
    })
    
    try:
        client = get_mqtt_client()
        result = client.publish(topic, payload)
        if result.rc == 0:
            return {"success": True, "message": f"Reboot command sent to {sn}", "delay": cmd.delay}
        else:
            raise HTTPException(status_code=500, detail="MQTT publish failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.post("/{sn}/ota")
async def send_ota_command(
    sn: str,
    cmd: OtaCommand,
    db: asyncpg.Pool = Depends(get_db)
):
    """
    发送OTA升级命令
    """
    # 检查设备是否存在
    async with db.acquire() as conn:
        device = await conn.fetchrow("SELECT sn FROM devices WHERE sn = $1", sn)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {sn} not found")
    
    # 发送MQTT命令
    topic = f"mcs/{sn}/cmd"
    payload = json.dumps({
        "cmd": "ota",
        "url": cmd.url,
        "md5": cmd.md5
    })
    
    try:
        client = get_mqtt_client()
        result = client.publish(topic, payload)
        if result.rc == 0:
            return {"success": True, "message": f"OTA command sent to {sn}", "url": cmd.url}
        else:
            raise HTTPException(status_code=500, detail="MQTT publish failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.post("/broadcast/debug")
async def broadcast_debug_command(
    cmd: DebugCommand,
    db: asyncpg.Pool = Depends(get_db)
):
    """
    向所有在线设备广播调试模式命令
    """
    async with db.acquire() as conn:
        devices = await conn.fetch("SELECT sn FROM devices WHERE status = 'online'")
    
    if not devices:
        return {"success": False, "message": "No online devices found"}
    
    client = get_mqtt_client()
    sent_count = 0
    
    for device in devices:
        sn = device['sn']
        topic = f"mcs/{sn}/cmd"
        payload = json.dumps({
            "cmd": "debug",
            "duration": min(cmd.duration, 600)
        })
        try:
            client.publish(topic, payload)
            sent_count += 1
        except:
            pass
    
    return {
        "success": True,
        "message": f"Debug command broadcast to {sent_count}/{len(devices)} devices"
    }
