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
