"""
MCS-IoT Load Testing Script
Simulates multiple devices connecting and sending data concurrently
"""

import asyncio
import json
import random
import time
import argparse
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC_PREFIX = "mcs"


def generate_payload(seq):
    """Generate simulated sensor payload"""
    v_raw = 2000 + random.uniform(-200, 200)
    temp = 25.0 + random.uniform(-5, 5)
    humi = 45.0 + random.uniform(-10, 10)
    
    # Occasionally generate high values to trigger alarms
    if random.random() < 0.05:  # 5% chance
        v_raw = v_raw * 1.5
    
    return {
        "ts": int(time.time()),
        "seq": seq,
        "v_raw": round(v_raw, 2),
        "temp": round(temp, 1),
        "humi": round(humi, 1),
        "bat": random.randint(70, 100),
        "rssi": random.randint(-90, -60),
        "net": "4G",
        "err": 0
    }


class DeviceSimulator:
    def __init__(self, device_id, username, password):
        self.device_id = device_id
        self.username = username
        self.password = password
        self.client = None
        self.connected = False
        self.messages_sent = 0
        self.seq = 0

    def connect(self):
        self.client = mqtt.Client(client_id=self.device_id, protocol=mqtt.MQTTv311)
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[{self.device_id}] Connect failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
        else:
            print(f"[{self.device_id}] Connect failed: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def send_data(self):
        if not self.connected:
            return False
        
        payload = generate_payload(self.seq)
        topic = f"{TOPIC_PREFIX}/{self.device_id}/up"
        
        result = self.client.publish(topic, json.dumps(payload))
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.messages_sent += 1
            self.seq = (self.seq + 1) % 65536
            return True
        return False

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


def run_load_test(num_devices, duration_seconds, interval_seconds):
    """Run load test with specified number of devices"""
    print("=" * 60)
    print(f"MCS-IoT Load Test")
    print(f"Devices: {num_devices}, Duration: {duration_seconds}s, Interval: {interval_seconds}s")
    print("=" * 60)
    
    # Create device simulators
    devices = []
    for i in range(num_devices):
        device_id = f"TEST{i:04d}"
        # Use admin credentials for testing (in prod, each device has unique creds)
        sim = DeviceSimulator(device_id, "admin", "admin123")
        devices.append(sim)
    
    # Connect all devices
    print(f"\nConnecting {num_devices} devices...")
    connected_count = 0
    for sim in devices:
        if sim.connect():
            connected_count += 1
    
    # Wait for connections
    time.sleep(2)
    
    connected_count = sum(1 for d in devices if d.connected)
    print(f"Connected: {connected_count}/{num_devices}")
    
    if connected_count == 0:
        print("No devices connected. Exiting.")
        return
    
    # Run test
    print(f"\nStarting load test for {duration_seconds} seconds...")
    start_time = time.time()
    total_messages = 0
    
    while time.time() - start_time < duration_seconds:
        cycle_start = time.time()
        
        for sim in devices:
            if sim.connected:
                if sim.send_data():
                    total_messages += 1
        
        # Wait for next cycle
        elapsed = time.time() - cycle_start
        sleep_time = max(0, interval_seconds - elapsed)
        time.sleep(sleep_time)
        
        # Progress update
        elapsed_total = time.time() - start_time
        rate = total_messages / elapsed_total if elapsed_total > 0 else 0
        print(f"\rMessages: {total_messages}, Rate: {rate:.1f} msg/s", end="", flush=True)
    
    print("\n")
    
    # Disconnect
    print("Disconnecting devices...")
    for sim in devices:
        sim.disconnect()
    
    # Summary
    duration = time.time() - start_time
    print("\n" + "=" * 60)
    print("Load Test Summary")
    print("=" * 60)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Devices: {num_devices}")
    print(f"Total Messages: {total_messages}")
    print(f"Average Rate: {total_messages / duration:.1f} messages/second")
    print(f"Per Device Rate: {total_messages / duration / num_devices:.2f} messages/second")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCS-IoT Load Testing Tool")
    parser.add_argument("-n", "--devices", type=int, default=10, help="Number of simulated devices")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("-i", "--interval", type=float, default=1.0, help="Message interval in seconds")
    
    args = parser.parse_args()
    
    run_load_test(args.devices, args.duration, args.interval)
