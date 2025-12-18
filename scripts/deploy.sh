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
INSTALL_DIR="/opt/mcs-iot"
REPO_URL="https://github.com/zhizinan1997/mcs-iot.git"
COMPOSE_VERSION="2.24.0"

# 用户配置变量
DOMAIN_MAIN=""
DOMAIN_API=""
DOMAIN_MQTT=""
DOMAIN_SCREEN=""
DB_PASSWORD=""
WEATHER_API_KEY=""
AI_API_KEY=""
AI_API_URL=""
EMAIL=""

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
    read -r -p "按 Enter 键继续..."
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

check_ports() {
    log_step "第三步：检测端口占用情况"
    
    REQUIRED_PORTS=(80 443 1883 8883 5432 6379)
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
        log_info "  - 80/443: Web 服务 (HTTP/HTTPS)"
        log_info "  - 1883/8883: MQTT 服务"
        log_info "  - 5432: PostgreSQL 数据库"
        log_info "  - 6379: Redis 缓存"
        echo ""
        log_info "提示: 您可以手动检查端口占用: ss -tuln | grep -E ':(80|443|1883|8883|5432|6379)'"
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

install_certbot() {
    log_step "第六步：安装 Certbot (Let's Encrypt)"
    
    if command -v certbot &> /dev/null; then
        log_info "Certbot 已安装"
        return 0
    fi
    
    log_info "正在安装 Certbot..."
    
    case $PKG_MANAGER in
        apt)
            $PKG_INSTALL certbot
            ;;
        yum|dnf)
            $PKG_INSTALL epel-release || true
            $PKG_INSTALL certbot
            ;;
    esac
    
    log_info "✓ Certbot 安装完成"
}

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
    
    # 获取服务器 IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "无法获取")
    log_info "当前服务器公网 IP: $SERVER_IP"
    echo ""
    log_warn "请确保以下 4 个域名都已解析到此 IP 地址!"
    echo ""
    
    wait_for_enter
    
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
    
    # AI API
    echo -e "${CYAN}AI API 用于生成智能分析报告 (可选)${NC}"
    echo -e "${CYAN}支持 OpenAI 兼容的 API 接口${NC}"
    read -r -p "请输入 AI API URL (留空则跳过): " AI_API_URL
    if [[ -n "$AI_API_URL" ]]; then
        read -r -p "请输入 AI API Key: " AI_API_KEY
        log_info "✓ AI API 已设置"
    else
        log_warn "未设置 AI API，大屏将不显示 AI 分析"
    fi
    
    echo ""
    
    # Let's Encrypt 邮箱
    echo -e "${CYAN}Let's Encrypt 需要一个邮箱地址用于证书通知${NC}"
    read -r -p "请输入您的邮箱地址: " EMAIL
    if [[ -z "$EMAIL" ]]; then
        log_error "邮箱地址是必填项 (用于 SSL 证书)"
        exit 1
    fi
    log_info "✓ 邮箱已设置: $EMAIL"
}

# =============================================================================
# 部署项目
# =============================================================================

clone_repository() {
    log_step "第九步：下载项目代码"
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warn "安装目录 $INSTALL_DIR 已存在"
        if confirm "是否删除并重新下载?"; then
            rm -rf "$INSTALL_DIR"
        else
            log_info "使用现有目录"
            return 0
        fi
    fi
    
    log_info "正在从 GitHub 克隆项目..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    
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

# 天气 API (心知天气)
WEATHER_API_KEY=${WEATHER_API_KEY}

# AI API 配置
AI_API_URL=${AI_API_URL}
AI_API_KEY=${AI_API_KEY}
EOF

    log_info "✓ 配置文件已生成: $INSTALL_DIR/.env"
}

