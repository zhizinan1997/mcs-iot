from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import re
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger("logs")

class LogEntry(BaseModel):
    timestamp: str
    level: str
    service: str
    message: str
    raw: str

class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int

# 日志级别映射
LEVEL_MAP = {
    'ERROR': 'error',
    'WARNING': 'warning',
    'WARN': 'warning',
    'INFO': 'info',
    'DEBUG': 'debug',
}

# 服务容器名称映射
SERVICES = {
    'backend': 'mcs_backend',
    'worker': 'mcs_worker',
}

# 中文日志翻译规则 (正则模式 -> 中文模板)
TRANSLATION_RULES = [
    # 报警相关
    (r'\[(\w+)\] ALARM HIGH.*value=([\d.]+).*threshold=([\d.]+)', '🚨 {0} 触发高浓度报警 (数值:{1}, 阈值:{2})'),
    (r'\[(\w+)\] ALARM LOW.*value=([\d.]+).*threshold=([\d.]+)', '🚨 {0} 触发低浓度报警 (数值:{1}, 阈值:{2})'),
    (r'\[(\w+)\] ALARM LOW_BAT.*value=([\d.]+)', '🔋 {0} 电池电量过低 ({1}%)'),
    (r'\[(\w+)\] ALARM WEAK_SIGNAL.*rssi=([-\d]+)', '📶 {0} 信号较弱 (信号强度:{1}dBm)'),
    (r'\[(\w+)\] ALARM OFFLINE', '⚠️ {0} 设备离线'),
    (r'Debounce key set with TTL=(\d+)s \((\d+)min\)', '⏱️ 设置报警消抖时间：{1}分钟'),
    (r'\[(\w+)\] Alarm \w+ debounced', '⏱️ {0} 报警已静默（处于消抖期）'),
    
    # Webhook 通知
    (r'Webhook notification sent via (\w+).*errcode.*0.*ok', '✅ Webhook 通知发送成功 ({0})'),
    (r'Webhook notification sent via (\w+)', '✅ Webhook 通知已发送 ({0})'),
    (r'\[Webhook\] Attempting to send.*platform=(\w+)', '📤 正在发送 Webhook 通知 ({0})'),
    (r'\[Notification\] Preparing to send.*webhook=True', '📤 准备发送报警通知'),
    (r'\[Notification\] Calling send_webhook', '📤 调用 Webhook 通知服务'),
    
    # 数据处理
    (r'\[(\w+)\] v=([\d.-]+), ppm=([\d.]+), bat=(\d+)%.*Saved', '💾 {0}: 浓度 {2}ppm, 电量 {3}%'),
    (r'\[(\w+)\].*v=([\d.-]+).*ppm=([\d.]+).*Saved', '💾 {0}: 保存数据 (浓度 {2}ppm)'),
    
    # 系统状态
    (r'Connected to Redis', '✅ Redis 缓存服务连接成功'),
    (r'Connected to MQTT Broker', '✅ MQTT 消息代理连接成功'),
    (r'Connected to TimescaleDB', '✅ 时序数据库连接成功'),
    (r'Connected to Database', '✅ 数据库连接成功'),
    (r'Subscribed to.*mcs/sens/#', '✅ 已订阅传感器数据主题'),
    (r'Subscribed to', '✅ 已订阅消息主题'),
    (r'Starting Backend API', '🚀 后端服务启动中'),
    (r'Starting Worker', '🚀 Worker 服务启动中'),
    (r'License initialized.*Device ID: (\w+)', '🔑 授权系统已初始化 (设备ID: {0})'),
    (r'License check bypassed', '⚙️ 授权检查已跳过'),
    (r'Scheduler started', '⏰ 定时任务调度器已启动'),
    (r'AlarmCenter initialized', '🔔 报警中心已初始化'),
    
    # HTTP 请求
    (r'GET /api/health.*200 OK', '💚 系统健康检查正常'),
    (r'GET /api/logs.*200 OK', '📋 日志查询成功'),
    (r'GET /api/devices.*200 OK', '📋 设备列表查询成功'),
    (r'GET /api/alarms.*200 OK', '📋 报警记录查询成功'),
    (r'GET /api/dashboard.*200 OK', '📊 仪表盘数据加载成功'),
    (r'GET /api/config.*200 OK', '⚙️ 配置信息读取成功'),
    (r'PUT /api/config.*200 OK', '💾 配置保存成功'),
    (r'POST /api/auth/login.*200 OK', '🔓 用户登录成功'),
    (r'GET.*200 OK', '✅ 请求处理成功'),
    (r'POST.*200 OK', '✅ 操作执行成功'),
    (r'PUT.*200 OK', '💾 更新保存成功'),
    (r'DELETE.*200 OK', '🗑️ 删除操作成功'),
    (r'.*401 Unauthorized', '🔒 身份验证失败'),
    (r'.*500 Internal Server Error', '❌ 服务器内部错误'),
    (r'.*404 Not Found', '❓ 资源不存在'),
    
    # 错误处理
    (r'Error.*:', '❌ 发生错误'),
    (r'Failed.*:', '❌ 操作失败'),
    (r'Exception', '❌ 系统异常'),
]

