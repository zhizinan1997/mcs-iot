# MCS-IoT 工业级气体监测系统

[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)]()

## 📖 项目概述

MCS-IoT (Metachip Cloud Sense) 是一套**低成本、高并发、商业保护**的工业物联网气体监测平台。

### ✨ 核心特性

- 🔧 **极低成本**：年运营成本 ¥189 (100台设备规模)
- 🚀 **高并发**：单服务器支持 500+ 设备
- 🔐 **商业保护**：硬件绑定 + 在线授权 + 宽限期机制
- 📊 **可视化大屏**：ECharts + WebSocket 实时展示
- 📦 **冷热分离**：TimescaleDB + R2 自动归档

## 🏗️ 系统架构

```
感知层 → 传输层 → 计算层 → 存储层 → 应用层
(设备)   (MQTT)   (Worker)  (DB)    (Admin)
```

### Docker 容器

| 容器 | 用途 | 端口 |
|------|------|------|
| mosquitto | MQTT Broker | 1883, 8883 |
| timescaledb | 时序数据库 | 5432 |
| redis | 缓存 | 6379 |
| worker | 核心处理 | - |
| backend | REST API | 8000 |
| nginx | 反向代理 | 80, 443 |

## 🚀 快速开始

### 开发环境

```bash
# 克隆项目
git clone https://github.com/zhizinan1997/mcs-iot.git
cd mcs-iot

# 启动服务
docker-compose up -d

# 启动前端开发服务器
cd frontend
npm install
npm run dev
```

### 生产部署

```bash
# 使用一键安装脚本 (Ubuntu/Debian)
sudo bash scripts/install.sh

# 或手动部署
docker-compose -f docker-compose.prod.yml up -d
```

## 📁 目录结构

```
mcs-iot/
├── docker-compose.yml        # 开发环境编排
├── docker-compose.prod.yml   # 生产环境编排
├── mosquitto/                # MQTT 配置
│   └── config/
├── worker/                   # 核心处理模块
│   └── src/
│       ├── main.py          # 入口
│       ├── mqtt_client.py   # MQTT 连接
│       ├── processor.py     # 消息处理
│       ├── calibrator.py    # 浓度解算
│       ├── storage.py       # 数据存储
│       ├── alarm.py         # 报警中心
│       ├── license.py       # 授权守卫
│       └── archiver.py      # R2 归档
├── backend/                  # FastAPI 后端
│   └── src/
│       ├── main.py          # API 入口
│       ├── auth.py          # 认证
│       ├── devices.py       # 设备管理
│       ├── alarms.py        # 报警记录
│       ├── config.py        # 配置管理
│       └── dashboard.py     # 大屏数据
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── views/
│       │   ├── login/       # 登录页
│       │   ├── dashboard/   # 仪表盘
│       │   ├── devices/     # 设备管理
│       │   ├── alarms/      # 报警记录
│       │   ├── config/      # 配置
│       │   └── screen/      # 可视化大屏
│       ├── router/          # 路由
│       ├── stores/          # Pinia 状态
│       └── api/             # API 封装
├── nginx/                    # Nginx 配置
└── scripts/                  # 辅助脚本
    ├── init.sql             # 数据库初始化
    ├── simulator.py         # 设备模拟器
    ├── loadtest.py          # 压力测试
    └── install.sh           # 一键安装
```

## 🔐 API 文档

启动后访问: <http://localhost:8000/docs>

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/auth/login` | POST | 登录获取 JWT |
| `/api/devices` | GET/POST | 设备列表/创建 |
| `/api/devices/{sn}` | GET/PUT/DELETE | 设备详情/更新/删除 |
| `/api/alarms` | GET | 报警记录 |
| `/api/config/*` | GET/PUT | 配置管理 |
| `/api/dashboard/ws` | WebSocket | 实时数据推送 |

## 🧪 测试

### 设备模拟

```bash
python scripts/simulator.py
```

### 压力测试

```bash
# 模拟 100 设备，持续 60 秒
python scripts/loadtest.py -n 100 -d 60
```

## 📊 开发进度

- [x] Phase 1: 基础设施 (Docker + MQTT + DB)
- [x] Phase 2: 核心联调 (Worker + 数据流)
- [x] Phase 3: 管理闭环 (报警 + 授权 + API + Admin)
- [x] Phase 4: 可视化大屏 (WebSocket + ECharts)
- [x] Phase 5: 归档交付 (R2 + 压测 + 部署)

## 📄 License

Proprietary - 元芯传感 © 2025
