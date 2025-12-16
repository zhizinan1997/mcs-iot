import paho.mqtt.client as mqtt
import os
import time
import logging
import json

# Configure Logging
logger = logging.getLogger(__name__)

# 默认配置 (首次启动或配置文件不存在时使用)
DEFAULT_MQTT_USER = "worker"
DEFAULT_MQTT_PASS = "worker123"

# 配置文件路径 (与 backend 共享的挂载目录)
CONFIG_FILE = "/app/mosquitto/mqtt_config.json"

def load_mqtt_config_from_file():
    """从配置文件加载 MQTT 账号密码"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                user = config.get("worker_user", DEFAULT_MQTT_USER)
                passwd = config.get("worker_pass", DEFAULT_MQTT_PASS)
                logger.info(f"Loaded MQTT config from file: user={user}")
                return user, passwd
        except Exception as e:
            logger.warning(f"Failed to load MQTT config from file: {e}")
    
    logger.info(f"Using default MQTT credentials: user={DEFAULT_MQTT_USER}")
    return DEFAULT_MQTT_USER, DEFAULT_MQTT_PASS


class MQTTClient:
    def __init__(self, on_message_callback, redis_client=None):
        self.broker = os.getenv("MQTT_HOST", "mosquitto")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        
        # 从配置文件读取凭据
        self.username, self.password = load_mqtt_config_from_file()
        
        self.client_id = f"worker_{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.username_pw_set(self.username, self.password)
        
        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = on_message_callback
        
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {self.broker}:{self.port}")
            self.connected = True
            # Subscribe to all device uplinks
            client.subscribe("mcs/+/up")
            client.subscribe("mcs/+/status")
            logger.info("Subscribed to mcs/+/up & mcs/+/status")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT (rc={rc})")
        self.connected = False

    def start(self):
        logger.info(f"Connecting to {self.broker}:{self.port}...")
        try:
            # Keep trying until successful (container dependency race condition)
            while True:
                try:
                    self.client.connect(self.broker, self.port, 60)
                    break
                except Exception as e:
                    logger.warning(f"Connection failed ({e}), retrying in 5s...")
                    time.sleep(5)
            
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Fatal MQTT Error: {e}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic, payload):
        if not self.connected:
            logger.warning("Attempted to publish while disconnected")
            return
        self.client.publish(topic, payload)
