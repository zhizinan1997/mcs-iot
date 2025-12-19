#!/bin/bash
# =============================================================================
# 元芯物联网智慧云平台 - Linux 一键部署脚本
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
VERSION="v1.0.2"
INSTALL_DIR="/opt/mcs-iot"
REPO_URL="https://github.com/zhizinan1997/mcs-iot.git"
REPO_URL_CN="https://ghproxy.com/https://github.com/zhizinan1997/mcs-iot.git"
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
AI_MODEL="gpt-3.5-turbo"

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
        "https://docker.m.daocloud.io",
        "https://dockerhub.icu",
        "https://docker.1panel.live"
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
        # 使用更精确的模式匹配，支持 IPv4 和 IPv6
        if ss -tuln 2>/dev/null | grep -E "(:${port}\s|:${port}$)" > /dev/null 2>&1; then
            # 二次验证：确保端口确实在监听
            if ss -tuln 2>/dev/null | awk -v p="$port" '$5 ~ ":"p"$" || $5 ~ ":"p"[^0-9]" {found=1} END {exit !found}'; then
                PORTS_IN_USE+=($port)
                log_warn "端口 $port 已被占用"
            fi
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
    pip3 install paho-mqtt --quiet 2>/dev/null || true
    
    log_info "✓ 依赖安装完成"
}

# =============================================================================
# 域名配置
# =============================================================================

configure_domains() {
    log_step "第七步：配置域名"
    
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      域名配置说明                             ║${NC}"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║ 本系统需要配置 4 个域名，请确保已将它们解析到本服务器 IP      ║${NC}"
    echo -e "${CYAN}║                                                               ║${NC}"
    echo -e "${CYAN}║ 1. 主域名/管理后台  - 例如: iot.example.com                   ║${NC}"
    echo -e "${CYAN}║ 2. API 接口域名      - 例如: api.example.com                  ║${NC}"
    echo -e "${CYAN}║ 3. MQTT 服务域名     - 例如: mqtt.example.com                 ║${NC}"
    echo -e "${CYAN}║ 4. 大屏展示域名      - 例如: screen.example.com               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # 获取服务器 IP (忽略错误)
    SERVER_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null) || SERVER_IP=""
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(curl -s --connect-timeout 5 ip.sb 2>/dev/null) || SERVER_IP=""
    fi
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || SERVER_IP="无法获取"
    fi
    log_info "当前服务器 IP: $SERVER_IP"
    echo ""
    log_warn "请确保以下 4 个域名都已解析到此 IP 地址!"
    echo ""
    
    echo -e "${YELLOW}按 Enter 键继续输入域名...${NC}"
    read -r DUMMY || true
    
    # 输入域名
    echo ""
    read -r -p "请输入主域名/管理后台域名 (例如 iot.example.com): " DOMAIN_MAIN
    read -r -p "请输入 API 接口域名 (例如 api.example.com): " DOMAIN_API
    read -r -p "请输入 MQTT 服务域名 (例如 mqtt.example.com): " DOMAIN_MQTT
    read -r -p "请输入大屏展示域名 (例如 screen.example.com): " DOMAIN_SCREEN
    
    # 验证域名
    if [[ -z "$DOMAIN_MAIN" || -z "$DOMAIN_API" || -z "$DOMAIN_MQTT" || -z "$DOMAIN_SCREEN" ]]; then
        log_error "所有域名都是必填项!"
        exit 1
    fi
    
    echo ""
    log_info "您配置的域名:"
    log_info "  主域名/管理后台: $DOMAIN_MAIN"
    log_info "  API 接口:        $DOMAIN_API"
    log_info "  MQTT 服务:       $DOMAIN_MQTT"
    log_info "  大屏展示:        $DOMAIN_SCREEN"
    echo ""
    
    if ! confirm "以上域名配置正确吗?"; then
        log_info "请重新运行脚本配置域名"
        exit 1
    fi
}

