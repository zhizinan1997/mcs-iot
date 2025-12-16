import logging
import json
import time
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

class AlarmCenter:
    def __init__(self, redis, storage):
        self.redis = redis
        self.storage = storage
        self.debounce_ttl = 600  # 10 minutes debounce

    async def get_device_config(self, sn):
        """Get device alarm thresholds from Redis or DB"""
        cache_key = f"device:{sn}"
        try:
            config = await self.redis.hgetall(cache_key)
            if config:
                return {
                    "high_limit": float(config.get("high_limit", 1000)),
                    "low_limit": float(config.get("low_limit")) if config.get("low_limit") else None,
                    "name": config.get("name", sn)
                }
        except Exception as e:
            logger.error(f"Redis error getting device config: {e}")
        
        # Default thresholds
        return {"high_limit": 1000.0, "low_limit": None, "name": sn}

    async def get_notification_config(self):
        """Get notification channel configs from Redis"""
        try:
            email_cfg = await self.redis.get("config:email")
            webhook_cfg = await self.redis.get("config:webhook")
            sms_cfg = await self.redis.get("config:sms")
            
            return {
                "email": json.loads(email_cfg) if email_cfg else {"enabled": False},
                "webhook": json.loads(webhook_cfg) if webhook_cfg else {"enabled": False},
                "sms": json.loads(sms_cfg) if sms_cfg else {"enabled": False}
            }
        except Exception as e:
            logger.error(f"Error loading notification config: {e}")
            return {"email": {"enabled": False}, "webhook": {"enabled": False}, "sms": {"enabled": False}}

    async def check_and_alert(self, sn, ppm, temp):
        """Check thresholds and trigger alerts if needed"""
        config = await self.get_device_config(sn)
        high_limit = config["high_limit"]
        low_limit = config["low_limit"]
        device_name = config["name"]

        alarm_type = None
        threshold = None

        # Check HIGH alarm
        if ppm > high_limit:
            alarm_type = "HIGH"
            threshold = high_limit
        # Check LOW alarm (if configured)
        elif low_limit is not None and ppm < low_limit:
            alarm_type = "LOW"
            threshold = low_limit

        if alarm_type:
            # Debounce check
            debounce_key = f"alarm:debounce:{sn}:{alarm_type}"
            if await self.redis.exists(debounce_key):
                logger.info(f"[{sn}] Alarm {alarm_type} debounced (within {self.debounce_ttl}s window)")
                return False

            # Set debounce key
            await self.redis.setex(debounce_key, self.debounce_ttl, "1")

            # Log alarm to database
            await self.log_alarm(sn, alarm_type, ppm, threshold)

            # Trigger notifications
            await self.send_notifications(sn, device_name, alarm_type, ppm, threshold)

            logger.warning(f"[{sn}] ALARM {alarm_type}: ppm={ppm} > threshold={threshold}")
            return True

        return False

    async def log_alarm(self, sn, alarm_type, value, threshold):
        """Log alarm to database"""
        try:
            if self.storage.pool:
                async with self.storage.pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO alarm_logs (sn, type, value, threshold) 
                           VALUES ($1, $2, $3, $4)""",
                        sn, alarm_type, value, threshold
                    )
        except Exception as e:
            logger.error(f"Failed to log alarm: {e}")

    async def send_notifications(self, sn, device_name, alarm_type, ppm, threshold):
        """Send notifications via all enabled channels"""
        config = await self.get_notification_config()
        
        message = f"⚠️ 报警通知\n设备: {device_name} ({sn})\n类型: {alarm_type}\n浓度: {ppm:.2f} ppm\n阈值: {threshold:.2f} ppm\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Email notification
        if config["email"].get("enabled"):
            await self.send_email(config["email"], sn, alarm_type, message)

        # Webhook notification (DingTalk, Feishu, etc.)
        if config["webhook"].get("enabled"):
            await self.send_webhook(config["webhook"], sn, alarm_type, ppm, threshold, device_name)

        # SMS notification (placeholder)
        if config["sms"].get("enabled"):
            await self.send_sms(config["sms"], sn, alarm_type, message)

    async def send_email(self, config, sn, alarm_type, message):
        """Send email notification"""
        try:
            smtp_host = config.get("smtp_host", "smtp.qq.com")
            smtp_port = config.get("smtp_port", 465)
            sender = config.get("sender")
            password = config.get("password")
            receivers = config.get("receivers", [])

            if not sender or not password or not receivers:
                logger.warning("Email config incomplete, skipping")
                return

            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = ", ".join(receivers)
            msg["Subject"] = f"[MCS-IoT] {alarm_type} 报警 - {sn}"
            msg.attach(MIMEText(message, "plain", "utf-8"))

            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(sender, password)
                server.sendmail(sender, receivers, msg.as_string())

            logger.info(f"Email sent to {receivers}")
        except Exception as e:
            logger.error(f"Email send failed: {e}")

    async def send_webhook(self, config, sn, alarm_type, ppm, threshold, device_name):
        """Send webhook notification (DingTalk/Feishu compatible)"""
        try:
            url = config.get("url")
            if not url:
                return

            # DingTalk/Feishu compatible payload
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"⚠️ MCS-IoT 报警\n设备: {device_name} ({sn})\n类型: {alarm_type}\n浓度: {ppm:.2f} ppm\n阈值: {threshold:.2f} ppm\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info(f"Webhook notification sent")
                    else:
                        logger.warning(f"Webhook returned {resp.status}")
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")

    async def send_sms(self, config, sn, alarm_type, message):
        """Send SMS notification (Aliyun SMS placeholder)"""
        # TODO: Implement Aliyun SMS integration
        logger.info(f"SMS notification placeholder for {sn}")
        pass

    async def check_device_offline(self, sn):
        """Check if device is offline and trigger alarm"""
        online_key = f"online:{sn}"
        if not await self.redis.exists(online_key):
            debounce_key = f"alarm:debounce:{sn}:OFFLINE"
            if not await self.redis.exists(debounce_key):
                await self.redis.setex(debounce_key, self.debounce_ttl, "1")
                await self.log_alarm(sn, "OFFLINE", 0, 0)
                config = await self.get_device_config(sn)
                await self.send_notifications(sn, config["name"], "OFFLINE", 0, 0)
                logger.warning(f"[{sn}] OFFLINE alarm triggered")
                return True
        return False