setup_ssl_certificates() {
    log_step "第十一步：申请 SSL 证书"
    
    log_info "正在为以下域名申请 Let's Encrypt SSL 证书..."
    log_info "  - $DOMAIN_MAIN"
    log_info "  - $DOMAIN_API"
    log_info "  - $DOMAIN_MQTT"
    log_info "  - $DOMAIN_SCREEN"
    echo ""
    
    echo -e "${YELLOW}提示: 证书申请过程可能需要 1-3 分钟，请耐心等待...${NC}"
    echo -e "${YELLOW}      Let's Encrypt 需要验证您的域名解析是否正确${NC}"
    echo ""
    
    # 确保 80 端口可用
    log_info "正在释放 80 端口..."
    systemctl stop nginx 2>/dev/null || true
    docker stop mcs_frontend 2>/dev/null || true
    sleep 2
    
    # 创建临时文件存储 certbot 输出
    CERTBOT_LOG=$(mktemp)
    
    # 后台运行 certbot
    log_info "正在与 Let's Encrypt 服务器通信..."
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN_MAIN" \
        -d "$DOMAIN_API" \
        -d "$DOMAIN_MQTT" \
        -d "$DOMAIN_SCREEN" > "$CERTBOT_LOG" 2>&1 &
    
    CERTBOT_PID=$!
    
    # 显示动态进度
    SPINNER='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    SPINNER_LEN=${#SPINNER}
    i=0
    elapsed=0
    
    while kill -0 $CERTBOT_PID 2>/dev/null; do
        printf "\r${CYAN}[%s]${NC} 正在验证域名... (%d 秒)" "${SPINNER:i++%SPINNER_LEN:1}" "$elapsed"
        sleep 1
        ((elapsed++))
        
        # 每 30 秒显示一次提示
        if [[ $((elapsed % 30)) -eq 0 ]]; then
            echo ""
            log_info "仍在处理中，请继续等待..."
        fi
    done
    
    # 清除进度行
    printf "\r%-60s\r" " "
    
    # 等待进程结束并获取退出码
    wait $CERTBOT_PID
    CERTBOT_EXIT=$?
    
    if [[ $CERTBOT_EXIT -ne 0 ]]; then
        echo ""
        log_error "SSL 证书申请失败！"
        echo ""
        echo -e "${RED}错误详情:${NC}"
        cat "$CERTBOT_LOG"
        echo ""
        log_info "常见原因:"
        log_info "  1. 域名未正确解析到此服务器 IP"
        log_info "  2. 80 端口被防火墙阻挡"
        log_info "  3. Let's Encrypt 申请次数超限 (等待 1 小时后重试)"
        echo ""
        log_info "您可以稍后手动运行:"
        echo "  certbot certonly --standalone -d $DOMAIN_MAIN -d $DOMAIN_API -d $DOMAIN_MQTT -d $DOMAIN_SCREEN"
        rm -f "$CERTBOT_LOG"
        exit 1
    fi
    
    rm -f "$CERTBOT_LOG"
    log_info "✓ SSL 证书申请成功！(耗时 ${elapsed} 秒)"
    
    # 复制证书到项目目录
    log_info "正在复制证书到项目目录..."
    mkdir -p "$INSTALL_DIR/nginx/ssl"
    cp "/etc/letsencrypt/live/$DOMAIN_MAIN/fullchain.pem" "$INSTALL_DIR/nginx/ssl/server.crt"
    cp "/etc/letsencrypt/live/$DOMAIN_MAIN/privkey.pem" "$INSTALL_DIR/nginx/ssl/server.key"
    
    # 设置自动续签
    log_info "配置证书自动续签..."
    
    cat > /etc/cron.d/mcs-iot-ssl-renew << EOF
# 每天凌晨 3 点检查并续签证书
0 3 * * * root certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/$DOMAIN_MAIN/fullchain.pem $INSTALL_DIR/nginx/ssl/server.crt && cp /etc/letsencrypt/live/$DOMAIN_MAIN/privkey.pem $INSTALL_DIR/nginx/ssl/server.key && docker restart mcs_frontend"
EOF
    
    log_info "✓ 证书已配置自动续签"
}

