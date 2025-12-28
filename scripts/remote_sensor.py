#!/usr/bin/env python3
"""
  MCS-IOT 远程传感器模拟器 (Remote Sensor Simulator)

  该脚本用于在外网或远程环境模拟物理传感器的行为，验证系统的跨网络上报性能。
  主要职责：
  1. 远程连接方案：支持基于 TLS (8883) 的安全加密连接与传统 TCP (1883) 通信。
  2. 批量设备模拟：支持同时模拟上百个逻辑设备，每个设备拥有独立的会话、SN 与数据序列。
  3. 全参数模拟：上报报文涵盖原始电压 (v_raw)、计算浓度、环境温湿度、电量、信号强度 (RSSI) 及网络类型。
  4. 稳定性测试：具备断线重连机制，自动处理网络波动，支持高频（每秒多次）上报压测。

  技术栈：Python 3, Paho-MQTT (V2 Callbacks), SSL/TLS, Threading.
"""
import paho.mqtt.client as mqtt
import json
import time
import random
import argparse
import ssl
import sys
import threading

# 禁用输出缓冲，确保 Windows 下实时显示
sys.stdout.reconfigure(line_buffering=True)

# ============================================================================
# 远程服务器配置
# ============================================================================

BROKER = "mqtt.zhizinan.top"  # 替换为你的 MQTT 服务器域名
MQTT_PORT_TLS = 8883  # TLS 加密端口
MQTT_PORT_TCP = 1883  # 非加密端口
MQTT_USER = "admin"
MQTT_PASS = "admin123"  # 替换为部署时设置的 MQTT 密码
TOPIC_PREFIX = "mcs"

# ============================================================================
# 传感器类型配置
# ============================================================================

SENSOR_CONFIGS = {
    "H2": {"name": "氢气", "unit": "ppm", "base": 30, "range": 40, "high_limit": 80},
    "CH4": {"name": "甲烷", "unit": "ppm", "base": 25, "range": 35, "high_limit": 80},
    "VOCs": {"name": "VOCs", "unit": "ppm", "base": 20, "range": 30, "high_limit": 80},
    "TEMP": {"name": "温度", "unit": "C", "base": 22, "range": 3, "high_limit": 28},
    "HUMI": {"name": "湿度", "unit": "%", "base": 40, "range": 10, "high_limit": 60},
    "PM25": {"name": "PM2.5", "unit": "ug/m3", "base": 35, "range": 25, "high_limit": 75},
}

# 传感器类型列表，用于随机分配
SENSOR_TYPES = list(SENSOR_CONFIGS.keys())

# 线程锁，用于控制输出
print_lock = threading.Lock()

# ============================================================================
# 传感器模拟器类
# ============================================================================

class RemoteSensor:
    def __init__(self, sn, sensor_type, mqtt_user=None, mqtt_pass=None, use_tls=True):
        self.sn = sn
        self.sensor_type = sensor_type
        self.config = SENSOR_CONFIGS.get(sensor_type, SENSOR_CONFIGS["CH4"])
        self.seq = 0
        self.bat = random.randint(80, 100)
        self.client = None
        self.connected = False
        self.mqtt_user = mqtt_user or MQTT_USER
        self.mqtt_pass = mqtt_pass or MQTT_PASS
        self.use_tls = use_tls
        self.port = MQTT_PORT_TLS if use_tls else MQTT_PORT_TCP
        self.running = True
        
    def generate_value(self):
        """生成传感器数值"""
        base = self.config["base"]
        value_range = self.config["range"]
        
        if self.sensor_type == "TEMP":
            value = base + random.uniform(-value_range, value_range)
            return min(value, 25.0)
        elif self.sensor_type == "HUMI":
            value = base + random.uniform(-value_range, value_range)
            return min(value, 50.0)
        else:
            return max(0, base + random.uniform(-value_range, value_range))
    
    def generate_payload(self):
        """生成完整数据包"""
        value = self.generate_value()
        
        # 温度和湿度
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
        if random.random() < 0.01:
            self.bat = max(20, self.bat - 1)
        
        payload = {
            "ts": int(time.time()),
            "seq": self.seq,
            "v_raw": round(value * 10 + random.uniform(-5, 5), 2),
            "temp": round(temp, 1),
            "humi": round(humi, 1),
            "bat": self.bat,
            "rssi": random.randint(-75, -55),
            "net": random.choice(["4G", "5G", "WiFi", "NB-IoT"]),
            "err": 0
        }
        self.seq = (self.seq + 1) % 65536
        return payload
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT 连接回调"""
        if reason_code == 0:
            self.connected = True
            with print_lock:
                print(f"[OK] {self.sn} 连接成功! ({self.config['name']})")
        else:
            with print_lock:
                print(f"[ERROR] {self.sn} 连接失败，错误码: {reason_code}")
    
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """MQTT 断开连接回调"""
        self.connected = False
        if reason_code != 0 and self.running:
            with print_lock:
                print(f"[WARN] {self.sn} 连接断开，将自动重连... (rc={reason_code})")
    
    def connect(self):
        """连接到 MQTT 服务器"""
        self.client = mqtt.Client(client_id=self.sn, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        
        # 仅在 TLS 模式下配置 SSL
        if self.use_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)
        
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        try:
            self.client.connect(BROKER, self.port, 60)
            self.client.loop_start()
            
            # 等待连接完成
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if not self.connected:
                with print_lock:
                    print(f"[ERROR] {self.sn} 连接超时")
                return False
            
            return True
        except Exception as e:
            with print_lock:
                print(f"[ERROR] {self.sn} 连接错误: {e}")
            return False
    
    def run(self, interval):
        """运行传感器，持续发送数据"""
        if not self.connect():
            return
        
        topic = f"{TOPIC_PREFIX}/{self.sn}/up"
        
        # 添加随机延迟，避免所有传感器同时发送
        time.sleep(random.uniform(0, interval))
        
        while self.running:
            if not self.connected:
                time.sleep(1)
                continue
            
            data = self.generate_payload()
            payload = json.dumps(data)
            
            result = self.client.publish(topic, payload)
            if result.rc == 0:
                # 格式化输出
                value = data["v_raw"] / 10
                with print_lock:
                    print(f"[{time.strftime('%H:%M:%S')}] {self.sn:12} | "
                          f"{self.config['name']:6}={value:6.1f}{self.config['unit']:6} | "
                          f"T={data['temp']:4.1f}C | "
                          f"H={data['humi']:4.1f}% | "
                          f"B={data['bat']:3d}% | "
                          f"RSSI={data['rssi']}dBm")
            
            time.sleep(interval)
    
    def stop(self):
        """停止传感器"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


