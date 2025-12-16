-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Device Management Table
CREATE TABLE IF NOT EXISTS devices (
    sn VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128),
    model VARCHAR(32),
    
    -- Config Params (Adjustable from Cloud)
    k_val FLOAT DEFAULT 1.0,
    b_val FLOAT DEFAULT 0.0,
    t_coef FLOAT DEFAULT 0.0,
    
    -- Alarm Thresholds
    high_limit FLOAT DEFAULT 1000.0,
    low_limit FLOAT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMP,
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
    err_code INT,
    
    -- Metadata
    msg_seq INT
);

-- Turn into Hypertable (Partition by time, 1 day chunks)
SELECT create_hypertable('sensor_data', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_sensor_sn_time ON sensor_data (sn, time DESC);

-- Enable Compression (Compress after 3 days)
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sn'
);
SELECT add_compression_policy('sensor_data', INTERVAL '3 days');

-- 3. Alarm Logs
CREATE TABLE IF NOT EXISTS alarm_logs (
    id SERIAL PRIMARY KEY,
    time TIMESTAMP DEFAULT NOW(),
    sn VARCHAR(64),
    type VARCHAR(32), -- HIGH, LOW, OFFLINE, ERROR
    value FLOAT,
    threshold FLOAT,
    status VARCHAR(20) DEFAULT 'new', -- new, ack, resolved
    notified BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_alarm_sn ON alarm_logs (sn);

-- 4. System Config (Key-Value)
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT, -- JSON value
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed Initial Config
INSERT INTO system_config (key, value) VALUES 
('email_config', '{"enabled": false, "smtp": "", "user": "", "pass": "", "receivers": []}'),
('sms_config', '{"enabled": false, "ak": "", "sk": "", "sign": "", "template": ""}'),
('webhook_config', '{"enabled": false, "url": ""}'),
('dashboard_config', '{"title": "MCS-IoT Dashboard", "refresh_rate": 5}')
ON CONFLICT DO NOTHING;
