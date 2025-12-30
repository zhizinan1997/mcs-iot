"""
MCS-IOT 配置管理模块 (Configuration Management)

该文件负责系统各项配置的读取、修改、验证及其对应的 API 接口。
主要功能包括：
1. 定义 Pydantic 模型，用于验证 Email、Webhook、SMS、报警、大屏、归档、AI 等模块的配置数据。
2. 提供 RESTful API 接口，实现配置的持久化存储（主要存储在 Redis 中）。
3. 支持多云存储方案（Cloudflare R2, 腾讯云 COS, 阿里云 OSS）的归档配置，并提供连接测试。
4. 提供手动触发的数据备份与本地数据库清理功能。
5. 集成 AI 接口配置及连通性测试。

结构：
- BaseModel 类群: 各种配置项的数据结构定义。
- API 路由: 按照功能划分的配置管理接口。
- 辅助函数: 包括配置迁移、存储终结点构建、云存储连接测试等逻辑。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import json
import os

router = APIRouter()

class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 465
    sender: str = ""
    password: str = ""
    receivers: List[str] = []

class WebhookConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    platform: str = "custom"  # dingtalk, feishu, wecom, custom
    secret: str = ""  # 加签密钥

class SMSConfig(BaseModel):
    enabled: bool = False
    access_key: str = ""
    secret_key: str = ""
    sign_name: str = ""
    template_id: str = ""

class AlarmGeneralConfig(BaseModel):
    """报警通用配置：消抖时间和报警时段"""
    debounce_minutes: int = 10  # 消抖时间(分钟)
    time_restriction_enabled: bool = False  # 是否启用时段限制
    time_restriction_days: List[int] = [1, 2, 3, 4, 5]  # 周一到周五
    time_restriction_start: str = "08:00"  # 开始时间
    time_restriction_end: str = "18:00"  # 结束时间

class DashboardConfig(BaseModel):
    title: str = "MCS-IoT Dashboard"
    refresh_rate: int = 5
    background_image: Optional[str] = None

class ArchiveConfig(BaseModel):
    """数据归档配置 (支持多云存储: Cloudflare R2, 腾讯云 COS, 阿里云 OSS)"""
    enabled: bool = False
    local_retention_days: int = 3  # 本地数据库保留天数
    cloud_retention_days: int = 30  # 云端备份保留天数
    # 云存储提供商: cloudflare, tencent, alibaba
    provider: str = "cloudflare"
    # 通用字段
    bucket: str = ""
    access_key: str = ""
    secret_key: str = ""
    # Cloudflare R2 专用
    account_id: str = ""
    # 腾讯云/阿里云 专用
    region: str = ""
    # 兼容旧版字段 (deprecated)
    r2_retention_days: int = 30
    r2_account_id: str = ""
    r2_bucket: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""

class SiteConfig(BaseModel):
    """站点品牌配置"""
    site_name: str = "MCS-IoT"
    logo_url: str = ""
    browser_title: str = "MCS-IoT Dashboard"

class ScreenBgConfig(BaseModel):
    """大屏背景配置"""
    image_url: str = ""

class WeatherConfig(BaseModel):
    """天气配置"""
    city_pinyin: str = "beijing"
    province: str = "北京"
    city: str = "北京"
    api_key: str = ""
    enabled: bool = True

class ScreenLayoutConfig(BaseModel):
    """大屏面板布局配置"""
    left: float = 75
    center: float = 0
    right: float = 25
    mainHeight: float = 70
    trendHeight: float = 30
    leftInner: float = 35
    centerInner: float = 65
    leftPanel1: float = 35
    leftPanel2: float = 34
    leftPanel3: float = 27

# AI 接口配置
AI_API_URL = "https://newapi2.zhizinan.top/v1"  # 固定 API 地址

class AIConfig(BaseModel):
    """仅配置 API Key 和模型，URL 已锁定"""
    api_key: str = ""
    model: str = "gpt-3.5-turbo"
    interval_hours: int = 4  # AI 总结间隔（小时），以0点为起点计算检查点

async def get_redis():
    from .main import redis_pool
    return redis_pool

async def get_db():
    from .main import db_pool
    return db_pool

# AI Config
@router.get("/ai", response_model=AIConfig)
async def get_ai_config(redis = Depends(get_redis)):
    data = await redis.get("config:ai")
    if data:
        return AIConfig(**json.loads(data))
    return AIConfig()

@router.put("/ai")
async def update_ai_config(config: AIConfig, redis = Depends(get_redis)):
    await redis.set("config:ai", config.json())
    return {"message": "AI config updated"}

@router.post("/ai/test")
async def test_ai_config(config: AIConfig):
    """Test AI configuration by sending a simple request"""
    try:
        from .ai import call_openai
        # Use a very simple prompt to save tokens and time
        response = await call_openai(config.dict(), "Hello, please reply with 'OK' only.")
        return {"success": True, "message": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ai/history")
async def get_ai_history(db = Depends(get_db), page: int = 1, size: int = 20):
    """获取 AI 总结历史记录列表"""
    try:
        offset = (page - 1) * size
        async with db.acquire() as conn:
            # 获取总数
            count_result = await conn.fetchrow("SELECT COUNT(*) as total FROM ai_summary_logs")
            total = count_result['total'] if count_result else 0
            
            # 获取分页数据
            rows = await conn.fetch("""
                SELECT id, time_range, content, alarm_count, instrument_count, created_at
                FROM ai_summary_logs
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, size, offset)
            
            history = []
            for row in rows:
                history.append({
                    "id": row['id'],
                    "time_range": row['time_range'],
                    "content": row['content'],
                    "alarm_count": row['alarm_count'],
                    "instrument_count": row['instrument_count'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return {"total": total, "data": history, "page": page, "size": size}
    except Exception as e:
        # 如果表不存在，返回空数据
        if "does not exist" in str(e):
            return {"total": 0, "data": [], "page": page, "size": size}
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/ai/history")
async def clear_ai_history(db = Depends(get_db), redis = Depends(get_redis)):
    """清空所有 AI 总结历史记录"""
    try:
        async with db.acquire() as conn:
            result = await conn.execute("DELETE FROM ai_summary_logs")
            # 获取删除的行数
            deleted_count = int(result.split()[-1]) if result else 0
        
        # 同时清除 Redis 中的缓存
        await redis.delete("ai:summary:content")
        await redis.delete("ai:summary:timestamp")
        await redis.delete("ai:summary:range")
        
        return {"message": f"已清空 {deleted_count} 条 AI 总结记录", "deleted_count": deleted_count}
    except Exception as e:
        if "does not exist" in str(e):
            return {"message": "AI 总结记录表不存在", "deleted_count": 0}
        raise HTTPException(status_code=500, detail=str(e))

# Email Config
@router.get("/alarm/email", response_model=EmailConfig)
async def get_email_config(redis = Depends(get_redis)):
    data = await redis.get("config:email")
    if data:
        return EmailConfig(**json.loads(data))
    return EmailConfig()

@router.put("/alarm/email")
async def update_email_config(config: EmailConfig, redis = Depends(get_redis)):
    await redis.set("config:email", config.json())
    return {"message": "Email config updated"}

# Webhook Config
@router.get("/alarm/webhook", response_model=WebhookConfig)
async def get_webhook_config(redis = Depends(get_redis)):
    data = await redis.get("config:webhook")
    if data:
        return WebhookConfig(**json.loads(data))
    return WebhookConfig()

@router.put("/alarm/webhook")
async def update_webhook_config(config: WebhookConfig, redis = Depends(get_redis)):
    await redis.set("config:webhook", config.json())
    return {"message": "Webhook config updated"}

# SMS Config
@router.get("/alarm/sms", response_model=SMSConfig)
async def get_sms_config(redis = Depends(get_redis)):
    data = await redis.get("config:sms")
    if data:
        return SMSConfig(**json.loads(data))
    return SMSConfig()

@router.put("/alarm/sms")
async def update_sms_config(config: SMSConfig, redis = Depends(get_redis)):
    await redis.set("config:sms", config.json())
    return {"message": "SMS config updated"}

# Alarm General Config (消抖时间和报警时段)
@router.get("/alarm/general", response_model=AlarmGeneralConfig)
async def get_alarm_general_config(redis = Depends(get_redis)):
    data = await redis.get("config:alarm_general")
    if data:
        return AlarmGeneralConfig(**json.loads(data))
    return AlarmGeneralConfig()

@router.put("/alarm/general")
async def update_alarm_general_config(config: AlarmGeneralConfig, redis = Depends(get_redis)):
    await redis.set("config:alarm_general", config.json())
    
    # 立即更新所有现有消抖键的 TTL，使新配置立即生效
    new_ttl = config.debounce_minutes * 60  # 转换为秒
    debounce_keys = await redis.keys("alarm:debounce:*")
    updated_count = 0
    for key in debounce_keys:
        # 只更新仍然存在的键（设置新的 TTL）
        current_ttl = await redis.ttl(key)
        if current_ttl > 0:
            # 如果新 TTL 小于当前剩余时间，立即更新
            # 如果新 TTL 大于当前剩余时间，也更新（延长消抖时间）
            await redis.expire(key, new_ttl)
            updated_count += 1
    
    return {"message": f"报警通用配置已保存，{updated_count} 个设备的消抖时间已同步更新"}

# Dashboard Config
@router.get("/dashboard", response_model=DashboardConfig)
async def get_dashboard_config(redis = Depends(get_redis)):
    data = await redis.get("config:dashboard")
    if data:
        return DashboardConfig(**json.loads(data))
    return DashboardConfig()

@router.put("/dashboard")
async def update_dashboard_config(config: DashboardConfig, redis = Depends(get_redis)):
    await redis.set("config:dashboard", config.json())
    return {"message": "Dashboard config updated"}

# Screen Layout Config
@router.get("/screen-layout", response_model=ScreenLayoutConfig)
async def get_screen_layout_config(redis = Depends(get_redis)):
    data = await redis.get("config:screen_layout")
    if data:
        return ScreenLayoutConfig(**json.loads(data))
    return ScreenLayoutConfig()

@router.put("/screen-layout")
async def update_screen_layout_config(config: ScreenLayoutConfig, redis = Depends(get_redis)):
    await redis.set("config:screen_layout", config.json())
    return {"message": "Screen layout config updated"}


@router.post("/dashboard/background")
async def upload_background(file: UploadFile = File(...)):
    # Save to static folder
    upload_dir = "/app/static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, "background.png")
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return {"message": "Background uploaded", "path": "/static/uploads/background.png"}

# Archive Config (Multi-Cloud: Cloudflare R2, Tencent COS, Alibaba OSS)
def _migrate_archive_config(config_dict: dict) -> dict:
    """
    迁移旧版配置到新版统一格式
    旧格式使用 r2_* 前缀，新格式使用统一字段名
    """
    # 迁移旧版 r2_endpoint 到 account_id
    if config_dict.get("r2_endpoint") and not config_dict.get("r2_account_id"):
        endpoint = config_dict.get("r2_endpoint", "")
        import re
        match = re.search(r'https?://([a-zA-Z0-9]+)\.r2\.cloudflarestorage\.com', endpoint)
        if match:
            config_dict["r2_account_id"] = match.group(1)
        config_dict.pop("r2_endpoint", None)
    
    # 迁移 r2_* 字段到新版统一字段
    if config_dict.get("r2_account_id") and not config_dict.get("account_id"):
        config_dict["provider"] = "cloudflare"
        config_dict["account_id"] = config_dict.get("r2_account_id", "")
        config_dict["bucket"] = config_dict.get("r2_bucket", "")
        config_dict["access_key"] = config_dict.get("r2_access_key", "")
        config_dict["secret_key"] = config_dict.get("r2_secret_key", "")
        config_dict["cloud_retention_days"] = config_dict.get("r2_retention_days", 30)
    
    return config_dict

def _build_storage_endpoint(config: dict) -> tuple:
    """
    根据提供商构建存储 endpoint URL
    返回: (endpoint_url, bucket_name, signature_version)
    """
    provider = config.get("provider", "cloudflare")
    bucket = config.get("bucket", "")
    
    if provider == "cloudflare":
        account_id = config.get("account_id", "").strip()
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        return (endpoint, bucket, "s3v4")
    
    elif provider == "tencent":
        region = config.get("region", "ap-guangzhou").strip()
        # 腾讯云 COS S3 兼容端点
        endpoint = f"https://cos.{region}.myqcloud.com"
        return (endpoint, bucket, "s3v4")
    
    elif provider == "alibaba":
        region = config.get("region", "oss-cn-hangzhou").strip()
        # 阿里云 OSS S3 兼容端点
        endpoint = f"https://{region}.aliyuncs.com"
        return (endpoint, bucket, "s3v4")
    
    else:
        raise ValueError(f"不支持的存储提供商: {provider}")

@router.get("/archive", response_model=ArchiveConfig)
async def get_archive_config(redis = Depends(get_redis)):
    """获取数据归档配置（自动迁移旧版配置）"""
    data = await redis.get("config:archive")
    if data:
        config_dict = json.loads(data)
        
        # 检查并迁移旧格式
        if config_dict.get("r2_endpoint") and not config_dict.get("r2_account_id"):
            config_dict = _migrate_archive_config(config_dict)
            # 保存迁移后的配置
            await redis.set("config:archive", json.dumps(config_dict))
        
        return ArchiveConfig(**config_dict)
    return ArchiveConfig()

@router.put("/archive")
async def update_archive_config(config: ArchiveConfig, redis = Depends(get_redis)):
    """更新数据归档配置"""
    await redis.set("config:archive", config.json())
    return {"message": "归档配置已保存"}

@router.post("/archive/test")
async def test_archive_connection(redis = Depends(get_redis)):
    """测试云存储连接 (支持 Cloudflare R2, 腾讯云 COS, 阿里云 OSS)"""
    import logging
    import subprocess
    import asyncio
    
    logger = logging.getLogger(__name__)
    
    data = await redis.get("config:archive")
    if not data:
        raise HTTPException(status_code=400, detail="归档配置未设置")
    
    config = json.loads(data)
    
    # 迁移旧配置
    if config.get("r2_endpoint") or (config.get("r2_account_id") and not config.get("account_id")):
        config = _migrate_archive_config(config)
        await redis.set("config:archive", json.dumps(config))
    
    provider = config.get("provider", "cloudflare")
    provider_names = {"cloudflare": "Cloudflare R2", "tencent": "腾讯云 COS", "alibaba": "阿里云 OSS"}
    provider_name = provider_names.get(provider, provider)
    
    # 验证必填字段
    if not config.get("bucket"):
        raise HTTPException(status_code=400, detail="请填写 Bucket 名称")
    
    if not config.get("access_key") or not config.get("secret_key"):
        raise HTTPException(status_code=400, detail="请填写访问密钥")
    
    if provider == "cloudflare" and not config.get("account_id"):
        raise HTTPException(status_code=400, detail="请填写 Cloudflare 账户 ID")
    
    if provider in ["tencent", "alibaba"] and not config.get("region"):
        raise HTTPException(status_code=400, detail="请选择存储区域")
    
    try:
        endpoint, bucket, sig_version = _build_storage_endpoint(config)
        access_key = config['access_key']
        secret_key = config['secret_key']
        
        def test_connection():
            import boto3
            from botocore.config import Config as BotoConfig
            import os
            
            os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
            
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=BotoConfig(
                    signature_version=sig_version,
                    connect_timeout=10,
                    read_timeout=15,
                    retries={'max_attempts': 3, 'mode': 'standard'}
                ),
                region_name='auto' if provider == 'cloudflare' else config.get('region', 'auto')
            )
            
            s3.head_bucket(Bucket=bucket)
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, test_connection)
        
        return {"message": f"{provider_name} 连接成功！Bucket: {bucket}"}
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"Storage test failed ({provider}): {e}")
        
        if '403' in error_str or 'Forbidden' in error_str or 'AccessDenied' in error_str:
            raise HTTPException(status_code=400, detail="访问被拒绝，请检查 Access Key 和 Secret Key")
        elif '404' in error_str or 'NoSuchBucket' in error_str:
            raise HTTPException(status_code=400, detail=f"Bucket '{config.get('bucket')}' 不存在")
        elif 'SSL' in error_str or 'ssl' in error_str:
            raise HTTPException(status_code=400, detail=f"SSL 连接失败，请检查网络配置: {error_str[:100]}")
        else:
            raise HTTPException(status_code=500, detail=f"连接测试失败: {error_str[:200]}")

