"""
License Authorization Management
- Device ID generation
- License verification via CF Worker
- Feature access control
"""
import os
import hashlib
import socket
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# License server URL (Cloudflare Worker)
LICENSE_SERVER = os.getenv("LICENSE_SERVER", "https://lic.zhizinan.cc")

# Grace period in days when verification fails (72 hours)
GRACE_PERIOD_DAYS = 3

# Features that require license
LICENSED_FEATURES = ["mqtt_external", "ai", "r2_archive", "notifications"]

# Device limit for unlicensed usage
UNLICENSED_DEVICE_LIMIT = 10

# Expected integrity hash (computed at build time)
# This is the SHA-256 hash of critical source files
EXPECTED_INTEGRITY_HASH = "cad58e7969ac3cba"


def compute_integrity_hash() -> str:
    """
    Compute SHA-256 hash of critical source files to detect tampering.
    Excludes the EXPECTED_INTEGRITY_HASH line itself to avoid circular dependency.
    Returns first 16 characters of hex digest.
    """
    import os
    
    # Critical files to hash (relative to src/)
    critical_files = [
        "license.py",
        "config.py", 
        "main.py"
    ]
    
    hasher = hashlib.sha256()
    src_dir = os.path.dirname(__file__)
    
    for filename in sorted(critical_files):
        filepath = os.path.join(src_dir, filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    content = f.read()
                    
                    # For license.py, exclude the EXPECTED_INTEGRITY_HASH line
                    if filename == 'license.py':
                        lines = content.decode('utf-8', errors='ignore').split('\n')
                        filtered_lines = [
                            line for line in lines 
                            if 'EXPECTED_INTEGRITY_HASH' not in line
                        ]
                        content = '\n'.join(filtered_lines).encode('utf-8')
                    
                    hasher.update(content)
        except Exception as e:
            logger.warning(f"Failed to read {filename} for integrity check: {e}")
    
    return hasher.hexdigest()[:16]


def check_integrity() -> Dict[str, Any]:
    """
    Check if source code has been tampered with.
    Returns dict with tampered flag and hash details.
    """
    actual_hash = compute_integrity_hash()
    expected_hash = EXPECTED_INTEGRITY_HASH
    
    # During development, expected hash might not be set yet
    if expected_hash == "PLACEHOLDER_HASH_WILL_BE_COMPUTED":
        logger.warning("Integrity check disabled: expected hash not set")
        return {
            "tampered": False,
            "expected": expected_hash,
            "actual": actual_hash,
            "warning": "Integrity check not configured"
        }
    
    tampered = (actual_hash != expected_hash)
    
    if tampered:
        logger.error(f"CODE TAMPERING DETECTED! Expected: {expected_hash}, Actual: {actual_hash}")
    
    return {
        "tampered": tampered,
        "expected": expected_hash,
        "actual": actual_hash
    }


class LicenseManager:
    """Manages license verification and feature access control"""
    
    def __init__(self, redis):
        self.redis = redis
        self._device_id = None
    
    def get_device_id(self) -> str:
        """
        Generate unique device ID based on HOST machine hardware.
        
        Priority:
        1. /app/host_machine_id (mounted from host's /etc/machine-id)
        2. /etc/machine-id (if running directly on host)
        3. Fallback to container-based identifiers (not recommended)
        
        This ensures:
        - Same server: ID never changes (restart, redeploy)
        - Different server: ID always changes (even with data migration)
        """
        if self._device_id:
            return self._device_id
        
        try:
            machine_id = None
            
            # Priority 1: Mounted host machine-id (Docker production)
            host_machine_id_path = "/app/host_machine_id"
            if os.path.exists(host_machine_id_path):
                with open(host_machine_id_path, "r") as f:
                    machine_id = f.read().strip()
                logger.info(f"Using host machine-id from mounted file")
            
            # Priority 2: System machine-id (direct host or some containers)
            if not machine_id and os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    machine_id = f.read().strip()
                logger.info(f"Using system /etc/machine-id")
            
            # Priority 3: Fallback - use container identifiers (less stable)
            if not machine_id:
                logger.warning("No host machine-id found, using fallback (may change on redeploy)")
                hostname = socket.gethostname()
                mac = ""
                try:
                    import uuid
                    mac = hex(uuid.getnode())[2:]
                except:
                    pass
                machine_id = f"{hostname}:{mac}"
            
            # Hash the machine_id to create consistent format
            hash_bytes = hashlib.sha256(machine_id.encode()).digest()
            
            # Format as MCS-XXXX-XXXX-XXXX
            hex_str = hash_bytes.hex()[:12].upper()
            self._device_id = f"MCS-{hex_str[:4]}-{hex_str[4:8]}-{hex_str[8:12]}"
            
            logger.info(f"Generated device ID: {self._device_id}")
            return self._device_id
            
        except Exception as e:
            logger.error(f"Failed to generate device ID: {e}")
            return "MCS-0000-0000-0000"
    
    async def verify_license(self) -> Dict[str, Any]:
        """Verify license with remote server"""
        device_id = self.get_device_id()
        
        # Perform integrity check
        integrity = check_integrity()
        integrity_hash = integrity["actual"]
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{LICENSE_SERVER}/verify",
                    json={
                        "device_id": device_id,
                        "integrity_hash": integrity_hash
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache successful verification
                    await self.redis.set("license:valid", "1", ex=86400 * 2)
                    await self.redis.set("license:last_check", datetime.now().isoformat())
                    
                    # Cache tampering status from server
                    tampered = data.get("tampered", False)
                    await self.redis.set("license:tampered", "1" if tampered else "0")
                    
                    if data.get("valid"):
                        await self.redis.set("license:status", "active")
                        await self.redis.set("license:expires", data.get("expires_at", ""))
                        await self.redis.set("license:customer", data.get("customer", ""))
                        await self.redis.delete("license:grace_start")
                        
                        return {
                            "valid": True,
                            "status": "active",
                            "expires_at": data.get("expires_at"),
                            "customer": data.get("customer"),
                            "features": data.get("features", LICENSED_FEATURES),
                            "tampered": tampered
                        }
                    else:
                        return await self._start_grace_period(data.get("error", "授权验证失败"))
                else:
                    return await self._start_grace_period("服务器返回错误")
                    
        except Exception as e:
            logger.error(f"License verification failed: {e}")
            return await self._check_grace_period()
    
    async def _start_grace_period(self, reason: str) -> Dict[str, Any]:
        """Start or continue grace period"""
        grace_start = await self.redis.get("license:grace_start")
        
        if not grace_start:
            grace_start = datetime.now().isoformat()
            await self.redis.set("license:grace_start", grace_start)
        
        await self.redis.set("license:status", "grace")
        await self.redis.set("license:error", reason)
        
        grace_end = datetime.fromisoformat(grace_start) + timedelta(days=GRACE_PERIOD_DAYS)
        remaining_seconds = (grace_end - datetime.now()).total_seconds()
        remaining_hours = int(remaining_seconds / 3600)
        
        if remaining_seconds > 0:
            return {
                "valid": True,  # Still valid during grace period
                "status": "grace",
                "grace_remaining_hours": remaining_hours,
                "grace_remaining_days": max(0, remaining_hours // 24),
                "error": reason,
                "features": []  # Limited features during grace
            }
        else:
            await self.redis.set("license:status", "expired")
            return {
                "valid": False,
                "status": "expired",
                "error": f"宽限期已过 ({reason})",
                "features": []
            }
    
    async def _check_grace_period(self) -> Dict[str, Any]:
        """Check if we're in grace period when server unreachable"""
        grace_start = await self.redis.get("license:grace_start")
        
        if grace_start:
            grace_end = datetime.fromisoformat(grace_start) + timedelta(days=GRACE_PERIOD_DAYS)
            remaining_seconds = (grace_end - datetime.now()).total_seconds()
            remaining_hours = int(remaining_seconds / 3600)
            
            if remaining_seconds > 0:
                return {
                    "valid": True,
                    "status": "grace",
                    "grace_remaining_hours": remaining_hours,
                    "grace_remaining_days": max(0, remaining_hours // 24),
                    "error": "无法连接授权服务器",
                    "features": []
                }
        
        # Check if we had a valid license recently
        last_valid = await self.redis.get("license:valid")
        if last_valid:
            # Start grace period now
            return await self._start_grace_period("无法连接授权服务器")
        
        return {
            "valid": False,
            "status": "unlicensed",
            "error": "未授权",
            "features": []
        }
    
    async def get_license_status(self) -> Dict[str, Any]:
        """Get current license status from cache"""
        device_id = self.get_device_id()
        status = await self.redis.get("license:status") or "unlicensed"
        expires = await self.redis.get("license:expires") or ""
        customer = await self.redis.get("license:customer") or ""
        last_check = await self.redis.get("license:last_check") or ""
        error = await self.redis.get("license:error") or ""
        grace_start = await self.redis.get("license:grace_start")
        tampered_str = await self.redis.get("license:tampered") or "0"
        
        result = {
            "device_id": device_id,
            "status": status,
            "expires_at": expires,
            "customer": customer,
            "last_check": last_check,
            "contact": "zinanzhi@gmail.com",
            "tampered": (tampered_str == "1")
        }
        
        if status == "grace" and grace_start:
            grace_end = datetime.fromisoformat(grace_start) + timedelta(days=GRACE_PERIOD_DAYS)
            result["grace_remaining_days"] = max(0, (grace_end - datetime.now()).days)
            result["error"] = error
        elif status == "unlicensed" or status == "expired":
            result["error"] = error or "未授权"
        
        # Determine allowed features
        if status == "active":
            result["features"] = LICENSED_FEATURES
        else:
            result["features"] = []
        
        return result
    
    async def is_feature_allowed(self, feature: str) -> bool:
        """Check if a specific feature is allowed"""
        status = await self.redis.get("license:status")
        
        if status == "active":
            return True
        
        # During grace period, allow basic features only
        if status == "grace":
            return feature not in LICENSED_FEATURES
        
        # Unlicensed - no premium features
        return feature not in LICENSED_FEATURES
    
    async def get_device_limit(self) -> int:
        """Get maximum allowed devices"""
        status = await self.redis.get("license:status")
        
        if status == "active":
            return 999999  # Unlimited for licensed users
        
        return UNLICENSED_DEVICE_LIMIT
    
    async def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed for MQTT connections"""
        status = await self.redis.get("license:status")
        
        # Licensed users can receive from any IP
        if status == "active":
            return True
        
        # Check if IP is internal network
        return self._is_internal_ip(ip)
    
    def _is_internal_ip(self, ip: str) -> bool:
        """Check if IP is from internal network"""
        if not ip:
            return True
        
        # Localhost
        if ip in ("127.0.0.1", "localhost", "::1"):
            return True
        
        # Docker internal
        if ip.startswith("172.") or ip.startswith("192.168.") or ip.startswith("10."):
            return True
        
        # Allow Docker container names
        if not any(c.isdigit() for c in ip.split('.')[0] if '.' in ip):
            return True
        
        return False


# Global license manager instance (initialized in main.py)
license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Get the global license manager instance"""
    global license_manager
    if license_manager is None:
        raise RuntimeError("License manager not initialized")
    return license_manager


async def init_license_manager(redis) -> LicenseManager:
    """Initialize the global license manager"""
    global license_manager
    license_manager = LicenseManager(redis)
    
    # Perform initial verification
    logger.info(f"Device ID: {license_manager.get_device_id()}")
    result = await license_manager.verify_license()
    logger.info(f"License status: {result.get('status')}")
    
    return license_manager