def translate_log(raw_log: str) -> str:
    """将原始日志翻译为中文概括"""
    for pattern, template in TRANSLATION_RULES:
        match = re.search(pattern, raw_log, re.IGNORECASE)
        if match:
            try:
                # 使用捕获组替换模板中的占位符
                groups = match.groups()
                result = template
                for i, g in enumerate(groups):
                    result = result.replace('{' + str(i) + '}', str(g))
                return result
            except:
                return template
    
    # 无法翻译的日志保持原样但去除多余信息
    clean = raw_log.strip()
    if len(clean) > 100:
        clean = clean[:100] + '...'
    return clean

def parse_log_line(line: str, service: str) -> Optional[LogEntry]:
    """解析单行日志"""
    if not line.strip():
        return None
    
    # 确定日志级别
    level = 'info'
    upper_line = line.upper()
    if 'ERROR' in upper_line or 'EXCEPTION' in upper_line or 'FAILED' in upper_line:
        level = 'error'
    elif 'WARNING' in upper_line or 'WARN' in upper_line or 'ALARM' in upper_line:
        level = 'warning'
    
    # 提取时间戳
    ts_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
    timestamp = ts_match.group(1) if ts_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 翻译日志消息
    translated = translate_log(line)
    
    return LogEntry(
        timestamp=timestamp,
        level=level,
        service=service,
        message=translated,
        raw=line.strip()[:300]
    )

def get_docker_logs(container_name: str, lines: int = 50) -> List[str]:
    """使用 Docker SDK 获取容器日志"""
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        logs = container.logs(tail=lines, timestamps=False).decode('utf-8', errors='replace')
        return logs.split('\n')
    except Exception as e:
        logger.warning(f"Failed to get logs from {container_name}: {e}")
        return []

@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    lines: int = 100
):
    """获取服务日志"""
    all_logs: List[LogEntry] = []
    
    if service and service in SERVICES:
        target_services = {service: SERVICES[service]}
    else:
        target_services = SERVICES
    
    lines_per_service = max(30, lines // len(target_services))
    
    for svc_name, container_name in target_services.items():
        log_lines = get_docker_logs(container_name, lines_per_service)
        
        for line in log_lines:
            entry = parse_log_line(line, svc_name)
            if entry:
                all_logs.append(entry)
    
    # 按级别筛选
    if level:
        all_logs = [log for log in all_logs if log.level == level]
    
    # 按时间戳排序（最新在前）
    all_logs.sort(key=lambda x: x.timestamp, reverse=True)
    
    return LogsResponse(logs=all_logs[:lines], total=len(all_logs))

@router.delete("/logs")
async def clear_logs():
    """清除日志提示"""
    return {
        "message": "日志显示已清除。",
        "note": "刷新页面可重新加载最新日志"
    }
