"""
MQTT 账号管理 API
管理 Mosquitto 的用户名和密码
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import subprocess
import os
import json

router = APIRouter()

# Mosquitto 密码文件路径 (容器内挂载)
PASSWD_FILE = "/app/mosquitto/passwd"
# Docker 容器名
MOSQUITTO_CONTAINER = "mcs_mosquitto"


class MQTTAccountConfig(BaseModel):
    admin_user: str = "admin"
    admin_pass: str = ""
    worker_user: str = "worker"
    worker_pass: str = ""
    device_user: str = "device"
    device_pass: str = ""


async def get_redis():
    from .main import redis_pool
    return redis_pool


def generate_passwd_hash(username: str, password: str) -> str:
    """使用 mosquitto_passwd 生成密码哈希"""
    import hashlib
    import base64
    import secrets
    
    # 使用简单的 PBKDF2 哈希 (Mosquitto 兼容格式不易在 Python 直接生成)
    # 这里我们采用直接写明文然后让 mosquitto_passwd 处理的方式
    # 但由于后端不在 mosquitto 容器内，我们需要用其他方式
    
    # 方案: 使用 SHA512 + salt (Mosquitto 支持)
    salt = secrets.token_bytes(12)
    iterations = 101
    dk = hashlib.pbkdf2_hmac('sha512', password.encode(), salt, iterations)
    
    salt_b64 = base64.b64encode(salt).decode().rstrip('=')
    hash_b64 = base64.b64encode(dk).decode().rstrip('=')
    
    return f"$7${iterations}${salt_b64}${hash_b64}"


def write_passwd_file(config: MQTTAccountConfig):
    """写入 Mosquitto 密码文件"""
    lines = []
    
    if config.admin_user and config.admin_pass:
        hash_val = generate_passwd_hash(config.admin_user, config.admin_pass)
        lines.append(f"{config.admin_user}:{hash_val}")
    
    if config.worker_user and config.worker_pass:
        hash_val = generate_passwd_hash(config.worker_user, config.worker_pass)
        lines.append(f"{config.worker_user}:{hash_val}")
    
    if config.device_user and config.device_pass:
        hash_val = generate_passwd_hash(config.device_user, config.device_pass)
        lines.append(f"{config.device_user}:{hash_val}")
    
    with open(PASSWD_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def reload_mosquitto():
    """重载 Mosquitto 配置 (发送 SIGHUP)"""
    try:
        # 通过 docker exec 发送 SIGHUP 信号
        result = subprocess.run(
            ["docker", "exec", MOSQUITTO_CONTAINER, "kill", "-HUP", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Reload Mosquitto error: {e}")
        return False


@router.get("/mqtt", response_model=MQTTAccountConfig)
async def get_mqtt_config(redis = Depends(get_redis)):
    """获取 MQTT 账号配置"""
    data = await redis.get("config:mqtt")
    if data:
        return MQTTAccountConfig(**json.loads(data))
    
    # 返回默认配置 (不含密码)
    return MQTTAccountConfig(
        admin_user="admin",
        admin_pass="",
        worker_user="worker",
        worker_pass="",
        device_user="device",
        device_pass=""
    )


@router.put("/mqtt")
async def update_mqtt_config(config: MQTTAccountConfig, redis = Depends(get_redis)):
    """更新 MQTT 账号配置"""
    # 验证必填字段
    if not config.device_user or not config.device_pass:
        raise HTTPException(status_code=400, detail="设备账号和密码不能为空")
    
    if not config.worker_user or not config.worker_pass:
        raise HTTPException(status_code=400, detail="Worker 账号和密码不能为空")
    
    try:
        # 1. 保存配置到 Redis (用于界面显示)
        await redis.set("config:mqtt", config.json())
        
        # 2. 写入 Mosquitto 密码文件
        write_passwd_file(config)
        
        # 3. 重载 Mosquitto
        if reload_mosquitto():
            return {"message": "MQTT 配置已更新并生效"}
        else:
            return {"message": "MQTT 配置已保存，但重载失败，请手动重启 Mosquitto"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/mqtt/reload")
async def reload_mqtt():
    """手动重载 Mosquitto 配置"""
    if reload_mosquitto():
        return {"message": "Mosquitto 配置已重载"}
    else:
        raise HTTPException(status_code=500, detail="重载失败，请检查 Docker 权限")