configure_credentials() {
    log_step "第八步：配置密码和 API 密钥"
    
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
    
    # AI API (URL 已固定)
    echo -e "${CYAN}AI API 用于生成智能分析报告 (可选)${NC}"
    echo -e "${CYAN}API 接口已固定，仅需配置 Key 和模型${NC}"
    read -r -p "请输入 AI API Key (留空则跳过): " AI_API_KEY
    if [[ -n "$AI_API_KEY" ]]; then
        echo ""
        echo -e "${CYAN}请选择 AI 模型:${NC}"
        echo "  1. gpt-3.5-turbo (推荐，快速经济)"
        echo "  2. gpt-4o-mini (精准)"
        echo "  3. gpt-4o (最强)"
        echo "  4. gemini-2.0-flash (Google)"
        echo "  5. claude-3-5-sonnet (Anthropic)"
        read -r -p "请选择 [1-5]，默认 1: " model_choice
        case $model_choice in
            2) AI_MODEL="gpt-4o-mini" ;;
            3) AI_MODEL="gpt-4o" ;;
            4) AI_MODEL="gemini-2.0-flash" ;;
            5) AI_MODEL="claude-3-5-sonnet" ;;
            *) AI_MODEL="gpt-3.5-turbo" ;;
        esac
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
    log_step "第九步：下载项目代码"
    
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
    
    log_info "✓ 项目代码下载完成"
}

generate_env_file() {
    log_step "第十步：生成配置文件"
    
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
MQTT_PASSWORD=${MQTT_PASSWORD}

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
    log_step "第十二步：启动 Docker 容器"
    
    cd "$INSTALL_DIR"
    
    # 检查是否使用预构建镜像
    if [[ -f "docker-compose.ghcr.yml" ]]; then
        echo ""
        echo -e "${CYAN}请选择部署方式:${NC}"
        echo "  1. 使用预构建镜像 (推荐，快速稳定)"
        echo "  2. 本地构建镜像 (需要更多内存和时间)"
        read -r -p "请选择 [1/2]，默认 1: " deploy_mode
        deploy_mode=${deploy_mode:-1}
        
        if [[ "$deploy_mode" == "1" ]]; then
            log_info "使用预构建镜像部署..."
            log_info "正在拉取镜像，首次可能需要几分钟..."
            echo ""
            
            if docker compose -f docker-compose.ghcr.yml pull 2>&1; then
                log_info "✓ 镜像拉取成功"
            else
                log_warn "部分镜像拉取失败，尝试继续..."
            fi
            
            log_info "启动服务..."
            if docker compose -f docker-compose.ghcr.yml up -d 2>&1; then
                log_info "✓ 服务启动成功"
            else
                log_error "服务启动失败"
                return 1
            fi
            
            # 等待服务启动
            log_info "等待服务就绪..."
            sleep 15
            
            if docker compose -f docker-compose.ghcr.yml ps | grep -q "healthy"; then
                log_info "✓ 所有服务已就绪"
            else
                log_warn "部分服务可能还在启动中，请稍后检查"
            fi
            
            return 0
        fi
    fi
    
    # 本地构建模式
    # 检查内存，决定构建方式
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    
    if [[ $TOTAL_MEM -lt 4096 ]]; then
        log_info "检测到低内存环境(${TOTAL_MEM}MB)，使用顺序构建模式..."
        log_info "这可能需要较长时间，请耐心等待..."
        echo ""
        
        # 带重试的 Docker 拉取函数
        docker_pull_retry() {
            local image=$1
            local max_attempts=5
            local attempt=1
            
            while [[ $attempt -le $max_attempts ]]; do
                log_info "  拉取 $image (尝试 $attempt/$max_attempts)..."
                if docker pull "$image" 2>&1; then
                    log_info "  ✓ $image 拉取成功"
                    return 0
                fi
                
                if [[ $attempt -lt $max_attempts ]]; then
                    local wait_time=$((attempt * 10))
                    log_warn "  拉取失败，${wait_time}秒后重试..."
                    sleep $wait_time
                fi
                ((attempt++))
            done
            
            log_warn "  ✗ $image 拉取失败，将在构建时重试"
            return 1
        }
        
        # 带重试的 Docker 构建函数
        docker_build_retry() {
            local service=$1
            local max_attempts=3
            local attempt=1
            
            while [[ $attempt -le $max_attempts ]]; do
                log_info "  构建 $service (尝试 $attempt/$max_attempts)..."
                if docker compose version &> /dev/null; then
                    if docker compose build --no-cache "$service" 2>&1; then
                        log_info "  ✓ $service 构建成功"
                        return 0
                    fi
                else
                    if docker-compose build --no-cache "$service" 2>&1; then
                        log_info "  ✓ $service 构建成功"
                        return 0
                    fi
                fi
                
                if [[ $attempt -lt $max_attempts ]]; then
                    local wait_time=$((attempt * 15))
                    log_warn "  构建失败，${wait_time}秒后重试..."
                    sleep $wait_time
                fi
                ((attempt++))
            done
            
            log_error "  ✗ $service 构建失败"
            return 1
        }
        
        # 顺序拉取基础镜像
        log_info "[1/6] 拉取基础镜像..."
        docker_pull_retry "timescale/timescaledb:latest-pg15"
        docker_pull_retry "redis:7-alpine"
        docker_pull_retry "eclipse-mosquitto:2"
        
        # 顺序构建自定义镜像
        log_info "[2/6] 构建 Worker 服务..."
        docker_build_retry "worker"
        
        log_info "[3/6] 构建 Backend 服务..."
        docker_build_retry "backend"
        
        log_info "[4/6] 构建 Frontend 服务..."
        docker_build_retry "frontend"
        
        log_info "[5/6] 启动所有服务..."
        if docker compose version &> /dev/null; then
            docker compose up -d
        else
            docker-compose up -d
        fi
    else
        log_info "正在构建并启动容器，这可能需要几分钟..."
        log_info "首次构建需要下载镜像，请耐心等待..."
        echo ""
        
        # 正常并行构建
        if docker compose version &> /dev/null; then
            docker compose up -d --build
        else
            docker-compose up -d --build
        fi
    fi
    
    echo ""
    log_info "[6/6] 等待服务启动..."
    sleep 10
    
    # 检查容器状态
    log_info "检查容器运行状态..."
    if docker compose version &> /dev/null; then
        docker compose ps
    else
        docker-compose ps
    fi
    
    log_info "✓ Docker 容器启动完成"
}

