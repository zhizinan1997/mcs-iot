"""
系统自检模块
提供详细的系统健康检查功能
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
import asyncio
import time
import os
import socket
import subprocess
import json

from .deps import get_redis, get_db

router = APIRouter()

# 自检项目定义
CHECK_ITEMS = [
    {"id": "database", "name": "数据库 (TimescaleDB)", "order": 1},
    {"id": "redis", "name": "缓存服务 (Redis)", "order": 2},
    {"id": "mqtt", "name": "MQTT 代理 (Mosquitto)", "order": 3},
    {"id": "worker", "name": "后台工作进程 (Worker)", "order": 4},
    {"id": "license", "name": "授权状态 (License)", "order": 5},
    {"id": "db_connectivity", "name": "数据库网络连通性", "order": 6},
    {"id": "redis_connectivity", "name": "Redis 网络连通性", "order": 7},
    {"id": "mqtt_connectivity", "name": "MQTT 网络连通性", "order": 8},
    {"id": "db_tables", "name": "数据库表结构完整性", "order": 9},
    {"id": "db_size", "name": "数据库存储空间", "order": 10},
    {"id": "redis_memory", "name": "Redis 内存使用", "order": 11},
    {"id": "device_count", "name": "设备统计", "order": 12},
    {"id": "alarm_status", "name": "报警系统状态", "order": 13},
    {"id": "r2_config", "name": "R2 归档配置", "order": 14},
    {"id": "ai_config", "name": "AI 接口配置", "order": 15},
]

@router.get("/items")
async def get_check_items():
    """获取所有自检项目列表"""
    return {"items": CHECK_ITEMS, "total": len(CHECK_ITEMS)}

@router.get("/run")
async def run_health_check(redis = Depends(get_redis), db = Depends(get_db)):
    """
    执行完整的系统自检
    返回每个检查项的详细结果
    """
    results = []
    overall_status = "healthy"
    
    # 1. 数据库检查
    result = await check_database(db)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 2. Redis 检查
    result = await check_redis(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 3. MQTT 检查
    result = await check_mqtt(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 4. Worker 检查
    result = await check_worker(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 5. 授权检查
    result = await check_license(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 6. 数据库网络连通性
    result = await check_network("timescaledb", 5432, "数据库网络连通性")
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 7. Redis 网络连通性
    result = await check_network("redis", 6379, "Redis 网络连通性")
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 8. MQTT 网络连通性
    result = await check_network("mosquitto", 1883, "MQTT 网络连通性")
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 9. 数据库表完整性
    result = await check_db_tables(db)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 10. 数据库存储空间
    result = await check_db_size(db)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 11. Redis 内存使用
    result = await check_redis_memory(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "unhealthy"
    
    # 12. 设备统计
    result = await check_device_count(db, redis)
    results.append(result)
    
    # 13. 报警系统状态
    result = await check_alarm_status(db)
    results.append(result)
    
    # 14. R2 归档配置
    result = await check_r2_config(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "warning" if overall_status == "healthy" else overall_status
    
    # 15. AI 接口配置
    result = await check_ai_config(redis)
    results.append(result)
    if result["status"] == "error":
        overall_status = "warning" if overall_status == "healthy" else overall_status
    
    return {
        "overall_status": overall_status,
        "timestamp": time.time(),
        "results": results,
        "total_checks": len(results),
        "passed": sum(1 for r in results if r["status"] == "ok"),
        "warnings": sum(1 for r in results if r["status"] == "warning"),
        "errors": sum(1 for r in results if r["status"] == "error")
    }


async def check_database(db) -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        start = time.time()
        async with db.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
        latency = int((time.time() - start) * 1000)
        
        return {
            "id": "database",
            "name": "数据库 (TimescaleDB)",
            "status": "ok",
            "latency_ms": latency,
            "message": f"连接正常 (响应时间: {latency}ms)",
            "details": {"version": version[:50] + "..." if len(version) > 50 else version}
        }
    except Exception as e:
        return {
            "id": "database",
            "name": "数据库 (TimescaleDB)",
            "status": "error",
            "message": "数据库连接失败",
            "error": str(e),
            "solution": "检查 TimescaleDB 容器是否运行正常，检查数据库连接配置"
        }


async def check_redis(redis) -> Dict[str, Any]:
    """检查 Redis 连接"""
    try:
        start = time.time()
        await redis.ping()
        latency = int((time.time() - start) * 1000)
        
        info = await redis.info("server")
        
        return {
            "id": "redis",
            "name": "缓存服务 (Redis)",
            "status": "ok",
            "latency_ms": latency,
            "message": f"连接正常 (响应时间: {latency}ms)",
            "details": {"redis_version": info.get("redis_version", "unknown")}
        }
    except Exception as e:
        return {
            "id": "redis",
            "name": "缓存服务 (Redis)",
            "status": "error",
            "message": "Redis 连接失败",
            "error": str(e),
            "solution": "检查 Redis 容器是否运行正常，检查 REDIS_HOST 环境变量"
        }


async def check_mqtt(redis) -> Dict[str, Any]:
    """检查 MQTT 状态"""
    try:
        # 首先直接检查 mqtt:last_message_time
        last_msg_time = await redis.get("mqtt:last_message_time")
        if last_msg_time:
            import time
            age = time.time() - float(last_msg_time)
            if age < 120:  # 2分钟内有消息
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "ok",
                    "message": f"MQTT 正常，最后消息 {int(age)} 秒前",
                    "details": {"last_message_age_sec": int(age)}
                }
            elif age < 600:  # 10分钟内
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "warning",
                    "message": f"MQTT 消息较久，最后消息 {int(age)} 秒前",
                    "solution": "如设备在线则可忽略，否则检查设备连接"
                }
        
        # 其次检查 worker 健康报告
        worker_health = await redis.get("system:health")
        if worker_health:
            data = json.loads(worker_health)
            mqtt_status = data.get("components", {}).get("mqtt", {})
            status = mqtt_status.get("status", "unknown")
            
            if status == "up":
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "ok",
                    "message": "MQTT 代理运行正常",
                    "details": mqtt_status
                }
            elif status == "warning":
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "warning",
                    "message": f"MQTT 最后消息较久 ({mqtt_status.get('last_message_age_sec', '?')} 秒前)",
                    "solution": "如设备在线则可忽略，否则检查设备连接"
                }
            elif status == "unknown":
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "warning",
                    "message": "暂无 MQTT 消息记录",
                    "solution": "等待设备发送消息，或检查设备是否在线"
                }
            else:
                return {
                    "id": "mqtt",
                    "name": "MQTT 代理 (Mosquitto)",
                    "status": "error",
                    "message": "MQTT 代理异常",
                    "error": mqtt_status.get("error", "Unknown error"),
                    "solution": "检查 Mosquitto 容器是否运行，检查 MQTT 配置文件"
                }
        else:
            return {
                "id": "mqtt",
                "name": "MQTT 代理 (Mosquitto)",
                "status": "warning",
                "message": "无法获取 MQTT 状态",
                "solution": "Worker 进程可能刚启动，请等待几分钟后重试"
            }
    except Exception as e:
        return {
            "id": "mqtt",
            "name": "MQTT 代理 (Mosquitto)",
            "status": "error",
            "message": "获取 MQTT 状态失败",
            "error": str(e),
            "solution": "检查 Worker 进程和 Redis 连接"
        }


async def check_worker(redis) -> Dict[str, Any]:
    """检查 Worker 进程"""
    try:
        worker_health = await redis.get("system:health")
        if worker_health:
            data = json.loads(worker_health)
            status = data.get("status", "unknown")
            if status == "healthy":
                return {
                    "id": "worker",
                    "name": "后台工作进程 (Worker)",
                    "status": "ok",
                    "message": "Worker 进程运行正常",
                    "details": {"status": status}
                }
            else:
                return {
                    "id": "worker",
                    "name": "后台工作进程 (Worker)",
                    "status": "warning",
                    "message": f"Worker 状态: {status}",
                    "solution": "检查 Worker 容器日志"
                }
        else:
            return {
                "id": "worker",
                "name": "后台工作进程 (Worker)",
                "status": "warning",
                "message": "未收到 Worker 心跳",
                "solution": "Worker 可能未运行，请检查 docker compose logs worker"
            }
    except Exception as e:
        return {
            "id": "worker",
            "name": "后台工作进程 (Worker)",
            "status": "error",
            "message": "获取 Worker 状态失败",
            "error": str(e),
            "solution": "检查 Redis 连接"
        }


async def check_license(redis) -> Dict[str, Any]:
    """检查授权状态"""
    try:
        status = await redis.get("license:status")
        expires = await redis.get("license:expires")
        
        if status == "active":
            return {
                "id": "license",
                "name": "授权状态 (License)",
                "status": "ok",
                "message": f"已授权" + (f"，到期: {expires}" if expires else ""),
                "details": {"status": status, "expires": expires}
            }
        elif status == "grace":
            grace_days = await redis.get("license:grace_remaining_days")
            return {
                "id": "license",
                "name": "授权状态 (License)",
                "status": "warning",
                "message": f"宽限期中 (剩余 {grace_days or '?'} 天)",
                "solution": "请尽快联系 zinanzhi@gmail.com 续费授权"
            }
        else:
            return {
                "id": "license",
                "name": "授权状态 (License)",
                "status": "warning",
                "message": "未授权或授权已过期",
                "solution": "请联系 zinanzhi@gmail.com 购买授权"
            }
    except Exception as e:
        return {
            "id": "license",
            "name": "授权状态 (License)",
            "status": "warning",
            "message": "无法获取授权状态",
            "error": str(e)
        }


async def check_network(host: str, port: int, name: str) -> Dict[str, Any]:
    """检查网络连通性"""
    try:
        start = time.time()
        # 使用 asyncio 进行异步 socket 连接
        loop = asyncio.get_event_loop()
        
        def _connect():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result
        
        result = await loop.run_in_executor(None, _connect)
        latency = int((time.time() - start) * 1000)
        
        if result == 0:
            return {
                "id": f"{host.replace('.', '_')}_connectivity",
                "name": name,
                "status": "ok",
                "latency_ms": latency,
                "message": f"{host}:{port} 可达 ({latency}ms)",
                "details": {"host": host, "port": port}
            }
        else:
            return {
                "id": f"{host.replace('.', '_')}_connectivity",
                "name": name,
                "status": "error",
                "message": f"{host}:{port} 不可达",
                "solution": f"检查 {host} 服务是否运行，检查 Docker 网络配置"
            }
    except Exception as e:
        return {
            "id": f"{host.replace('.', '_')}_connectivity",
            "name": name,
            "status": "error",
            "message": f"网络检测失败: {host}:{port}",
            "error": str(e),
            "solution": "检查 DNS 解析和 Docker 网络"
        }


async def check_db_tables(db) -> Dict[str, Any]:
    """检查数据库表完整性"""
    required_tables = ["devices", "sensor_data", "alarm_logs", "instruments", "users"]
    
    try:
        async with db.acquire() as conn:
            existing = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            existing_tables = [r['tablename'] for r in existing]
            
        missing = [t for t in required_tables if t not in existing_tables]
        
        if not missing:
            return {
                "id": "db_tables",
                "name": "数据库表结构完整性",
                "status": "ok",
                "message": f"所有 {len(required_tables)} 个核心表存在",
                "details": {"tables": existing_tables[:10]}
            }
        else:
            return {
                "id": "db_tables",
                "name": "数据库表结构完整性",
                "status": "error",
                "message": f"缺少表: {', '.join(missing)}",
                "solution": "运行数据库初始化脚本或检查 schema.sql"
            }
    except Exception as e:
        return {
            "id": "db_tables",
            "name": "数据库表结构完整性",
            "status": "error",
            "message": "无法检查表结构",
            "error": str(e),
            "solution": "检查数据库连接"
        }


async def check_db_size(db) -> Dict[str, Any]:
    """检查数据库大小"""
    try:
        async with db.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    (SELECT COUNT(*) FROM sensor_data) as sensor_rows
            """)
        
        size_bytes = result['db_size']
        sensor_rows = result['sensor_rows'] or 0
        
        # 格式化大小
        if size_bytes < 1024 * 1024:
            size_human = f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_human = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_human = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        
        # 如果超过 10GB，警告
        status = "ok"
        message = f"数据库大小: {size_human}，传感器数据: {sensor_rows:,} 条"
        solution = None
        
        if size_bytes > 10 * 1024 * 1024 * 1024:
            status = "warning"
            solution = "数据库较大，建议启用 R2 归档功能定期清理历史数据"
        
        return {
            "id": "db_size",
            "name": "数据库存储空间",
            "status": status,
            "message": message,
            "solution": solution,
            "details": {"size_bytes": size_bytes, "sensor_rows": sensor_rows}
        }
    except Exception as e:
        return {
            "id": "db_size",
            "name": "数据库存储空间",
            "status": "error",
            "message": "无法获取数据库大小",
            "error": str(e)
        }


