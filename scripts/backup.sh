#!/bin/bash
# MCS-IoT 数据库备份脚本
# 支持本地备份和上传到 R2

set -e

# 配置
BACKUP_DIR="/opt/mcs-iot/backups"
DB_HOST="${DB_HOST:-timescaledb}"
DB_NAME="${DB_NAME:-mcs_iot}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-password}"
RETENTION_DAYS=7

# R2 配置 (可选)
R2_ENDPOINT="${R2_ENDPOINT:-}"
R2_BUCKET="${R2_BUCKET:-}"
R2_ACCESS_KEY="${R2_ACCESS_KEY:-}"
R2_SECRET_KEY="${R2_SECRET_KEY:-}"

# 生成备份文件名
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="mcs_iot_backup_${TIMESTAMP}.sql.gz"

echo "=========================================="
echo "MCS-IoT 数据库备份"
echo "时间: $(date)"
echo "=========================================="

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行 pg_dump
echo "正在备份数据库..."
export PGPASSWORD="$DB_PASS"

pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_DIR/$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "备份完成: $BACKUP_FILE ($BACKUP_SIZE)"

# 上传到 R2 (如果配置了)
if [ -n "$R2_ENDPOINT" ] && [ -n "$R2_BUCKET" ]; then
    echo "正在上传到 R2..."
    
    # 使用 AWS CLI (需要预先安装)
    if command -v aws &> /dev/null; then
        export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY"
        export AWS_SECRET_ACCESS_KEY="$R2_SECRET_KEY"
        
        aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" \
            "s3://$R2_BUCKET/backups/$BACKUP_FILE" \
            --endpoint-url "$R2_ENDPOINT"
        
        echo "已上传到 R2: backups/$BACKUP_FILE"
    else
        echo "警告: AWS CLI 未安装，跳过 R2 上传"
    fi
fi

# 清理旧备份
echo "清理 ${RETENTION_DAYS} 天前的备份..."
find "$BACKUP_DIR" -name "mcs_iot_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# 统计
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/mcs_iot_backup_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

echo "=========================================="
echo "备份统计:"
echo "  当前备份数: $BACKUP_COUNT"
echo "  总大小: $TOTAL_SIZE"
echo "=========================================="
echo "备份完成!"