# =============================================================================
# 演示数据
# =============================================================================

import_demo_data() {
    log_step "第十三步：生成演示数据 (可选)"
    
    echo ""
    echo -e "${CYAN}演示数据生成器将创建:${NC}"
    echo "  - 4 个仪表 (总经理办公室/员工办公室/公共走廊/创新实验室)"
    echo "  - 24 个传感器 (氢气/甲烷/VOCs/温度/湿度/PM2.5)"
    echo "  - 实时模拟数据 (每10秒)"
    echo "  - 偶尔触发报警 (每小时1-2次)"
    echo ""
    
    if ! confirm "是否生成演示数据?"; then
        log_info "跳过演示数据生成"
        return 0
    fi
    
    echo ""
    echo -e "${CYAN}请选择数据生成时长:${NC}"
    echo "  1. 10 分钟 (快速演示)"
    echo "  2. 30 分钟 (推荐)"
    echo "  3. 60 分钟 (完整数据)"
    echo "  4. 仅创建设备，不生成数据"
    echo ""
    read -r -p "请输入选项 [1-4]: " duration_choice
    
    case $duration_choice in
        1) duration=10 ;;
        2) duration=30 ;;
        3) duration=60 ;;
        4) 
            log_info "仅创建设备..."
            cd "$INSTALL_DIR"
            python3 scripts/demo_generator.py --init-only 2>&1 || true
            log_info "✓ 设备创建完成"
            return 0
            ;;
        *) duration=30 ;;
    esac
    
    log_info "启动演示数据生成器 (${duration}分钟)..."
    
    # 后台运行演示生成器
    cd "$INSTALL_DIR"
    nohup python3 scripts/demo_generator.py -d "$duration" > /var/log/mcs-demo-generator.log 2>&1 &
    DEMO_PID=$!
    echo $DEMO_PID > /var/run/mcs-demo-generator.pid
    
    echo ""
    log_info "✓ 演示数据生成器已在后台启动"
    log_info "  PID: $DEMO_PID"
    log_info "  时长: ${duration} 分钟"
    log_info "  日志: tail -f /var/log/mcs-demo-generator.log"
    log_info "  停止: kill $DEMO_PID"
    echo ""
}

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
echo "可选参数: -d 分钟数 (默认60)"

DURATION=${1:-60}
nohup python3 scripts/demo_generator.py -d "$DURATION" --skip-init > /var/log/mcs-simulator.log 2>&1 &
echo $! > /var/run/mcs-simulator.pid
echo "模拟器已启动，PID: $(cat /var/run/mcs-simulator.pid)"
echo "运行时长: ${DURATION} 分钟"
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

