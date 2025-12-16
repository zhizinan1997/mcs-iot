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
            raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
