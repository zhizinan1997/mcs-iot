import paho.mqtt.client as mqtt
import json
import time
import random
import ssl

# Configuration
BROKER = "localhost"
PORT = 1883 # Use 1883 for dev simulator (eats less CPU than SSL)
TOPIC_PREFIX = "mcs"
DEVICE_ID = "A001"
USERNAME = "device_A001"
PASSWORD = "device123"

def generate_payload(seq):
    # Simulate partial random data
    v_raw = 2000 + random.uniform(-100, 100) # Baseline 2000mV
    temp = 25.0 + random.uniform(-2, 2)
    humi = 45.0 + random.uniform(-5, 5)
    
    payload = {
        "ts": int(time.time()),
        "seq": seq,
        "v_raw": round(v_raw, 2),
        "temp": round(temp, 1),
        "humi": round(humi, 1),
        "bat": 98,
        "rssi": -75,
        "net": "4G",
        "err": 0
    }
    return payload

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to Broker as {DEVICE_ID}!")
    else:
        print(f"Failed to connect, return code {rc}")

def main():
    client = mqtt.Client(client_id=DEVICE_ID)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect

    print(f"Connecting to {BROKER}:{PORT}...")
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Connection Error: {e}")
        print("Ensure Mosquitto container is running (even if other containers failed).")
        return

    seq = 0
    try:
        while True:
            data = generate_payload(seq)
            topic = f"{TOPIC_PREFIX}/{DEVICE_ID}/up"
            
            msg = json.dumps(data)
            info = client.publish(topic, msg)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[TX] {topic} : {msg}")
            else:
                print(f"[ERR] Publish failed: {info.rc}")
            
            seq = (seq + 1) % 65536
            time.sleep(10) # 10s interval
            
    except KeyboardInterrupt:
        print("Stopping simulator...")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
