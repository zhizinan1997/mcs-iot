# MCS-IoT 敏感信息与配置项汇总 (Configuration & Secrets Summary)

为了确保系统安全运行，请务必在部署或开发前填写以下配置文件中的关键信息。

## 1. 核心环境变量 (.env)
**文件位置**: 项目根目录 `/.env` (由 `.env.example` 复制而来)

| 变量名 | 说明 | 建议 |
| :--- | :--- | :--- |
| `DB_PASS` | PostgreSQL 数据库密码 | 生产环境请使用强密码 |
| `MQTT_PASS` | Mosquitto 管理员 (admin) 的密码 | 需与 `mqtt_config.json` 保持一致 |
| `JWT_SECRET` | 后端接口 Token 签名密钥 | 长度建议 32 位以上随机字符串 |
| `ADMIN_INITIAL_PASSWORD` | 系统首次运行生成的 admin 账户密码 | 首次登录后建议在 Web 端修改 |

---

## 2. MQTT 连通性凭证 (mqtt_config.json)
**文件位置**:
- `/scripts/mqtt_config.json` (模拟器使用)
- `/mosquitto/config/mqtt_config.json` (后端 Worker 使用)

| 配置项 | 对应角色 | 说明 |
| :--- | :--- | :--- |
| `device_user/pass` | 传感器设备 | 用于数据上报 (mcs/+/up) |
| `worker_user/pass` | 后端 Worker | 用于订阅并入库 (mcs/+/up, status) |
| `admin_user/pass` | 管理员 | 用于内部管理与诊断 |

> [!IMPORTANT]
> 这两个位置的文件内容应保持同步。修改后，需运行 `docker compose restart backend` 以更新 Mosquitto 内部密码表。

---

## 3. 外部服务 API 密钥
**文件位置**: 可选在 `.env` 中预设，或在 **Web 管理后台 -> 系统配置** 中填写。

| 服务类别 | 关键字段 | 获取方式 |
| :--- | :--- | :--- |
| **AI 助手** | `AI_API_KEY` | 前往 Ryan AI 或 OpenRouter 申请 |
| **天气预报** | `WEATHER_API_KEY` | 前往 心知天气 (Seniverse) 申请私钥 |

---

## 4. 多云归档存储 (Archive Storage)
**文件位置**: 仅通过 **Web 管理后台 -> 归档配置** 填写。

支持的提供商：Cloudflare R2, 腾讯云 COS, 阿里云 OSS。

| 字段 | 说明 |
| :--- | :--- |
| `Bucket` | 存储桶名称 |
| `Access Key` | API 访问密钥 ID |
| `Secret Key` | API 访问密钥 Secret |
| `Account ID` | (仅 R2) Cloudflare 账户 ID |
| `Region` | (仅 COS/OSS) 存储桶所在地域 |

---

## 5. 其他安全建议
1. **不要提交实名配置**：切勿将填写了真实密码的以上文件提交至公共 Git 仓库。
2. **定期轮换**：建议每 3-6 个月更换一次 `JWT_SECRET` 和云存储 Key。
3. **最小权限**：为云存储 Key 分配权限时，建议仅保留对象管理权限，不授予账户完全访问权。
