#!/bin/bash

# ==============================================================================
# MCS-IoT 一键自动化部署脚本
# 适用于 Ubuntu 20.04+, Debian 11+, CentOS 7+
# ==============================================================================

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 全局变量
INSTALL_DIR="/opt/mcs-iot"
REPO_URL="https://github.com/zhizinan1997/mcs-iot.git"
DOCKER_COMPOSE_VERSION="v2.24.1"

# 打印带颜色的日志
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_input() { echo -e "${CYAN}[INPUT]${NC} $1"; }

# 检查是否以 root 运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 权限运行此脚本 (sudo bash deploy.sh)"
        exit 1
    fi
}

# 检查系统配置
check_system() {
    log_info "正在检查系统环境..."
    
    # 检查 CPU 核心数
    CPU_CORES=$(nproc)
    if [ "$CPU_CORES" -lt 2 ]; then
        log_warn "检测到 CPU 核心数少于 2 核 ($CPU_CORES 核)，可能导致运行缓慢。"
    else
        log_success "CPU 核心数检查通过: $CPU_CORES 核"
    fi

    # 检查内存
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 2048 ]; then
        log_warn "检测到内存少于 2GB (${TOTAL_MEM}MB)，强烈建议升级配置。"
    else
        log_success "内存检查通过: ${TOTAL_MEM}MB"
    fi

    # 检查磁盘空间
    FREE_DISK=$(df -m . | awk 'NR==2 {print $4}')
    if [ "$FREE_DISK" -lt 10240 ]; then
        log_warn "检测到可用磁盘空间少于 10GB (${FREE_DISK}MB)，请注意清理。"
    else
        log_success "磁盘空间检查通过: ${FREE_DISK}MB 可用"
    fi
}

# 安装依赖工具
install_dependencies() {
    log_info "正在检查并安装依赖工具..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi

    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
        apt-get update -y
        apt-get install -y curl git python3 python3-pip openssl
    elif [[ "$OS" == "centos" || "$OS" == "rhel" ]]; then
        yum install -y curl git python3 python3-pip openssl
    else
        log_warn "未知的操作系统: $OS，尝试继续..."
    fi

    # 安装 Python 依赖 (用于模拟器)
    pip3 install paho-mqtt || pip install paho-mqtt
}

# 安装 Docker
install_docker() {
    if ! command -v docker &> /dev/null; then
        log_info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        log_success "Docker 安装完成"
    else
        log_success "Docker 已安装"
    fi

    # 安装 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_info "正在安装 Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose 安装完成"
    else
        log_success "Docker Compose 已安装"
    fi
}

# 克隆代码库
clone_repo() {
    log_info "准备代码库..."
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warn "检测到安装目录 $INSTALL_DIR 已存在"
        read -p "是否覆盖更新? (y/n) [y]: " confirm
        confirm=${confirm:-y}
        if [[ "$confirm" == "y" ]]; then
            log_info "正在备份旧数据..."
            mv "$INSTALL_DIR" "${INSTALL_DIR}_backup_$(date +%s)"
        else
            log_info "使用现有目录继续..."
            cd "$INSTALL_DIR"
            git pull
            return
        fi
    fi

    log_info "正在克隆代码库到 $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
}

