# MCS-IoT 工业级气体监测系统

[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)

## 📖 项目概述

**MCS-IoT** (Metachip Cloud Sense) 是一套专为工业气体监测场景设计的物联网平台，具备以下核心优势：

| 特性 | 说明 |
|------|------|
| 💰 **极低成本** | 年运营成本 ¥189 (100台设备规模) |
| 🚀 **高并发** | 单服务器支持 500+ 设备同时在线 |
| 🔐 **商业保护** | 硬件绑定 + 在线授权 + 72h宽限期 |
| 📊 **实时可视化** | WebSocket + ECharts 大屏展示 |
| 📦 **冷热分离** | TimescaleDB 热存储 + R2 冷归档 |
| ⏰ **定时任务** | 自动归档、健康检查、授权校验 |
| 🔔 **智能报警** | 多通道通知、时段限制、防抖去重 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层 (User Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Admin 后台  │  │  可视化大屏  │  │      API 接口        │   │
│  │  (Vue 3)     │  │  (ECharts)   │  │    (FastAPI)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (Application Layer)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Backend (FastAPI)                      │   │
│  │  • 认证授权 (JWT)    • 设备管理    • 报警记录              │   │
│  │  • 配置管理          • 大屏数据    • WebSocket             │   │
│  │  • 数据导出          • 设备命令    • 健康检查              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        计算层 (Compute Layer)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Worker (Python)                        │   │
│  │  • MQTT 订阅       • 浓度解算      • 报警检测              │   │
│  │  • 数据存储        • 授权守卫      • 数据归档              │   │
│  │  • 定时任务        • 离线检测      • 健康检查              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        存储层 (Storage Layer)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ TimescaleDB │  │    Redis    │  │    Cloudflare R2       │  │
│  │  (热数据)   │  │   (缓存)    │  │     (冷归档)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        传输层 (Transport Layer)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Mosquitto (MQTT Broker)                  │   │
│  │  • TCP 1883     • TLS 8883     • WebSocket 9001          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        感知层 (Device Layer)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  气体传感器  │  │  温湿度传感器 │  │    ESP32 + 4G模组      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐳 Docker 容器

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `mcs_mosquitto` | eclipse-mosquitto:2 | 1883, 8883, 9001 | MQTT Broker |
| `mcs_db` | timescale/timescaledb:pg15 | 5432 | 时序数据库 |
| `mcs_redis` | redis:7-alpine | 6379 | 缓存服务 |
| `mcs_worker` | mcs-iot-worker | - | 核心处理服务 |
| `mcs_backend` | mcs-iot-backend | 8000 | REST API 服务 |
| `mcs_frontend` | mcs-iot-frontend | 80 | Vue 前端 (Nginx) |

---

## 🌐 网络配置

### 端口说明

| 端口 | 协议 | 用途 | 对外暴露 |
|------|------|------|----------|
| **80** | HTTP | Web 前端界面 | ✅ 必须 |
| **443** | HTTPS | Web 前端界面 (SSL) | ✅ 生产环境必须 |
| **8000** | HTTP | REST API | ⚠️ 开发环境（生产环境通过 Nginx 代理） |
| **1883** | MQTT/TCP | 设备连接 (无加密) | ⚠️ 仅开发环境 |
| **8883** | MQTTS/TLS | 设备连接 (加密) | ✅ 生产环境必须 |
| **9001** | WebSocket | MQTT over WS | ❌ 可选 |
| **5432** | TCP | PostgreSQL | ❌ 内部使用 |
| **6379** | TCP | Redis | ❌ 内部使用 |

### 域名配置

生产环境部署需要配置以下域名：

| 域名 | 用途 | 指向 |
|------|------|------|
| `iot.yourdomain.com` | Web 界面 + API | 服务器 IP (端口 80/443) |
| `mqtt.yourdomain.com` | 设备 MQTT 连接 | 服务器 IP (端口 8883) |

### 需要修改的配置文件

部署到生产环境时，需要修改以下文件中的地址：

```bash
# 1. 前端 API 地址 (必须修改)
frontend/src/api/index.ts
  └── baseURL: 'https://iot.yourdomain.com/api'

# 2. 设备固件中的 MQTT 地址
  └── MQTT_HOST: mqtt.yourdomain.com
  └── MQTT_PORT: 8883

# 3. Nginx 配置 (生产环境)
nginx/nginx.conf
  └── server_name: iot.yourdomain.com

# 4. 环境变量 (docker-compose.prod.yml)
  └── JWT_SECRET: 改为安全的随机字符串
  └── DB_PASS: 改为安全的数据库密码
```

### 防火墙规则

```bash
# 开放必要端口
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8883/tcp  # MQTTS (设备连接)

# 可选 (开发调试用)
sudo ufw allow 1883/tcp  # MQTT (无加密)
sudo ufw allow 8000/tcp  # API 直连
```

---

## � 硬件开发参考手册

本章节面向**硬件/固件开发工程师**，说明设备如何与 MCS-IoT 平台通信。

### MQTT 连接参数

| 参数 | 开发环境 | 生产环境 |
|------|----------|----------|
| **Broker 地址** | `localhost` 或 `服务器IP` | `mqtt.yourdomain.com` |
| **TCP 端口** | 1883 | - |
| **TLS 端口** | 8883 | 8883 (必须使用) |
| **用户名** | 在 Admin 界面配置 | 在 Admin 界面配置 |
| **密码** | 在 Admin 界面配置 | 在 Admin 界面配置 |
| **Client ID** | 设备 SN (唯一) | 设备 SN (唯一) |
| **Keep Alive** | 60 秒 | 60 秒 |
| **Clean Session** | true | true |

> **账号管理说明**
>
> 所有设备使用**统一账号密码**，在 Admin 界面 → 系统配置 → MQTT账号 中设置。
>
> | 账号类型 | 用途 |
> |----------|------|
> | 管理员账号 | MQTT 调试工具连接 |
> | Worker 账号 | 后台服务连接（修改后需重启 Worker 容器） |
> | 设备账号 | 所有硬件设备统一使用 |

### Topic 命名规范

```
mcs/{设备SN}/up       # 设备上行数据 (设备 → 服务器)
mcs/{设备SN}/down     # 服务器下行命令 (服务器 → 设备)
mcs/{设备SN}/status   # 设备状态 (可选)
```

**示例：**

- 设备 SN 为 `GAS001` 的上行 Topic: `mcs/GAS001/up`
- 设备 SN 为 `GAS001` 的下行 Topic: `mcs/GAS001/down`

### 上行数据格式 (设备 → 服务器)

设备每隔固定间隔（默认 10 秒）向 `mcs/{SN}/up` 发送 JSON 数据：

```json
{
  "ts": 1702723200,
  "seq": 123,
  "v_raw": 2045.5,
  "temp": 25.3,
  "humi": 45.2,
  "bat": 85,
  "rssi": -72,
  "net": "4G",
  "err": 0
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ts` | int | ✅ | Unix 时间戳（秒） |
| `seq` | int | ✅ | 消息序号 (0-65535 循环) |
| `v_raw` | float | ✅ | 传感器原始电压值 (mV) |
| `temp` | float | ✅ | 环境温度 (°C) |
| `humi` | float | ✅ | 环境湿度 (%) |
| `bat` | int | ✅ | 电池电量 (0-100%) |
| `rssi` | int | ✅ | 信号强度 (dBm, 负数) |
| `net` | string | ❌ | 网络类型: "4G", "WiFi", "NB" |
| `err` | int | ❌ | 错误码 (0=正常) |

**错误码定义：**

| 错误码 | 说明 |
|--------|------|
| 0 | 正常 |
| 1 | 传感器故障 |
| 2 | 温度异常 |
| 3 | 通信超时 |
| 4 | 校准失效 |

### 下行命令格式 (服务器 → 设备)

设备需订阅 `mcs/{SN}/down`，接收服务器下发的命令：

#### 1. 调试模式

```json
{
  "cmd": "debug",
  "duration": 600,
  "interval": 1
}
```

| 字段 | 说明 |
|------|------|
| `duration` | 调试模式持续时间（秒） |
| `interval` | 采集间隔（秒），调试模式下通常为 1 秒 |

#### 2. 校准参数更新

```json
{
  "cmd": "calibrate",
  "k": 1.05,
  "b": 0.5,
  "t_ref": 25.0,
  "t_comp": 0.1
}
```

| 字段 | 说明 |
|------|------|
| `k` | 校准斜率 |
| `b` | 校准截距 |
| `t_ref` | 参考温度 (°C) |
| `t_comp` | 温度补偿系数 |

#### 3. 设备重启

```json
{
  "cmd": "reboot",
  "delay": 5
}
```

| 字段 | 说明 |
|------|------|
| `delay` | 延迟重启时间（秒） |

#### 4. OTA 固件升级

```json
{
  "cmd": "ota",
  "url": "https://ota.example.com/firmware/v1.2.0.bin",
  "version": "1.2.0",
  "md5": "a1b2c3d4e5f6..."
}
```

| 字段 | 说明 |
|------|------|
| `url` | 固件下载地址 |
| `version` | 目标版本号 |
| `md5` | 固件 MD5 校验值 |

### 浓度计算公式

服务器端会根据校准参数计算 PPM 浓度：

```
ppm = k × v_raw + b + t_comp × (temp - t_ref)
```

- `k`, `b`, `t_ref`, `t_comp` 由后台配置，设备无需计算
- 设备只需上报原始 `v_raw` 值

### Arduino/ESP32 示例代码

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// MQTT 配置
const char* MQTT_HOST = "mqtt.yourdomain.com";
const int   MQTT_PORT = 8883;
const char* DEVICE_SN = "GAS001";
const char* MQTT_USER = "device_GAS001";
const char* MQTT_PASS = "your_password";

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

uint16_t msgSeq = 0;

void sendData() {
    StaticJsonDocument<256> doc;
    doc["ts"] = time(nullptr);
    doc["seq"] = msgSeq++;
    doc["v_raw"] = analogRead(A0) * 3.3 / 4095 * 1000; // mV
    doc["temp"] = readTemperature();
    doc["humi"] = readHumidity();
    doc["bat"] = getBatteryPercent();
    doc["rssi"] = WiFi.RSSI();
    doc["net"] = "WiFi";
    doc["err"] = 0;
    
    char payload[256];
    serializeJson(doc, payload);
    
    char topic[64];
    sprintf(topic, "mcs/%s/up", DEVICE_SN);
    mqtt.publish(topic, payload);
}

void onMessage(char* topic, byte* payload, unsigned int length) {
    StaticJsonDocument<256> doc;
    deserializeJson(doc, payload, length);
    
    const char* cmd = doc["cmd"];
    if (strcmp(cmd, "reboot") == 0) {
        delay(doc["delay"].as<int>() * 1000);
        ESP.restart();
    } else if (strcmp(cmd, "debug") == 0) {
        // 进入调试模式
        int interval = doc["interval"].as<int>();
        // 设置采集间隔为 interval 秒
    }
}

void setup() {
    // 连接 WiFi...
    
    // 配置 TLS (生产环境)
    // espClient.setCACert(ca_cert);
    
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setCallback(onMessage);
    
    // 连接 MQTT
    String clientId = String("device_") + DEVICE_SN;
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
        // 订阅下行命令
        char downTopic[64];
        sprintf(downTopic, "mcs/%s/down", DEVICE_SN);
        mqtt.subscribe(downTopic);
    }
}