async def check_redis_memory(redis) -> Dict[str, Any]:
    """检查 Redis 内存使用"""
    try:
        info = await redis.info("memory")
        used = info.get("used_memory", 0)
        peak = info.get("used_memory_peak", 0)
        
        # 格式化
        if used < 1024 * 1024:
            used_human = f"{used / 1024:.2f} KB"
        else:
            used_human = f"{used / (1024 * 1024):.2f} MB"
        
        status = "ok"
        solution = None
        
        # 如果超过 500MB，警告
        if used > 500 * 1024 * 1024:
            status = "warning"
            solution = "Redis 内存使用较高，检查是否有内存泄漏"
        
        return {
            "id": "redis_memory",
            "name": "Redis 内存使用",
            "status": status,
            "message": f"当前使用: {used_human}",
            "solution": solution,
            "details": {"used_memory": used, "peak_memory": peak}
        }
    except Exception as e:
        return {
            "id": "redis_memory",
            "name": "Redis 内存使用",
            "status": "error",
            "message": "无法获取 Redis 内存信息",
            "error": str(e)
        }


async def check_device_count(db, redis) -> Dict[str, Any]:
    """检查设备统计"""
    try:
        async with db.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM devices")
            online = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE status = 'online'")
        
        return {
            "id": "device_count",
            "name": "设备统计",
            "status": "ok",
            "message": f"总设备: {total}，在线: {online}，离线: {total - online}",
            "details": {"total": total, "online": online, "offline": total - online}
        }
    except Exception as e:
        return {
            "id": "device_count",
            "name": "设备统计",
            "status": "warning",
            "message": "无法获取设备统计",
            "error": str(e)
        }


