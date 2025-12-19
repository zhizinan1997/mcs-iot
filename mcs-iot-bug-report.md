# MCS-IoT 部署问题修复报告

## 概述

本报告记录了 MCS-IoT 部署过程中发现的问题及修复方案。

---

## 问题 1：Docker 容器启动顺序问题

### 现象
- 用户登录时返回 **502 Bad Gateway**
- 所有 `/api/` 请求失败

### 错误日志
```
# docker logs mcs_frontend
upstream: "http://198.18.0.24:8000/api/auth/login"
```

### 原因
`mcs_frontend` 容器内的 nginx 在启动时解析 `backend` 主机名并缓存 IP。如果 `backend` 容器还未就绪，DNS 会解析到错误的临时 IP。

### 修复方案

修改 `docker-compose.yml`：

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
    interval: 5s
    timeout: 5s
    retries: 5
    start_period: 10s

frontend:
  depends_on:
    backend:
      condition: service_healthy
```

---

## 问题 2：数据库列名与代码不匹配

### 现象
- 大屏底部折线图无数据

### 错误日志
```
# docker logs mcs_worker
ERROR: column "seq" of relation "sensor_data" does not exist
```

### 原因
数据库表定义使用 `msg_seq`，但代码中使用 `seq`。

### 修复方案

修改 `scripts/init.sql`，将 `msg_seq` 改为 `seq`：

```diff
-   msg_seq INT
+   seq INT
```

---

## 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `docker-compose.yml` | 为 backend 添加 healthcheck，frontend 添加 condition: service_healthy |
| `scripts/init.sql` | 将 msg_seq 改为 seq |

---

## 问题 3：AI API 环境变量未传递给后端

### 现象
- 在部署脚本中配置的 AI API Key 没有生效

### 原因
`docker-compose.yml` 中的 `backend` 服务没有配置 `AI_API_KEY` 和 `AI_API_URL` 环境变量，即使 `.env` 文件中有这些值。

### 修复方案

修改 `docker-compose.yml`，在 backend 服务的 environment 中添加：

```yaml
backend:
  environment:
    # ... 其他配置 ...
    - AI_API_URL=${AI_API_URL:-}
    - AI_API_KEY=${AI_API_KEY:-}
    - WEATHER_API_KEY=${WEATHER_API_KEY:-}
```

---

## 问题 4：演示数据生成器无法连接后端

### 现象
- 部署完成后仪表数据为空
- 日志显示 `[错误] 无法连接后端，请确保服务已启动`

### 原因
演示数据生成器在后端服务完全就绪前尝试连接，导致失败。

### 修复方案

在 `scripts/deploy.sh` 的演示数据生成逻辑中，增加更长的等待时间和重试机制：

```bash
# 等待后端 API 完全就绪
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
        break
    fi
    sleep 2
done
```

---

## 更新后的文件清单

| 文件 | 修改内容 |
|------|---------|
| `docker-compose.yml` | 1. 添加 backend healthcheck 2. 添加 AI/天气 API 环境变量 3. frontend 添加 condition: service_healthy |
| `scripts/init.sql` | 将 msg_seq 改为 seq |
| `scripts/deploy.sh` | 演示数据生成器增加等待和重试逻辑 |

---

## 问题 5：Nginx proxy_pass 使用变量导致路径错误

### 现象
- 前端界面无法获取任何数据
- 所有 API 请求返回 404 Not Found
- 后端日志显示收到的路径是 `/instruments` 而不是 `/api/instruments`

### 错误日志
```
# docker logs mcs_backend
INFO: GET /instruments HTTP/1.1" 404 Not Found
# 应该是 /api/instruments
```

### 原因
`nginx-simple.conf` 中使用变量方式配置 proxy_pass：

```nginx
set $backend_server backend:8000;
location /api/ {
    proxy_pass http://$backend_server/api/;  # ❌ 使用变量会导致路径处理异常
}
```

当 nginx 的 `proxy_pass` 使用变量时，它不会按照常规方式替换 URI 路径，导致请求路径被错误处理。

### 修复方案

修改 `nginx/nginx-simple.conf`，使用 `upstream` 定义后端服务器：

```nginx
# 添加 upstream 定义
upstream backend_api {
    server backend:8000;
}

