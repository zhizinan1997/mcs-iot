# MCS-IoT 工业级气体监测物联网平台

专为工业气体监测场景设计的物联网云平台，支持实时数据采集、可视化大屏、智能报警、设备管理和 AI 分析。

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3.5-42b883?logo=vue.js" alt="Vue 3.5"/>
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/TimescaleDB-PG15-1E90FF?logo=postgresql" alt="TimescaleDB"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/MQTT-TLS-660066" alt="MQTT TLS"/>
</p>

---

## 目录

- [🚀 一键部署](#-一键部署)
- [📖 系统架构](#-系统架构)
- [🔧 技术栈](#-技术栈)
- [📁 项目结构](#-项目结构)
- [🐳 Docker 容器详解](#-docker-容器详解)
- [🗄️ 数据库结构](#️-数据库结构)
- [📡 API 接口](#-api-接口)
- [🔌 设备接入](#-设备接入)
- [🔐 授权系统](#-授权系统)
- [🛠️ 服务管理](#️-服务管理)
- [❓ 常见问题](#-常见问题)

---

## 🚀 一键部署

支持 Ubuntu 20.04+、CentOS 7+、OpenCloudOS、Debian 10+

```bash
# 一键部署（自动拉取最新脚本）
bash <(curl -sSL https://raw.githubusercontent.com/zhizinan1997/mcs-iot/main/scripts/deploy.sh)
```

### 部署流程

1. ✅ 检测系统环境和服务器资源
2. ✅ 安装 Docker 和必要依赖
3. ✅ 输入一级域名，自动生成 4 个子域名
4. ✅ 引导在宝塔面板配置 DNS、反向代理、SSL 证书
5. ✅ 自动复制 SSL 证书到项目目录
6. ✅ 配置数据库密码、管理员密码、MQTT 密码
7. ✅ 拉取预构建 Docker 镜像并启动

### 域名配置

输入一级域名（如 `zhizinan.top`），脚本自动生成：

| 子域名                | 用途      | 反向代理目标            |
| --------------------- | --------- | ----------------------- |
| `iot.zhizinan.top`    | 管理后台  | `http://127.0.0.1:3000` |
| `api.zhizinan.top`    | API 接口  | `http://127.0.0.1:8000` |
| `screen.zhizinan.top` | 大屏展示  | `http://127.0.0.1:3000` |
| `mqtt.zhizinan.top`   | MQTT 服务 | 端口 8883 (TLS)         |

> ⚠️ **重要提示**: 反向代理目标必须使用 `127.0.0.1`，不能使用公网 IP，否则会导致 502 错误！

---

## 📖 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户访问层                                  │
│   浏览器 (管理后台/大屏)    │    IoT 设备 (MQTT 上报)               │
└───────────────┬─────────────┴──────────────────┬────────────────────┘
                │                                │
                ▼                                ▼
┌───────────────────────────────┐    ┌───────────────────────────────┐
│       Nginx (宝塔面板)        │    │      Mosquitto MQTT Broker    │
│   反向代理 + SSL 终止         │    │   端口: 1883 (TCP) / 8883 (TLS)│
└───────────────┬───────────────┘    └───────────────┬───────────────┘
                │                                    │
                ▼                                    ▼
┌───────────────────────────────┐    ┌───────────────────────────────┐
│        Frontend (Vue3)        │    │         Worker (Python)       │
│    端口: 3000 → Nginx:80      │    │   MQTT 订阅 → 数据处理 → 存储  │
└───────────────┬───────────────┘    └───────────────┬───────────────┘
                │ API 请求                           │ 数据写入
                ▼                                    ▼
┌───────────────────────────────┐    ┌───────────────────────────────┐
│       Backend (FastAPI)       │    │      TimescaleDB (PG15)       │
│   端口: 8000 (RESTful API)    │◄───│   时序数据库 (自动压缩)        │
└───────────────┬───────────────┘    └───────────────────────────────┘
                │                                    ▲
                ▼                                    │
┌───────────────────────────────┐                    │
│         Redis (缓存)          │────────────────────┘
│   实时状态 / 会话 / 设备缓存   │
└───────────────────────────────┘
```

---

## 🔧 技术栈

### Backend (Python)

| 组件             | 版本   | 用途                   |
| ---------------- | ------ | ---------------------- |
| FastAPI          | Latest | Web 框架               |
| asyncpg          | Latest | 异步 PostgreSQL 驱动   |
| Redis            | Latest | 缓存和会话管理         |
| paho-mqtt        | 1.6+   | MQTT 客户端 (下发指令) |
| python-jose      | Latest | JWT 认证               |
| passlib + bcrypt | 4.0.1  | 密码哈希               |
| boto3            | Latest | S3/R2 对象存储         |
| httpx + aiohttp  | Latest | HTTP 客户端            |
| loguru           | Latest | 日志管理               |

### Worker (Python)

| 组件         | 版本   | 用途                |
| ------------ | ------ | ------------------- |
| paho-mqtt    | 1.6.1  | MQTT 订阅和消息处理 |
| asyncpg      | Latest | 异步数据库写入      |
| numpy        | Latest | 数据校准计算        |
| cryptography | Latest | 授权文件加解密      |
| boto3        | Latest | 数据归档到 R2       |

### Frontend (TypeScript/Vue)

| 组件         | 版本  | 用途               |
| ------------ | ----- | ------------------ |
| Vue          | 3.5+  | 前端框架           |
| Vite         | 7.2+  | 构建工具           |
| Element Plus | 2.12+ | UI 组件库          |
| ECharts      | 6.0+  | 数据可视化图表     |
| vue-echarts  | 8.0+  | Vue 封装的 ECharts |
| Pinia        | 3.0+  | 状态管理           |
| Axios        | 1.13+ | HTTP 请求          |
| vue-router   | 4.6+  | 路由管理           |

### 基础设施

| 组件        | 版本     | 用途                   |
| ----------- | -------- | ---------------------- |
| TimescaleDB | PG15     | 时序数据库 (自动压缩)  |
| Redis       | 7-alpine | 缓存 (LRU 策略, 256MB) |
| Mosquitto   | 2.x      | MQTT Broker (TLS 支持) |
| Docker      | 20.10+   | 容器运行时             |

---

## 📁 项目结构

```
mcs-iot/
├── backend/                    # 后端 API 服务
│   ├── Dockerfile              # 后端镜像构建
│   ├── requirements.txt        # Python 依赖
│   └── src/
│       ├── main.py             # FastAPI 入口
│       ├── auth.py             # 用户认证 (JWT)
│       ├── devices.py          # 设备管理 API
│       ├── instruments.py      # 仪表/分组管理
│       ├── dashboard.py        # 仪表盘实时数据
│       ├── alarms.py           # 报警管理
│       ├── config.py           # 系统配置 API
│       ├── commands.py         # 设备指令下发
│       ├── export.py           # 数据导出
│       ├── health.py           # 系统健康检查
│       ├── logs.py             # 操作日志
│       ├── license.py          # 授权验证
│       ├── ai.py               # AI 分析接口
│       ├── mqtt.py             # MQTT 发布 (指令下发)
│       ├── uploads.py          # 文件上传
│       └── deps.py             # 依赖注入
│
├── worker/                     # 核心数据处理服务
│   ├── Dockerfile              # Worker 镜像构建
│   ├── requirements.txt        # Python 依赖
│   └── src/
│       ├── main.py             # Worker 入口
│       ├── mqtt_client.py      # MQTT 订阅客户端
│       ├── processor.py        # 数据处理管道
│       ├── calibrator.py       # 传感器校准算法
│       ├── storage.py          # 数据库写入
│       ├── alarm.py            # 报警检测与通知
│       ├── archiver.py         # 数据归档到 R2
│       ├── scheduler.py        # 定时任务调度
│       └── license.py          # 授权检查
│
├── frontend/                   # 前端 Vue3 应用
│   ├── Dockerfile              # 前端镜像构建
│   ├── package.json            # npm 依赖
│   ├── vite.config.ts          # Vite 配置
│   ├── nginx.conf              # Nginx 配置 (容器内)
│   └── src/
│       ├── views/              # 页面组件
│       ├── components/         # 通用组件
│       ├── stores/             # Pinia 状态
│       ├── router/             # Vue Router
│       └── api/                # API 请求封装
│
├── scripts/                    # 部署和管理脚本
│   ├── deploy.sh               # 一键部署脚本 (主入口)
│   ├── backup.sh               # 数据库备份脚本
│   ├── uninstall.sh            # 卸载脚本
│   ├── init.sql                # 数据库初始化 SQL
│   ├── demo_generator.py       # 模拟数据生成器
│   └── mqtt_config.json        # MQTT 配置模板
│
├── mosquitto/                  # MQTT 配置
│   ├── config/
│   │   ├── mosquitto.conf      # Mosquitto 主配置
│   │   ├── passwd              # 用户密码文件
│   │   └── acl                 # 访问控制列表
│   ├── data/                   # 数据目录 (持久化)
│   └── log/                    # 日志目录
│
├── nginx/                      # Nginx 配置
│   ├── nginx-simple.conf       # 简化版配置
│   ├── nginx.conf              # 完整版配置
│   └── ssl/                    # SSL 证书目录
│       ├── server.crt          # 服务器证书
│       ├── server.key          # 私钥
│       └── ca.crt              # CA 证书
│
├── docs/                       # 文档
│   ├── ESP32_SDK.md            # ESP32 设备接入 SDK
│   ├── Python_SDK.md           # Python 设备接入 SDK
│   └── 技术细节.md             # 技术实现细节
│
├── cfworker/                   # Cloudflare Worker
│   └── license-server.js       # 授权服务器代码
│
├── .github/workflows/          # GitHub Actions
│   └── docker-publish.yml      # 自动构建 Docker 镜像
│
├── docker-compose.yml          # 开发环境 Compose
├── docker-compose.ghcr.yml     # 生产环境 Compose (预构建镜像)
├── .env.example                # 环境变量模板
└── README.md                   # 本文档
```

---

## 🐳 Docker 容器详解

### 容器列表

| 容器名          | 镜像                                | 端口        | 功能          |
| --------------- | ----------------------------------- | ----------- | ------------- |
| `mcs_mosquitto` | `eclipse-mosquitto:2`               | 1883, 8883  | MQTT 消息代理 |
| `mcs_db`        | `timescale/timescaledb:latest-pg15` | 5432 (内部) | 时序数据库    |
| `mcs_redis`     | `redis:7-alpine`                    | 6379 (内部) | 缓存服务      |
| `mcs_worker`    | `ghcr.io/.../mcs-iot-worker`        | -           | 数据处理      |
| `mcs_backend`   | `ghcr.io/.../mcs-iot-backend`       | 8000        | API 服务      |
| `mcs_frontend`  | `ghcr.io/.../mcs-iot-frontend`      | 3000        | Web 前端      |

### 1. Mosquitto MQTT Broker

**功能**: 接收设备上报的传感器数据，支持 TLS 加密连接

**配置文件**: `mosquitto/config/mosquitto.conf`

```conf
# TCP 监听 (内网/开发用)
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwd

# TLS 监听 (生产环境)
listener 8883
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
```

**环境变量**: 无 (通过配置文件)

**卷挂载**:

- `./mosquitto/config` → `/mosquitto/config` (配置)
- `./nginx/ssl` → `/mosquitto/certs` (证书)

---

### 2. TimescaleDB 数据库

**功能**: 存储时序传感器数据，自动压缩历史数据

**特性**:

- 基于 PostgreSQL 15
- 按天分区 (chunk_time_interval = 1 day)
- 自动压缩 1 天前的数据
- 按设备 SN 分段压缩

**环境变量**:
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `POSTGRES_DB` | `mcs_iot` | 数据库名 |
| `POSTGRES_USER` | `postgres` | 用户名 |
| `POSTGRES_PASSWORD` | `changeme` | 密码 |

---

### 3. Redis 缓存

**功能**: 缓存设备实时状态、用户会话、API 响应

**配置**:

- 最大内存: 256MB
- 淘汰策略: allkeys-lru (优先删除最少使用)
- 持久化: appendonly (AOF)

---

### 4. Worker 数据处理服务

**功能**:

- 订阅 MQTT 消息并解析
- 应用校准公式计算 PPM 浓度
- 写入 TimescaleDB 时序数据
- 检测报警条件并发送通知
- 定时归档历史数据到 R2

**环境变量**:
| 变量 | 说明 |
|------|------|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` | 数据库连接 |
| `REDIS_HOST` | Redis 地址 |
| `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS` | MQTT 连接 |
| `DEV_MODE` | 开发模式 (跳过授权检查) |

**核心模块**:

| 模块             | 功能                                                                    |
| ---------------- | ----------------------------------------------------------------------- |
| `mqtt_client.py` | MQTT 订阅和消息分发                                                     |
| `processor.py`   | 数据验证和转换                                                          |
| `calibrator.py`  | 传感器校准算法: `ppm = (v_raw * k + b) * (1 + t_comp * (temp - t_ref))` |
| `storage.py`     | 异步批量写入数据库                                                      |
| `alarm.py`       | 报警检测 (高限/低限/离线/低电量)                                        |
| `archiver.py`    | 定时归档到 Cloudflare R2                                                |
| `scheduler.py`   | 定时任务 (归档/清理/AI 分析)                                            |

---

### 5. Backend API 服务

**功能**: 提供 RESTful API，支持 WebSocket 实时推送

**环境变量**:
| 变量 | 说明 |
|------|------|
| `JWT_SECRET` | JWT 签名密钥 |
| `ADMIN_INITIAL_PASSWORD` | 管理员初始密码 |
| `AI_API_KEY`, `AI_MODEL` | AI 分析 API 配置 |
| `WEATHER_API_KEY` | 天气 API (心知天气) |

**API 模块**:

| 模块             | 路由前缀           | 功能                     |
| ---------------- | ------------------ | ------------------------ |
| `auth.py`        | `/api/auth`        | 用户登录/登出/Token 刷新 |
| `devices.py`     | `/api/devices`     | 设备 CRUD / 状态查询     |
| `instruments.py` | `/api/instruments` | 仪表分组管理             |
| `dashboard.py`   | `/api/dashboard`   | 仪表盘数据 / WebSocket   |
| `alarms.py`      | `/api/alarms`      | 报警记录 / 确认          |
| `config.py`      | `/api/config`      | 系统配置 (通知/阈值等)   |
| `commands.py`    | `/api/commands`    | 设备指令下发             |
| `export.py`      | `/api/export`      | 数据导出 (CSV/Excel)     |
| `health.py`      | `/api/health`      | 健康检查 / 系统状态      |
| `logs.py`        | `/api/logs`        | 操作日志查询             |
| `ai.py`          | `/api/ai`          | AI 智能分析              |
| `license.py`     | `/api/license`     | 授权状态查询             |

---

### 6. Frontend 前端服务

**功能**: Vue3 单页应用，包含管理后台和数据大屏

**页面**:

- `/` - 仪表盘 (设备状态总览)
- `/devices` - 设备管理
- `/alarms` - 报警记录
- `/config` - 系统配置
- `/screen` - 可视化大屏 (全屏展示)

**Nginx 配置** (容器内):

```nginx
location /api/ {
    set $backend_url http://backend:8000;
    resolver 127.0.0.11 valid=10s;
    proxy_pass $backend_url;
}
```

---

## 🗄️ 数据库结构

### 表结构概览

```
┌─────────────────┐     ┌─────────────────┐
│   instruments   │     │     devices     │
│   (仪表分组)     │◄────│   (设备管理)     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐
│   sensor_data   │     │   alarm_logs    │
│  (时序数据表)    │     │   (报警记录)     │
│  [Hypertable]   │     └─────────────────┘
└─────────────────┘
                        ┌─────────────────┐
┌─────────────────┐     │  system_config  │
│     users       │     │   (系统配置)     │
│   (用户管理)     │     └─────────────────┘
└─────────────────┘
                        ┌─────────────────┐
┌─────────────────┐     │  archive_logs   │
│ operation_logs  │     │   (归档记录)     │
│   (操作日志)     │     └─────────────────┘
└─────────────────┘
```

### 1. instruments (仪表/分组)

| 字段             | 类型         | 说明           |
| ---------------- | ------------ | -------------- |
| `id`             | SERIAL       | 主键           |
| `name`           | VARCHAR(128) | 仪表名称       |
| `description`    | TEXT         | 描述           |
| `color`          | VARCHAR(16)  | 显示颜色       |
| `pos_x`, `pos_y` | FLOAT        | 大屏坐标 (%)   |
| `is_displayed`   | BOOLEAN      | 是否显示在大屏 |
| `sort_order`     | INT          | 排序顺序       |

### 2. devices (设备管理)

| 字段                          | 类型         | 说明                  |
| ----------------------------- | ------------ | --------------------- |
| `sn`                          | VARCHAR(64)  | 设备序列号 (主键)     |
| `name`                        | VARCHAR(128) | 设备名称              |
| `model`                       | VARCHAR(32)  | 型号                  |
| `location`                    | VARCHAR(256) | 安装位置              |
| `sensor_type`                 | VARCHAR(32)  | 传感器类型            |
| `unit`                        | VARCHAR(16)  | 单位                  |
| `instrument_id`               | INT          | 所属仪表 (外键)       |
| `calib_k`, `calib_b`          | FLOAT        | 校准参数 (斜率/截距)  |
| `calib_t_ref`, `calib_t_comp` | FLOAT        | 温度补偿参数          |
| `high_limit`, `low_limit`     | FLOAT        | 报警阈值              |
| `bat_limit`                   | FLOAT        | 低电量阈值            |
| `status`                      | VARCHAR(20)  | 状态 (online/offline) |
| `last_seen`                   | TIMESTAMP    | 最后在线时间          |

### 3. sensor_data (时序数据) [Hypertable]

| 字段       | 类型        | 说明       |
| ---------- | ----------- | ---------- |
| `time`     | TIMESTAMP   | 时间戳     |
| `sn`       | VARCHAR(64) | 设备 SN    |
| `v_raw`    | FLOAT       | 原始值     |
| `ppm`      | FLOAT       | 校准后浓度 |
| `temp`     | FLOAT       | 温度       |
| `humi`     | FLOAT       | 湿度       |
| `bat`      | INT         | 电池电量   |
| `rssi`     | INT         | 信号强度   |
| `err_code` | INT         | 错误码     |

**TimescaleDB 特性**:

- 按天自动分区
- 1 天后自动压缩
- 按 `sn` 分段压缩

### 4. alarm_logs (报警记录)

| 字段           | 类型         | 说明                            |
| -------------- | ------------ | ------------------------------- |
| `id`           | SERIAL       | 主键                            |
| `triggered_at` | TIMESTAMP    | 触发时间                        |
| `sn`           | VARCHAR(64)  | 设备 SN                         |
| `type`         | VARCHAR(32)  | 类型 (HIGH/LOW/OFFLINE/LOW_BAT) |
| `value`        | FLOAT        | 触发时的值                      |
| `threshold`    | FLOAT        | 阈值                            |
| `status`       | VARCHAR(32)  | 状态 (active/ack/resolved)      |
| `notified`     | BOOLEAN      | 是否已通知                      |
| `channels`     | VARCHAR(128) | 通知渠道                        |

### 5. system_config (系统配置)

键值对存储，value 为 JSON 格式：

| Key          | 说明                         |
| ------------ | ---------------------------- |
| `email`      | 邮件通知配置                 |
| `sms`        | 短信通知配置 (阿里云)        |
| `webhook`    | Webhook 通知 (钉钉/企业微信) |
| `alarm_time` | 报警时间窗口                 |
| `dashboard`  | 大屏配置 (标题/背景/刷新率)  |
| `archive`    | 数据归档配置 (R2)            |

### 6. users (用户管理)

| 字段            | 类型         | 说明              |
| --------------- | ------------ | ----------------- |
| `id`            | SERIAL       | 主键              |
| `username`      | VARCHAR(64)  | 用户名            |
| `password_hash` | VARCHAR(256) | 密码哈希          |
| `role`          | VARCHAR(32)  | 角色 (admin/user) |
| `is_active`     | BOOLEAN      | 是否激活          |

---

## 📡 API 接口

### 认证

所有 API 需要 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer <token>" https://api.example.com/api/devices
```

### 主要接口

| 方法   | 路径                      | 说明               |
| ------ | ------------------------- | ------------------ |
| POST   | `/api/auth/login`         | 用户登录           |
| GET    | `/api/devices`            | 获取设备列表       |
| POST   | `/api/devices`            | 添加设备           |
| GET    | `/api/devices/{sn}`       | 获取设备详情       |
| PUT    | `/api/devices/{sn}`       | 更新设备           |
| DELETE | `/api/devices/{sn}`       | 删除设备           |
| GET    | `/api/dashboard/realtime` | 实时数据           |
| WS     | `/api/dashboard/ws`       | WebSocket 实时推送 |
| GET    | `/api/alarms`             | 报警列表           |
| POST   | `/api/alarms/{id}/ack`    | 确认报警           |
| GET    | `/api/export/data`        | 导出数据           |

---

## 🔌 设备接入

### MQTT 连接参数

| 参数   | 值                      |
| ------ | ----------------------- |
| Broker | `mqtt.yourdomain.com`   |
| 端口   | 8883 (TLS) / 1883 (TCP) |
| 用户名 | 部署时配置的 MQTT 用户  |
| 密码   | 部署时配置的 MQTT 密码  |

### 上行数据 (设备 → 服务器)

**Topic**: `mcs/{设备SN}/up`

```json
{
  "ts": 1702723200, // Unix 时间戳
  "seq": 123, // 序列号
  "v_raw": 2045.5, // 传感器原始值
  "temp": 25.3, // 温度 (°C)
  "humi": 45.2, // 湿度 (%)
  "bat": 85, // 电池 (%)
  "rssi": -72, // 信号强度 (dBm)
  "net": "4G", // 网络类型
  "err": 0 // 错误码
}
```

### 下行指令 (服务器 → 设备)

**Topic**: `mcs/{设备SN}/down`

```json
{
  "cmd": "config",
  "params": {
    "interval": 10
  }
}
```

支持的指令: `config`, `reboot`, `update`

### 硬件开发文档

- [ESP32 设备接入 SDK](docs/ESP32_SDK.md) - 完整驱动库和示例代码
- [Python 设备接入 SDK](docs/Python_SDK.md) - Python 版本 SDK

---

## 🔐 授权系统

本项目包含基于 Cloudflare Worker 的授权管理系统。

### 授权验证流程

1. Worker 启动时生成设备 ID (主机名 + MAC + 硬件特征)
2. 向授权服务器发送验证请求
3. 验证通过后缓存授权状态 24 小时
4. 验证失败有 1 天宽限期

### 未授权限制

| 功能      | 限制       |
| --------- | ---------- |
| 设备数量  | 最多 10 台 |
| 外网 MQTT | 禁用       |
| AI 分析   | 禁用       |
| R2 归档   | 禁用       |
| 报警通知  | 禁用       |

### 部署授权服务器

详见 [授权系统部署文档](#授权系统) 或 `cfworker/license-server.js`

---

## 🛠️ 服务管理

```bash
# 服务控制
mcs-iot start      # 启动所有服务
mcs-iot stop       # 停止所有服务
mcs-iot restart    # 重启所有服务
mcs-iot status     # 查看容器状态
mcs-iot logs       # 查看日志 (跟随模式)
mcs-iot update     # 拉取最新镜像并重启

# 模拟器 (测试用)
mcs-simulator-start    # 启动 24 个模拟传感器
mcs-simulator-stop     # 停止模拟器

# 数据库操作
mcs-iot logs db        # 查看数据库日志
docker exec -it mcs_db psql -U postgres mcs_iot  # 进入数据库
```

### 升级方法

```bash
cd /opt/mcs-iot
bash scripts/deploy.sh
# 选择 1 - 更新到最新版本
```

升级自动执行: 备份数据库 → 拉取代码 → 更新镜像 → 重启服务

---

## ❓ 常见问题

### 1. 容器无法启动

```bash
mcs-iot status    # 查看容器状态
mcs-iot logs      # 查看日志
docker logs mcs_worker --tail 100  # 查看特定容器日志
```

### 2. 502 Bad Gateway

**原因**: 宝塔反向代理配置使用了公网 IP 而非 127.0.0.1

**解决**:

```bash
# 修改 Nginx 配置
sed -i 's|proxy_pass http://公网IP:3000;|proxy_pass http://127.0.0.1:3000;|g' \
    /www/server/panel/vhost/nginx/iot.yourdomain.com.conf
nginx -t && nginx -s reload
```

### 3. MQTT 连接失败

- 检查 SSL 证书是否在 `/opt/mcs-iot/nginx/ssl/`
- 确保文件名为 `server.crt` 和 `server.key`
- 检查 8883 端口是否开放
- 重启服务: `mcs-iot restart`

### 4. 数据库备份恢复

```bash
# 备份
docker exec mcs_db pg_dump -U postgres mcs_iot > backup.sql

# 恢复
cat backup.sql | docker exec -i mcs_db psql -U postgres mcs_iot
```

---

## 📄 许可证

MIT License

---

## 联系方式

**开发者**: Ryan Zhi  
**邮箱**: <zinanzhi@gmail.com>  
**GitHub**: [zhizinan1997/mcs-iot](https://github.com/zhizinan1997/mcs-iot)
