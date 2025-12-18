#!/bin/bash
# =============================================================================
# 元芯物联网智慧云平台 - 卸载脚本
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/mcs-iot"

echo ""
echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                     元芯物联网平台 - 卸载                         ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}警告: 此操作将删除以下内容:${NC}"
echo "  - 所有 Docker 容器和镜像"
echo "  - 数据库数据"
echo "  - 配置文件"
echo "  - 安装目录 ($INSTALL_DIR)"
echo ""

read -r -p "确定要卸载吗? 输入 'YES' 确认: " confirm

if [[ "$confirm" != "YES" ]]; then
    echo "卸载已取消"
    exit 0
fi

echo ""
echo -e "${YELLOW}正在停止服务...${NC}"

# 停止模拟器
if [[ -f /var/run/mcs-simulator.pid ]]; then
    kill $(cat /var/run/mcs-simulator.pid) 2>/dev/null || true
    rm -f /var/run/mcs-simulator.pid
fi
pkill -f "simulator.py" 2>/dev/null || true

# 停止 Docker 容器
cd "$INSTALL_DIR" 2>/dev/null || true
docker compose down -v 2>/dev/null || docker-compose down -v 2>/dev/null || true

echo -e "${YELLOW}正在删除 Docker 镜像...${NC}"
docker rmi mcs-iot-frontend mcs-iot-backend mcs-iot-worker 2>/dev/null || true

echo -e "${YELLOW}正在删除安装目录...${NC}"
rm -rf "$INSTALL_DIR"

echo -e "${YELLOW}正在删除管理命令...${NC}"
rm -f /usr/local/bin/mcs-iot
rm -f /usr/local/bin/mcs-simulator-start
rm -f /usr/local/bin/mcs-simulator-stop

echo -e "${YELLOW}正在删除定时任务...${NC}"
rm -f /etc/cron.d/mcs-iot-ssl-renew

echo ""
echo -e "${GREEN}✓ 卸载完成${NC}"
echo ""
echo "注意: SSL 证书保留在 /etc/letsencrypt/ 目录"
echo "如需删除证书，请手动运行: certbot delete --cert-name <domain>"
echo ""