server {
    # 删除这行
    # set $backend_server backend:8000;
    
    location /api/ {
        proxy_pass http://backend_api;  # ✅ 不带尾部路径，保留原始 URI
        # ... 其他配置保持不变
    }
    
    location /api/dashboard/ws {
        proxy_pass http://backend_api;  # ✅ 同样修改
        # ...
    }
    
    location /docs {
        proxy_pass http://backend_api;
        # ...
    }
    
    location /openapi.json {
        proxy_pass http://backend_api;
        # ...
    }
}
```

**关键点**：
1. 使用 `upstream` 而非变量
2. `proxy_pass` 后面不要带路径（如 `/api/`），让 nginx 保留原始请求路径

---

## 最终修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `docker-compose.yml` | 1. 添加 backend healthcheck 2. 添加 AI/天气 API 环境变量 3. frontend 添加 condition: service_healthy |
| `scripts/init.sql` | 将 msg_seq 改为 seq |
| `scripts/deploy.sh` | 演示数据生成器增加等待和重试逻辑 |
| `nginx/nginx-simple.conf` | 使用 upstream 替代变量，修复 proxy_pass 路径问题 |

---

## 问题 6：仪表盘实时数据不显示仪表名称

### 现象
- 仪表盘界面的实时传感器状态列表中，仪表名称显示为空

### 原因
后端 `backend/src/dashboard.py` 的 `get_realtime_data` 函数只查询了 `instrument_id`，没有 JOIN `instruments` 表获取名称和颜色。

### API 返回示例
```json
{
  "sn": "GAS001",
  "instrument_id": 1,
  "instrument_name": null,  // ← 应该有值
  "instrument_color": null  // ← 应该有值
}
```

### 修复方案

修改 `backend/src/dashboard.py` 的 `get_realtime_data` 函数，改用 JOIN 查询：

```python
@router.get("/realtime", response_model=List[DeviceRealtime])
async def get_realtime_data(db = Depends(get_db), redis = Depends(get_redis)):
    devices = []
    
    async with db.acquire() as conn:
        # 修改：添加 LEFT JOIN instruments 表
        rows = await conn.fetch("""
            SELECT d.sn, d.name, d.instrument_id, d.unit, d.sensor_type,
                   i.name as instrument_name, i.color as instrument_color
            FROM devices d
            LEFT JOIN instruments i ON d.instrument_id = i.id
        """)
    
    for row in rows:
        sn = row['sn']
        rt_data = await redis.hgetall(f"realtime:{sn}")
        is_online = await redis.exists(f"online:{sn}")
        pos_data = await redis.hgetall(f"position:{sn}")
        
        devices.append(DeviceRealtime(
            sn=sn,
            name=row['name'],
            # ... 其他字段 ...
            instrument_id=row['instrument_id'],
            instrument_name=row['instrument_name'],   # ← 添加
            instrument_color=row['instrument_color'], # ← 添加
            unit=row['unit'] or "ppm",
            sensor_type=row['sensor_type']
        ))
    
    return devices
```

---

## 问题 7：报警类型显示英文

### 现象
- 报警界面显示 "WEAK_SIGNAL" 等英文报警类型

### 修复方案

修改前端 `frontend/src/views/screen/index.vue` 或通用工具函数，添加报警类型的中文映射：

```typescript
// 报警类型中文映射
const ALARM_TYPE_MAP: Record<string, string> = {
  'HIGH_VALUE': '浓度超标',
  'LOW_VALUE': '浓度过低',
  'LOW_BATTERY': '电量不足',
  'WEAK_SIGNAL': '信号弱',
  'OFFLINE': '设备离线',
  'SENSOR_ERROR': '传感器故障',
  'CALIBRATION_DUE': '需要校准'
}

function fmtAlarmType(type: string | undefined): string {
  if (!type) return '未知'
  return ALARM_TYPE_MAP[type] || type
}
```

同时检查 `frontend/src/views/alarms/index.vue` 是否使用了相同的函数。

---

## 最终修改文件清单（共 7 个问题）

| 文件 | 修改内容 |
|------|---------|
| `docker-compose.yml` | 1. 添加 backend healthcheck 2. 添加 AI/天气 API 环境变量 3. frontend 添加 condition: service_healthy |
| `scripts/init.sql` | 将 msg_seq 改为 seq |
| `scripts/deploy.sh` | 演示数据生成器增加等待和重试逻辑 |
| `nginx/nginx-simple.conf` | 使用 upstream 替代变量，修复 proxy_pass 路径问题 |
| `backend/src/dashboard.py` | get_realtime_data 添加 JOIN instruments 获取名称和颜色 |
| `frontend/src/views/screen/index.vue` | fmtAlarmType 函数添加 WEAK_SIGNAL 等中文映射 |
| `frontend/src/views/alarms/index.vue` | 同样添加报警类型中文映射 |
