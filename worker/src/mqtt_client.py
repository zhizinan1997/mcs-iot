import paho.mqtt.client as mqtt
import os
import time
import logging

# Configure Logging
logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, on_message_callback):
        self.broker = os.getenv("MQTT_HOST", "mosquitto")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        # Internal worker uses specific credentials if needed, or admin for simplicity in dev
        # In prod, use "worker" user
        self.username = "worker"
        self.password = "qiuqiu"  # 与 admin 界面 MQTT 配置一致
        
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
