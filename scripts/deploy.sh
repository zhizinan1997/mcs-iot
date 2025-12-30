#!/bin/bash
# =============================================================================
# MCS-IOT 自动化部署工具 (Linux One-Click Installer)
#
# 该脚本负责全栈系统的生产环境环境初始化、依赖安装及 Docker 容器编排。
# 主要职责：
# 1. 环境自检：评估操作系统版本 (Ubuntu/CentOS/Debian)、内存资源及端口占用。
# 2. 自动化更新：支持无损平滑升级，自动备份数据库、拉取最新镜像并执行 Schema 迁移。
# 3. 宝塔面板联动：提供详细的解析记录与反向代理配置指引，整合 SSL 证书路径自动检测。
# 4. 性能优化：根据服务器配置自动创建 Swap 交换分区及国内镜像加速配置。
#
# 支持: Ubuntu 20.04+, CentOS 7+, OpenCloudOS, Debian 10+
# GitHub: https://github.com/zhizinan1997/mcs-iot
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 全局变量
VERSION="v1.0.3"
INSTALL_DIR="/opt/mcs-iot"
REPO_URL="https://github.com/zhizinan1997/mcs-iot.git"
REPO_URL_CN="https://gh-proxy.com/https://github.com/zhizinan1997/mcs-iot.git"
COMPOSE_VERSION="2.24.0"
USE_CHINA_MIRROR=false

# 用户配置变量
DOMAIN_MAIN=""
DOMAIN_API=""
DOMAIN_MQTT=""
DOMAIN_SCREEN=""
DB_PASSWORD=""
ADMIN_PASSWORD=""
MQTT_PASSWORD=""
JWT_SECRET=""
WEATHER_API_KEY=""
AI_API_KEY=""
AI_MODEL="gemini-lite"

# =============================================================================
# 工具函数
# =============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║          元芯物联网智慧云平台 - 一键部署脚本                      ║"
    echo "║                  MCS-IoT One-Click Installer                       ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "                        版本: ${GREEN}${VERSION}${NC}"
    echo -e "           开发者: Ryan Zhi  邮箱: zinanzhi@gmail.com"
    echo ""
}

