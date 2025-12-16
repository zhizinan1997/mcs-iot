import logging
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

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
                    "bat_limit": float(config.get("bat_limit", 20)),  # 低电量阈值
                    "name": config.get("name", sn)
                }
        except Exception as e:
            logger.error(f"Redis error getting device config: {e}")
        
        # Default thresholds
        return {"high_limit": 1000.0, "low_limit": None, "bat_limit": 20.0, "name": sn}

    async def get_notification_config(self):
        """Get notification channel configs from Redis"""
        try:
            email_cfg = await self.redis.get("config:email")
            webhook_cfg = await self.redis.get("config:webhook")
            sms_cfg = await self.redis.get("config:sms")
            time_cfg = await self.redis.get("config:alarm_time")
            
            return {
                "email": json.loads(email_cfg) if email_cfg else {"enabled": False},
                "webhook": json.loads(webhook_cfg) if webhook_cfg else {"enabled": False},
                "sms": json.loads(sms_cfg) if sms_cfg else {"enabled": False},
                "time_restriction": json.loads(time_cfg) if time_cfg else {"enabled": False}
            }
        except Exception as e:
            logger.error(f"Error loading notification config: {e}")
            return {
                "email": {"enabled": False}, 
                "webhook": {"enabled": False}, 
                "sms": {"enabled": False},
                "time_restriction": {"enabled": False}
            }

    def is_in_notification_window(self, time_config: dict) -> bool:
        """
        检查当前时间是否在通知时段内
        time_config: {
            "enabled": true,
            "days": [1,2,3,4,5],  # 周一到周五
            "start": "08:00",
            "end": "18:00"
        }
        """
        if not time_config.get("enabled"):
            return True  # 未启用时段限制，允许所有时间
        
        now = datetime.now()
        weekday = now.weekday() + 1  # Python weekday 0=周一, 需要+1匹配配置
        
        allowed_days = time_config.get("days", [1, 2, 3, 4, 5])
        if weekday not in allowed_days:
            return False
        
        current_time = now.strftime("%H:%M")
        start_time = time_config.get("start", "00:00")
        end_time = time_config.get("end", "23:59")
        
        return start_time <= current_time <= end_time

    async def check_and_alert(self, sn: str, ppm: float, temp: float, bat: int = 100):
        """Check thresholds and trigger alerts if needed"""
        config = await self.get_device_config(sn)
        high_limit = config["high_limit"]
        low_limit = config["low_limit"]
        bat_limit = config.get("bat_limit", 20)
        device_name = config["name"]

        # 检查高浓度报警
        if ppm > high_limit:
            await self.process_alarm(sn, "HIGH", ppm, high_limit, 
                f"设备 {device_name} 浓度超标: {ppm:.2f} ppm (阈值: {high_limit:.2f})")
        
        # 检查低浓度报警 (如果配置了)
        elif low_limit is not None and ppm < low_limit:
            await self.process_alarm(sn, "LOW", ppm, low_limit,
                f"设备 {device_name} 浓度过低: {ppm:.2f} ppm (阈值: {low_limit:.2f})")
        
        # 检查低电量报警
        if bat < bat_limit:
            await self.process_alarm(sn, "LOW_BAT", bat, bat_limit,
                f"设备 {device_name} 电量过低: {bat}% (阈值: {bat_limit}%)")

    async def process_alarm(self, sn: str, alarm_type: str, value: float, 
                           threshold: float, message: str = ""):
        """
        统一的报警处理接口
        - 防抖检查
        - 时段检查
        - 记录日志
        - 发送通知
        """
        # 防抖检查
        debounce_key = f"alarm:debounce:{sn}:{alarm_type}"
        if await self.redis.exists(debounce_key):
            logger.debug(f"[{sn}] Alarm {alarm_type} debounced")
            return False

        # 设置防抖键
        await self.redis.setex(debounce_key, self.debounce_ttl, "1")

        # 获取通知配置
        notify_config = await self.get_notification_config()
        time_config = notify_config.get("time_restriction", {})
        
        # 时段检查
        in_window = self.is_in_notification_window(time_config)
        
        # 记录到数据库 (始终记录)
        await self.log_alarm(sn, alarm_type, value, threshold, notified=in_window)

        # 只在工作时段发送通知
        if in_window:
            config = await self.get_device_config(sn)
            device_name = config["name"]
            if not message:
                message = f"设备 {device_name} ({sn}) 触发 {alarm_type} 报警"
            await self.send_notifications(sn, device_name, alarm_type, value, threshold, message)
            logger.warning(f"[{sn}] ALARM {alarm_type}: value={value}, threshold={threshold}")
        else:
            logger.info(f"[{sn}] ALARM {alarm_type} recorded but not notified (outside window)")

        return True

    async def log_alarm(self, sn: str, alarm_type: str, value: float, 
                       threshold: float, notified: bool = True):
        """Log alarm to database"""
        try:
            if self.storage.pool:
                async with self.storage.pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO alarm_logs (sn, type, value, threshold, notified) 
                           VALUES ($1, $2, $3, $4, $5)""",
                        sn, alarm_type, value, threshold, notified
                    )
        except Exception as e:
            logger.error(f"Failed to log alarm: {e}")

    async def send_notifications(self, sn: str, device_name: str, alarm_type: str, 
                                value: float, threshold: float, message: str = ""):
        """Send notifications via all enabled channels"""
        config = await self.get_notification_config()
        
        if not message:
            message = f"⚠️ 报警通知\n设备: {device_name} ({sn})\n类型: {alarm_type}\n数值: {value:.2f}\n阈值: {threshold:.2f}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Email notification
        if config["email"].get("enabled"):
            await self.send_email(config["email"], sn, alarm_type, message)

        # Webhook notification (DingTalk, Feishu, etc.)
        if config["webhook"].get("enabled"):
            await self.send_webhook(config["webhook"], sn, alarm_type, value, threshold, device_name)

        # SMS notification
        if config["sms"].get("enabled"):
            await self.send_sms(config["sms"], sn, alarm_type, value)

    async def send_email(self, config: dict, sn: str, alarm_type: str, message: str):
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

    def _generate_dingtalk_sign(self, secret: str) -> tuple:
        """生成钉钉机器人签名"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    async def send_webhook(self, config: dict, sn: str, alarm_type: str, 
                          value: float, threshold: float, device_name: str):
        """Send webhook notification (DingTalk/Feishu compatible with signing)"""
        try:
            url = config.get("url")
            if not url:
                return

            platform = config.get("platform", "dingtalk")  # dingtalk, feishu, wecom, custom
            secret = config.get("secret", "")
            at_mobiles = config.get("at_mobiles", [])

            # 构建消息内容
            content = f"⚠️ MCS-IoT 报警\n设备: {device_name} ({sn})\n类型: {alarm_type}\n数值: {value:.2f}\n阈值: {threshold:.2f}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # 钉钉格式
            if platform == "dingtalk":
                # 添加签名
                if secret:
                    timestamp, sign = self._generate_dingtalk_sign(secret)
                    url = f"{url}&timestamp={timestamp}&sign={sign}"
                
                payload = {
                    "msgtype": "text",
                    "text": {"content": content},
                    "at": {
                        "atMobiles": at_mobiles,
                        "isAtAll": False
                    }
                }
            
            # 飞书格式
            elif platform == "feishu":
                payload = {
                    "msg_type": "text",
                    "content": {"text": content}
                }
            
            # 企业微信格式
            elif platform == "wecom":
                payload = {
                    "msgtype": "text",
                    "text": {"content": content}
                }
            
            # 自定义格式
            else:
                payload = {
                    "msgtype": "text",
                    "text": {"content": content}
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info(f"Webhook notification sent via {platform}")
                    else:
                        logger.warning(f"Webhook returned {resp.status}")
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")

    async def send_sms(self, config: dict, sn: str, alarm_type: str, value: float):
        """Send SMS notification via Aliyun SMS"""
        try:
            access_key_id = config.get("access_key_id")
            access_key_secret = config.get("access_key_secret")
            sign_name = config.get("sign_name")
            template_code = config.get("template_code")
            phone_numbers = config.get("phone_numbers", [])

            if not all([access_key_id, access_key_secret, sign_name, template_code, phone_numbers]):
                logger.debug("SMS config incomplete, skipping")
                return

            # 阿里云 SMS API 调用
            # 注意：需要安装 aliyun-python-sdk-core 和 aliyun-python-sdk-dysmsapi
            try:
                from aliyunsdkcore.client import AcsClient
                from aliyunsdkdysmsapi.request.v20170525.SendSmsRequest import SendSmsRequest
                
                client = AcsClient(access_key_id, access_key_secret, 'cn-hangzhou')
                request = SendSmsRequest()
                request.set_PhoneNumbers(','.join(phone_numbers))
                request.set_SignName(sign_name)
                request.set_TemplateCode(template_code)
                request.set_TemplateParam(json.dumps({
                    "device": sn,
                    "type": alarm_type,
                    "value": f"{value:.2f}"
                }))
                
                response = client.do_action_with_exception(request)
                logger.info(f"SMS sent: {response}")
            except ImportError:
                logger.warning("Aliyun SMS SDK not installed, skipping SMS")
            
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