# 配置向导
configure_deployment() {
    echo ""
    log_info "=== 开始配置向导 ==="
    
    # 1. 域名配置
    echo ""
    log_input "请输入您的服务器域名或 IP (例如: iot.example.com 或 192.168.1.100)"
    read -p "域名/IP: " DOMAIN
    DOMAIN=${DOMAIN:-localhost}
    
    # 2. SSL 配置
    echo ""
    log_input "是否为该域名自动申请 SSL 证书 (Let's Encrypt)?"
    log_warn "注意: 需要您已将域名解析到本机 IP，且 80 端口未被占用。"
    read -p "是否申请证书? (y/n) [n]: " ENABLE_SSL
    ENABLE_SSL=${ENABLE_SSL:-n}

    mkdir -p nginx/ssl

    if [[ "$ENABLE_SSL" == "y" ]]; then
        log_input "请输入用于接收证书通知的邮箱:"
        read -p "邮箱: " EMAIL
        
        log_info "正在安装 Certbot..."
        if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
            apt-get install -y certbot
        elif [[ "$OS" == "centos" ]]; then
            yum install -y certbot
        fi

        log_info "正在申请证书，请稍候..."
        # 临时停止占用 80 端口的服务
        systemctl stop nginx 2>/dev/null || true
        docker stop mcs_frontend 2>/dev/null || true
        
        certbot certonly --standalone -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive

        if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
            log_success "证书申请成功!"
            # 复制证书
            cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" nginx/ssl/server.crt
            cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" nginx/ssl/server.key
            # 复制 CA 链 (用于 Mosquitto)
            cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" nginx/ssl/ca.crt
            USE_SSL=true
        else
            log_error "证书申请失败，将回退到自签名证书模式。"
            ENABLE_SSL="n"
        fi
    fi

    if [[ "$ENABLE_SSL" != "y" ]]; then
        log_info "正在生成自签名证书..."
        openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
            -keyout nginx/ssl/server.key -out nginx/ssl/server.crt \
            -subj "/C=CN/ST=State/L=City/O=MCS-IoT/CN=$DOMAIN"
        # 自签名 CA 就是自己
        cp nginx/ssl/server.crt nginx/ssl/ca.crt
        USE_SSL=false
    fi

    # 3. 密码配置
    echo ""
    log_input "正在生成安全密码..."
    DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9')
    MQTT_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9')
    ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
    JWT_SECRET=$(openssl rand -base64 32)
    
    # 保存配置到 .env
    cat > .env << EOF
# Generated by deploy.sh
DOMAIN=${DOMAIN}
DB_HOST=timescaledb
DB_PORT=5432
DB_USER=postgres
DB_PASS=${DB_PASSWORD}
DB_NAME=mcs_iot

REDIS_HOST=redis
REDIS_PORT=6379

MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USER=admin
MQTT_PASSWORD=${MQTT_PASSWORD}

JWT_SECRET=${JWT_SECRET}
ADMIN_INITIAL_PASSWORD=${ADMIN_PASSWORD}

# SSL Config
USE_SSL=${USE_SSL}
EOF

    # 4. 配置 Mosquitto 密码
    log_info "配置 MQTT 用户..."
    # 确保 config 目录存在并有权限
    mkdir -p mosquitto/config mosquitto/data mosquitto/log
    touch mosquitto/config/passwd
    # 临时给权限，确保 docker 可以写入
    chmod 777 mosquitto/config/passwd
    
    # 使用 docker 生成密码文件
    docker run --rm -v $(pwd)/mosquitto/config:/mosquitto/config eclipse-mosquitto:2 \
        mosquitto_passwd -b -c /mosquitto/config/passwd admin "${MQTT_PASSWORD}"
    
    # 恢复权限 (Mosquitto 容器内 uid 1883)
    # chmod 644 mosquitto/config/passwd
}

# 启动服务
start_services() {
    log_info "正在启动 Docker 服务..."
    docker-compose down
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        log_success "服务启动成功!"
    else
        log_error "服务启动失败，请检查 Docker 日志"
        exit 1
    fi
}

# 模拟器
run_simulation() {
    echo ""
    log_info "=== 模拟测试 ==="
    log_input "是否启动 30 个模拟传感器进行测试? (y/n) [y]"
    read -p "是否启动? " RUN_SIM
    RUN_SIM=${RUN_SIM:-y}
    
    if [[ "$RUN_SIM" == "y" ]]; then
        log_info "正在启动模拟器 (30个设备)..."
        # 确保 mqtt_config.json 存在
        echo "{\"device_user\": \"admin\", \"device_pass\": \"${MQTT_PASSWORD}\"}" > scripts/mqtt_config.json
        
        # 后台运行
        nohup python3 scripts/simulator.py -n 30 > simulation.log 2>&1 &
        SIM_PID=$!
        log_success "模拟器已在后台启动 (PID: $SIM_PID)"
        log_info "日志查看: tail -f simulation.log"
    fi
}

# 总结
show_summary() {
    echo ""
    echo "================================================================"
    echo -e "   ${GREEN}MCS-IoT 部署完成!${NC}"
    echo "================================================================"
    echo ""
    echo -e "访问地址:"
    echo -e "  - 管理后台: ${BLUE}http://${DOMAIN}:8000${NC} (或 https)"
    echo -e "  - 数据大屏: ${BLUE}http://${DOMAIN}${NC} (或 https)"
    echo ""
    echo -e "账号信息 (${RED}请务必保存!${NC}):"
    echo -e "  - 管理员账号: ${YELLOW}admin${NC}"
    echo -e "  - 管理员密码: ${YELLOW}admin123${NC} (默认) 或 ${YELLOW}${ADMIN_PASSWORD}${NC}"
    echo -e "  - 数据库密码: ${YELLOW}${DB_PASSWORD}${NC}"
    echo -e "  - MQTT 密码 : ${YELLOW}${MQTT_PASSWORD}${NC}"
    echo ""
    echo -e "安装目录: ${INSTALL_DIR}"
    echo "================================================================"
    echo -e "${RED}警告: 请立即登录后台修改默认密码，并妥善保管上述凭证!${NC}"
    echo "================================================================"
}

# 主流程
main() {
    clear
    echo "================================================================"
    echo "   MCS-IoT 智能部署脚本 v1.0"
    echo "   作者: zhizinan"
    echo "================================================================"
    sleep 1

    check_root
    check_system
    install_dependencies
    install_docker
    clone_repo
    configure_deployment
    start_services
    run_simulation
    show_summary
}

main
