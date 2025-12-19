# MCS-IoT 工业级气体监测物联网平台

专为工业气体监测场景设计的物联网云平台，支持实时数据采集、可视化大屏、智能报警、设备管理和 AI 分析。

---

## 🚀 一键部署

支持 Ubuntu 20.04+、CentOS 7+、OpenCloudOS、Debian 10+

```bash
# 一键部署（自动拉取最新脚本）
bash <(curl -sSL https://raw.githubusercontent.com/zhizinan1997/mcs-iot/main/scripts/deploy.sh)
```

**首次安装自动完成：**

- ✅ 环境检测与依赖安装 (Docker)
- ✅ 域名配置与 API 密钥配置
- ✅ 拉取预构建 Docker 镜像 (无需本地构建)
- ✅ 数据库初始化
- ✅ 可选导入演示数据

**已有安装时自动检测，支持：**

- 🔄 更新到最新版本 (保留数据)
- 💾 自动备份数据库
- 📦 拉取最新镜像并重启

> ⚠️ **注意**: SSL 证书需要在宝塔面板中手动申请和配置

---

## 🆕 最新功能

- **授权管理系统** - 基于 Cloudflare Worker 的设备授权验证
- **防破解机制** - 代码完整性校验 + 篡改自动上报
- **AI 智能分析** - 定时生成平台运行状况智能总结
- **预构建镜像** - 托管于 ghcr.io，无需本地构建
- **一键升级** - 自动检测现有部署，支持无缝升级

---

## ⚠️ 部署前准备

### 1. 准备域名

| 域名      | 用途       | 示例                 |
| --------- | ---------- | -------------------- |
| 主域名    | 管理后台   | `iot.example.com`    |
| API 域名  | 接口服务   | `api.example.com`    |
| MQTT 域名 | 设备连接   | `mqtt.example.com`   |
| 大屏域名  | 可视化展示 | `screen.example.com` |

### 2. 开放端口

| 端口 | 用途        |
| ---- | ----------- |
| 80   | HTTP        |
| 443  | HTTPS       |
| 8883 | MQTT TLS    |
| 1883 | MQTT (可选) |

---

## 🔧 部署后配置

### 宝塔面板配置

1. **创建网站并申请 SSL 证书** - 使用 Let's Encrypt
2. **配置反向代理**：
   - 主站: `127.0.0.1:3000`
   - API: `127.0.0.1:8000`
3. **MQTT TLS 证书** - 复制到 `/opt/mcs-iot/nginx/ssl/`

---

## 🔐 授权系统 (License Server)

本项目包含完整的设备授权管理系统，基于 Cloudflare Workers 部署，具备防破解能力。

### 授权机制概述

| 特性     | 说明                                                              |
| -------- | ----------------------------------------------------------------- |
| 设备绑定 | 基于主机名 + MAC 地址 + 硬件特征生成唯一设备 ID                   |
| 云端验证 | 每次启动和每 24 小时自动验证授权状态                              |
| 宽限期   | 验证失败后有 1 天宽限期，期间系统仍可运行                         |
| 功能限制 | 未授权时禁用：外网 MQTT、AI 分析、R2 归档、报警通知，设备限 10 台 |
| 防篡改   | SHA-256 代码完整性校验，检测源码修改并自动上报                    |

### 部署 Cloudflare Worker

#### 1. 创建 KV 命名空间

```bash
# 安装 Wrangler CLI
npm install -g wrangler

# 登录 Cloudflare
wrangler login

# 创建 KV 命名空间
wrangler kv:namespace create "LICENSES"
# 记录返回的 namespace ID
```

#### 2. 创建 Worker