generate_nginx_config() {
    log_step "生成 Nginx 配置"
    
    cat > "$INSTALL_DIR/nginx/nginx.conf" << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;
    client_max_body_size 50M;

    # 主站和管理后台
    server {
        listen 80;
        listen 443 ssl http2;
        server_name DOMAIN_MAIN_PLACEHOLDER;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;

        # HTTP 重定向到 HTTPS
        if ($scheme != "https") {
            return 301 https://$host$request_uri;
        }

        location / {
            root   /usr/share/nginx/html;
            index  index.html;
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://backend:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /ws {
            proxy_pass http://backend:8000/ws;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

    # API 接口
    server {
        listen 80;
        listen 443 ssl http2;
        server_name DOMAIN_API_PLACEHOLDER;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;

        if ($scheme != "https") {
            return 301 https://$host$request_uri;
        }

        location / {
            proxy_pass http://backend:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # 大屏展示
    server {
        listen 80;
        listen 443 ssl http2;
        server_name DOMAIN_SCREEN_PLACEHOLDER;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;

        if ($scheme != "https") {
            return 301 https://$host$request_uri;
        }

        location / {
            root   /usr/share/nginx/html;
            index  index.html;
            try_files $uri $uri/ /index.html;
            # 直接跳转到大屏页面
            rewrite ^/$ /screen redirect;
        }

        location /api/ {
            proxy_pass http://backend:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
NGINX_EOF

    # 替换域名占位符
    sed -i "s/DOMAIN_MAIN_PLACEHOLDER/$DOMAIN_MAIN/g" "$INSTALL_DIR/nginx/nginx.conf"
    sed -i "s/DOMAIN_API_PLACEHOLDER/$DOMAIN_API/g" "$INSTALL_DIR/nginx/nginx.conf"
    sed -i "s/DOMAIN_SCREEN_PLACEHOLDER/$DOMAIN_SCREEN/g" "$INSTALL_DIR/nginx/nginx.conf"
    
    log_info "✓ Nginx 配置已生成"
}

deploy_containers() {
    log_step "第十二步：启动 Docker 容器"
    
    cd "$INSTALL_DIR"
    
    log_info "正在构建并启动容器，这可能需要几分钟..."
    echo ""
    
    # 使用 docker compose (V2) 或 docker-compose (V1)
    if docker compose version &> /dev/null; then
        docker compose up -d --build
    else
        docker-compose up -d --build
    fi
    
    log_info "等待服务启动..."
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
    log_step "第十三步：导入演示数据 (可选)"
    
    echo ""
    echo -e "${CYAN}演示数据包含:${NC}"
    echo "  - 24 个模拟传感器设备"
    echo "  - 4 个仪表/区域"
    echo "  - 大屏背景图"
    echo "  - 示例报警记录"
    echo ""
    log_warn "注意: 您设置的密码和 API 配置不会被覆盖"
    echo ""
    
    if confirm "是否导入演示数据?"; then
        log_info "正在导入演示数据..."
        
        # 等待数据库就绪
        sleep 5
        
        # 导入演示数据
        if [[ -f "$INSTALL_DIR/scripts/demo_data.sql" ]]; then
            docker exec -i mcs_db psql -U postgres -d mcs_iot < "$INSTALL_DIR/scripts/demo_data.sql" 2>/dev/null || true
            log_info "✓ 演示数据导入完成"
        else
            log_warn "未找到演示数据文件，跳过导入"
        fi
    else
        log_info "跳过演示数据导入"
    fi
}

# =============================================================================
# 部署完成
# =============================================================================

create_management_scripts() {
    log_step "创建管理脚本"
    
    # 模拟器启动脚本
    cat > "$INSTALL_DIR/start-simulator.sh" << 'EOF'
#!/bin/bash
# 启动 24 个模拟传感器
cd /opt/mcs-iot
echo "正在启动 24 个模拟传感器..."
nohup python3 scripts/simulator.py -n 24 > /var/log/mcs-simulator.log 2>&1 &
echo $! > /var/run/mcs-simulator.pid
echo "模拟器已启动，PID: $(cat /var/run/mcs-simulator.pid)"
echo "查看日志: tail -f /var/log/mcs-simulator.log"
EOF
    chmod +x "$INSTALL_DIR/start-simulator.sh"
    
    # 模拟器停止脚本
    cat > "$INSTALL_DIR/stop-simulator.sh" << 'EOF'
#!/bin/bash
# 停止模拟传感器
if [[ -f /var/run/mcs-simulator.pid ]]; then
    PID=$(cat /var/run/mcs-simulator.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "模拟器已停止 (PID: $PID)"
        rm -f /var/run/mcs-simulator.pid
    else
        echo "模拟器进程不存在"
        rm -f /var/run/mcs-simulator.pid
    fi
else
    echo "未找到模拟器 PID 文件"
    # 尝试查找并停止
    pkill -f "simulator.py" && echo "已停止所有模拟器进程" || echo "无运行中的模拟器"
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
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}║              🎉 元芯物联网智慧云平台 部署成功！ 🎉                ║${NC}"
    echo -e "${GREEN}║                                                                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}                         访问地址                                   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  🖥️  管理后台:     ${GREEN}https://${DOMAIN_MAIN}${NC}"
    echo -e "  📊  大屏展示:     ${GREEN}https://${DOMAIN_SCREEN}/screen${NC}"
    echo -e "  🔌  API 接口:     ${GREEN}https://${DOMAIN_API}${NC}"
    echo -e "  📡  MQTT 服务:    ${GREEN}mqtts://${DOMAIN_MQTT}:8883${NC}"
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
    echo -e "    ${YELLOW}mcs-iot rebuild${NC}        - 重新构建"
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
    echo -e "  🔐 SSL 证书:     /etc/letsencrypt/live/${DOMAIN_MAIN}/"
    echo -e "  📋 日志目录:     ${INSTALL_DIR}/logs/"
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
    echo "  3. 配置域名和 SSL 证书"
    echo "  4. 部署物联网平台"
    echo "  5. 可选导入演示数据"
    echo ""
    
    if ! confirm "是否继续安装?" "Y"; then
        log_info "安装已取消"
        exit 0
    fi
    
    # 执行安装步骤
    detect_os
    check_resources
    check_ports
    install_dependencies
    install_docker
    install_docker_compose
    install_certbot
    configure_domains
    configure_credentials
    clone_repository
    generate_env_file
    setup_ssl_certificates
    generate_nginx_config
    deploy_containers
    import_demo_data
    create_management_scripts
    print_success
}

# 运行主函数
main "$@"
