/*
  MCS-IOT 数据库初始化脚本 (Database Initialization Schema)

  该文件定义了全栈系统的核心持久化层结构，集成了 TimescaleDB 时间序列优化。
  主要职责：
  1. 基础架构：定义仪表 (Instruments)、设备 (Devices) 及用户 (Users) 的元数据模型。
  2. 时序优化：基于 TimescaleDB 构建传感器数据超表 (Hypertables)，实现高效的数据分区与压缩策略。
  3. 报警与日志：建立报警记录 (Alarm Logs)、操作日志 (Operation Logs) 及系统配置 (System Config) 体系。
  4. 权限与安全：预设子账号 RBAC 系统权限列及初始管理员账户 (bcrypt 加密)。
  5. 自动化运维：配置归档日志 (Archive Logs) 与数据库版本追踪 (Schema Migrations) 机制。

  技术栈：PostgreSQL, TimescaleDB, SQL Schema Design.
*/

-- Set timezone to Beijing (China Standard Time)
SET timezone = 'Asia/Shanghai';

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Instruments Table (仪表/分组)
CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    color VARCHAR(16) DEFAULT '#409eff',
    sort_order INT DEFAULT 0,
    is_displayed BOOLEAN DEFAULT TRUE,
    pos_x FLOAT DEFAULT 50.0,      -- 大屏 X 坐标 (百分比 0-100)
    pos_y FLOAT DEFAULT 50.0,      -- 大屏 Y 坐标 (百分比 0-100)
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Device Management Table
CREATE TABLE IF NOT EXISTS devices (
    sn VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128),
    model VARCHAR(32),
    location VARCHAR(256),           -- 安装位置描述
    
    -- Sensor type and unit
    sensor_type VARCHAR(32) DEFAULT 'custom',
    unit VARCHAR(16) DEFAULT 'ppm',
    
    -- Instrument association
    instrument_id INT REFERENCES instruments(id) ON DELETE SET NULL,
    sensor_order INT DEFAULT 0,
    
    -- 大屏坐标 (百分比)
    pos_x FLOAT DEFAULT 50.0,
    pos_y FLOAT DEFAULT 50.0,
    
    -- 校准参数
    calib_k FLOAT DEFAULT 1.0,       -- 斜率
    calib_b FLOAT DEFAULT 0.0,       -- 截距
    calib_t_ref FLOAT DEFAULT 25.0,  -- 参考温度
    calib_t_comp FLOAT DEFAULT 0.1,  -- 温度补偿系数
    
    -- 报警阈值
    high_limit FLOAT DEFAULT 1000.0,
    low_limit FLOAT,
    bat_limit FLOAT DEFAULT 20.0,    -- 低电量阈值
    
    -- 状态
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMP,
    firmware_ver VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Sensor Data Hypertable
CREATE TABLE IF NOT EXISTS sensor_data (
    time TIMESTAMP NOT NULL,
    sn VARCHAR(64) NOT NULL,
    
    -- Raw & Calculated
    v_raw FLOAT,
    ppm FLOAT,
    
    -- Environmental
    temp FLOAT,
    humi FLOAT,
    
    -- Device Health
    bat INT,
    rssi INT,
    err_code INT DEFAULT 0,
    
    -- Metadata
    seq INT
);

-- Turn into Hypertable (Partition by time, 1 day chunks)
SELECT create_hypertable('sensor_data', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_sensor_sn_time ON sensor_data (sn, time DESC);

-- Enable Compression (Compress after 1 day for storage efficiency)
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sn'
);
SELECT add_compression_policy('sensor_data', INTERVAL '1 day', if_not_exists => TRUE);

-- 4. Alarm Logs
CREATE TABLE IF NOT EXISTS alarm_logs (
    id SERIAL PRIMARY KEY,
    triggered_at TIMESTAMP DEFAULT NOW(),
    sn VARCHAR(64),
    type VARCHAR(32),                -- HIGH, LOW, OFFLINE, LOW_BAT, ERROR
    value FLOAT,
    threshold FLOAT,
    status VARCHAR(32) DEFAULT 'active', -- active, ack, resolved
    notified BOOLEAN DEFAULT FALSE,
    channels VARCHAR(128),           -- 通知渠道: email,sms,webhook
    ack_at TIMESTAMP,
    ack_by VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_alarm_sn ON alarm_logs (sn);
CREATE INDEX IF NOT EXISTS idx_alarm_time ON alarm_logs (triggered_at DESC);

-- 4. System Config (Key-Value)
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT,                      -- JSON value
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. Archive Logs (归档记录)
CREATE TABLE IF NOT EXISTS archive_logs (
    id SERIAL PRIMARY KEY,
    archive_date DATE NOT NULL,
    file_name VARCHAR(256),
    file_size BIGINT,                -- 文件大小(字节)
    row_count INT,                   -- 归档行数
    r2_path VARCHAR(512),            -- R2存储路径
    status VARCHAR(32) DEFAULT 'pending', -- pending, uploaded, deleted, failed
    created_at TIMESTAMP DEFAULT NOW()
);

-- 添加 archive_date 唯一索引 (支持 ON CONFLICT 语法)
CREATE UNIQUE INDEX IF NOT EXISTS archive_logs_date_unique ON archive_logs(archive_date);

-- 6. Operation Logs (操作日志)
CREATE TABLE IF NOT EXISTS operation_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_name VARCHAR(64),
    action VARCHAR(64),              -- login, logout, create_device, update_config, etc.
    target_type VARCHAR(32),         -- device, alarm, config, user
    target_id VARCHAR(64),
    details TEXT,                    -- JSON额外信息
    ip_address VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_oplog_time ON operation_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_oplog_user ON operation_logs (user_name);

-- 7. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(32) DEFAULT 'user', -- admin, user
    email VARCHAR(128),
    phone VARCHAR(32),
    is_active BOOLEAN DEFAULT TRUE,
    permissions TEXT DEFAULT '{}',   -- JSON: 各功能模块访问权限
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 8. Schema Migrations Table (用于追踪数据库版本)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW()
);

-- 标记初始迁移已应用 (新安装时)
INSERT INTO schema_migrations (version, description) VALUES 
(1, '添加 users.permissions 字段用于子账号权限管理')
ON CONFLICT DO NOTHING;

-- Create default admin user (Change password on first login)
-- Recommended: Set a strong password in production via environment variables or UI.
INSERT INTO users (username, password_hash, role, permissions) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.SHJGrMeVwBVzGO', 'admin', '{}')
ON CONFLICT DO NOTHING;

-- Seed Initial Config
INSERT INTO system_config (key, value) VALUES 
('email', '{"enabled": false, "smtp_host": "", "smtp_port": 465, "sender": "", "password": "", "receivers": []}'),
('sms', '{"enabled": false, "access_key_id": "", "access_key_secret": "", "sign_name": "", "template_code": "", "phone_numbers": []}'),
('webhook', '{"enabled": false, "platform": "dingtalk", "url": "", "secret": "", "at_mobiles": []}'),
('alarm_time', '{"enabled": false, "days": [1,2,3,4,5], "start": "08:00", "end": "18:00"}'),
('dashboard', '{"title": "MCS-IoT 气体监测大屏", "background": "", "refresh_rate": 5}'),
('archive', '{"enabled": false, "retention_days": 3, "r2_endpoint": "", "r2_bucket": "", "r2_access_key": "", "r2_secret_key": ""}')
ON CONFLICT DO NOTHING;