async def check_alarm_status(db) -> Dict[str, Any]:
    """检查报警系统状态"""
    try:
        async with db.acquire() as conn:
            today = await conn.fetchval(
                "SELECT COUNT(*) FROM alarm_logs WHERE triggered_at >= CURRENT_DATE"
            )
            unacked = await conn.fetchval(
                "SELECT COUNT(*) FROM alarm_logs WHERE status = 'active'"
            )
        
        status = "ok"
        message = f"今日报警: {today}，未确认: {unacked}"
        
        if unacked > 10:
            status = "warning"
        
        return {
            "id": "alarm_status",
            "name": "报警系统状态",
            "status": status,
            "message": message,
            "details": {"today": today, "unacked": unacked}
        }
    except Exception as e:
        return {
            "id": "alarm_status",
            "name": "报警系统状态",
            "status": "warning",
            "message": "无法获取报警统计",
            "error": str(e)
        }


async def check_r2_config(redis) -> Dict[str, Any]:
    """检查 R2 归档配置"""
    try:
        data = await redis.get("config:archive")
        if data:
            config = json.loads(data)
            if config.get("enabled"):
                # 支持新版字段 (account_id, bucket) 和旧版字段 (r2_account_id, r2_bucket)
                has_account = config.get("account_id") or config.get("r2_account_id")
                has_bucket = config.get("bucket") or config.get("r2_bucket")
                bucket_name = config.get("bucket") or config.get("r2_bucket")
                if has_account and has_bucket:
                    return {
                        "id": "r2_config",
                        "name": "R2 归档配置",
                        "status": "ok",
                        "message": f"已配置 Bucket: {bucket_name}",
                        "details": {"bucket": bucket_name}
                    }
                else:
                    return {
                        "id": "r2_config",
                        "name": "R2 归档配置",
                        "status": "warning",
                        "message": "归档已启用但配置不完整",
                        "solution": "请填写完整的 R2 Endpoint、Bucket 和密钥"
                    }
            else:
                return {
                    "id": "r2_config",
                    "name": "R2 归档配置",
                    "status": "warning",
                    "message": "归档未启用",
                    "solution": "建议启用 R2 归档以备份历史数据"
                }
        else:
            return {
                "id": "r2_config",
                "name": "R2 归档配置",
                "status": "warning",
                "message": "归档未配置",
                "solution": "前往 数据归档 页面配置 Cloudflare R2"
            }
    except Exception as e:
        return {
            "id": "r2_config",
            "name": "R2 归档配置",
            "status": "warning",
            "message": "无法获取归档配置",
            "error": str(e)
        }


async def check_ai_config(redis) -> Dict[str, Any]:
    """检查 AI 接口配置"""
    try:
        data = await redis.get("config:ai")
        if data:
            config = json.loads(data)
            if config.get("api_key"):
                return {
                    "id": "ai_config",
                    "name": "AI 接口配置",
                    "status": "ok",
                    "message": f"已配置，模型: {config.get('model', 'unknown')}",
                    "details": {"model": config.get("model")}
                }
            else:
                return {
                    "id": "ai_config",
                    "name": "AI 接口配置",
                    "status": "warning",
                    "message": "AI API Key 未配置",
                    "solution": "前往 AI 接口 页面配置 API Key"
                }
        else:
            return {
                "id": "ai_config",
                "name": "AI 接口配置",
                "status": "warning",
                "message": "AI 接口未配置",
                "solution": "前往 AI 接口 页面进行配置"
            }
    except Exception as e:
        return {
            "id": "ai_config",
            "name": "AI 接口配置",
            "status": "warning",
            "message": "无法获取 AI 配置",
            "error": str(e)
        }