case "$1" in
    start)
        echo "启动服务..."
        docker compose up -d 2>/dev/null || docker-compose up -d
        ;;
    stop)
        echo "停止服务..."
        docker compose down 2>/dev/null || docker-compose down
        ;;
    restart)
        echo "重启服务..."
        docker compose restart 2>/dev/null || docker-compose restart
        ;;
    status)
        docker compose ps 2>/dev/null || docker-compose ps
        ;;
    logs)
        docker compose logs -f ${2:-} 2>/dev/null || docker-compose logs -f ${2:-}
        ;;
    rebuild)
        echo "重新构建并启动..."
        docker compose up -d --build 2>/dev/null || docker-compose up -d --build
        ;;
    *)
        echo "用法: mcs-iot {start|stop|restart|status|logs|rebuild}"
        echo ""
        echo "  start   - 启动所有服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看日志 (可指定服务名)"
        echo "  rebuild - 重新构建并启动"
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
    echo -e "${CYAN}                   ❗ 完成宝塔配置后方可访问 ❗                      ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}【第一步】在宝塔面板中为以下域名创建网站并申请 SSL 证书${NC}"
    echo ""
    echo -e "  域名用途                反向代理目标"
    echo -e "  ───────────────────────────────────"
    echo -e "  ${GREEN}${DOMAIN_MAIN}${NC}      →  127.0.0.1:3000  (主站/管理后台)"
    echo -e "  ${GREEN}${DOMAIN_API}${NC}       →  127.0.0.1:8000  (API 接口)"
    echo -e "  ${GREEN}${DOMAIN_SCREEN}${NC}    →  127.0.0.1:3000  (大屏展示，访问 /screen)"
    echo ""
    echo -e "${YELLOW}【第二步】配置 MQTT TLS 证书 (设备加密连接用)${NC}"
    echo ""
    echo -e "  ${CYAN}操作步骤:${NC}"
    echo -e "  1. 在宝塔面板中，进入主域名的 SSL 设置，点击「下载证书」"
    echo -e "  2. 解压下载的证书压缩包，选择 ${GREEN}Nginx${NC} 文件夹"
    echo -e "  3. 里面有两个文件，需要重命名后上传到服务器:"
    echo -e "     ${GREEN}fullchain.pem${NC}  →  重命名为  ${YELLOW}server.crt${NC}"
    echo -e "     ${GREEN}privkey.pem${NC}    →  重命名为  ${YELLOW}server.key${NC}"
    echo -e "  4. 将这两个文件上传到: ${INSTALL_DIR}/nginx/ssl/"
    echo ""
    echo -e "  ${CYAN}或者使用命令直接复制 (如果证书在服务器上):${NC}"
    echo -e "  cp /www/server/panel/vhost/ssl/${DOMAIN_MAIN}/fullchain.pem ${INSTALL_DIR}/nginx/ssl/server.crt"
    echo -e "  cp /www/server/panel/vhost/ssl/${DOMAIN_MAIN}/privkey.pem ${INSTALL_DIR}/nginx/ssl/server.key"
    echo ""
    echo -e "  ${RED}⚠️ 上传/复制完成后，必须重启所有 Docker 容器:${NC}"
    echo -e "  ${YELLOW}mcs-iot restart${NC}"
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
    echo ""
    echo -e "  模拟器:"
    echo -e "    ${YELLOW}mcs-simulator-start${NC}    - 启动 24 个模拟传感器"
    echo -e "    ${YELLOW}mcs-simulator-stop${NC}     - 停止模拟传感器"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                         重要信息                                   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  📁 安装目录:     ${INSTALL_DIR}"
    echo -e "  📄 配置文件:     ${INSTALL_DIR}/.env"
    echo -e "  📄 MQTT 证书:  ${INSTALL_DIR}/nginx/ssl/"
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
    
    log_info "欢迎使用元芯物联网智慧云平台一键部署脚本"
    log_info "此脚本将自动完成以下任务:"
    echo "  1. 检测操作系统和服务器资源"
    echo "  2. 安装 Docker 和必要依赖"
    echo "  3. 配置域名和 API 密钥"
    echo "  4. 部署物联网平台"
    echo "  5. 可选导入演示数据"
    echo ""
    log_warn "注意: SSL 证书需要在宝塔面板中手动申请和配置"
    echo ""
    
    if ! confirm "是否继续安装?" "Y"; then
        log_info "安装已取消"
        exit 0
    fi
    
    # 执行安装步骤
    detect_os
    check_resources
    setup_swap
    configure_china_mirror
    check_ports
    install_dependencies
    install_docker
    install_docker_compose
    configure_domains
    configure_credentials
    clone_repository
    generate_env_file
    deploy_containers
    import_demo_data
    create_management_scripts
    print_success
}

# 运行主函数
main "$@"