登录 [Cloudflare Dashboard](https://dash.cloudflare.com/) → Workers

1. 点击 **Create a Worker**
2. 复制 `cfworker/license-server.js` 全部代码粘贴
3. 点击 **Save and Deploy**

#### 3. 绑定 KV 和设置环境变量

在 Worker 设置页面：

**Settings → Variables → KV Namespace Bindings:**
| Variable name | Namespace |
|---------------|-----------|
| `LICENSES` | 选择步骤 1 创建的命名空间 |

**Settings → Variables → Environment Variables:**
| Variable name | Value |
|---------------|-------|
| `ADMIN_TOKEN` | 设置一个安全的管理员密码 |

#### 4. (可选) 绑定自定义域名

Settings → Triggers → Custom Domains → 添加 `lic.yourdomain.com`

### 授权管理后台

部署完成后访问 `https://your-worker.workers.dev/admin`

功能包括：

- ✅ 查看/添加/删除授权
- ✅ 设置客户名称、过期时间、功能权限
- ✅ 设置代码完整性哈希 (防破解)
- ✅ 查看破解记录 (Tamper Logs)

### 防破解机制

#### 代码完整性校验

系统会计算关键源文件 (`license.py`, `config.py`, `main.py`) 的 SHA-256 哈希值：

```python
# backend/src/license.py 中的预期哈希值
EXPECTED_INTEGRITY_HASH = "1f872545cd99018c"
```

每次验证授权时，后端会：

1. 计算当前代码的实际哈希值
2. 与预期哈希值对比
3. 上报哈希值给授权服务器
4. 服务器比对并记录差异

#### 生成新的哈希值

当代码有合法更新时，在容器内执行：

```bash
docker exec -it mcs_backend python -c "
from src.license import compute_integrity_hash
print('New hash:', compute_integrity_hash())
"
```

将输出的哈希值更新到：

1. `backend/src/license.py` 的 `EXPECTED_INTEGRITY_HASH`
2. 授权管理后台对应客户的 "Expected Hash" 字段

#### 破解检测

如果检测到代码被篡改：

- ⚠️ 前端显示红色警告 "检测到代码被非法修改"
- ⚠️ 后端日志记录 `CODE TAMPERING DETECTED`
- ⚠️ 授权服务器自动保存破解记录 (设备 ID、时间、哈希差异)
- ⚠️ 管理后台可查看所有破解记录

---

## 🛠️ 服务管理

```bash
# 服务管理
mcs-iot start      # 启动服务
mcs-iot stop       # 停止服务
mcs-iot restart    # 重启服务
mcs-iot status     # 查看状态
mcs-iot logs       # 查看日志

# 模拟器 (永久运行，10秒/条数据)
mcs-simulator-start    # 启动 24 个模拟传感器
mcs-simulator-stop     # 停止模拟器
```

---

## 🔄 升级方法

```bash
cd /opt/mcs-iot
bash scripts/deploy.sh
# 选择 1 - 更新到最新版本
```

升级过程会自动：备份数据库 → 拉取代码 → 更新镜像 → 重启服务

---

## 📡 设备接入

### MQTT 参数

| 参数   | 值                    |
| ------ | --------------------- |
| Broker | `mqtt.yourdomain.com` |
| 端口   | 8883 (TLS)            |
| 用户名 | 管理后台配置          |

### 上行数据 (Topic: `mcs/{设备SN}/up`)

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

---

## 🐳 Docker 镜像

预构建镜像托管于 GitHub Container Registry：

```
ghcr.io/zhizinan1997/mcs-iot-backend:latest
ghcr.io/zhizinan1997/mcs-iot-worker:latest
ghcr.io/zhizinan1997/mcs-iot-frontend:latest
```

手动部署：

```bash
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
```

---

## ❗ 常见问题

### 容器无法启动

```bash
mcs-iot status
mcs-iot logs
```

### MQTT 连接失败

- 检查 SSL 证书是否在 `/opt/mcs-iot/nginx/ssl/`
- 确保文件名为 `server.crt` 和 `server.key`
- 重启：`mcs-iot restart`

### 升级后服务异常

```bash
# 恢复数据库备份
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i mcs_db psql -U postgres mcs_iot
```

---

## 📄 许可证

MIT License

---

**开发者**: Ryan Zhi | **邮箱**: <zinanzhi@gmail.com>
