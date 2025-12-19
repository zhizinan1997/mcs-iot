# MCS-IoT 工业级气体监测物联网平台

专为工业气体监测场景设计的物联网云平台，支持实时数据采集、可视化大屏、智能报警和设备管理。

---

## 🚀 一键部署

支持 Ubuntu 20.04+、CentOS 7+、OpenCloudOS、Debian 10+

```bash
curl -sSL https://raw.githubusercontent.com/zhizinan1997/mcs-iot/main/scripts/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

**脚本将自动完成：**

- ✅ 环境检测与依赖安装 (Docker)
- ✅ 域名配置与 API 密钥配置
- ✅ 数据库密码配置
- ✅ Docker 容器部署
- ✅ 可选导入演示数据

> ⚠️ **注意**: SSL 证书需要在宝塔面板中手动申请和配置

---

## ⚠️ 部署前准备

### 1. 准备域名

部署前请准备 3-4 个域名并解析到服务器 IP：

| 域名      | 用途       | 示例                 |
| --------- | ---------- | -------------------- |
| 主域名    | 管理后台   | `iot.example.com`    |
| API 域名  | 接口服务   | `api.example.com`    |
| MQTT 域名 | 设备连接   | `mqtt.example.com`   |
| 大屏域名  | 可视化展示 | `screen.example.com` |

### 2. 开放端口

在云服务商控制台（阿里云/腾讯云安全组）放行以下端口：

| 端口 | 用途        |
| ---- | ----------- |
| 80   | HTTP        |
| 443  | HTTPS       |
| 8883 | MQTT TLS    |
| 1883 | MQTT (可选) |

---

## 🔧 部署后宝塔配置

部署脚本完成后，需要在宝塔面板中配置 nginx 反向代理和 SSL 证书。

### 第一步：创建网站并申请 SSL 证书

在宝塔面板中为每个域名创建网站，并使用「SSL」功能申请 Let's Encrypt 证书。

### 第二步：配置反向代理

| 域名用途     | 反向代理目标端口       |
| ------------ | ---------------------- |
| 主站/管理后台 | 127.0.0.1:3000         |
| API 接口     | 127.0.0.1:8000         |
| 大屏展示     | 127.0.0.1:3000 (访问 /screen 路径) |

### 第三步：配置 MQTT TLS 证书

将宝塔申请的 SSL 证书文件复制到 `/opt/mcs-iot/nginx/ssl/` 目录：

| 原文件名                    | 复制后文件名 |
| --------------------------- | ------------ |
| fullchain.pem 或 证书.pem   | server.crt   |
| privkey.pem 或 私钥.pem     | server.key   |

证书文件通常位于：`/www/server/panel/vhost/ssl/域名/`

---

## 🛠️ 部署后管理

```bash
# 服务管理
mcs-iot start      # 启动服务
mcs-iot stop       # 停止服务
mcs-iot restart    # 重启服务
mcs-iot status     # 查看状态
mcs-iot logs       # 查看日志

# 模拟器
mcs-simulator-start    # 启动 24 个模拟传感器
mcs-simulator-stop     # 停止模拟器
```

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

## ❗ 常见问题

### 容器无法启动

```bash
# 查看容器状态
mcs-iot status

# 查看详细日志
mcs-iot logs
```

### MQTT 连接失败

- 检查 SSL 证书是否已正确复制到 `/opt/mcs-iot/nginx/ssl/`
- 确保证书文件名为 `server.crt` 和 `server.key`
- 重启服务：`mcs-iot restart`

---

## 📄 许可证

MIT License