log_info() {
    echo -e "${GREEN}[信息]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

log_error() {
    echo -e "${RED}[错误]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

confirm() {
    local prompt="$1"
    local default="${2:-N}"
    local response
    
    if [[ "$default" == "Y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -r -p "$prompt" response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

wait_for_enter() {
    echo ""
    read -r -p "按 Enter 键继续..." || true
}

# =============================================================================
# 升级检测
# =============================================================================

check_existing_deployment() {
    # 检查是否已部署
    if [[ -d "$INSTALL_DIR" ]] && [[ -f "$INSTALL_DIR/docker-compose.ghcr.yml" || -f "$INSTALL_DIR/docker-compose.yml" ]]; then
        # 检查容器是否在运行
        cd "$INSTALL_DIR"
        if docker compose ps 2>/dev/null | grep -q "mcs_" || docker-compose ps 2>/dev/null | grep -q "mcs_"; then
            return 0  # 已部署且运行中
        elif docker ps -a 2>/dev/null | grep -q "mcs_"; then
            return 0  # 已部署但停止
        fi
    fi
    return 1  # 未部署
}

run_update_mode() {
    log_step "检测到已有部署，进入更新模式"
    
    cd "$INSTALL_DIR"
    
    echo ""
    echo -e "${CYAN}已检测到现有安装:${NC}"
    echo -e "  📁 安装目录: $INSTALL_DIR"
    
    # 显示当前版本信息
    if docker compose ps 2>/dev/null | head -5; then
        :
    else
        docker-compose ps 2>/dev/null | head -5
    fi
    
    echo ""
    echo -e "${CYAN}请选择操作:${NC}"
    echo "  1. 更新到最新版本 (保留数据)"
    echo "  2. 完全重新安装 (会丢失数据)"
    echo "  3. 退出"
    read -r -p "请选择 [1/2/3]，默认 1: " update_choice
    update_choice=${update_choice:-1}
    
    case $update_choice in
        1)
            perform_update
            ;;
        2)
            log_warn "完全重新安装将删除所有数据!"
            if confirm "确定要删除现有数据并重新安装?" "N"; then
                log_info "停止现有服务..."
                docker compose down 2>/dev/null || docker-compose down 2>/dev/null
                log_info "清理数据..."
                docker volume prune -f 2>/dev/null || true
                return 1  # 继续全新安装
            else
                log_info "已取消"
                exit 0
            fi
            ;;
        *)
            log_info "已退出"
            exit 0
            ;;
    esac
}

update_simulator_scripts() {
    # 重新生成模拟器启动脚本
    cat > "$INSTALL_DIR/start-simulator.sh" << 'EOF'
#!/bin/bash
cd /opt/mcs-iot
echo "正在启动 24 个模拟传感器..."
DURATION=${1:-0}
nohup python3 scripts/demo_generator.py -d "$DURATION" --skip-init > /var/log/mcs-simulator.log 2>&1 &
echo $! > /var/run/mcs-simulator.pid
echo "模拟器已启动，PID: $(cat /var/run/mcs-simulator.pid)"
if [[ "$DURATION" -eq 0 ]]; then
    echo "运行模式: 永久运行"
else
    echo "运行时长: ${DURATION} 分钟"
fi
echo "查看日志: tail -f /var/log/mcs-simulator.log"
EOF
    chmod +x "$INSTALL_DIR/start-simulator.sh"
    
    # 重新生成模拟器停止脚本
    cat > "$INSTALL_DIR/stop-simulator.sh" << 'EOF'
#!/bin/bash
stopped=false
if [[ -f /var/run/mcs-simulator.pid ]]; then
    PID=$(cat /var/run/mcs-simulator.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID 2>/dev/null
        rm -f /var/run/mcs-simulator.pid
        echo "模拟器已停止 (PID: $PID)"
        stopped=true
    fi
fi
pkill -f demo_generator.py 2>/dev/null && stopped=true
if ! $stopped; then
    echo "模拟器未在运行"
fi
EOF
    chmod +x "$INSTALL_DIR/stop-simulator.sh"
}

perform_update() {
    log_step "开始更新..."
    
    cd "$INSTALL_DIR"
    
    # 步骤1: 备份数据库
    log_info "[1/8] 备份数据库..."
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # 检查数据库容器是否运行且健康
    if docker ps --filter "name=mcs_db" --filter "health=healthy" -q 2>/dev/null | grep -q .; then
        if docker exec mcs_db pg_dump -U postgres mcs_iot > "$BACKUP_FILE" 2>/dev/null; then
            log_info "✓ 数据库已备份到: $INSTALL_DIR/$BACKUP_FILE"
        else
            log_warn "数据库备份失败，继续更新..."
        fi
    elif docker ps --filter "name=mcs_db" -q 2>/dev/null | grep -q .; then
        # 容器运行中但可能健康检查未通过，尝试备份
        if docker exec mcs_db pg_dump -U postgres mcs_iot > "$BACKUP_FILE" 2>/dev/null; then
            log_info "✓ 数据库已备份到: $INSTALL_DIR/$BACKUP_FILE"
        else
            log_warn "数据库备份失败，继续更新..."
        fi
    else
        log_warn "数据库容器未运行，跳过备份"
    fi
    
    # 步骤2: 拉取最新代码
    log_info "[2/8] 拉取最新代码..."
    if [[ -d ".git" ]]; then
        git fetch origin 2>/dev/null || true
        git pull origin main 2>/dev/null || git reset --hard origin/main 2>/dev/null || true
        log_info "✓ 代码已更新"
    else
        log_warn "非 Git 仓库，跳过代码更新"
    fi
    
    # 步骤3: 拉取最新镜像
    log_info "[3/8] 拉取最新镜像..."
    if [[ -f "docker-compose.ghcr.yml" ]]; then
        if docker compose -f docker-compose.ghcr.yml pull 2>&1; then
            log_info "✓ 镜像已更新"
        else
            log_warn "部分镜像拉取失败"
        fi
        COMPOSE_FILE="docker-compose.ghcr.yml"
    else
        log_info "使用本地构建模式"
        docker compose build --no-cache 2>/dev/null || docker-compose build --no-cache 2>/dev/null
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # 步骤4: 数据库 Schema 迁移
    log_info "[4/8] 检查数据库 Schema..."
    if docker ps --filter "name=mcs_db" -q 2>/dev/null | grep -q .; then
        # 迁移1: 检查 users 表是否存在 permissions 列
        HAS_PERMISSIONS=$(docker exec mcs_db psql -U postgres -d mcs_iot -t -c \
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='permissions';" 2>/dev/null | tr -d ' ')
        
        if [[ -z "$HAS_PERMISSIONS" ]]; then
            log_info "正在添加 permissions 字段到 users 表..."
            docker exec mcs_db psql -U postgres -d mcs_iot -c \
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT DEFAULT '{}';" 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log_info "✓ 已添加 permissions 字段"
            else
                log_warn "permissions 字段添加失败"
            fi
        fi
        
        # 迁移2: 检查 ai_summary_logs 表是否存在
        HAS_AI_SUMMARY_TABLE=$(docker exec mcs_db psql -U postgres -d mcs_iot -t -c \
            "SELECT table_name FROM information_schema.tables WHERE table_name='ai_summary_logs';" 2>/dev/null | tr -d ' ')
        
        if [[ -z "$HAS_AI_SUMMARY_TABLE" ]]; then
            log_info "正在创建 ai_summary_logs 表..."
            docker exec mcs_db psql -U postgres -d mcs_iot -c "
                CREATE TABLE IF NOT EXISTS ai_summary_logs (
                    id SERIAL PRIMARY KEY,
                    time_range VARCHAR(32),
                    content TEXT NOT NULL,
                    alarm_count INT DEFAULT 0,
                    instrument_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_ai_summary_time ON ai_summary_logs (created_at DESC);
            " 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log_info "✓ 已创建 ai_summary_logs 表"
            else
                log_warn "ai_summary_logs 表创建失败"
            fi
        fi
        
        log_info "✓ 数据库 Schema 检查完成"
    else
        log_warn "数据库容器未运行，跳过 Schema 迁移 (服务启动后会自动处理)"
    fi
    
    # 步骤5: 清除授权缓存（确保使用新的设备ID验证）
    log_info "[5/8] 清除授权缓存..."
    if docker ps --filter "name=mcs_redis" -q 2>/dev/null | grep -q .; then
        docker exec mcs_redis redis-cli DEL license:status license:grace_start license:error license:tampered 2>/dev/null || true
        log_info "✓ 授权缓存已清除"
    fi
    
    # 步骤6: 重启服务
    log_info "[6/8] 重启服务..."
    docker compose -f "$COMPOSE_FILE" up -d 2>/dev/null || docker-compose -f "$COMPOSE_FILE" up -d 2>/dev/null
    
    # 步骤7: 更新管理脚本
    log_info "[7/8] 更新管理脚本..."
    update_simulator_scripts
    log_info "✓ 脚本已更新"
    
    # 步骤8: 等待服务就绪
    log_info "[8/8] 等待服务就绪..."
    sleep 15
    
    # 显示状态
    echo ""
    log_info "服务状态:"
    docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || docker-compose -f "$COMPOSE_FILE" ps 2>/dev/null
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✓ 更新完成!                                    ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  📁 备份文件: $INSTALL_DIR/$BACKUP_FILE"
    echo -e "  🌐 访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'your-server-ip'):3000"
    echo ""
    
    exit 0
}

# =============================================================================
# 环境检测
# =============================================================================

detect_os() {
    log_step "第一步：检测操作系统环境"
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_NAME=$NAME
        OS_VERSION=$VERSION_ID
        OS_ID=$ID
    else
        log_error "无法检测操作系统版本，请确保使用的是受支持的 Linux 发行版"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS_NAME $OS_VERSION"
    
    # 检查是否支持
    case $OS_ID in
        ubuntu|debian)
            PKG_MANAGER="apt"
            PKG_UPDATE="apt update"
            PKG_INSTALL="apt install -y"
            ;;
        centos|rhel|rocky|almalinux|opencloudos|openeuler)
            PKG_MANAGER="yum"
            PKG_UPDATE="yum makecache"
            PKG_INSTALL="yum install -y"
            # CentOS 8+ 使用 dnf
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf makecache"
                PKG_INSTALL="dnf install -y"
            fi
            ;;
        fedora)
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf makecache"
            PKG_INSTALL="dnf install -y"
            ;;
        *)
            log_warn "未经测试的操作系统: $OS_ID，将尝试继续安装"
            PKG_MANAGER="apt"
            PKG_UPDATE="apt update"
            PKG_INSTALL="apt install -y"
            ;;
    esac
    
    log_info "包管理器: $PKG_MANAGER"
    
    # 检查是否为 root
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 用户运行此脚本，或使用 sudo"
        log_info "使用方法: sudo bash deploy.sh"
        exit 1
    fi
    
    log_info "✓ 操作系统检测通过"
}

check_resources() {
    log_step "第二步：检测服务器资源"
    
    # 检查内存
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    log_info "总内存: ${TOTAL_MEM}MB"
    
    if [[ $TOTAL_MEM -lt 1024 ]]; then
        log_warn "内存较低 (< 1GB)，可能会影响系统运行"
        if ! confirm "是否继续安装?"; then
            exit 1
        fi
    fi
    
    # 检查磁盘空间
    DISK_FREE=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    log_info "根目录可用空间: ${DISK_FREE}GB"
    
    if [[ $DISK_FREE -lt 5 ]]; then
        log_error "磁盘空间不足 (< 5GB)，请清理后重试"
        exit 1
    fi
    
    # 检查 CPU
    CPU_CORES=$(nproc)
    log_info "CPU 核心数: $CPU_CORES"
    
    log_info "✓ 服务器资源检测通过"
}

setup_swap() {
    log_step "内存优化：检查 Swap 空间"
    
    # 检查是否已有 swap
    SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
    
    if [[ $SWAP_TOTAL -gt 0 ]]; then
        log_info "✓ 已有 Swap 空间: ${SWAP_TOTAL}MB"
        return 0
    fi
    
    # 检查内存，小于4GB时自动创建swap
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    
    if [[ $TOTAL_MEM -lt 4096 ]]; then
        log_warn "内存较低(${TOTAL_MEM}MB)，没有 Swap，将自动创建 2GB Swap 空间"
        
        # 检查磁盘空间是否足够
        DISK_FREE=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
        if [[ $DISK_FREE -lt 3 ]]; then
            log_warn "磁盘空间不足，跳过 Swap 创建"
            return 0
        fi
        
        log_info "正在创建 2GB Swap 文件..."
        
        # 创建 swap 文件
        if dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress 2>&1; then
            chmod 600 /swapfile
            mkswap /swapfile
            swapon /swapfile
            
            # 添加到 fstab 使其永久生效
            if ! grep -q '/swapfile' /etc/fstab; then
                echo '/swapfile none swap sw 0 0' >> /etc/fstab
            fi
            
            log_info "✓ Swap 空间创建成功 (2GB)"
        else
            log_warn "Swap 创建失败，继续安装"
        fi
    else
        log_info "✓ 内存充足(${TOTAL_MEM}MB)，无需 Swap"
    fi
}

configure_china_mirror() {
    log_step "网络加速配置"
    
    echo ""
    echo -e "${CYAN}如果您的服务器在中国大陆，建议使用国内镜像加速${NC}"
    echo -e "${CYAN}这将加快 GitHub 代码拉取和 Docker 镜像下载速度${NC}"
    echo ""
    
    if confirm "是否使用中国大陆镜像加速?"; then
        USE_CHINA_MIRROR=true
        log_info "已启用中国大陆镜像加速"
        
        # 配置 Docker 镜像加速
        log_info "配置 Docker 镜像加速..."
        mkdir -p /etc/docker
        cat > /etc/docker/daemon.json << 'EOF'
{
    "registry-mirrors": [
        "https://docker.1panel.live",
        "https://hub.rat.dev",
        "https://docker.kejilion.pro"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
        
        # 如果 Docker 已安装，重启服务
        if command -v docker &> /dev/null && systemctl is-active --quiet docker; then
            systemctl daemon-reload
            systemctl restart docker
            log_info "✓ Docker 镜像加速已配置并生效"
        else
            log_info "✓ Docker 镜像加速已配置 (Docker 安装后生效)"
        fi
    else
        USE_CHINA_MIRROR=false
        log_info "使用默认国际源"
    fi
}

check_ports() {
    log_step "第三步：检测端口占用情况"
    
    # 注意: 80/443 端口由宝塔 nginx 管理，不再检测
    REQUIRED_PORTS=(1883 8883 3000 5432 6379 8000)
    PORTS_IN_USE=()
    
    log_info "检测以下端口: ${REQUIRED_PORTS[*]}"
    
    for port in "${REQUIRED_PORTS[@]}"; do
        # 简化端口检测逻辑，直接匹配 :端口 模式
        if ss -tuln 2>/dev/null | grep -qE "[[:space:]].*:${port}[[:space:]]"; then
            PORTS_IN_USE+=($port)
            log_warn "端口 $port 已被占用"
        fi
    done
    
    if [[ ${#PORTS_IN_USE[@]} -gt 0 ]]; then
        echo ""
        log_warn "以下端口已被占用: ${PORTS_IN_USE[*]}"
        log_info "端口说明:"
        log_info "  - 3000: 前端服务"
        log_info "  - 8000: 后端 API"
        log_info "  - 1883/8883: MQTT 服务"
        log_info "  - 5432: PostgreSQL 数据库"
        log_info "  - 6379: Redis 缓存"
        echo ""
        log_info "提示: 80/443 端口由宝塔 nginx 管理，无需检测"
        echo ""
        if ! confirm "是否继续? (部署后 Docker 将使用这些端口)"; then
            exit 1
        fi
    else
        log_info "✓ 所有必需端口均可用"
    fi
}

# =============================================================================
# 安装依赖
# =============================================================================

install_docker() {
    log_step "第四步：安装 Docker"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        log_info "Docker 已安装，版本: $DOCKER_VERSION"
        
        # 确保 Docker 服务运行
        if ! systemctl is-active --quiet docker; then
            log_info "启动 Docker 服务..."
            systemctl start docker
            systemctl enable docker
        fi
        return 0
    fi
    
    log_info "正在安装 Docker..."
    
    case $PKG_MANAGER in
        apt)
            $PKG_UPDATE
            $PKG_INSTALL ca-certificates curl gnupg lsb-release
            
            # 添加 Docker GPG 密钥
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS_ID/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            chmod a+r /etc/apt/keyrings/docker.gpg
            
            # 添加 Docker 源
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS_ID $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            $PKG_UPDATE
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        yum|dnf)
            $PKG_INSTALL yum-utils
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            $PKG_INSTALL docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
    esac
    
    # 启动 Docker
    systemctl start docker
    systemctl enable docker
    
    log_info "✓ Docker 安装完成"
}

install_docker_compose() {
    log_step "第五步：检查 Docker Compose"
    
    # 检查新版 docker compose (V2)
    if docker compose version &> /dev/null; then
        log_info "Docker Compose 已安装 (V2)"
        return 0
    fi
    
    # 检查旧版 docker-compose
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose 已安装 (V1)"
        return 0
    fi
    
    log_info "正在安装 Docker Compose..."
    
    # 下载 docker-compose
    curl -L "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    log_info "✓ Docker Compose 安装完成"
}

# install_certbot() 函数已移除
# SSL 证书改由用户在宝塔面板中申请和管理

install_dependencies() {
    log_step "安装其他依赖"
    
    case $PKG_MANAGER in
        apt)
            $PKG_UPDATE
            $PKG_INSTALL git curl wget nano python3 python3-pip
            ;;
        yum|dnf)
            $PKG_UPDATE
            $PKG_INSTALL git curl wget nano python3 python3-pip
            ;;
    esac
    
    # 安装 Python 依赖 (用于模拟器)
    # 兼容不同版本的 pip
    pip3 install paho-mqtt requests --quiet --break-system-packages 2>/dev/null || \
    pip3 install paho-mqtt requests --quiet 2>/dev/null || true
    
    log_info "✓ 依赖安装完成"
}

# =============================================================================
# 域名配置
# =============================================================================

configure_domains() {
    log_step "第七步：配置域名"
    
    # 获取服务器 IP
    SERVER_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null) || SERVER_IP=""
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(curl -s --connect-timeout 5 ip.sb 2>/dev/null) || SERVER_IP=""
    fi
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || SERVER_IP="无法获取"
    fi
    
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                        域名配置说明                               ║${NC}"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║  本系统需要使用 4 个子域名，您只需输入一级域名即可               ║${NC}"
    echo -e "${CYAN}║                                                                   ║${NC}"
    echo -e "${CYAN}║  例如输入: zhizinan.top                                           ║${NC}"
    echo -e "${CYAN}║  系统将自动使用以下子域名:                                        ║${NC}"
    echo -e "${CYAN}║    • iot.zhizinan.top    - 主站/管理后台                          ║${NC}"
    echo -e "${CYAN}║    • api.zhizinan.top    - API 接口                               ║${NC}"
    echo -e "${CYAN}║    • mqtt.zhizinan.top   - MQTT 服务                              ║${NC}"
    echo -e "${CYAN}║    • screen.zhizinan.top - 大屏展示                               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "当前服务器 IP: ${GREEN}$SERVER_IP${NC}"
    echo ""
    
    # 输入一级域名
    while true; do
        read -r -p "请输入您的一级域名 (例如 zhizinan.top): " BASE_DOMAIN
        
        # 验证域名格式
        if [[ -z "$BASE_DOMAIN" ]]; then
            log_warn "域名不能为空，请重新输入"
            continue
        fi
        
        # 去除可能的 http/https 前缀和末尾斜杠
        BASE_DOMAIN=$(echo "$BASE_DOMAIN" | sed 's|^https\?://||' | sed 's|/$||')
        
        # 检查是否已经是子域名
        if [[ "$BASE_DOMAIN" =~ ^(iot|api|mqtt|screen)\. ]]; then
            log_warn "请输入一级域名，不要输入子域名"
            continue
        fi
        
        break
    done
    
    # 自动生成 4 个子域名
    DOMAIN_MAIN="iot.${BASE_DOMAIN}"
    DOMAIN_API="api.${BASE_DOMAIN}"
    DOMAIN_MQTT="mqtt.${BASE_DOMAIN}"
    DOMAIN_SCREEN="screen.${BASE_DOMAIN}"
    
    echo ""
    echo -e "${GREEN}将使用以下域名:${NC}"
    echo -e "  ${YELLOW}主站/管理后台:${NC} $DOMAIN_MAIN  →  反代到 ${CYAN}127.0.0.1:3000${NC}"
    echo -e "  ${YELLOW}API 接口:${NC}      $DOMAIN_API   →  反代到 ${CYAN}127.0.0.1:8000${NC}"
    echo -e "  ${YELLOW}MQTT 服务:${NC}     $DOMAIN_MQTT  →  (仅需 DNS 解析，无需反代)"
    echo -e "  ${YELLOW}大屏展示:${NC}      $DOMAIN_SCREEN →  反代到 ${CYAN}127.0.0.1:3000${NC}"
    echo ""
    
    if ! confirm "域名配置正确吗?"; then
        log_info "请重新运行脚本"
        exit 1
    fi
}

guide_bt_panel_setup() {
    log_step "第八步：在宝塔面板配置域名"
    
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ⚠️  重要：请先完成以下操作  ⚠️                  ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}【步骤 1】在 DNS 服务商处添加解析记录${NC}"
    echo -e "  请将以下 4 个子域名的 A 记录指向本服务器 IP: ${GREEN}$SERVER_IP${NC}"
    echo ""
    echo -e "    ${CYAN}iot.${BASE_DOMAIN}${NC}    →  $SERVER_IP"
    echo -e "    ${CYAN}api.${BASE_DOMAIN}${NC}    →  $SERVER_IP"
    echo -e "    ${CYAN}mqtt.${BASE_DOMAIN}${NC}   →  $SERVER_IP"
    echo -e "    ${CYAN}screen.${BASE_DOMAIN}${NC} →  $SERVER_IP"
    echo ""
    echo -e "${YELLOW}【步骤 2】在宝塔面板中创建网站并配置反向代理${NC}"
    echo ""
    echo -e "  打开宝塔面板 → 网站 → 添加站点，分别创建以下 3 个网站:"
    echo ""
    echo -e "  ┌─────────────────────────────────────────────────────────────────┐"
    echo -e "  │  域名                    │  反向代理目标                        │"
    echo -e "  ├─────────────────────────────────────────────────────────────────┤"
    echo -e "  │  ${GREEN}iot.${BASE_DOMAIN}${NC}        │  http://${RED}127.0.0.1${NC}:3000              │"
    echo -e "  │  ${GREEN}api.${BASE_DOMAIN}${NC}        │  http://${RED}127.0.0.1${NC}:8000              │"
    echo -e "  │  ${GREEN}screen.${BASE_DOMAIN}${NC}     │  http://${RED}127.0.0.1${NC}:3000              │"
    echo -e "  └─────────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e "  ${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "  ${RED}║  ⚠️  重要警告：反向代理目标必须使用 127.0.0.1，不能用公网 IP  ║${NC}"
    echo -e "  ${RED}║                                                               ║${NC}"
    echo -e "  ${RED}║  ❌ 错误: http://$SERVER_IP:3000                     ║${NC}"
    echo -e "  ${RED}║  ✅ 正确: http://127.0.0.1:3000                               ║${NC}"
    echo -e "  ${RED}║                                                               ║${NC}"
    echo -e "  ${RED}║  使用公网 IP 会导致 502 Bad Gateway 错误!                     ║${NC}"
    echo -e "  ${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}提示: mqtt.${BASE_DOMAIN} 不需要创建网站，只需 DNS 解析即可${NC}"
    echo ""
    echo -e "${YELLOW}【步骤 3】为每个网站申请 SSL 证书${NC}"
    echo ""
    echo -e "  在宝塔面板中，点击每个网站 → SSL → Let's Encrypt → 申请证书"
    echo -e "  ${RED}⚠️ 特别注意: iot.${BASE_DOMAIN} 的证书将用于 MQTT TLS 加密${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    read -r -p "请完成以上操作后按 Enter 键继续..." DUMMY
    echo ""
    
    if ! confirm "您是否已完成 DNS 解析、反向代理配置和 SSL 证书申请?"; then
        log_warn "请完成配置后重新运行脚本"
        exit 1
    fi
}

verify_bt_panel_config() {
    log_step "第九步：验证宝塔面板配置"
    
    log_info "正在检查 Nginx 配置和 SSL 证书..."
    echo ""
    
    # 宝塔 SSL 证书可能的路径
    BT_SSL_PATHS=(
        "/www/server/panel/vhost/ssl/${DOMAIN_MAIN}"
        "/www/server/panel/vhost/cert/${DOMAIN_MAIN}"
        "/etc/letsencrypt/live/${DOMAIN_MAIN}"
    )
    
    SSL_FOUND=false
    SSL_PATH=""
    
    for path in "${BT_SSL_PATHS[@]}"; do
        if [[ -d "$path" ]]; then
            # 检查证书文件是否存在
            if [[ -f "$path/fullchain.pem" || -f "$path/server.crt" || -f "$path/cert.pem" ]]; then
                SSL_FOUND=true
                SSL_PATH="$path"
                log_info "✓ 找到 SSL 证书目录: $path"
                break
            fi
        fi
    done
    
    # 检查 Nginx 配置
    NGINX_CONF_PATHS=(
        "/www/server/panel/vhost/nginx/${DOMAIN_MAIN}.conf"
        "/www/server/nginx/conf/vhost/${DOMAIN_MAIN}.conf"
    )
    
    NGINX_FOUND=false
    for conf in "${NGINX_CONF_PATHS[@]}"; do
        if [[ -f "$conf" ]]; then
            NGINX_FOUND=true
            log_info "✓ 找到 Nginx 配置: $conf"
            break
        fi
    done
    
    if [[ "$SSL_FOUND" == "false" ]]; then
        log_warn "未找到 iot.${BASE_DOMAIN} 的 SSL 证书"
        echo ""
        echo -e "${YELLOW}请检查是否已在宝塔面板中申请 SSL 证书${NC}"
        echo -e "${YELLOW}证书应该位于以下路径之一:${NC}"
        for path in "${BT_SSL_PATHS[@]}"; do
            echo -e "  - $path"
        done
        echo ""
        
        if confirm "是否跳过证书检查，使用自签名证书?"; then
            log_info "将生成自签名证书..."
            USE_SELF_SIGNED=true
        else
            log_error "请先申请 SSL 证书后重新运行脚本"
            exit 1
        fi
    fi
    
    if [[ "$NGINX_FOUND" == "false" ]]; then
        log_warn "未找到 iot.${BASE_DOMAIN} 的 Nginx 配置"
        log_warn "请确保已在宝塔面板中创建网站并配置反向代理"
        echo ""
        if ! confirm "是否继续安装? (反向代理需要在部署后手动配置)"; then
            exit 1
        fi
    fi
    
    echo ""
    log_info "✓ 配置验证完成"
}

copy_ssl_certificates() {
    log_step "第十步：配置 SSL 证书"
    
    local SSL_DIR="$INSTALL_DIR/nginx/ssl"
    mkdir -p "$SSL_DIR"
    
    if [[ "${USE_SELF_SIGNED:-false}" == "true" ]]; then
        # 生成自签名证书
        log_info "生成临时自签名证书..."
        
        if openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/server.key" \
            -out "$SSL_DIR/server.crt" \
            -subj "/CN=${DOMAIN_MQTT}/O=MCS-IoT/C=CN" 2>/dev/null; then
            
            cp "$SSL_DIR/server.crt" "$SSL_DIR/ca.crt"
            chmod 644 "$SSL_DIR/server.crt" "$SSL_DIR/ca.crt"
            chmod 600 "$SSL_DIR/server.key"
            
            log_info "✓ 自签名证书已生成"
            log_warn "注意: 生产环境建议使用正式 SSL 证书"
        else
            log_error "证书生成失败"
            return 1
        fi
    else
        # 从宝塔复制证书
        log_info "从宝塔面板复制 SSL 证书..."
        
        # 确定证书文件名
        if [[ -f "$SSL_PATH/fullchain.pem" ]]; then
            CERT_FILE="fullchain.pem"
            KEY_FILE="privkey.pem"
        elif [[ -f "$SSL_PATH/server.crt" ]]; then
            CERT_FILE="server.crt"
            KEY_FILE="server.key"
        elif [[ -f "$SSL_PATH/cert.pem" ]]; then
            CERT_FILE="cert.pem"
            KEY_FILE="key.pem"
        else
            log_warn "未找到标准证书文件，尝试生成自签名证书"
            USE_SELF_SIGNED=true
            copy_ssl_certificates
            return $?
        fi
        
        # 复制并重命名证书
        if cp "$SSL_PATH/$CERT_FILE" "$SSL_DIR/server.crt" && \
           cp "$SSL_PATH/$KEY_FILE" "$SSL_DIR/server.key"; then
            
            # 创建 ca.crt (用于 MQTT)
            cp "$SSL_DIR/server.crt" "$SSL_DIR/ca.crt"
            
            chmod 644 "$SSL_DIR/server.crt" "$SSL_DIR/ca.crt"
            chmod 600 "$SSL_DIR/server.key"
            
            log_info "✓ SSL 证书已复制到 $SSL_DIR/"
            log_info "  - server.crt (来自 $CERT_FILE)"
            log_info "  - server.key (来自 $KEY_FILE)"
            log_info "  - ca.crt (MQTT 使用)"
        else
            log_error "证书复制失败"
            log_warn "尝试生成自签名证书..."
            USE_SELF_SIGNED=true
            copy_ssl_certificates
            return $?
        fi
    fi
}

configure_credentials() {
    log_step "第十一步：配置密码和 API 密钥"
    
    echo ""
    echo -e "${CYAN}接下来需要设置一些密码和 API 密钥${NC}"
    echo ""
    
    # 数据库密码
    echo -e "${YELLOW}提示: 输入密码时不会显示任何字符，这是正常的安全特性，请放心输入${NC}"
    echo ""
    while true; do
        read -r -s -p "请设置数据库密码 (至少8位): " DB_PASSWORD
        echo ""
        if [[ ${#DB_PASSWORD} -lt 8 ]]; then
            log_warn "密码太短，请设置至少 8 位密码"
            continue
        fi
        read -r -s -p "请再次输入数据库密码: " DB_PASSWORD_CONFIRM
        echo ""
        if [[ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]]; then
            log_warn "两次输入的密码不一致，请重试"
            continue
        fi
        break
    done
    log_info "✓ 数据库密码已设置"
    
    echo ""
    
    # 后台管理员密码
    echo -e "${CYAN}后台管理员账号为 admin，请设置密码${NC}"
    while true; do
        read -r -s -p "请设置后台管理员密码 (至少6位): " ADMIN_PASSWORD
        echo ""
        if [[ ${#ADMIN_PASSWORD} -lt 6 ]]; then
            log_warn "密码太短，请设置至少 6 位密码"
            continue
        fi
        break
    done
    log_info "✓ 后台管理员密码已设置"
    
    echo ""
    
    # MQTT 密码
    echo -e "${CYAN}MQTT 用于设备与平台通信，请设置访问密码${NC}"
    while true; do
        read -r -s -p "请设置 MQTT 密码 (至少6位): " MQTT_PASSWORD
        echo ""
        if [[ ${#MQTT_PASSWORD} -lt 6 ]]; then
            log_warn "密码太短，请设置至少 6 位密码"
            continue
        fi
        break
    done
    log_info "✓ MQTT 密码已设置"
    
    # 自动生成 JWT 密钥
    JWT_SECRET=$(openssl rand -hex 32)
    log_info "✓ JWT 密钥已自动生成"
    
    echo ""
    
    # 天气 API
    echo -e "${CYAN}心知天气 API 用于获取天气数据显示在大屏上${NC}"
    echo -e "${CYAN}获取地址: https://www.seniverse.com/${NC}"
    read -r -p "请输入心知天气 API Key (留空则跳过): " WEATHER_API_KEY
    if [[ -n "$WEATHER_API_KEY" ]]; then
        log_info "✓ 天气 API Key 已设置"
    else
        log_warn "未设置天气 API，大屏将不显示天气信息"
    fi
    
    echo ""
    
    # AI API 配置
    echo -e "${CYAN}AI API 用于生成智能分析报告 (可选)${NC}"
    echo -e "${YELLOW}购买 AI API Key 请前往: https://zhizinan.top${NC}"
    echo ""
    read -r -p "请输入 AI API Key (留空则跳过): " AI_API_KEY
    if [[ -n "$AI_API_KEY" ]]; then
        echo ""
        echo -e "${CYAN}请输入 AI 模型名称:${NC}"
        echo -e "${CYAN}常用模型参考: gemini-lite, gpt-4o-mini, gpt-4o, gemini-2.0-flash, claude-3-5-sonnet${NC}"
        read -r -p "请输入模型名称 (默认 gemini-lite): " AI_MODEL
        AI_MODEL=${AI_MODEL:-gemini-lite}
        log_info "✓ AI API 已设置，模型: $AI_MODEL"
    else
        log_warn "未设置 AI API，可稍后在管理后台配置"
    fi
    
    # Let's Encrypt 邮箱部分已移除，改由用户在宝塔面板申请证书
}

# =============================================================================
# 部署项目
# =============================================================================

clone_repository() {
    log_step "第八步：下载项目代码"
    
    # 确保不在安装目录内
    cd /root || cd /tmp || cd /
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warn "安装目录 $INSTALL_DIR 已存在"
        if confirm "是否删除并重新下载?"; then
            rm -rf "$INSTALL_DIR"
        else
            log_info "使用现有目录"
            return 0
        fi
    fi
    
    # 选择 GitHub 源
    if [[ "$USE_CHINA_MIRROR" == "true" ]]; then
        log_info "使用中国镜像加速下载..."
        git clone "$REPO_URL_CN" "$INSTALL_DIR" || {
            log_warn "镜像源失败，尝试直接访问 GitHub..."
            git clone "$REPO_URL" "$INSTALL_DIR"
        }
    else
        log_info "正在从 GitHub 克隆项目..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    
    # 创建必要的目录
    mkdir -p "$INSTALL_DIR/nginx/ssl"
    mkdir -p "$INSTALL_DIR/mosquitto/config"
    mkdir -p "$INSTALL_DIR/mosquitto/data"
    mkdir -p "$INSTALL_DIR/mosquitto/log"
    
    log_info "✓ 项目代码下载完成"
}

# generate_ssl_certificates 已移除，现使用 copy_ssl_certificates 函数

generate_env_file() {
    log_step "第十二步：生成配置文件"
    
    cat > "$INSTALL_DIR/.env" << EOF
# =============================================================================
# 元芯物联网智慧云平台 - 环境配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# =============================================================================

# 域名配置
DOMAIN_MAIN=${DOMAIN_MAIN}
DOMAIN_API=${DOMAIN_API}
DOMAIN_MQTT=${DOMAIN_MQTT}
DOMAIN_SCREEN=${DOMAIN_SCREEN}

# 数据库配置
DB_HOST=timescaledb
DB_PORT=5432
DB_USER=postgres
DB_PASS=${DB_PASSWORD}
DB_NAME=mcs_iot

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379

# MQTT 配置
MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USER=admin
MQTT_PASS=${MQTT_PASSWORD}

# 后台管理员密码
ADMIN_INITIAL_PASSWORD=${ADMIN_PASSWORD}

# JWT 密钥 (用于用户登录认证)
JWT_SECRET=${JWT_SECRET}

# 天气 API (心知天气)
WEATHER_API_KEY=${WEATHER_API_KEY}

# AI API 配置 (URL 已固定为 https://newapi2.zhizinan.top/v1)
AI_API_KEY=${AI_API_KEY}
AI_MODEL=${AI_MODEL}
EOF

    log_info "✓ 配置文件已生成: $INSTALL_DIR/.env"
}

# setup_ssl_certificates() 函数已移除
# SSL 证书改由用户在宝塔面板中申请和管理

# generate_nginx_config() 函数已移除
# Nginx 配置改由宝塔面板管理，Docker 内使用 nginx-simple.conf

deploy_containers() {
    log_step "第十三步：拉取镜像并启动 Docker 容器"
    
    cd "$INSTALL_DIR"
    
    # 只使用 ghcr 预构建镜像
    if [[ ! -f "docker-compose.ghcr.yml" ]]; then
        log_error "未找到 docker-compose.ghcr.yml 文件"
        return 1
    fi
    
    log_info "使用预构建镜像部署..."
    log_info "正在拉取镜像，首次可能需要几分钟..."
    echo ""
    
    # 带重试的镜像拉取
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "[1/3] 拉取镜像 (尝试 $attempt/$max_attempts)..."
        if docker compose -f docker-compose.ghcr.yml pull 2>&1; then
            log_info "✓ 镜像拉取成功"
            break
        else
            if [[ $attempt -lt $max_attempts ]]; then
                log_warn "部分镜像拉取失败，30 秒后重试..."
                sleep 30
            else
                log_warn "镜像拉取失败，尝试继续启动..."
            fi
        fi
        ((attempt++))
    done
    
    log_info "[2/3] 启动服务..."
    if docker compose -f docker-compose.ghcr.yml up -d 2>&1; then
        log_info "✓ 服务启动成功"
        # 创建标记文件，供 mcs-iot.sh 识别部署方式
        touch "$INSTALL_DIR/.deployed_with_ghcr"
    else
        log_error "服务启动失败"
        log_info "请检查错误信息并尝试手动运行:"
        log_info "  cd $INSTALL_DIR && docker compose -f docker-compose.ghcr.yml up -d"
        return 1
    fi
    
    # 等待服务启动
    log_info "[3/3] 等待服务就绪..."
    sleep 20
    
    # 检查容器状态
    log_info "检查容器运行状态..."
    docker compose -f docker-compose.ghcr.yml ps
    
    # 检查健康状态
    local healthy_count=$(docker compose -f docker-compose.ghcr.yml ps --format json 2>/dev/null | grep -c '"healthy"' || echo "0")
    if [[ $healthy_count -gt 0 ]]; then
        log_info "✓ 所有服务已就绪"
    else
        log_warn "部分服务可能还在启动中"
        log_info "可使用 'mcs-iot status' 检查服务状态"
    fi
    
    log_info "✓ Docker 容器启动完成"
}

# =============================================================================
# MQTT 密码同步
# =============================================================================

sync_mqtt_password() {
    log_step "第十四步：同步 MQTT 密码"
    
    log_info "正在同步 MQTT 密码到 Mosquitto..."
    
    # 等待 Mosquitto 容器完全启动
    local max_wait=30
    local waited=0
    while ! docker exec mcs_mosquitto ls /mosquitto/config 2>/dev/null | grep -q passwd; do
        if [[ $waited -ge $max_wait ]]; then
            log_warn "等待 Mosquitto 超时，跳过密码同步"
            return 1
        fi
        sleep 1
        ((waited++))
    done
    
    # 使用 mosquitto_passwd 设置密码
    # admin 用户用于所有后端服务连接
    if docker exec mcs_mosquitto mosquitto_passwd -b /mosquitto/config/passwd admin "$MQTT_PASSWORD" 2>/dev/null; then
        log_info "✓ MQTT admin 用户密码已同步"
    else
        log_warn "MQTT 密码同步失败，可能需要手动设置"
        log_info "手动设置方法: docker exec -it mcs_mosquitto mosquitto_passwd -b /mosquitto/config/passwd admin <密码>"
        return 1
    fi
    
    # 重启 Mosquitto 使密码生效
    log_info "重启 Mosquitto 使配置生效..."
    docker restart mcs_mosquitto >/dev/null 2>&1
    sleep 3
    
    # 验证 Mosquitto 是否正常运行
    if docker ps --filter "name=mcs_mosquitto" --filter "status=running" -q | grep -q .; then
        log_info "✓ Mosquitto 已重启并运行"
    else
        log_warn "Mosquitto 重启后未运行，请检查日志"
    fi
    
    log_info "✓ MQTT 密码同步完成"
}

# =============================================================================
# 演示数据 (已禁用 - 不再自动导入模拟数据)
# =============================================================================

# import_demo_data() 函数已禁用
# 如需运行演示数据生成器，请使用: mcs-simulator-start

# =============================================================================
# 部署完成
# =============================================================================

create_management_scripts() {
    log_step "创建管理脚本"
    
    # 模拟器启动脚本
    cat > "$INSTALL_DIR/start-simulator.sh" << 'EOF'
#!/bin/bash
# 启动演示数据生成器
cd /opt/mcs-iot
echo "正在启动 24 个模拟传感器..."
echo "可选参数: -d 分钟数 (默认0=永久运行)"

DURATION=${1:-0}
nohup python3 scripts/demo_generator.py -d "$DURATION" --skip-init > /var/log/mcs-simulator.log 2>&1 &
echo $! > /var/run/mcs-simulator.pid
echo "模拟器已启动，PID: $(cat /var/run/mcs-simulator.pid)"
if [[ "$DURATION" -eq 0 ]]; then
    echo "运行模式: 永久运行"
else
    echo "运行时长: ${DURATION} 分钟"
fi
echo "查看日志: tail -f /var/log/mcs-simulator.log"
EOF
    chmod +x "$INSTALL_DIR/start-simulator.sh"
    
    # 模拟器停止脚本
    cat > "$INSTALL_DIR/stop-simulator.sh" << 'EOF'
#!/bin/bash
# 停止模拟传感器
stopped=false

# 停止演示生成器
if [[ -f /var/run/mcs-demo-generator.pid ]]; then
    PID=$(cat /var/run/mcs-demo-generator.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "演示生成器已停止 (PID: $PID)"
        stopped=true
    fi
    rm -f /var/run/mcs-demo-generator.pid
fi

# 停止模拟器
if [[ -f /var/run/mcs-simulator.pid ]]; then
    PID=$(cat /var/run/mcs-simulator.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "模拟器已停止 (PID: $PID)"
        stopped=true
    fi
    rm -f /var/run/mcs-simulator.pid
fi

if [[ "$stopped" == "false" ]]; then
    # 尝试查找并停止
    pkill -f "demo_generator.py" && echo "已停止演示生成器" || true
    pkill -f "simulator.py" && echo "已停止模拟器" || echo "无运行中的模拟器"
fi
EOF
    chmod +x "$INSTALL_DIR/stop-simulator.sh"
    
    # 服务管理脚本
    cat > "$INSTALL_DIR/mcs-iot.sh" << 'EOF'
#!/bin/bash
# 元芯物联网平台管理脚本
cd /opt/mcs-iot

# 自动检测使用的 compose 文件
if [[ -f ".deployed_with_ghcr" ]]; then
    COMPOSE_FILE="docker-compose.ghcr.yml"
elif [[ -f "docker-compose.ghcr.yml" ]] && docker ps --format '{{.Image}}' 2>/dev/null | grep -q "ghcr.io"; then
    COMPOSE_FILE="docker-compose.ghcr.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

compose_cmd() {
    if docker compose version &>/dev/null; then
        docker compose -f "$COMPOSE_FILE" "$@"
    else
        docker-compose -f "$COMPOSE_FILE" "$@"
    fi
}

case "$1" in
    start)
        echo "启动服务 (使用 $COMPOSE_FILE)..."
        compose_cmd up -d
        ;;
    stop)
        echo "停止服务..."
        compose_cmd down
        ;;
    restart)
        echo "重启服务..."
        compose_cmd restart
        ;;
    status)
        compose_cmd ps
        ;;
    logs)
        compose_cmd logs -f ${2:-}
        ;;
    rebuild)
        echo "重新构建并启动..."
        compose_cmd up -d --build
        ;;
    update)
        echo "更新镜像并重启..."
        compose_cmd pull
        compose_cmd up -d
        ;;
    *)
        echo "用法: mcs-iot {start|stop|restart|status|logs|rebuild|update}"
        echo ""
        echo "  start   - 启动所有服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看日志 (可指定服务名)"
        echo "  rebuild - 重新构建并启动"
        echo "  update  - 更新镜像并重启"
        exit 1
        ;;
esac
EOF
    chmod +x "$INSTALL_DIR/mcs-iot.sh"
    
    # 创建全局命令
    ln -sf "$INSTALL_DIR/mcs-iot.sh" /usr/local/bin/mcs-iot
    ln -sf "$INSTALL_DIR/start-simulator.sh" /usr/local/bin/mcs-simulator-start
    ln -sf "$INSTALL_DIR/stop-simulator.sh" /usr/local/bin/mcs-simulator-stop
    
    log_info "✓ 管理脚本已创建"
}

print_success() {
    echo ""
    echo -e "${GREEN}╭═══════════════════════════════════════════════════════════════════╮${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}║              🎉 元芯物联网智慧云平台 部署成功！ 🎉                ║${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}╰═══════════════════════════════════════════════════════════════════╯${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                         访问地址                                   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  📊 ${YELLOW}管理后台:${NC}  https://${DOMAIN_MAIN}"
    echo -e "  📡 ${YELLOW}API 接口:${NC}  https://${DOMAIN_API}"
    echo -e "  🖥️  ${YELLOW}大屏展示:${NC}  https://${DOMAIN_SCREEN}/screen"
    echo -e "  🔌 ${YELLOW}MQTT 服务:${NC} ${DOMAIN_MQTT}:8883 (TLS)"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                         管理命令                                   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  服务管理:"
    echo -e "    ${YELLOW}mcs-iot start${NC}          - 启动所有服务"
    echo -e "    ${YELLOW}mcs-iot stop${NC}           - 停止所有服务"
    echo -e "    ${YELLOW}mcs-iot restart${NC}        - 重启所有服务"
    echo -e "    ${YELLOW}mcs-iot status${NC}         - 查看服务状态"
    echo -e "    ${YELLOW}mcs-iot logs${NC}           - 查看日志"
    echo -e "    ${YELLOW}mcs-iot update${NC}         - 更新镜像并重启"
    echo ""
    echo -e "  模拟器:"
    echo -e "    ${YELLOW}mcs-simulator-start${NC}    - 启动 24 个模拟传感器"
    echo -e "    ${YELLOW}mcs-simulator-stop${NC}     - 停止模拟传感器"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                         重要信息                                   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  📁 安装目录:    ${INSTALL_DIR}"
    echo -e "  📄 配置文件:    ${INSTALL_DIR}/.env"
    echo -e "  🔐 SSL 证书:    ${INSTALL_DIR}/nginx/ssl/"
    echo -e "  👤 管理员账号:  admin"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if confirm "是否立即启动模拟传感器进行测试?"; then
        log_info "启动模拟传感器..."
        /usr/local/bin/mcs-simulator-start
    fi
    
    echo ""
    log_info "感谢您使用元芯物联网智慧云平台！如有问题，请访问 GitHub 提交 Issue"
    echo ""
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    print_banner
    
    # 首先检查是否已有部署
    if check_existing_deployment; then
        run_update_mode
        # 如果 run_update_mode 返回，说明用户选择了重新安装
    fi
    
    log_info "欢迎使用元芯物联网智慧云平台一键部署脚本"
    log_info "此脚本将自动完成以下任务:"
    echo "  1. 检测操作系统和服务器资源"
    echo "  2. 安装 Docker 和必要依赖"
    echo "  3. 克隆项目代码"
    echo "  4. 引导您在宝塔面板配置域名和 SSL 证书"
    echo "  5. 验证配置并复制证书"
    echo "  6. 配置密码和 API 密钥"
    echo "  7. 拉取镜像并部署服务"
    echo ""
    log_warn "重要: 本脚本需要您的宝塔面板已安装 Nginx"
    echo ""
    
    if ! confirm "是否继续安装?" "Y"; then
        log_info "安装已取消"
        exit 0
    fi
    
    # ===== 第一阶段: 环境准备 =====
    detect_os
    check_resources
    setup_swap
    configure_china_mirror
    check_ports
    install_dependencies
    install_docker
    install_docker_compose
    
    # ===== 第二阶段: 域名配置和代码克隆 =====
    configure_domains           # 第七步: 输入一级域名
    clone_repository            # 第八步调整为: 下载项目代码
    
    # ===== 第三阶段: 宝塔配置引导 =====
    guide_bt_panel_setup        # 第九步调整为: 引导用户在宝塔面板配置
    verify_bt_panel_config      # 第十步调整为: 验证宝塔配置
    copy_ssl_certificates       # 第十一步调整为: 复制/生成 SSL 证书
    
    # ===== 第四阶段: 密码配置和部署 =====
    configure_credentials       # 第十二步: 配置密码和 API 密钥
    generate_env_file           # 第十三步: 生成配置文件
    deploy_containers           # 第十四步: 拉取镜像并启动容器
    sync_mqtt_password          # 第十五步: 同步 MQTT 密码到 Mosquitto
    
    # ===== 第五阶段: 完成 =====
    create_management_scripts
    print_success
}

# 运行主函数
main "$@"
