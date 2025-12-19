#!/usr/bin/env python3
"""
MCS-IoT 演示数据生成器
创建演示用仪表和设备，并持续发送模拟数据

使用方法:
  python3 demo_generator.py --duration 60   # 运行60分钟
  python3 demo_generator.py --init-only     # 仅创建设备，不发送数据
"""
import paho.mqtt.client as mqtt
import json
import time
import random
import threading
import argparse
import os
import requests

# ============================================================================
# 配置
# ============================================================================

BROKER = "localhost"
MQTT_PORT = 1883
API_BASE = "http://localhost:8000/api"
TOPIC_PREFIX = "mcs"

# 配置文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "mqtt_config.json")

# 默认 MQTT 账号密码
DEFAULT_MQTT_USER = "device"
DEFAULT_MQTT_PASS = "device123"

# ============================================================================
# 仪表和传感器配置
# ============================================================================

INSTRUMENTS = [
    {"name": "总经理办公室", "color": "#409eff", "pos_x": 20, "pos_y": 25},
    {"name": "员工办公室", "color": "#67c23a", "pos_x": 80, "pos_y": 25},
    {"name": "公共走廊", "color": "#e6a23c", "pos_x": 20, "pos_y": 75},
    {"name": "创新实验室", "color": "#f56c6c", "pos_x": 80, "pos_y": 75},
]

# 每个仪表下的传感器类型
SENSOR_TYPES = [
    {"type": "H2", "name": "氢气", "unit": "ppm", "base": 30, "range": 40, "high_limit": 80},
    {"type": "CH4", "name": "甲烷", "unit": "ppm", "base": 25, "range": 35, "high_limit": 80},
    {"type": "VOCs", "name": "VOCs", "unit": "ppm", "base": 20, "range": 30, "high_limit": 80},
    {"type": "TEMP", "name": "温度", "unit": "°C", "base": 22, "range": 3, "high_limit": 28},
    {"type": "HUMI", "name": "湿度", "unit": "%", "base": 40, "range": 10, "high_limit": 60},
    {"type": "PM25", "name": "PM2.5", "unit": "μg/m³", "base": 35, "range": 25, "high_limit": 75},
]

# ============================================================================
# 工具函数
# ============================================================================