@router.get("/archive/stats")
async def get_storage_stats(redis = Depends(get_redis), db = Depends(get_db)):
    """获取存储空间统计"""
    stats = {
        "local_db": {"size_bytes": 0, "size_human": "0 B", "row_count": 0},
        "r2": {"size_bytes": 0, "size_human": "0 B", "file_count": 0, "message": ""}
    }
    
    def format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    # 获取本地数据库大小
    try:
        async with db.acquire() as conn:
            # Use pg_database_size for total database size (more accurate)
            size_result = await conn.fetchrow("""
                SELECT pg_database_size(current_database()) as size,
                       (SELECT COUNT(*) FROM sensor_data) as count
            """)
            if size_result:
                stats["local_db"]["size_bytes"] = size_result['size'] or 0
                stats["local_db"]["size_human"] = format_size(size_result['size'] or 0)
                stats["local_db"]["row_count"] = size_result['count'] or 0
    except Exception as e:
        stats["local_db"]["error"] = str(e)
    
    # 获取云端存储大小
    config_str = await redis.get("config:archive")
    if config_str:
        config = json.loads(config_str)
        # 迁移旧配置
        if config.get("r2_account_id") and not config.get("account_id"):
            config = _migrate_archive_config(config)
        
        # 检查是否配置了云存储
        has_config = config.get("account_id") or config.get("region")
        if has_config and config.get("bucket") and config.get("access_key"):
            try:
                import asyncio
                import boto3
                from botocore.config import Config as BotoConfig
                
                def get_cloud_stats():
                    endpoint, bucket, sig_version = _build_storage_endpoint(config)
                    provider = config.get("provider", "cloudflare")
                    
                    s3 = boto3.client(
                        's3',
                        endpoint_url=endpoint,
                        aws_access_key_id=config['access_key'],
                        aws_secret_access_key=config['secret_key'],
                        config=BotoConfig(
                            signature_version=sig_version,
                            retries={'max_attempts': 3, 'mode': 'standard'}
                        ),
                        region_name='auto' if provider == 'cloudflare' else config.get('region', 'auto')
                    )
                    
                    total_size = 0
                    file_count = 0
                    
                    paginator = s3.get_paginator('list_objects_v2')
                    for page in paginator.paginate(Bucket=bucket, Prefix='archive/'):
                        for obj in page.get('Contents', []):
                            total_size += obj.get('Size', 0)
                            file_count += 1
                    
                    return total_size, file_count
                
                loop = asyncio.get_event_loop()
                total_size, file_count = await loop.run_in_executor(None, get_cloud_stats)
                
                stats["r2"]["size_bytes"] = total_size
                stats["r2"]["size_human"] = format_size(total_size)
                stats["r2"]["file_count"] = file_count
            except ImportError:
                stats["r2"]["message"] = "boto3 未安装"
            except Exception as e:
                stats["r2"]["error"] = str(e)
        else:
            stats["r2"]["message"] = "云存储未配置"
    else:
        stats["r2"]["message"] = "归档配置未设置"
    
    return stats