void loop() {
    mqtt.loop();
    
    static unsigned long lastSend = 0;
    if (millis() - lastSend >= 10000) { // 10秒间隔
        sendData();
        lastSend = millis();
    }
}
```

### Python/MicroPython 示例代码

适用于树莓派、工控机或 MicroPython 设备：

```python
#!/usr/bin/env python3
"""
MCS-IoT 设备端 Python 示例代码
适用于: 树莓派、Linux 工控机、MicroPython (ESP32)
"""
import json
import time
import random
import paho.mqtt.client as mqtt

# ============ 配置区 ============
MQTT_HOST = "mqtt.yourdomain.com"  # 生产环境: mqtt.yourdomain.com
MQTT_PORT = 8883                    # 生产环境: 8883 (TLS)
DEVICE_SN = "GAS001"
MQTT_USER = f"device_{DEVICE_SN}"
MQTT_PASS = "your_password"
UPLOAD_INTERVAL = 10  # 上报间隔(秒)
# ================================

class SensorDevice:
    def __init__(self):
        self.seq = 0
        self.client = mqtt.Client(client_id=DEVICE_SN)
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # 生产环境启用 TLS
        # self.client.tls_set(ca_certs="ca.crt")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{DEVICE_SN}] 连接成功")
            # 订阅下行命令
            client.subscribe(f"mcs/{DEVICE_SN}/down")
        else:
            print(f"[{DEVICE_SN}] 连接失败: {rc}")
    
    def on_message(self, client, userdata, msg):
        """处理服务器下发的命令"""
        try:
            cmd = json.loads(msg.payload.decode())
            print(f"[{DEVICE_SN}] 收到命令: {cmd}")
            
            if cmd.get("cmd") == "reboot":
                delay = cmd.get("delay", 5)
                print(f"[{DEVICE_SN}] 将在 {delay} 秒后重启...")
                time.sleep(delay)
                # os.system("reboot")  # Linux 重启
                
            elif cmd.get("cmd") == "debug":
                duration = cmd.get("duration", 600)
                interval = cmd.get("interval", 1)
                print(f"[{DEVICE_SN}] 进入调试模式: {duration}秒, 间隔{interval}秒")
                
            elif cmd.get("cmd") == "calibrate":
                k = cmd.get("k", 1.0)
                b = cmd.get("b", 0.0)
                print(f"[{DEVICE_SN}] 更新校准参数: k={k}, b={b}")
                # 保存到本地配置文件
                
        except Exception as e:
            print(f"[{DEVICE_SN}] 命令解析错误: {e}")
    
    def read_sensor(self):
        """读取传感器数据 (请替换为实际传感器读取逻辑)"""
        # 示例: 模拟数据
        return {
            "v_raw": 500 + random.uniform(-50, 50),  # 传感器电压 (mV)
            "temp": 25.0 + random.uniform(-2, 2),    # 温度 (°C)
            "humi": 50.0 + random.uniform(-5, 5),    # 湿度 (%)
            "bat": random.randint(80, 100),          # 电量 (%)
            "rssi": random.randint(-80, -60),        # 信号 (dBm)
        }
    
    def send_data(self):
        """上报传感器数据"""
        sensor = self.read_sensor()
        
        payload = {
            "ts": int(time.time()),
            "seq": self.seq,
            "v_raw": round(sensor["v_raw"], 2),
            "temp": round(sensor["temp"], 1),
            "humi": round(sensor["humi"], 1),
            "bat": sensor["bat"],
            "rssi": sensor["rssi"],
            "net": "WiFi",
            "err": 0
        }
        
        topic = f"mcs/{DEVICE_SN}/up"
        self.client.publish(topic, json.dumps(payload))
        print(f"[{DEVICE_SN}] 上报: ppm≈{payload['v_raw']:.1f}, temp={payload['temp']}°C")
        
        self.seq = (self.seq + 1) % 65536
    
    def run(self):
        """主循环"""
        print(f"[{DEVICE_SN}] 连接 {MQTT_HOST}:{MQTT_PORT}...")
        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()
        
        try:
            while True:
                self.send_data()
                time.sleep(UPLOAD_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n[{DEVICE_SN}] 停止运行")
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    device = SensorDevice()
    device.run()
```

**安装依赖：**

```bash
pip install paho-mqtt
```

**运行：**

```bash
python device.py
```

### 设备 SN 命名规范

| 类型 | 前缀 | 示例 |
|------|------|------|
| 甲烷传感器 | `GAS` | GAS001, GAS002 |
| 二氧化碳传感器 | `CO2` | CO2001, CO2002 |
| 氨气传感器 | `NH3` | NH3001, NH3002 |
| 通用传感器 | `DEV` | DEV001, DEV002 |

### 心跳与离线检测

- 设备应每 **10 秒** 上报一次数据
- 服务器在 **90 秒** 内未收到数据会将设备标记为离线
- 离线后会触发 `OFFLINE` 类型告警

---

## �🛠️ 技术栈

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11 | 主要编程语言 |
| **FastAPI** | Latest | REST API 框架 |
| **asyncio** | Built-in | 异步编程 |
| **asyncpg** | Latest | PostgreSQL 异步驱动 |
| **paho-mqtt** | Latest | MQTT 客户端 |
| **redis.asyncio** | Latest | Redis 异步客户端 |
| **boto3** | Latest | AWS S3/R2 SDK |
| **aiohttp** | Latest | 异步 HTTP 客户端 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue** | 3.x | 前端框架 |
| **TypeScript** | 5.x | 类型安全 |
| **Vite** | Latest | 构建工具 |
| **Element Plus** | Latest | UI 组件库 |
| **Vue Router** | 4.x | 路由管理 |
| **Pinia** | Latest | 状态管理 |
| **ECharts** | 5.x | 图表可视化 |
| **Axios** | Latest | HTTP 客户端 |

### 基础设施

| 技术 | 版本 | 用途 |
|------|------|------|
| **Docker** | 24+ | 容器化 |
| **Docker Compose** | 2.x | 容器编排 |
| **Mosquitto** | 2.x | MQTT Broker |
| **PostgreSQL** | 15 | 关系数据库 |
| **TimescaleDB** | Latest | 时序数据扩展 |
| **Redis** | 7.x | 缓存 |
| **Nginx** | Alpine | 反向代理 |

---

## 📁 项目结构

```
mcs-iot/
├── docker-compose.yml          # 开发环境容器编排
├── docker-compose.prod.yml     # 生产环境容器编排
├── README.md                   # 项目文档
├── license.key                 # 授权文件 (不提交到 Git)
│
├── mosquitto/                  # MQTT Broker 配置
│   └── config/
│       ├── mosquitto.conf      # Mosquitto 主配置
│       ├── passwd              # 用户密码文件
│       └── acl                 # 访问控制列表
│
├── worker/                     # 核心处理服务 (Python)
│   ├── Dockerfile              # Worker 容器构建
│   ├── requirements.txt        # Python 依赖
│   └── src/
│       ├── main.py             # 入口文件，启动所有模块
│       ├── mqtt_client.py      # MQTT 连接和消息订阅
│       ├── processor.py        # 消息处理器，解析和分发
│       ├── calibrator.py       # 浓度解算 (K/B/温度补偿)
│       ├── storage.py          # TimescaleDB 数据存储
│       ├── alarm.py            # 报警中心 (阈值/防抖/通知)
│       ├── license.py          # 授权守卫 (硬件绑定/校验)
│       ├── archiver.py         # R2 冷数据归档
│       └── scheduler.py        # 定时任务调度器
│
├── backend/                    # REST API 服务 (FastAPI)
│   ├── Dockerfile              # Backend 容器构建
│   ├── requirements.txt        # Python 依赖
│   └── src/
│       ├── __init__.py         # 包初始化
│       ├── main.py             # FastAPI 入口，路由注册
│       ├── auth.py             # 认证模块 (JWT)
│       ├── devices.py          # 设备管理 API
│       ├── alarms.py           # 报警记录 API
│       ├── config.py           # 配置管理 API
│       ├── dashboard.py        # 大屏数据 API + WebSocket
│       ├── export.py           # 数据导出 API (CSV)
│       └── commands.py         # 设备命令 API (MQTT 下行)
│
├── frontend/                   # Vue 3 前端
│   ├── Dockerfile              # 多阶段构建 (Node + Nginx)
│   ├── nginx.conf              # 容器内 Nginx 配置
│   ├── package.json            # NPM 依赖
│   ├── vite.config.ts          # Vite 配置
│   └── src/
│       ├── main.ts             # Vue 入口
│       ├── App.vue             # 根组件
│       ├── router/
│       │   └── index.ts        # 路由配置
│       ├── stores/
│       │   └── auth.ts         # Pinia 认证状态
│       ├── api/
│       │   └── index.ts        # API 封装
│       ├── layouts/
│       │   └── MainLayout.vue  # 主布局 (侧边栏+顶栏)
│       └── views/
│           ├── login/          # 登录页
│           ├── dashboard/      # 仪表盘
│           ├── devices/        # 设备管理
│           ├── alarms/         # 报警记录
│           ├── config/         # 系统配置
│           └── screen/         # 可视化大屏
│
├── nginx/                      # Nginx 配置 (生产环境)
│   ├── nginx.conf              # 反向代理配置
│   └── ssl/                    # SSL 证书目录
│
└── scripts/                    # 辅助脚本
    ├── init.sql                # 数据库初始化
    ├── simulator.py            # 设备模拟器
    ├── loadtest.py             # 并发压测工具
    ├── install.sh              # 一键安装脚本
    ├── backup.sh               # 数据库备份脚本
    └── gen_passwd.py           # Mosquitto 密码生成
```

---

## 📚 核心模块详解

### Worker 模块

| 文件 | 功能 | 说明 |
|------|------|------|
| `main.py` | 入口 | 初始化 Redis/DB/MQTT/Scheduler，启动事件循环 |
| `mqtt_client.py` | MQTT 连接 | 订阅 `mcs/+/up` 和 `mcs/+/status` |
| `processor.py` | 消息处理 | 解析 Topic/Payload，调用解算和存储 |
| `calibrator.py` | 浓度解算 | 公式: `ppm = k * v_raw + b + t_coef * (temp - 25)` |
| `storage.py` | 数据存储 | 异步写入 TimescaleDB `sensor_data` 表 |
| `alarm.py` | 报警中心 | 阈值检测 → 时段限制 → 10分钟防抖 → 多通道通知 |
| `license.py` | 授权守卫 | 硬件指纹 → 在线校验 → 72小时宽限期 |
| `archiver.py` | 数据归档 | 导出冷数据 → CSV.GZ 压缩 → 上传 R2 → 清理 |
| `scheduler.py` | 定时任务 | 离线检测/健康检查/归档/授权校验/DB优化 |

### Backend 模块

| 文件 | 功能 | API 路径 |
|------|------|----------|
| `main.py` | 入口 | 数据库连接池，路由注册，健康检查 |
| `auth.py` | 认证 | `POST /api/auth/login`, `GET /api/auth/me` |
| `devices.py` | 设备 | `GET/POST/PUT/DELETE /api/devices` |
| `alarms.py` | 报警 | `GET /api/alarms`, `POST /api/alarms/{id}/ack` |
| `config.py` | 配置 | `GET/PUT /api/config/alarm/*` |
| `dashboard.py` | 大屏 | `GET /api/dashboard/*`, `WS /api/dashboard/ws` |
| `export.py` | 导出 | `GET /api/export/sensor-data`, `GET /api/export/alarms` |
| `commands.py` | 命令 | `POST /api/commands/{sn}/*` |

### Frontend 页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 登录 | `/login` | JWT 认证，表单验证 |
| 仪表盘 | `/` | 统计卡片，实时设备列表 |
| 设备管理 | `/devices` | CRUD，校准参数配置 |
| 报警记录 | `/alarms` | 筛选，确认操作 |
| 系统配置 | `/config` | 邮件/Webhook/大屏配置 |
| 可视化大屏 | `/screen` | 全屏展示，ECharts 趋势图 |

---

## 🔌 API 端点详解

### 认证 API (`/api/auth`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录，返回 JWT Token |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 设备 API (`/api/devices`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/devices` | 获取设备列表 |
| GET | `/api/devices/{sn}` | 获取单个设备详情 |
| POST | `/api/devices` | 添加新设备 |
| PUT | `/api/devices/{sn}` | 更新设备信息 |
| DELETE | `/api/devices/{sn}` | 删除设备 |
| GET | `/api/devices/{sn}/history` | 获取历史数据 |

### 报警 API (`/api/alarms`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/alarms` | 获取报警列表 (支持筛选) |
| GET | `/api/alarms/{id}` | 获取报警详情 |
| POST | `/api/alarms/{id}/ack` | 确认报警 |

### 配置 API (`/api/config`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/config/{key}` | 获取配置项 |
| PUT | `/api/config/{key}` | 更新配置项 |

### 大屏 API (`/api/dashboard`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 获取统计数据 |
| GET | `/api/dashboard/devices` | 获取设备状态列表 |
| WS | `/api/dashboard/ws` | WebSocket 实时数据推送 |

### 导出 API (`/api/export`) 📥

| 方法 | 端点 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/export/sensor-data` | `sn`, `start`, `end` | 导出传感器数据 CSV |
| GET | `/api/export/alarms` | `sn`, `type`, `start`, `end` | 导出报警记录 CSV |

**示例：**

```bash
# 导出最近7天传感器数据
curl "http://localhost/api/export/sensor-data?start=2025-12-10&end=2025-12-16" \
  -H "Authorization: Bearer <token>" \
  -o sensor_data.csv

# 导出指定设备的报警记录
curl "http://localhost/api/export/alarms?sn=DEV001&type=HIGH" \
  -H "Authorization: Bearer <token>" \
  -o alarms.csv
```

### 设备命令 API (`/api/commands`) 📡

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/commands/{sn}/debug` | 切换调试模式 (1秒采集) |
| POST | `/api/commands/{sn}/calibrate` | 更新校准参数 |
| POST | `/api/commands/{sn}/reboot` | 远程重启设备 |
| POST | `/api/commands/{sn}/ota` | OTA 固件升级 |
| POST | `/api/commands/broadcast/debug` | 广播调试模式到所有在线设备 |

**示例：**

```bash
# 切换设备到调试模式 (10分钟)
curl -X POST "http://localhost/api/commands/DEV001/debug" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"duration": 600}'

# 更新校准参数
curl -X POST "http://localhost/api/commands/DEV001/calibrate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"k": 1.05, "b": 0.5, "t_ref": 25.0, "t_comp": 0.1}'

# 远程重启设备
curl -X POST "http://localhost/api/commands/DEV001/reboot" \
  -H "Authorization: Bearer <token>" \
  -d '{"delay": 5}'
```

### 健康检查 API (`/api/health`) 🏥

```bash
curl http://localhost/api/health
```

**响应：**

```json
{
  "status": "healthy",
  "timestamp": 1765873958.92,
  "components": {
    "database": {"status": "up", "latency_ms": 11},
    "redis": {"status": "up", "latency_ms": 1},
    "worker": {"status": "healthy"},
    "mqtt": {"status": "up", "last_message_age_sec": 45},
    "license": {"status": "valid"}
  },
  "metrics": {
    "devices_online": 95,
    "devices_offline": 5,
    "devices_total": 100,
    "alarms_today": 3
  }
}
```

---

## ⏰ 定时任务

Worker 内置定时任务调度器，自动执行以下任务：

| 执行时间 | 任务名称 | 功能 |
|----------|----------|------|
| 每分钟 | 设备离线检测 | 扫描 Redis 在线标记，标记离线设备，触发离线报警 |
| 每5分钟 | 健康检查 | 检查 DB/Redis/MQTT 状态，存储到 Redis 供 API 查询 |
| 每日 02:00 | 数据归档 | 导出冷数据到 CSV.GZ，上传 R2，清理本地 |
| 每日 03:00 | 授权校验 | 向授权服务器验证 License 有效性 |
| 每日 04:00 | 数据库优化 | 执行 VACUUM ANALYZE 更新统计信息 |

---

## 🔔 报警系统

### 报警类型

| 类型 | 触发条件 | 说明 |
|------|----------|------|
| `HIGH` | ppm > high_limit | 浓度超标报警 |
| `LOW` | ppm < low_limit | 浓度过低报警 (可选) |
| `LOW_BAT` | bat < bat_limit | 低电量报警 (默认 20%) |
| `OFFLINE` | 设备离线 | 超过 90 秒无数据上报 |

### 通知渠道

| 渠道 | 配置项 | 说明 |
|------|--------|------|
| **邮件** | SMTP 配置 | 支持 QQ/163/企业邮箱 |
| **Webhook** | URL + 平台类型 | 钉钉/飞书/企业微信 (支持加签) |
| **短信** | 阿里云 SMS | 需配置 AccessKey 和模板 |

### 时段限制

可配置工作时段，非工作时间只记录报警，不发送通知：

```json
{
  "enabled": true,
  "days": [1, 2, 3, 4, 5],
  "start": "08:00",
  "end": "18:00"
}
```

### 防抖机制

同一设备同一类型报警在 10 分钟内只触发一次，避免频繁通知。

---

## 🚀 快速开始

### 环境要求

- Docker 24+
- Docker Compose 2.x
- Git

### 一键启动

```bash
# 克隆项目
git clone https://github.com/zhizinan1997/mcs-iot.git
cd mcs-iot

# 启动所有服务
docker-compose up -d

# 查看容器状态
docker-compose ps
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | <http://localhost> | Vue Admin 界面 |
| 大屏 | <http://localhost/screen> | 可视化大屏 |
| API | <http://localhost:8000/docs> | Swagger 文档 |
| 健康检查 | <http://localhost/api/health> | 系统状态 |

### 默认账号

- **用户名**: `admin`
- **密码**: `admin123`

> ⚠️ 生产环境请立即修改默认密码！

---

## 🧪 测试工具

### 设备模拟器

```bash
# 模拟单个设备发送数据
python scripts/simulator.py
```

### 压力测试

```bash
# 模拟 100 台设备，持续 60 秒
python scripts/loadtest.py -n 100 -d 60 -i 1

# 参数说明:
#   -n: 模拟设备数量
#   -d: 测试持续时间 (秒)
#   -i: 消息间隔 (秒)
```

---

## 📊 数据库设计

### 核心表结构

```sql
-- 设备表
CREATE TABLE devices (
    sn            VARCHAR(64) PRIMARY KEY,
    name          VARCHAR(128),
    model         VARCHAR(32),
    location      VARCHAR(256),
    pos_x         FLOAT DEFAULT 50.0,         -- 大屏 X 坐标 (%)
    pos_y         FLOAT DEFAULT 50.0,         -- 大屏 Y 坐标 (%)
    calib_k       FLOAT DEFAULT 1.0,          -- 校准斜率
    calib_b       FLOAT DEFAULT 0.0,          -- 校准截距
    calib_t_ref   FLOAT DEFAULT 25.0,         -- 参考温度
    calib_t_comp  FLOAT DEFAULT 0.1,          -- 温度补偿系数
    high_limit    FLOAT DEFAULT 1000.0,       -- 高报警阈值
    low_limit     FLOAT,                      -- 低报警阈值
    bat_limit     FLOAT DEFAULT 20.0,         -- 低电量阈值
    status        VARCHAR(20) DEFAULT 'offline',
    last_seen     TIMESTAMP,
    firmware_ver  VARCHAR(32),
    created_at    TIMESTAMP DEFAULT NOW()
);

-- 传感器数据表 (TimescaleDB 超表)
CREATE TABLE sensor_data (
    time      TIMESTAMP NOT NULL,
    sn        VARCHAR(64) NOT NULL,
    v_raw     FLOAT,
    ppm       FLOAT,
    temp      FLOAT,
    humi      FLOAT,
    bat       INT,
    rssi      INT,
    err_code  INT DEFAULT 0,
    seq       INT
);

-- 报警日志表
CREATE TABLE alarm_logs (
    id           SERIAL PRIMARY KEY,
    triggered_at TIMESTAMP DEFAULT NOW(),
    sn           VARCHAR(64),
    type         VARCHAR(32),          -- HIGH/LOW/OFFLINE/LOW_BAT
    value        FLOAT,
    threshold    FLOAT,
    notified     BOOLEAN DEFAULT FALSE,
    channels     VARCHAR(128),          -- email,sms,webhook
    ack_at       TIMESTAMP,
    ack_by       VARCHAR(64)
);

-- 归档日志表
CREATE TABLE archive_logs (
    id           SERIAL PRIMARY KEY,
    archive_date DATE NOT NULL,
    file_name    VARCHAR(256),
    file_size    BIGINT,
    row_count    INT,
    r2_path      VARCHAR(512),
    status       VARCHAR(32) DEFAULT 'pending',
    created_at   TIMESTAMP DEFAULT NOW()
);

-- 操作日志表
CREATE TABLE operation_logs (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP DEFAULT NOW(),
    user_name   VARCHAR(64),
    action      VARCHAR(64),
    target_type VARCHAR(32),
    target_id   VARCHAR(64),
    details     TEXT,
    ip_address  VARCHAR(64)
);

-- 用户表
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role          VARCHAR(32) DEFAULT 'user',
    email         VARCHAR(128),
    phone         VARCHAR(32),
    is_active     BOOLEAN DEFAULT TRUE,
    last_login    TIMESTAMP,
    created_at    TIMESTAMP DEFAULT NOW()
);
```

---

## 🔐 安全特性

| 特性 | 实现 |
|------|------|
| MQTT 认证 | 用户名/密码 + ACL 访问控制 |
| MQTT 加密 | TLS 1.2+ (端口 8883) |
| API 认证 | JWT Token (24小时过期) |
| 授权保护 | 硬件指纹 + 在线校验 + 宽限期 |
| Webhook 签名 | 钉钉机器人加签验证 |

---

## 📋 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看日志
docker-compose logs -f worker
docker-compose logs -f backend

# 重启单个服务
docker-compose restart worker

# 重新构建镜像
docker-compose build --no-cache backend
docker-compose up -d backend

# 进入容器
docker exec -it mcs_worker bash
docker exec -it mcs_db psql -U postgres -d mcs_iot

# 查看数据库数据
docker-compose exec timescaledb psql -U postgres -d mcs_iot \
    -c "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 10;"

# 健康检查
curl http://localhost/api/health

# 数据库备份
./scripts/backup.sh
```

---

## 🔧 运维脚本

### 数据库备份 (`scripts/backup.sh`)

```bash
# 手动执行备份
./scripts/backup.sh

# 设置定时备份 (每周日凌晨3点)
crontab -e
# 添加: 0 3 * * 0 /opt/mcs-iot/scripts/backup.sh
```

### 功能

- pg_dump 全量备份
- gzip 压缩
- 可选上传到 R2
- 自动清理 7 天前备份

---

## 📄 开源协议

**Proprietary License** - 元芯传感 © 2025

本项目为商业项目，未经授权不得用于商业用途。

---

## 📞 联系方式

- **公司**: 元芯传感
- **邮箱**: <contact@metachip-iot.com>
- **GitHub**: <https://github.com/zhizinan1997/mcs-iot>
