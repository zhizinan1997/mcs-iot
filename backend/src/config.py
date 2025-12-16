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
    # TODO: Implement actual test notification
    return {"message": f"Test notification sent to {channel}"}
