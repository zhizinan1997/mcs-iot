import logging
import hashlib
import os
import json
import time
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LicenseGuard:
    def __init__(self, redis):
        self.redis = redis
        self.license_file = "/app/license.key"
        self.host_id_file = "/app/host_id"
        self.verify_url = os.getenv("LICENSE_VERIFY_URL", "https://lic.zhizinan.cc/verify")
        self.grace_period_hours = 72
        self.is_valid = False
        self.last_check = None
        self.status = "UNKNOWN"  # VALID, GRACE, EXPIRED, UNKNOWN

    def get_host_id(self):
        """Read host machine ID (mounted from /etc/machine-id)"""
        try:
            if os.path.exists(self.host_id_file):
                with open(self.host_id_file, 'r') as f:
                    return f.read().strip()
            # Fallback for Mac (no machine-id)
            import uuid
            return str(uuid.getnode())
        except Exception as e:
            logger.error(f"Failed to get host ID: {e}")
            return "unknown"

    def get_license_key(self):
        """Read license key from file"""
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read license: {e}")
        return None

    def generate_fingerprint(self):
        """Generate unique fingerprint from host_id + license_key"""
        host_id = self.get_host_id()
        license_key = self.get_license_key()
        if not license_key:
            return None
        combined = f"{host_id}:{license_key}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def verify_online(self):
        """Verify license with remote server"""
        fingerprint = self.generate_fingerprint()
        if not fingerprint:
            logger.error("No license key found")
            return False

        try:
            payload = {
                "fingerprint": fingerprint,
                "timestamp": int(time.time()),
                "version": "1.0.0"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.verify_url, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("valid"):
                            await self.update_token(data.get("expires_at"))
                            self.status = "VALID"
                            self.is_valid = True
                            logger.info("License verified online: VALID")
                            return True
                    logger.warning(f"Online verification failed: {resp.status}")
        except Exception as e:
            logger.warning(f"Online verification error (will use grace period): {e}")

        return False

    async def update_token(self, expires_at=None):
        """Update local token cache after successful verification"""
        token_data = {
            "verified_at": int(time.time()),
            "expires_at": expires_at or int(time.time()) + 86400,  # 24h default
            "fingerprint": self.generate_fingerprint()
        }
        await self.redis.set("license:token", json.dumps(token_data))

    async def check_local_token(self):
        """Check if local token is still within grace period"""
        try:
            token_json = await self.redis.get("license:token")
            if not token_json:
                return False

            token = json.loads(token_json)
            verified_at = token.get("verified_at", 0)
            grace_deadline = verified_at + (self.grace_period_hours * 3600)

            current_time = int(time.time())
            
            if current_time < grace_deadline:
                hours_left = (grace_deadline - current_time) / 3600
                if hours_left < 24:
                    self.status = "GRACE"
                    logger.warning(f"License in GRACE period: {hours_left:.1f}h remaining")
                else:
                    self.status = "VALID"
                self.is_valid = True
                return True
            else:
                self.status = "EXPIRED"
                self.is_valid = False
                logger.error("License EXPIRED: Grace period exceeded")
                return False

        except Exception as e:
            logger.error(f"Token check failed: {e}")
            return False

    async def verify(self):
        """Main verification routine - called daily at 03:00 or on startup"""
        logger.info("Starting license verification...")

        # 1. Try online verification
        if await self.verify_online():
            self.last_check = datetime.now()
            return True

        # 2. Fallback to local token (grace period)
        if await self.check_local_token():
            self.last_check = datetime.now()
            return True

        # 3. No valid license
        self.is_valid = False
        self.status = "EXPIRED"
        return False

    async def startup_check(self):
        """Check license on worker startup"""
        # For development, allow bypass
        if os.getenv("DEV_MODE") == "true":
            logger.warning("DEV_MODE: License check bypassed")
            self.is_valid = True
            self.status = "DEV"
            return True

        # First try local token (fast path)
        if await self.check_local_token():
            logger.info(f"License status: {self.status}")
            return True

        # No local token, try online
        return await self.verify()

    def is_licensed(self):
        """Quick check if system is licensed"""
        return self.is_valid

    def get_status(self):
        """Get license status for API/Dashboard"""
        return {
            "valid": self.is_valid,
            "status": self.status,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }
    
    def is_internal_ip(self, ip: str) -> bool:
        """Check if IP is from internal network"""
        if not ip:
            return True
        
        # Localhost
        if ip in ("127.0.0.1", "localhost", "::1"):
            return True
        
        # Docker internal networks
        if ip.startswith("172.") or ip.startswith("192.168.") or ip.startswith("10."):
            return True
        
        # Allow Docker container names (no dots or non-numeric first segment)
        if '.' not in ip:
            return True
        
        return False
    
    def is_mqtt_allowed(self, client_ip: str = None) -> bool:
        """
        Check if MQTT data should be processed.
        - If licensed: allow all
        - If not licensed: only allow internal IPs
        """
        if self.is_valid:
            return True
        
        # Not licensed - only allow internal network
        if client_ip and not self.is_internal_ip(client_ip):
            logger.warning(f"Unlicensed: Rejected external MQTT from {client_ip}")
            return False
        
        return True

