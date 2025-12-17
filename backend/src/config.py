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

class DashboardConfig(BaseModel):
    title: str = "MCS-IoT Dashboard"
    refresh_rate: int = 5
    background_image: Optional[str] = None

class ArchiveConfig(BaseModel):
    """数据归档配置 (Cloudflare R2)"""
    enabled: bool = False
    retention_days: int = 3
    r2_endpoint: str = ""
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

async def get_redis():
    from .main import redis_pool
    return redis_pool

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

# Archive Config (R2)
@router.get("/archive", response_model=ArchiveConfig)
async def get_archive_config(redis = Depends(get_redis)):
    """获取数据归档配置"""
    data = await redis.get("config:archive")
    if data:
        return ArchiveConfig(**json.loads(data))
    return ArchiveConfig()

@router.put("/archive")
async def update_archive_config(config: ArchiveConfig, redis = Depends(get_redis)):
    """更新数据归档配置"""
    await redis.set("config:archive", config.json())
    return {"message": "归档配置已保存"}

@router.post("/archive/test")
async def test_archive_connection(redis = Depends(get_redis)):
    """测试 R2 连接"""
    import logging
    import subprocess
    import asyncio
    
    logger = logging.getLogger(__name__)
    
    data = await redis.get("config:archive")
    if not data:
        raise HTTPException(status_code=400, detail="归档配置未设置")
    
    config = json.loads(data)
    
    if not config.get("r2_endpoint") or not config.get("r2_bucket"):
        raise HTTPException(status_code=400, detail="请填写完整的 R2 配置")
    
    if not config.get("r2_access_key") or not config.get("r2_secret_key"):
        raise HTTPException(status_code=400, detail="请填写 R2 访问密钥")
    
    try:
        endpoint = config['r2_endpoint'].rstrip('/')
        bucket = config['r2_bucket']
        access_key = config['r2_access_key']
        secret_key = config['r2_secret_key']
        
        # 使用 boto3 在同步模式下测试（在线程池中运行）
        def test_connection():
            import boto3
            from botocore.config import Config as BotoConfig
            from botocore.exceptions import ClientError
            import os
            
            # 设置环境变量禁用 SSL 警告
            os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
            
            # 创建 session 并设置自定义 HTTP 选项
            session = boto3.Session()
            
            s3 = session.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=BotoConfig(
                    signature_version='s3v4',
                    connect_timeout=10,
                    read_timeout=15,
                    retries={'max_attempts': 1}
                ),
                verify=False
            )
            
            # 测试连接
            s3.head_bucket(Bucket=bucket)
            return True
        
        # 在线程池中运行同步代码
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, test_connection)
        
        return {"message": f"R2 连接成功！Bucket: {bucket}"}
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"R2 test failed: {e}")
        
        # 解析常见错误
        if 'SSL' in error_str or 'ssl' in error_str:
            # SSL 仍然失败，尝试使用 curl 作为后备方案
            try:
                test_url = f"{endpoint}/{bucket}"
                result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-I', '-k', test_url],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                status_code = result.stdout.strip()
                if status_code in ['200', '403', '404']:
                    if status_code == '200':
                        return {"message": f"R2 连接成功！Bucket: {bucket}"}
                    elif status_code == '403':
                        raise HTTPException(status_code=400, detail="访问被拒绝，请检查 Access Key 和 Secret Key（注意：curl 测试无签名）")
                    else:
                        raise HTTPException(status_code=400, detail=f"Bucket '{bucket}' 不存在")
                else:
                    raise HTTPException(status_code=400, detail=f"R2 Endpoint 可达，但返回状态码 {status_code}")
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=400, detail="连接超时，请检查 Endpoint URL")
            except FileNotFoundError:
                raise HTTPException(status_code=500, detail=f"SSL 错误且 curl 不可用: {error_str}")
        elif '403' in error_str or 'Forbidden' in error_str or 'AccessDenied' in error_str:
            raise HTTPException(status_code=400, detail="访问被拒绝，请检查 Access Key 和 Secret Key")
        elif '404' in error_str or 'NoSuchBucket' in error_str:
            raise HTTPException(status_code=400, detail=f"Bucket '{bucket}' 不存在")
        else:
            raise HTTPException(status_code=500, detail=f"连接测试失败: {error_str}")

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
