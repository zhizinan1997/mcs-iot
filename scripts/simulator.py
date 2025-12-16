#!/usr/bin/env python3
"""
MCS-IoT 多设备模拟器
模拟多个传感器设备同时发送数据
"""
import paho.mqtt.client as mqtt
import json
import time
import random
import threading
import argparse

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC_PREFIX = "mcs"

# 设备配置模板
DEVICE_CONFIGS = [
    {"prefix": "GAS", "count": 10, "base_v": 500, "type": "甲烷"},      # 甲烷传感器
    {"prefix": "CO2", "count": 5, "base_v": 800, "type": "二氧化碳"},   # CO2 传感器
    {"prefix": "NH3", "count": 5, "base_v": 300, "type": "氨气"},       # 氨气传感器
]


class DeviceSimulator:
    def __init__(self, device_id, base_voltage=500, device_type="气体"):
        self.device_id = device_id
        self.base_voltage = base_voltage
        self.device_type = device_type
        self.seq = 0
        self.bat = random.randint(60, 100)
        self.client = None
        self.running = False
        
    def generate_payload(self):
        # 模拟数据波动
        v_raw = self.base_voltage + random.uniform(-50, 100)
        temp = 25.0 + random.uniform(-3, 3)
        humi = 50.0 + random.uniform(-10, 10)
        
        # 电量缓慢下降
        if random.random() < 0.1:
            self.bat = max(10, self.bat - 1)
        
        payload = {
            "ts": int(time.time()),
            "seq": self.seq,
            "v_raw": round(v_raw, 2),
            "temp": round(temp, 1),
            "humi": round(humi, 1),
            "bat": self.bat,
            "rssi": random.randint(-85, -60),
            "net": "4G",
            "err": 0
        }
        self.seq = (self.seq + 1) % 65536
        return payload
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ [{self.device_id}] 已连接 ({self.device_type})")
        else:
            print(f"✗ [{self.device_id}] 连接失败: {rc}")
    
    def start(self, interval=10):
        self.client = mqtt.Client(client_id=self.device_id)
        # 使用通用设备账号 (已在 Mosquitto 中配置)
        self.client.username_pw_set("device_A001", "device123")
        self.client.on_connect = self.on_connect
        
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            self.running = True
        except Exception as e:
            print(f"✗ [{self.device_id}] 连接错误: {e}")
            return
        
        while self.running:
            data = self.generate_payload()
            topic = f"{TOPIC_PREFIX}/{self.device_id}/up"
            msg = json.dumps(data)
            self.client.publish(topic, msg)
            time.sleep(interval + random.uniform(-1, 1))  # 加入随机延迟
    
    def stop(self):
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="MCS-IoT 多设备模拟器")
    parser.add_argument("-n", "--count", type=int, default=20, help="设备总数 (默认: 20)")
    parser.add_argument("-i", "--interval", type=int, default=10, help="发送间隔秒数 (默认: 10)")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  MCS-IoT 多设备模拟器")
    print(f"  设备数量: {args.count}")
    print(f"  发送间隔: {args.interval}秒")
    print("=" * 50)
    
    devices = []
    threads = []
    
    # 生成设备列表
    device_id = 1
    for config in DEVICE_CONFIGS:
        count = min(config["count"], args.count - len(devices))
        if count <= 0:
            break
        for i in range(count):
            dev_id = f"{config['prefix']}{device_id:03d}"
            simulator = DeviceSimulator(
                device_id=dev_id,
                base_voltage=config["base_v"] + random.uniform(-50, 50),
                device_type=config["type"]
            )
            devices.append(simulator)
            device_id += 1
    
    # 如果设备数不够，补充通用设备
    while len(devices) < args.count:
        dev_id = f"DEV{device_id:03d}"
        simulator = DeviceSimulator(
            device_id=dev_id,
            base_voltage=random.uniform(300, 800),
            device_type="通用"
        )
        devices.append(simulator)
        device_id += 1
    
    print(f"\n启动 {len(devices)} 个设备模拟器...\n")
    
    # 启动所有设备线程
    for dev in devices:
        t = threading.Thread(target=dev.start, args=(args.interval,), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.1)  # 错开启动时间
    
    print(f"\n所有设备已启动! 按 Ctrl+C 停止...\n")
    
    # 定期打印状态
    try:
        while True:
            time.sleep(30)
            online = sum(1 for d in devices if d.running)
            print(f"[状态] 在线设备: {online}/{len(devices)}, "
                  f"总消息数: {sum(d.seq for d in devices)}")
    except KeyboardInterrupt:
        print("\n\n正在停止所有设备...")
        for dev in devices:
            dev.stop()
        print("已停止所有设备模拟器")


if __name__ == "__main__":
    main()