def load_mqtt_config():
    """从配置文件加载 MQTT 账号密码"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                user = config.get("device_user", DEFAULT_MQTT_USER)
                passwd = config.get("device_pass", DEFAULT_MQTT_PASS)
                return user, passwd
        except Exception:
            pass
    return DEFAULT_MQTT_USER, DEFAULT_MQTT_PASS


def get_admin_token():
    """获取管理员 token"""
    try:
        resp = requests.post(f"{API_BASE}/auth/login", data={
            "username": "admin",
            "password": "admin123"
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        print(f"[错误] 无法获取 admin token: {e}")
    return None


def create_instruments_and_devices(token):
    """通过 API 创建仪表和设备"""
    headers = {"Authorization": f"Bearer {token}"}
    created_devices = []
    
    print("\n📦 创建演示数据...")
    
    for inst_idx, inst in enumerate(INSTRUMENTS):
        # 创建仪表
        print(f"  创建仪表: {inst['name']}")
        try:
            resp = requests.post(f"{API_BASE}/instruments", json={
                "name": inst["name"],
                "description": f"演示仪表 - {inst['name']}",
                "color": inst["color"],
                "pos_x": inst["pos_x"],
                "pos_y": inst["pos_y"],
                "sort_order": inst_idx + 1
            }, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                inst_id = resp.json().get("id")
            else:
                # 可能已存在，尝试获取
                resp = requests.get(f"{API_BASE}/instruments", headers=headers, timeout=10)
                instruments = resp.json()
                inst_id = None
                for i in instruments:
                    if i["name"] == inst["name"]:
                        inst_id = i["id"]
                        break
                if not inst_id:
                    print(f"    ⚠️ 创建仪表失败: {resp.text}")
                    continue
        except Exception as e:
            print(f"    ⚠️ 创建仪表异常: {e}")
            continue
        
        # 为该仪表创建 6 个传感器
        for sensor_idx, sensor in enumerate(SENSOR_TYPES):
            sn = f"{sensor['type']}{inst_idx + 1:02d}{sensor_idx + 1:02d}"
            device_name = f"{inst['name']}-{sensor['name']}"
            
            device_data = {
                "sn": sn,
                "name": device_name,
                "model": f"MCS-{sensor['type']}",
                "sensor_type": sensor["type"].lower(),
                "unit": sensor["unit"],
                "high_limit": sensor["high_limit"],
                "instrument_id": inst_id,
                "sensor_order": sensor_idx + 1
            }
            
            try:
                resp = requests.post(f"{API_BASE}/devices", json=device_data, headers=headers, timeout=10)
                if resp.status_code == 200:
                    print(f"    ✓ 创建设备: {sn} ({device_name})")
                    created_devices.append({
                        "sn": sn,
                        "sensor_type": sensor["type"],
                        "base": sensor["base"],
                        "range": sensor["range"],
                        "high_limit": sensor["high_limit"],
                        "unit": sensor["unit"]
                    })
                else:
                    # 设备可能已存在
                    if "already exists" in resp.text or resp.status_code == 409:
                        print(f"    ⚪ 设备已存在: {sn}")
                        created_devices.append({
                            "sn": sn,
                            "sensor_type": sensor["type"],
                            "base": sensor["base"],
                            "range": sensor["range"],
                            "high_limit": sensor["high_limit"],
                            "unit": sensor["unit"]
                        })
            except Exception as e:
                print(f"    ⚠️ 创建设备异常: {e}")
    
    print(f"\n✓ 共创建/确认 {len(created_devices)} 个设备\n")
    return created_devices


# ============================================================================
# 传感器模拟器
# ============================================================================

class SensorSimulator:
    def __init__(self, sn, sensor_type, base, value_range, high_limit, unit):
        self.sn = sn
        self.sensor_type = sensor_type
        self.base = base
        self.value_range = value_range
        self.high_limit = high_limit
        self.unit = unit
        self.seq = 0
        self.bat = random.randint(70, 100)
        self.client = None
        self.running = False
        self.alarm_triggered = False
        
    def generate_value(self, trigger_alarm=False):
        """生成传感器数值"""
        if trigger_alarm:
            # 触发报警：超过阈值
            return self.high_limit + random.uniform(5, 20)
        
        # 正常范围内波动
        if self.sensor_type in ["TEMP"]:
            # 温度在 22 度附近，不超过 25
            value = self.base + random.uniform(-self.value_range, self.value_range)
            return min(value, 25.0)
        elif self.sensor_type in ["HUMI"]:
            # 湿度在 40% 附近，不超过 50%
            value = self.base + random.uniform(-self.value_range, self.value_range)
            return min(value, 50.0)
        else:
            # 气体传感器 0-100 ppm
            return max(0, self.base + random.uniform(-self.value_range, self.value_range))
    
    def generate_payload(self, trigger_alarm=False):
        """生成完整数据包"""
        value = self.generate_value(trigger_alarm)
        
        # 温度和湿度额外字段
        if self.sensor_type == "TEMP":
            temp = value
            humi = 40.0 + random.uniform(-5, 5)
        elif self.sensor_type == "HUMI":
            temp = 22.0 + random.uniform(-2, 2)
            humi = value
        else:
            temp = 22.0 + random.uniform(-2, 2)
            humi = 40.0 + random.uniform(-5, 5)
        
        # 电量缓慢下降
        if random.random() < 0.05:
            self.bat = max(20, self.bat - 1)
        
        # 网络类型随机
        net_types = ["4G", "5G", "WiFi", "NB-IoT"]
        
        payload = {
            "ts": int(time.time()),
            "seq": self.seq,
            "v_raw": round(value * 10 + random.uniform(-5, 5), 2),  # 模拟原始电压
            "temp": round(temp, 1),
            "humi": round(humi, 1),
            "bat": self.bat,
            "rssi": random.randint(-75, -55),
            "net": random.choice(net_types),
            "err": 0
        }
        self.seq = (self.seq + 1) % 65536
        return payload
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"  ✓ [{self.sn}] 已连接")
        else:
            print(f"  ✗ [{self.sn}] 连接失败: {rc}")
    
    def start(self, interval, alarm_queue):
        """启动模拟器"""
        mqtt_user, mqtt_pass = load_mqtt_config()
        
        self.client = mqtt.Client(client_id=self.sn)
        self.client.username_pw_set(mqtt_user, mqtt_pass)
        self.client.on_connect = self.on_connect
        
        try:
            self.client.connect(BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            self.running = True
        except Exception as e:
            print(f"  ✗ [{self.sn}] 连接错误: {e}")
            return
        
        while self.running:
            # 检查是否需要触发报警
            trigger_alarm = self.sn in alarm_queue
            if trigger_alarm:
                alarm_queue.remove(self.sn)
                print(f"  ⚠️ [{self.sn}] 触发报警!")
            
            data = self.generate_payload(trigger_alarm)
            topic = f"{TOPIC_PREFIX}/{self.sn}/up"
            self.client.publish(topic, json.dumps(data))
            
            # 添加随机延迟
            time.sleep(interval + random.uniform(-1, 1))
    
    def stop(self):
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


# ============================================================================
# 主程序
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="MCS-IoT 演示数据生成器")
    parser.add_argument("-d", "--duration", type=int, default=60, 
                        help="运行时长(分钟)，默认60分钟")
    parser.add_argument("-i", "--interval", type=int, default=10, 
                        help="数据发送间隔(秒)，默认10秒")
    parser.add_argument("--init-only", action="store_true", 
                        help="仅创建设备，不发送数据")
    parser.add_argument("--skip-init", action="store_true", 
                        help="跳过设备创建，仅发送数据")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  MCS-IoT 演示数据生成器")
    print("=" * 60)
    
    devices = []
    
    # 步骤1: 创建仪表和设备
    if not args.skip_init:
        print("\n等待后端服务就绪...")
        time.sleep(5)
        
        token = get_admin_token()
        if not token:
            print("[错误] 无法连接后端，请确保服务已启动")
            return
        
        devices = create_instruments_and_devices(token)
        
        if args.init_only:
            print("✓ 设备创建完成，已退出")
            return
    else:
        # 使用默认设备配置
        for inst_idx in range(4):
            for sensor_idx, sensor in enumerate(SENSOR_TYPES):
                sn = f"{sensor['type']}{inst_idx + 1:02d}{sensor_idx + 1:02d}"
                devices.append({
                    "sn": sn,
                    "sensor_type": sensor["type"],
                    "base": sensor["base"],
                    "range": sensor["range"],
                    "high_limit": sensor["high_limit"],
                    "unit": sensor["unit"]
                })
    
    if not devices:
        print("[错误] 没有可用设备")
        return
    
    # 步骤2: 启动数据发送
    print(f"\n🚀 启动 {len(devices)} 个传感器模拟器...")
    print(f"   发送间隔: {args.interval} 秒")
    print(f"   运行时长: {args.duration} 分钟")
    print()
    
    simulators = []
    threads = []
    alarm_queue = []  # 共享的报警队列
    
    for dev in devices:
        sim = SensorSimulator(
            sn=dev["sn"],
            sensor_type=dev["sensor_type"],
            base=dev["base"],
            value_range=dev["range"],
            high_limit=dev["high_limit"],
            unit=dev["unit"]
        )
        simulators.append(sim)
        t = threading.Thread(target=sim.start, args=(args.interval, alarm_queue), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.1)
    
    print(f"\n✓ 所有传感器已启动!")
    print(f"  运行至 {time.strftime('%H:%M', time.localtime(time.time() + args.duration * 60))}")
    print(f"  按 Ctrl+C 可提前停止\n")
    
    # 定时触发报警 (每小时 1-2 次)
    start_time = time.time()
    end_time = start_time + args.duration * 60
    last_alarm_time = start_time
    alarm_interval = 3600 / 2  # 平均每 30 分钟一次报警
    
    try:
        while time.time() < end_time:
            current_time = time.time()
            elapsed = int((current_time - start_time) / 60)
            remaining = args.duration - elapsed
            
            # 检查是否需要触发报警
            if current_time - last_alarm_time > alarm_interval:
                # 随机选择 1-2 个设备触发报警
                alarm_count = random.randint(1, 2)
                alarm_devices = random.sample([d["sn"] for d in devices], min(alarm_count, len(devices)))
                alarm_queue.extend(alarm_devices)
                last_alarm_time = current_time
                print(f"[报警] 将触发设备: {', '.join(alarm_devices)}")
            
            # 状态报告
            online = sum(1 for s in simulators if s.running)
            total_msgs = sum(s.seq for s in simulators)
            print(f"[状态] 在线: {online}/{len(simulators)}, 消息数: {total_msgs}, 剩余: {remaining}分钟")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n正在停止...")
    
    # 停止所有模拟器
    for sim in simulators:
        sim.stop()
    
    total_time = int((time.time() - start_time) / 60)
    total_msgs = sum(s.seq for s in simulators)
    print(f"\n✓ 演示数据生成完成!")
    print(f"  运行时长: {total_time} 分钟")
    print(f"  总消息数: {total_msgs}")


if __name__ == "__main__":
    main()
