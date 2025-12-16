# MCS-IoT 工业级气体监测系统

[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)

## 📖 项目概述

**MCS-IoT** (Metachip Cloud Sense) 是一套专为工业气体监测场景设计的物联网平台，具备以下核心优势：

| 特性 | 说明 |
|------|------|
| � **极低成本** | 年运营成本 ¥189 (100台设备规模) |
| 🚀 **高并发** | 单服务器支持 500+ 设备同时在线 |
| 🔐 **商业保护** | 硬件绑定 + 在线授权 + 72h宽限期 |
| 📊 **实时可视化** | WebSocket + ECharts 大屏展示 |
| 📦 **冷热分离** | TimescaleDB 热存储 + R2 冷归档 |

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
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        计算层 (Compute Layer)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Worker (Python)                        │   │
│  │  • MQTT 订阅       • 浓度解算      • 报警检测              │   │
│  │  • 数据存储        • 授权守卫      • 数据归档              │   │
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

## �️ 技术栈

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
│       └── archiver.py         # R2 冷数据归档
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
│       └── dashboard.py        # 大屏数据 API + WebSocket
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
    └── gen_passwd.py           # Mosquitto 密码生成
```

---

## � 核心模块详解

### Worker 模块

| 文件 | 功能 | 说明 |
|------|------|------|
| `main.py` | 入口 | 初始化 Redis/DB/MQTT，启动事件循环 |
| `mqtt_client.py` | MQTT 连接 | 订阅 `mcs/+/up` 和 `mcs/+/status` |
| `processor.py` | 消息处理 | 解析 Topic/Payload，调用解算和存储 |
| `calibrator.py` | 浓度解算 | 公式: `ppm = k * v_raw + b + t_coef * (temp - 25)` |
| `storage.py` | 数据存储 | 异步写入 TimescaleDB `sensor_data` 表 |
| `alarm.py` | 报警中心 | 阈值检测 → 10分钟防抖 → 邮件/Webhook/SMS |
| `license.py` | 授权守卫 | 硬件指纹 → 在线校验 → 72小时宽限期 |
| `archiver.py` | 数据归档 | 导出 3 天前数据 → 压缩 → 上传 R2 → 清理 |

### Backend 模块

| 文件 | 功能 | API 路径 |
|------|------|----------|
| `main.py` | 入口 | 数据库连接池，路由注册 |
| `auth.py` | 认证 | `POST /api/auth/login`, `GET /api/auth/me` |
| `devices.py` | 设备 | `GET/POST/PUT/DELETE /api/devices` |
| `alarms.py` | 报警 | `GET /api/alarms`, `POST /api/alarms/{id}/ack` |
| `config.py` | 配置 | `GET/PUT /api/config/alarm/*` |
| `dashboard.py` | 大屏 | `GET /api/dashboard/*`, `WS /api/dashboard/ws` |

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
    sn          VARCHAR(32) PRIMARY KEY,
    name        VARCHAR(64),
    model       VARCHAR(32),
    high_limit  DECIMAL(10,2) DEFAULT 1000,
    low_limit   DECIMAL(10,2),
    k_val       DECIMAL(10,4) DEFAULT 1.0,
    b_val       DECIMAL(10,4) DEFAULT 0.0,
    t_coef      DECIMAL(10,4) DEFAULT 0.0,
    status      VARCHAR(16) DEFAULT 'offline',
    last_seen   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 传感器数据表 (TimescaleDB 超表)
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ NOT NULL,
    sn          VARCHAR(32) NOT NULL,
    v_raw       DECIMAL(10,2),
    ppm         DECIMAL(10,2),
    temp        DECIMAL(5,1),
    humi        DECIMAL(5,1),
    bat         INTEGER,
    rssi        INTEGER,
    err_code    INTEGER,
    msg_seq     INTEGER
);

-- 报警日志表
CREATE TABLE alarm_logs (
    id          SERIAL PRIMARY KEY,
    time        TIMESTAMPTZ DEFAULT NOW(),
    sn          VARCHAR(32),
    type        VARCHAR(16),
    value       DECIMAL(10,2),
    threshold   DECIMAL(10,2),
    status      VARCHAR(16) DEFAULT 'new',
    notified    BOOLEAN DEFAULT FALSE
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
docker-compose build --no-cache frontend
docker-compose up -d frontend

# 进入容器
docker exec -it mcs_worker bash
docker exec -it mcs_db psql -U postgres -d mcs_iot

# 查看数据库数据
docker-compose exec timescaledb psql -U postgres -d mcs_iot \
    -c "SELECT * FROM sensor_data ORDER BY time DESC LIMIT 10;"
```

---

## 📄 开源协议

**Proprietary License** - 元芯传感 © 2025

本项目为商业项目，未经授权不得用于商业用途。

---

## 📞 联系方式

- **公司**: 元芯传感
- **邮箱**: <contact@metachip-iot.com>
- **GitHub**: <https://github.com/zhizinan1997/mcs-iot>
