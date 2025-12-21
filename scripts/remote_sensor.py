#!/usr/bin/env python3
"""
MCS-IoT 远程传感器模拟器
连接到远程 MQTT 服务器，模拟单个传感器每秒发送数据

使用方法:
  python3 remote_sensor.py                    # 使用默认配置运行 (TLS)
  python3 remote_sensor.py --no-tls           # 不使用 TLS (端口 1883)
  python3 remote_sensor.py --sn DEMO001       # 指定传感器序列号
  python3 remote_sensor.py --type CH4         # 指定传感器类型
  python3 remote_sensor.py --interval 0.5     # 每0.5秒发送一次
"""
import paho.mqtt.client as mqtt
import json
import time
import random
import argparse
import ssl

# ============================================================================
# 远程服务器配置
# ============================================================================

BROKER = "mqtt.yourdomain.com"  # 替换为你的 MQTT 服务器域名
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
    "TEMP": {"name": "温度", "unit": "°C", "base": 22, "range": 3, "high_limit": 28},
    "HUMI": {"name": "湿度", "unit": "%", "base": 40, "range": 10, "high_limit": 60},
    "PM25": {"name": "PM2.5", "unit": "μg/m³", "base": 35, "range": 25, "high_limit": 75},
}

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
            mode = "TLS" if self.use_tls else "TCP"
            print(f"✅ 连接成功!")
            print(f"   服务器: {BROKER}:{self.port} ({mode})")
            print(f"   传感器: {self.sn} ({self.config['name']})")
        else:
            print(f"❌ 连接失败，错误码: {reason_code}")
    
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """MQTT 断开连接回调"""
        self.connected = False
        if reason_code != 0:
            print(f"⚠️ 连接断开，将自动重连... (rc={reason_code})")
    
    def connect(self):
        """连接到 MQTT 服务器"""
        mode = "TLS" if self.use_tls else "TCP"
        print(f"\n🔌 正在连接 {BROKER}:{self.port} ({mode})...")
        
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
                print("❌ 连接超时")
                return False
            
            return True
        except Exception as e:
            print(f"❌ 连接错误: {e}")
            return False
    
    def run(self, interval):
        """运行传感器，持续发送数据"""
        if not self.connect():
            return
        
        topic = f"{TOPIC_PREFIX}/{self.sn}/up"
        print(f"\n📡 开始发送数据...")
        print(f"   Topic: {topic}")
        print(f"   间隔: {interval} 秒")
        print(f"   按 Ctrl+C 停止\n")
        print("-" * 60)
        
        try:
            while True:
                if not self.connected:
                    print("⚠️ 等待重连...")
                    time.sleep(1)
                    continue
                
                data = self.generate_payload()
                payload = json.dumps(data)
                
                result = self.client.publish(topic, payload)
                if result.rc == 0:
                    # 格式化输出
                    value = data["v_raw"] / 10
                    print(f"[{time.strftime('%H:%M:%S')}] "
                          f"seq={data['seq']:05d} | "
                          f"{self.config['name']}={value:.1f}{self.config['unit']} | "
                          f"温度={data['temp']}°C | "
                          f"湿度={data['humi']}% | "
                          f"电池={data['bat']}% | "
                          f"信号={data['rssi']}dBm")
                else:
                    print(f"⚠️ 发送失败 (rc={result.rc})")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 停止中...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"✅ 已断开连接，共发送 {self.seq} 条消息")


# ============================================================================
# 主程序
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MCS-IoT 远程传感器模拟器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
传感器类型:
  H2     氢气传感器
  CH4    甲烷传感器 (默认)
  VOCs   挥发性有机物传感器
  TEMP   温度传感器
  HUMI   湿度传感器
  PM25   PM2.5 传感器

示例:
  python remote_sensor.py                     # 默认配置 (TLS)
  python remote_sensor.py --no-tls            # 不使用 TLS
  python remote_sensor.py --sn DEMO001        # 自定义序列号
  python remote_sensor.py --type TEMP         # 温度传感器
  python remote_sensor.py --interval 0.5      # 每0.5秒发送
"""
    )
    parser.add_argument("--sn", type=str, default="REMOTE001", 
                        help="传感器序列号 (默认: REMOTE001)")
    parser.add_argument("--type", type=str, default="CH4", 
                        choices=list(SENSOR_CONFIGS.keys()),
                        help="传感器类型 (默认: CH4)")
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
    
    print("=" * 60)
    print("  MCS-IoT 远程传感器模拟器")
    print("=" * 60)
    print(f"  服务器: {BROKER}:{port} ({mode})")
    print(f"  传感器: {args.sn}")
    print(f"  类型: {args.type} ({SENSOR_CONFIGS[args.type]['name']})")
    print(f"  间隔: {args.interval} 秒")
    print("=" * 60)
    
    sensor = RemoteSensor(args.sn, args.type, args.user, args.password, use_tls)
    sensor.run(args.interval)


if __name__ == "__main__":
    main()