@router.get("/archive/files")
async def list_archive_files(redis = Depends(get_redis)):
    """列出云存储中的所有归档文件"""
    import asyncio
    
    config_str = await redis.get("config:archive")
    if not config_str:
        return {"files": [], "message": "归档配置未设置"}
    
    config = json.loads(config_str)
    
    # 迁移旧配置
    if config.get("r2_account_id") and not config.get("account_id"):
        config = _migrate_archive_config(config)
    
    # 检查是否配置了云存储
    has_config = config.get("account_id") or config.get("region")
    if not has_config or not config.get("bucket"):
        return {"files": [], "message": "云存储未配置"}
    
    try:
        import boto3
        from botocore.config import Config as BotoConfig
        
        def get_files_list():
            endpoint, bucket, sig_version = _build_storage_endpoint(config)
            provider = config.get("provider", "cloudflare")
            
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=config['access_key'],
                aws_secret_access_key=config['secret_key'],
                config=BotoConfig(
                    signature_version=sig_version,
                    retries={'max_attempts': 3, 'mode': 'standard'}
                ),
                region_name='auto' if provider == 'cloudflare' else config.get('region', 'auto')
            )
            
            files = []
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix='archive/'):
                for obj in page.get('Contents', []):
                    key = obj.get('Key', '')
                    size = obj.get('Size', 0)
                    last_modified = obj.get('LastModified')
                    
                    # 生成预签名下载 URL (有效期 1 小时)
                    download_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=3600
                    )
                    
                    # 格式化文件大小
                    if size < 1024:
                        size_human = f"{size} B"
                    elif size < 1024 * 1024:
                        size_human = f"{size / 1024:.2f} KB"
                    elif size < 1024 * 1024 * 1024:
                        size_human = f"{size / (1024 * 1024):.2f} MB"
                    else:
                        size_human = f"{size / (1024 * 1024 * 1024):.2f} GB"
                    
                    files.append({
                        "key": key,
                        "name": key.split('/')[-1],
                        "size": size,
                        "size_human": size_human,
                        "last_modified": last_modified.isoformat() if last_modified else None,
                        "download_url": download_url
                    })
            
            # 按时间倒序排列
            files.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
            return files
        
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, get_files_list)
        
        return {"files": files, "count": len(files)}
        
    except ImportError:
        return {"files": [], "message": "boto3 未安装"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DeleteFileRequest(BaseModel):
    key: str  # R2 文件路径，如 "archive/2025/12/sensor_data_20251220.csv.gz"

@router.post("/archive/delete")
async def delete_archive_file(request: DeleteFileRequest, redis = Depends(get_redis)):
    """删除 R2 中的单个归档文件"""
    import asyncio
    
    config_str = await redis.get("config:archive")
    if not config_str:
        raise HTTPException(status_code=400, detail="归档配置未设置")
    
    config = json.loads(config_str)
    
    # 迁移旧配置
    if config.get("r2_account_id") and not config.get("account_id"):
        config = _migrate_archive_config(config)
    
    # 检查是否配置了云存储
    has_config = config.get("account_id") or config.get("region")
    if not has_config or not config.get("bucket"):
        raise HTTPException(status_code=400, detail="云存储未配置")
    
    file_key = request.key
    if not file_key or not file_key.startswith("archive/"):
        raise HTTPException(status_code=400, detail="无效的文件路径")
    
    try:
        import boto3
        from botocore.config import Config as BotoConfig
        
        def delete_file():
            endpoint, bucket, sig_version = _build_storage_endpoint(config)
            provider = config.get("provider", "cloudflare")
            
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=config['access_key'],
                aws_secret_access_key=config['secret_key'],
                config=BotoConfig(
                    signature_version=sig_version,
                    retries={'max_attempts': 3, 'mode': 'standard'}
                ),
                region_name='auto' if provider == 'cloudflare' else config.get('region', 'auto')
            )
            
            # 先检查文件是否存在
            try:
                s3.head_object(Bucket=bucket, Key=file_key)
            except:
                raise Exception(f"文件不存在: {file_key}")
            
            # 删除文件
            s3.delete_object(Bucket=bucket, Key=file_key)
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, delete_file)
        
        file_name = file_key.split('/')[-1]
        return {
            "status": "success",
            "message": f"已删除文件: {file_name}",
            "deleted_key": file_key
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="boto3 未安装")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/archive/backup")
async def manual_backup(redis = Depends(get_redis), db = Depends(get_db)):
    """手动触发备份今日数据到云存储"""
    import asyncio
    from datetime import datetime, date
    
    config_str = await redis.get("config:archive")
    if not config_str:
        raise HTTPException(status_code=400, detail="归档配置未设置")
    
    config = json.loads(config_str)
    
    # 迁移旧配置
    if config.get("r2_endpoint") or (config.get("r2_account_id") and not config.get("account_id")):
        config = _migrate_archive_config(config)
        await redis.set("config:archive", json.dumps(config))
    
    # 检查是否配置了云存储
    has_config = config.get("account_id") or config.get("region")
    if not has_config or not config.get("bucket"):
        raise HTTPException(status_code=400, detail="请先配置云存储")
    
    try:
        import boto3
        from botocore.config import Config as BotoConfig
        import gzip
        import csv
        import io
        
        # 构建 endpoint URL
        endpoint, bucket, sig_version = _build_storage_endpoint(config)
        provider = config.get("provider", "cloudflare")
        
        # 获取今日数据
        today = date.today()
        
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, sn, v_raw, ppm, temp, humi, bat, rssi, seq
                FROM sensor_data
                WHERE time::date = $1
                ORDER BY time
            """, today)
        
        if not rows:
            return {"status": "empty", "message": f"今日 ({today}) 暂无数据可备份"}
        
        # 生成 CSV
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["time", "sn", "v_raw", "ppm", "temp", "humi", "bat", "rssi", "seq"])
        
        for row in rows:
            writer.writerow([
                row['time'].isoformat(),
                row['sn'],
                row['v_raw'],
                row['ppm'],
                row['temp'],
                row['humi'],
                row['bat'],
                row['rssi'],
                row['seq']
            ])
        
        # 压缩
        csv_content = csv_buffer.getvalue().encode('utf-8')
        gzipped = gzip.compress(csv_content)
        
        # 上传到云存储
        file_name = f"sensor_data_{today.strftime('%Y%m%d')}_manual.csv.gz"
        cloud_path = f"archive/{today.year}/{today.month:02d}/{file_name}"
        
        def upload_to_cloud():
            s3 = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=config['access_key'],
                aws_secret_access_key=config['secret_key'],
                config=BotoConfig(
                    signature_version=sig_version,
                    retries={'max_attempts': 3, 'mode': 'standard'}
                ),
                region_name='auto' if provider == 'cloudflare' else config.get('region', 'auto')
            )
            s3.put_object(
                Bucket=bucket,
                Key=cloud_path,
                Body=gzipped,
                ContentType='application/gzip'
            )
            return True
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, upload_to_cloud)
        
        # 格式化文件大小
        size = len(gzipped)
        if size < 1024:
            size_human = f"{size} B"
        elif size < 1024 * 1024:
            size_human = f"{size / 1024:.2f} KB"
        else:
            size_human = f"{size / (1024 * 1024):.2f} MB"
        
        provider_names = {"cloudflare": "R2", "tencent": "COS", "alibaba": "OSS"}
        provider_name = provider_names.get(provider, "云存储")
        
        return {
            "status": "success",
            "message": f"备份到 {provider_name} 成功！{len(rows)} 条记录，{size_human}",
            "row_count": len(rows),
            "file_size": size,
            "file_path": cloud_path
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="boto3 未安装")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {str(e)}")

class CleanupRequest(BaseModel):
    days: int  # 保留最近多少天的数据

@router.post("/archive/cleanup")
async def manual_cleanup(request: CleanupRequest, db = Depends(get_db)):
    """手动清理本地数据库中超过指定天数的数据"""
    from datetime import datetime, timedelta
    
    days = request.days
    if days < 1:
        raise HTTPException(status_code=400, detail="保留天数必须大于 0")
    
    # 允许的清理选项：3天、7天、30天
    allowed_days = [1, 3, 7, 30]
    if days not in allowed_days:
        raise HTTPException(status_code=400, detail=f"保留天数必须是以下之一: {allowed_days}")
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        async with db.acquire() as conn:
            # 先统计要删除的行数
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM sensor_data
                WHERE time::date < $1
            """, cutoff_date)
            
            if count == 0:
                return {
                    "status": "empty",
                    "message": f"没有 {days} 天前的数据需要清理",
                    "deleted_rows": 0,
                    "cutoff_date": str(cutoff_date)
                }
            
            # 删除旧数据
            await conn.execute("""
                DELETE FROM sensor_data
                WHERE time::date < $1
            """, cutoff_date)
            
            return {
                "status": "success",
                "message": f"成功清理 {count} 条 {days} 天前的数据",
                "deleted_rows": count,
                "cutoff_date": str(cutoff_date)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

# Test notification
@router.post("/alarm/test")
async def test_notification(channel: str, redis = Depends(get_redis)):
    """Send a test notification to verify configuration"""
    import aiohttp
    import time
    import hashlib
    import hmac
    import base64
    import urllib.parse
    
    if channel == "webhook":
        data = await redis.get("config:webhook")
        if not data:
            raise HTTPException(status_code=400, detail="Webhook not configured")
        
        config = json.loads(data)
        if not config.get("enabled") or not config.get("url"):
            raise HTTPException(status_code=400, detail="Webhook not enabled or URL not set")
        
        url = config["url"]
        secret = config.get("secret", "")
        platform = config.get("platform", "custom")
        
        # 自动检测平台 (如果是 custom 但 URL 包含特定域名)
        if platform == "custom":
            if "dingtalk.com" in url or "oapi.dingtalk" in url:
                platform = "dingtalk"
            elif "feishu.cn" in url or "open.feishu" in url:
                platform = "feishu"
            elif "qyapi.weixin.qq.com" in url:
                platform = "wecom"
        
        # 构建测试消息 (包含中文逗号作为常用关键词)
        test_msg = f"🔔 MCS-IoT 测试通知，这是一条测试消息，用于验证 Webhook 配置是否正确。\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 根据平台构建不同的 payload
        if platform == "dingtalk":
            # 钉钉签名
            if secret:
                timestamp = str(round(time.time() * 1000))
                sign_str = f"{timestamp}\n{secret}"
                sign = base64.b64encode(
                    hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()
                ).decode()
                url = f"{url}&timestamp={timestamp}&sign={urllib.parse.quote_plus(sign)}"
            
            payload = {
                "msgtype": "text",
                "text": {"content": test_msg}
            }
        elif platform == "feishu":
            payload = {
                "msg_type": "text",
                "content": {"text": test_msg}
            }
        elif platform == "wecom":
            payload = {
                "msgtype": "text",
                "text": {"content": test_msg}
            }
        else:
            payload = {
                "type": "test",
                "message": test_msg,
                "timestamp": int(time.time())
            }
        
        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    result = await resp.text()
                    if resp.status == 200:
                        # 检查钉钉/飞书等返回的 errcode
                        try:
                            result_json = json.loads(result)
                            errcode = result_json.get("errcode", result_json.get("code", 0))
                            errmsg = result_json.get("errmsg", result_json.get("msg", ""))
                            if errcode != 0:
                                raise HTTPException(status_code=400, detail=f"Webhook 返回错误: {errmsg}")
                        except json.JSONDecodeError:
                            pass  # 非 JSON 响应，忽略
                        return {"message": "Webhook 测试消息发送成功", "response": result}
                    else:
                        raise HTTPException(status_code=resp.status, detail=f"Webhook 返回错误: {result}")
        except aiohttp.ClientError as e:
            raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")
    
    elif channel == "email":
        data = await redis.get("config:email")
        if not data:
            raise HTTPException(status_code=400, detail="Email not configured")
        
        config = json.loads(data)
        if not config.get("enabled"):
            raise HTTPException(status_code=400, detail="Email not enabled")
        
        # 简化版邮件发送测试
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            msg = MIMEText(f"MCS-IoT 测试邮件\n\n这是一条测试邮件，用于验证邮件配置是否正确。\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            msg['Subject'] = '🔔 MCS-IoT 测试通知'
            msg['From'] = config['sender']
            msg['To'] = ', '.join(config['receivers'])
            
            with smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port']) as server:
                server.login(config['sender'], config['password'])
                server.sendmail(config['sender'], config['receivers'], msg.as_string())
            
            
            return {"message": "邮件测试发送成功"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail="Unknown channel")

# Site Config
@router.get("/site", response_model=SiteConfig)
async def get_site_config(redis = Depends(get_redis)):
    data = await redis.get("config:site")
    if data:
        return json.loads(data)
    return SiteConfig()

@router.put("/site")
async def update_site_config(config: SiteConfig, redis = Depends(get_redis)):
    await redis.set("config:site", json.dumps(config.dict()))
    return config

# Screen Background Config
@router.get("/screen_bg", response_model=ScreenBgConfig)
async def get_screen_bg_config(redis = Depends(get_redis)):
    data = await redis.get("config:screen_bg")
    if data:
        return json.loads(data)
    return ScreenBgConfig()

@router.put("/screen_bg")
async def update_screen_bg_config(config: ScreenBgConfig, redis = Depends(get_redis)):
    await redis.set("config:screen_bg", json.dumps(config.dict()))
    return config

# Weather Config
@router.get("/weather", response_model=WeatherConfig)
async def get_weather_config(redis = Depends(get_redis)):
    data = await redis.get("config:weather")
    if data:
        return json.loads(data)
    return WeatherConfig()

@router.put("/weather")
async def update_weather_config(config: WeatherConfig, redis = Depends(get_redis)):
    await redis.set("config:weather", json.dumps(config.dict()))
    return config

# =============================================================================
# License API
# =============================================================================

@router.get("/license")
async def get_license_status():
    """获取授权状态和设备编码"""
    try:
        from .license import get_license_manager
        mgr = get_license_manager()
        return await mgr.get_license_status()
    except Exception as e:
        # 如果 license manager 未初始化，返回基本信息
        from .license import LicenseManager
        import os
        import hashlib
        
        # Generate device ID using same logic as LicenseManager
        machine_id = None
        
        # Priority 1: Mounted host machine-id
        if os.path.exists("/app/host_machine_id"):
            with open("/app/host_machine_id", "r") as f:
                machine_id = f.read().strip()
        # Priority 2: System machine-id
        elif os.path.exists("/etc/machine-id"):
            with open("/etc/machine-id", "r") as f:
                machine_id = f.read().strip()
        # Priority 3: Fallback
        else:
            import socket
            import uuid
            hostname = socket.gethostname()
            mac = hex(uuid.getnode())[2:]
            machine_id = f"{hostname}:{mac}"
        
        hash_bytes = hashlib.sha256(machine_id.encode()).digest()
        hex_str = hash_bytes.hex()[:12].upper()
        device_id = f"MCS-{hex_str[:4]}-{hex_str[4:8]}-{hex_str[8:12]}"
        
        return {
            "device_id": device_id,
            "status": "unlicensed",
            "error": str(e),
            "contact": "zinanzhi@gmail.com",
            "features": []
        }

@router.post("/license/verify")
async def verify_license():
    """手动触发授权验证"""
    try:
        from .license import get_license_manager
        mgr = get_license_manager()
        return await mgr.verify_license()
    except Exception as e:
        return {"valid": False, "error": str(e)}
