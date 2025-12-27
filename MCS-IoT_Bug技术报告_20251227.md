# MCS-IoT 系统 Bug 技术报告

**报告日期**: 2025-12-27  
**系统版本**: Docker 部署版本 (ghcr.io/zhizinan1997/mcs-iot-*)  
**报告人**: 系统管理员

---

## Bug 汇总

| 序号 | 严重程度 | 模块 | 问题描述 | 状态 |
|------|----------|------|----------|------|
| 1 | 🔴 严重 | Worker | 许可证文件编码错误导致 Worker 锁定 | 临时修复 |
| 2 | 🔴 严重 | Backend | R2 统计接口缺少 asyncio import | 临时修复 |
| 3 | 🟡 中等 | Database | archive_logs 表缺少唯一索引 | 临时修复 |
| 4 | 🟡 中等 | Config | 归档配置字段不一致 | 需优化 |

---

## Bug 详细描述

### Bug #1: 许可证文件编码错误导致 Worker 服务锁定

**严重程度**: 🔴 严重  
**影响范围**: Worker 服务完全无法执行定时任务（包括数据归档）

**问题现象**:
```
ERROR:src.license:Failed to read license: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
ERROR:src.license:No license key found
ERROR:Worker:License check failed! System may be locked.
```

**根本原因**:  
`/opt/mcs-iot/license.key` 文件使用了 **UTF-16 LE** 编码（带 BOM: `0xFFFE`），而代码使用 UTF-8 读取导致解析失败。

**原始文件内容 (hex)**:
```
00000000: fffe 4400 4500 5600 5f00 4d00 4f00 4400  ..D.E.V._.M.O.D.
00000010: 4500 3d00 7400 7200 7500 6500 0d00 0a00  E.=.t.r.u.e.....
```

**临时修复**:
```bash
echo "DEV_MODE=true" > /opt/mcs-iot/license.key
docker restart mcs_worker
```

**建议修复**:
1. 在代码中添加自动编码检测，或强制使用 UTF-8
2. 部署脚本中确保 license.key 使用 UTF-8 无 BOM 格式

---

### Bug #2: R2 统计接口缺少 asyncio import

**严重程度**: 🔴 严重  
**影响范围**: 前端无法显示 R2 云端存储统计

**问题现象**:  
API `/api/config/archive/stats` 返回:
```json
{
  "r2": {
    "size_bytes": 0,
    "file_count": 0,
    "error": "name 'asyncio' is not defined"
  }
}
```

**根本原因**:  
文件 `src/config.py` 中 `get_storage_stats` 函数（约第403行）使用了 `asyncio.get_event_loop()`，但函数内部没有 `import asyncio`。

**问题代码位置**: `backend/src/config.py` 约第477行
```python
loop = asyncio.get_event_loop()  # ❌ asyncio 未导入
total_size, file_count = await loop.run_in_executor(None, get_cloud_stats)
```

**临时修复**:  
在使用 asyncio 前添加 import:
```python
import asyncio
loop = asyncio.get_event_loop()
```

**建议修复**:  
在 `get_storage_stats` 函数的 try 块开头添加 `import asyncio`，与其他类似函数保持一致。

---

### Bug #3: archive_logs 表缺少唯一约束

**严重程度**: 🟡 中等  
**影响范围**: 归档任务执行失败

**问题现象**:
```
Archive failed for 2025-12-26: there is no unique or exclusion constraint matching the ON CONFLICT specification
```

**根本原因**:  
归档代码使用了 `INSERT ... ON CONFLICT (archive_date)` 语法，但 `archive_logs` 表的 `archive_date` 字段没有唯一约束。

**表结构问题**:
```sql
-- 当前缺少的索引
CREATE UNIQUE INDEX archive_logs_date_unique ON archive_logs(archive_date);
```

**临时修复**:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS archive_logs_date_unique ON archive_logs(archive_date);
```

**建议修复**:  
在数据库迁移脚本中添加此唯一索引，确保新部署自动创建。

---

### Bug #4: 归档配置字段命名不一致

**严重程度**: 🟡 中等  
**影响范围**: 配置保存后实际使用时可能读取错误字段

**问题现象**:  
Redis 中存储的配置同时存在两套字段命名:

```json
{
  "bucket": "ryanai",           // 新字段
  "r2_bucket": "archive",       // 旧字段（错误值）
  "account_id": "xxx",          // 新字段
  "r2_account_id": "",          // 旧字段（空）
  "access_key": "xxx",          // 新字段
  "r2_access_key": "xxx"        // 旧字段
}
```

**根本原因**:  
前端保存使用新字段名（`bucket`, `account_id`），但部分后端代码可能读取旧字段名（`r2_bucket`, `r2_account_id`），导致配置不一致。

**临时修复**:  
手动同步 Redis 配置，确保新旧字段值一致。

**建议修复**:
1. 统一字段命名，移除旧字段
2. 添加配置迁移逻辑，自动将旧字段映射到新字段

---

## 环境信息

| 组件 | 版本/信息 |
|------|-----------|
| 操作系统 | Linux |
| Docker | 运行中 |
| 后端镜像 | ghcr.io/zhizinan1997/mcs-iot-backend:latest |
| Worker 镜像 | ghcr.io/zhizinan1997/mcs-iot-worker:latest |
| 前端镜像 | ghcr.io/zhizinan1997/mcs-iot-frontend:latest |
| 数据库 | TimescaleDB (PostgreSQL 15) |
| 设备 ID | MCS-7B88-D687-DD71 |

---

## 附加说明

1. **所有修复均为临时修复**，容器重新部署后可能会恢复原状
2. 建议厂家在下个版本中修复以上问题
3. 如需进一步技术支持，可提供完整的容器日志

---

*报告生成时间: 2025-12-27 17:10*
