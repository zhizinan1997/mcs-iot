# MCS-IoT Python 设备接入 SDK

本文档提供 Python 设备接入 MCS-IoT 平台的完整驱动库和示例代码，适用于树莓派、Linux 设备等。

---

## 目录

- [1. 安装依赖](#1-安装依赖)
- [2. 驱动库](#2-驱动库)
- [3. 使用示例](#3-使用示例)
- [4. 高级用法](#4-高级用法)

---

## 1. 安装依赖

```bash
pip install paho-mqtt
```

---

## 2. 驱动库

### 2.1 MCS-IoT 客户端类 `mcs_iot.py`

```python
#!/usr/bin/env python3
"""
MCS-IoT Python 设备接入 SDK
版本: 1.0.0
作者: MCS-IoT Team

使用方法:
    from mcs_iot import MCSClient
    
    client = MCSClient(
        broker="mqtt.example.com",
        device_sn="H20101",
        username="device",
        password="your-password"
    )
    client.connect()
    client.report(v_raw=45.5, temp=25.3, humi=48.0)
"""

import json
import time
import ssl
import logging
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, asdict

import paho.mqtt.client as mqtt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('MCS-IoT')


@dataclass
class SensorData:
    """传感器数据结构"""
    v_raw: float = 0.0          # 传感器原始值
    temp: float = 25.0          # 温度 (°C)
    humi: float = 50.0          # 湿度 (%)
    bat: int = 100              # 电池电量 (%)
    rssi: int = -60             # 信号强度 (dBm)
    net: str = "WiFi"           # 网络类型
    err: int = 0                # 错误码
    
    def to_dict(self) -> dict:
        return asdict(self)


class MCSClient:
    """MCS-IoT MQTT 客户端"""
    
    def __init__(
        self,
        broker: str,
        device_sn: str,
        username: str = "",
        password: str = "",
        port: int = 1883,
        use_tls: bool = False,
        ca_cert: Optional[str] = None,
        keepalive: int = 60
    ):
        """
        初始化 MCS-IoT 客户端
        
        Args:
            broker: MQTT 服务器地址
            device_sn: 设备序列号
            username: MQTT 用户名
            password: MQTT 密码
            port: MQTT 端口 (1883=TCP, 8883=TLS)
            use_tls: 是否使用 TLS
            ca_cert: CA 证书路径 (TLS 时可选)
            keepalive: 心跳间隔 (秒)
        """
        self.broker = broker
        self.port = port
        self.device_sn = device_sn
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.ca_cert = ca_cert
        self.keepalive = keepalive
        
        # 内部状态
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._seq = 0
        self._cmd_callback: Optional[Callable[[str, dict], None]] = None
        self._lock = threading.Lock()
        
        # Topic
        self.topic_up = f"mcs/{device_sn}/up"
        self.topic_down = f"mcs/{device_sn}/down"
        
        logger.info(f"MCS 客户端初始化: SN={device_sn}, Broker={broker}:{port}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            logger.info("MQTT 已连接")
            self._connected = True
            # 订阅下行 Topic
            client.subscribe(self.topic_down, qos=1)
            logger.info(f"已订阅: {self.topic_down}")
        else:
            error_msgs = {
                1: "协议版本错误",
                2: "客户端标识无效",
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权"
            }
            logger.error(f"连接失败: {error_msgs.get(rc, f'未知错误 {rc}')}")
            self._connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """断开回调"""
        self._connected = False
        if rc != 0:
            logger.warning(f"意外断开连接: {rc}")
        else:
            logger.info("已断开连接")
    
    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            payload = json.loads(msg.payload.decode())
            cmd = payload.get("cmd")
            params = payload.get("params", {})
            
            logger.info(f"收到指令: {cmd}, 参数: {params}")
            
            if self._cmd_callback:
                self._cmd_callback(cmd, params)
                
        except json.JSONDecodeError:
            logger.error(f"无法解析消息: {msg.payload}")
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
    
    def connect(self, blocking: bool = True) -> bool:
        """
        连接到 MQTT 服务器
        
        Args:
            blocking: 是否阻塞等待连接成功
            
        Returns:
            是否连接成功
        """
        try:
            # 创建客户端
            self._client = mqtt.Client(
                client_id=self.device_sn,
                protocol=mqtt.MQTTv311
            )
            
            # 设置回调
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            
            # 设置认证
            if self.username:
                self._client.username_pw_set(self.username, self.password)
            
            # 配置 TLS
            if self.use_tls:
                if self.ca_cert:
                    self._client.tls_set(ca_certs=self.ca_cert)
                else:
                    self._client.tls_set(cert_reqs=ssl.CERT_NONE)
                    self._client.tls_insecure_set(True)
            
            # 连接
            logger.info(f"正在连接 {self.broker}:{self.port}...")
            self._client.connect(self.broker, self.port, self.keepalive)
            
            # 启动网络循环
            self._client.loop_start()
            
            # 等待连接
            if blocking:
                for _ in range(30):  # 最多等待 30 秒
                    if self._connected:
                        return True
                    time.sleep(1)
                logger.error("连接超时")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    def report(
        self,
        v_raw: float,
        temp: float = 25.0,
        humi: float = 50.0,
        bat: int = 100,
        rssi: int = -60,
        net: str = "WiFi",
        err: int = 0
    ) -> bool:
        """
        上报传感器数据
        
        Args:
            v_raw: 传感器原始值
            temp: 温度
            humi: 湿度
            bat: 电池电量
            rssi: 信号强度
            net: 网络类型
            err: 错误码
            
        Returns:
            是否发送成功
        """
        data = SensorData(
            v_raw=v_raw,
            temp=temp,
            humi=humi,
            bat=bat,
            rssi=rssi,
            net=net,
            err=err
        )
        return self.report_data(data)
    
    def report_data(self, data: SensorData) -> bool:
        """
        上报传感器数据对象
        
        Args:
            data: SensorData 对象
            
        Returns:
            是否发送成功
        """
        if not self._connected:
            logger.error("未连接到服务器")
            return False
        
        with self._lock:
            seq = self._seq
            self._seq = (self._seq + 1) % 65536
        
        payload = {
            "ts": int(time.time()),
            "seq": seq,
            **data.to_dict()
        }
        
        try:
            result = self._client.publish(
                self.topic_up,
                json.dumps(payload),
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"数据已上报: seq={seq}")
                return True
            else:
                logger.error(f"发送失败: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发送异常: {e}")
            return False
    
    def set_cmd_callback(self, callback: Callable[[str, dict], None]):
        """
        设置指令回调函数
        
        Args:
            callback: 回调函数，参数为 (cmd, params)
        """
        self._cmd_callback = callback
    
    def loop_forever(self):
        """阻塞运行，用于简单场景"""
        if self._client:
            self._client.loop_forever()


# ============================================================================
# 便捷函数
# ============================================================================

def create_client(
    broker: str,
    device_sn: str,
    username: str = "",
    password: str = "",
    use_tls: bool = False
) -> MCSClient:
    """
    快速创建客户端
    
    Args:
        broker: MQTT 服务器
        device_sn: 设备序列号
        username: 用户名
        password: 密码
        use_tls: 是否 TLS
        
    Returns:
        MCSClient 实例
    """
    port = 8883 if use_tls else 1883
    return MCSClient(
        broker=broker,
        device_sn=device_sn,
        username=username,
        password=password,
        port=port,
        use_tls=use_tls
    )


# ============================================================================
# 模块入口 (测试用)
# ============================================================================

if __name__ == "__main__":
    import argparse
    import random
    
    parser = argparse.ArgumentParser(description="MCS-IoT Python SDK 测试")
    parser.add_argument("--broker", required=True, help="MQTT 服务器")
    parser.add_argument("--sn", required=True, help="设备序列号")
    parser.add_argument("--user", default="device", help="用户名")
    parser.add_argument("--password", default="", help="密码")
    parser.add_argument("--tls", action="store_true", help="使用 TLS")
    parser.add_argument("--interval", type=int, default=10, help="上报间隔")
    args = parser.parse_args()
    
    client = create_client(
        broker=args.broker,
        device_sn=args.sn,
        username=args.user,
        password=args.password,
        use_tls=args.tls
    )
    
    def on_cmd(cmd, params):
        print(f"收到指令: {cmd}, 参数: {params}")
    
    client.set_cmd_callback(on_cmd)
    
    if client.connect():
        print(f"已连接，开始上报数据 (间隔 {args.interval} 秒)")
        try:
            while True:
                v = 30 + random.uniform(-10, 10)
                client.report(
                    v_raw=v,
                    temp=25 + random.uniform(-2, 2),
                    humi=45 + random.uniform(-5, 5)
                )
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n停止")
        finally:
            client.disconnect()
    else:
        print("连接失败")
```

---

## 3. 使用示例

### 3.1 基础示例

```python
#!/usr/bin/env python3
"""基础使用示例"""

from mcs_iot import MCSClient
import time

# 创建客户端
client = MCSClient(
    broker="mqtt.yourdomain.com",
    device_sn="H20101",
    username="device",
    password="your-password",
    port=8883,
    use_tls=True
)

# 连接
if client.connect():
    print("连接成功!")
    
    # 上报数据
    client.report(
        v_raw=45.5,
        temp=25.3,
        humi=48.0,
        bat=85,
        rssi=-65,
        net="WiFi"
    )
    
    # 断开
    client.disconnect()
else:
    print("连接失败")
```

### 3.2 定时上报示例

```python
#!/usr/bin/env python3
"""定时上报示例"""

from mcs_iot import MCSClient, SensorData
import time
import random

# 配置
BROKER = "mqtt.yourdomain.com"
DEVICE_SN = "CH40102"
USERNAME = "device"
PASSWORD = "your-password"
INTERVAL = 10  # 上报间隔 (秒)

def read_sensor() -> SensorData:
    """读取传感器 (示例: 模拟数据)"""
    # TODO: 替换为实际的传感器读取代码
    return SensorData(
        v_raw=30 + random.uniform(-10, 10),
        temp=25 + random.uniform(-2, 2),
        humi=45 + random.uniform(-5, 5),
        bat=random.randint(80, 100),
        rssi=random.randint(-80, -50),
        net="WiFi"
    )

def main():
    client = MCSClient(
        broker=BROKER,
        device_sn=DEVICE_SN,
        username=USERNAME,
        password=PASSWORD,
        port=8883,
        use_tls=True
    )
    
    if not client.connect():
        print("连接失败")
        return
    
    print(f"=== MCS-IoT 设备 {DEVICE_SN} ===")
    print(f"上报间隔: {INTERVAL} 秒")
    print("按 Ctrl+C 停止")
    
    try:
        while True:
            if client.is_connected:
                data = read_sensor()
                if client.report_data(data):
                    print(f"[上报] v_raw={data.v_raw:.2f}, temp={data.temp:.1f}, humi={data.humi:.1f}")
                else:
                    print("[错误] 上报失败")
            else:
                print("[警告] 未连接")
            
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n停止...")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
```

### 3.3 指令处理示例

```python
#!/usr/bin/env python3
"""指令处理示例"""

from mcs_iot import MCSClient
import time
import os

# 全局配置
config = {
    "interval": 10
}

def on_command(cmd: str, params: dict):
    """处理服务器下发的指令"""
    print(f"[指令] {cmd}: {params}")
    
    if cmd == "config":
        # 更新配置
        if "interval" in params:
            config["interval"] = params["interval"]
            print(f"上报间隔已更新为: {config['interval']} 秒")
    
    elif cmd == "reboot":
        # 重启设备
        print("收到重启指令，3秒后重启...")
        time.sleep(3)
        os.system("sudo reboot")
    
    elif cmd == "upgrade":
        # OTA 升级
        url = params.get("url")
        if url:
            print(f"开始下载固件: {url}")
            # TODO: 实现 OTA 逻辑

def main():
    client = MCSClient(
        broker="mqtt.yourdomain.com",
        device_sn="H20101",
        username="device",
        password="your-password",
        port=8883,
        use_tls=True
    )
    
    # 设置指令回调
    client.set_cmd_callback(on_command)
    
    if not client.connect():
        print("连接失败")
        return
    
    print("等待服务器指令...")
    
    try:
        while True:
            # 定时上报
            if client.is_connected:
                client.report(v_raw=45.5, temp=25.0, humi=50.0)
            time.sleep(config["interval"])
            
    except KeyboardInterrupt:
        print("\n停止...")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
```

---

## 4. 高级用法

### 4.1 多传感器设备

```python
#!/usr/bin/env python3
"""多传感器设备示例"""

from mcs_iot import MCSClient
import time
import random
import threading

# 传感器配置
SENSORS = [
    {"sn": "H20101", "type": "H2", "base": 30},
    {"sn": "CH40102", "type": "CH4", "base": 25},
    {"sn": "TEMP0103", "type": "TEMP", "base": 25},
]

def run_sensor(sensor_config: dict):
    """单个传感器线程"""
    client = MCSClient(
        broker="mqtt.yourdomain.com",
        device_sn=sensor_config["sn"],
        username="device",
        password="your-password",
        port=8883,
        use_tls=True
    )
    
    if not client.connect():
        print(f"[{sensor_config['sn']}] 连接失败")
        return
    
    print(f"[{sensor_config['sn']}] 已启动")
    
    try:
        while True:
            value = sensor_config["base"] + random.uniform(-5, 5)
            client.report(v_raw=value)
            time.sleep(10)
    except:
        pass
    finally:
        client.disconnect()

def main():
    threads = []
    
    for sensor in SENSORS:
        t = threading.Thread(target=run_sensor, args=(sensor,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)  # 错开连接
    
    print(f"已启动 {len(SENSORS)} 个传感器")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止...")

if __name__ == "__main__":
    main()
```

### 4.2 树莓派 GPIO 读取

```python
#!/usr/bin/env python3
"""树莓派 GPIO + MQ-2 传感器示例"""

from mcs_iot import MCSClient
import time

try:
    import RPi.GPIO as GPIO
    import Adafruit_ADS1x15
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False
    print("警告: 未检测到树莓派硬件库，使用模拟数据")

# ADC 配置
if HAS_HARDWARE:
    adc = Adafruit_ADS1x15.ADS1115()
    GAIN = 1  # +/- 4.096V

def read_mq2_sensor() -> float:
    """读取 MQ-2 气体传感器"""
    if HAS_HARDWARE:
        # 读取 ADC 通道 0
        raw = adc.read_adc(0, gain=GAIN)
        # 转换为 ppm (需根据实际传感器校准)
        voltage = raw * 4.096 / 32767
        ppm = voltage * 100  # 简化公式
        return ppm
    else:
        import random
        return 30 + random.uniform(-10, 10)

def main():
    client = MCSClient(
        broker="mqtt.yourdomain.com",
        device_sn="MQ20101",
        username="device",
        password="your-password",
        port=8883,
        use_tls=True
    )
    
    if not client.connect():
        print("连接失败")
        return
    
    try:
        while True:
            ppm = read_mq2_sensor()
            client.report(v_raw=ppm, net="WiFi")
            print(f"MQ-2: {ppm:.2f} ppm")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n停止...")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
```

---

## 5. 协议参考

### 上行数据字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ts | int | ✓ | Unix 时间戳 |
| seq | int | ✓ | 序列号 |
| v_raw | float | ✓ | 传感器原始值 |
| temp | float | ○ | 温度 (°C) |
| humi | float | ○ | 湿度 (%) |
| bat | int | ○ | 电池 (%) |
| rssi | int | ○ | 信号 (dBm) |
| net | string | ○ | 网络类型 |
| err | int | ○ | 错误码 |

### 下行指令

| 指令 | 参数 | 说明 |
|------|------|------|
| config | interval | 修改上报间隔 |
| reboot | - | 重启设备 |
| upgrade | url | OTA 升级 |

---

## 6. 常见问题

### Q: 连接超时怎么办？

A: 检查网络、服务器地址、端口、用户名密码

### Q: 如何使用自签名证书？

A: 设置 `use_tls=True`，不指定 `ca_cert` 即可跳过证书验证

### Q: 断线后会自动重连吗？

A: 是的，paho-mqtt 会自动尝试重连

---

**技术支持**: <zinanzhi@gmail.com>