# ============================================================================
# 多传感器管理器
# ============================================================================

class SensorManager:
    def __init__(self, count, mqtt_user, mqtt_pass, use_tls, interval):
        self.sensors = []
        self.threads = []
        self.count = count
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.use_tls = use_tls
        self.interval = interval
    
    def create_sensors(self):
        """创建多个传感器实例"""
        for i in range(self.count):
            sn = f"SENSOR{i+1:03d}"
            sensor_type = SENSOR_TYPES[i % len(SENSOR_TYPES)]
            sensor = RemoteSensor(sn, sensor_type, self.mqtt_user, self.mqtt_pass, self.use_tls)
            self.sensors.append(sensor)
    
    def start(self):
        """启动所有传感器"""
        self.create_sensors()
        
        for sensor in self.sensors:
            thread = threading.Thread(target=sensor.run, args=(self.interval,), daemon=True)
            thread.start()
            self.threads.append(thread)
            # 错开连接时间，避免同时连接
            time.sleep(0.2)
    
    def stop(self):
        """停止所有传感器"""
        for sensor in self.sensors:
            sensor.stop()
        
        for thread in self.threads:
            thread.join(timeout=2)


# ============================================================================
# 主程序
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MCS-IoT 远程传感器模拟器 (多传感器版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
传感器类型 (自动轮流分配):
  H2     氢气传感器
  CH4    甲烷传感器
  VOCs   挥发性有机物传感器
  TEMP   温度传感器
  HUMI   湿度传感器
  PM25   PM2.5 传感器

示例:
  python remote_sensor.py                     # 默认运行 10 个传感器 (TLS)
  python remote_sensor.py --count 5           # 运行 5 个传感器
  python remote_sensor.py --no-tls            # 不使用 TLS
  python remote_sensor.py --interval 0.5      # 每0.5秒发送
"""
    )
    parser.add_argument("--count", type=int, default=10, 
                        help="模拟传感器数量 (默认: 10)")
    parser.add_argument("--interval", type=float, default=1.0, 
                        help="数据发送间隔/秒 (默认: 1.0)")
    parser.add_argument("--user", type=str, default=MQTT_USER,
                        help=f"MQTT 用户名 (默认: {MQTT_USER})")
    parser.add_argument("--pass", dest="password", type=str, default=MQTT_PASS,
                        help="MQTT 密码")
    parser.add_argument("--no-tls", dest="no_tls", action="store_true",
                        help="不使用 TLS 加密 (使用端口 1883)")
    args = parser.parse_args()
    
    use_tls = not args.no_tls
    port = MQTT_PORT_TLS if use_tls else MQTT_PORT_TCP
    mode = "TLS" if use_tls else "TCP"
    
    print("=" * 70)
    print("  MCS-IoT 远程传感器模拟器 (多传感器版)")
    print("=" * 70)
    print(f"  服务器: {BROKER}:{port} ({mode})")
    print(f"  传感器数量: {args.count}")
    print(f"  发送间隔: {args.interval} 秒")
    print(f"  传感器类型: 自动轮流分配 (H2, CH4, VOCs, TEMP, HUMI, PM25)")
    print("=" * 70)
    print()
    print("[INFO] 正在启动传感器...")
    print()
    
    manager = SensorManager(args.count, args.user, args.password, use_tls, args.interval)
    
    try:
        manager.start()
        
        # 等待所有传感器连接完成
        time.sleep(args.count * 0.3 + 2)
        
        print()
        print("-" * 70)
        print(f"[INFO] {args.count} 个传感器已启动，正在发送数据...")
        print("[INFO] 按 Ctrl+C 停止")
        print("-" * 70)
        print()
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] 停止中...")
        manager.stop()
        print(f"[OK] 已停止所有 {args.count} 个传感器")


if __name__ == "__main__":
    main()
