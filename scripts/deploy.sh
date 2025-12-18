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
    # 检查是否在项目根目录下运行 (本地部署模式)
    if [ -f "docker-compose.yml" ] && [ -d ".git" ]; then
        log_info "检测到当前目录似乎是项目根目录。"
        read -p "是否直接在当前目录 ($(pwd)) 进行部署? (y/n) [y]: " USE_CURRENT
        USE_CURRENT=${USE_CURRENT:-y}
        if [[ "$USE_CURRENT" == "y" ]]; then
            INSTALL_DIR=$(pwd)
            log_info "已选择本地部署模式，跳过代码克隆。"
            return
        fi
    fi

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
    # 尝试自动获取内网 IP
    DEFAULT_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    # 如果 hostname -I 失败 (macOS/BSD)，尝试 ipconfig/ifconfig
    if [ -z "$DEFAULT_IP" ]; then
        DEFAULT_IP=$(ipconfig getifaddr en0 2>/dev/null)
    fi
    if [ -z "$DEFAULT_IP" ]; then
        DEFAULT_IP="localhost"
    fi

    log_input "请输入您的服务器域名或 IP (例如: iot.example.com 或 192.168.1.100)"
    read -p "域名/IP [$DEFAULT_IP]: " DOMAIN
    DOMAIN=${DOMAIN:-$DEFAULT_IP}
    
    # 配置向导
    HTTP_PORT=80
    HTTPS_PORT=443

    # 检测是否为内网/本地 IP
    IS_LOCAL=false
    if [[ "$DOMAIN" == "localhost" || "$DOMAIN" == "127.0.0.1" ]]; then
        IS_LOCAL=true
    elif [[ "$DOMAIN" =~ ^192\.168\. ]]; then
        IS_LOCAL=true
    elif [[ "$DOMAIN" =~ ^10\. ]]; then
        IS_LOCAL=true
    elif [[ "$DOMAIN" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]]; then
        IS_LOCAL=true
    fi

    if [ "$IS_LOCAL" = true ]; then
        log_warn "检测到本地局域网或回环地址 ($DOMAIN)。"
        log_info "将自动跳过 Let's Encrypt 证书申请，使用自签名证书。"
        
        # 3.1 生成 OpenSSH 开发证书 (响应用户需求)
        log_info "正在生成 OpenSSH 开发证书 (仅用于内网开发测试)..."
        mkdir -p mosquitto/config/ssh
        
        # 生成 SSH CA (使用 Docker 避免依赖)
        if command -v ssh-keygen &> /dev/null; then
            rm -f mosquitto/config/ssh/id_rsa*
            ssh-keygen -t rsa -b 4096 -f mosquitto/config/ssh/id_rsa -N "" -C "mcs-iot-dev"
            log_success "OpenSSH 开发证书 (密钥对) 已生成: mosquitto/config/ssh/id_rsa"
        else
            log_warn "未找到 ssh-keygen，跳过 SSH 证书生成。"
        fi

        ENABLE_SSL="n"
    else
        # ICP 备案检测
        echo ""
        log_input "您的域名是否已在中国大陆备案? (y/n) [y]"
        log_warn "如果未备案，请选择 n，脚本将自动规避 80/443 端口。"
        read -p "是否已备案: " IS_ICP
        IS_ICP=${IS_ICP:-y}
        
        if [[ "$IS_ICP" == "n" ]]; then
            log_warn "检测到域名未备案，将使用自定义端口 9696 部署。"
            HTTP_PORT=9696
            HTTPS_PORT=9697
            log_info "HTTP 端口已设置为: $HTTP_PORT"
            log_info "HTTPS 端口已设置为: $HTTPS_PORT"
            
            log_warn "由于 80 端口不可用，无法自动申请 Let's Encrypt 证书。"
            log_info "将自动切换为自签名证书模式。"
            ENABLE_SSL="n"
        else
            # 2. SSL 配置 (仅公网 IP/域名询问)
            echo ""
            log_input "是否为该域名自动申请 SSL 证书 (Let's Encrypt)?"
            log_warn "注意: 需要您已将域名解析到本机 IP，且 80 端口未被占用。"
            read -p "是否申请证书? (y/n) [n]: " ENABLE_SSL
            ENABLE_SSL=${ENABLE_SSL:-n}
        fi
    fi

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
        log_info "正在生成自签名 SSL 证书 (支持 SAN)..."
        
        # 创建 OpenSSL 配置文件以支持 SAN (Subject Alternative Names)
        cat > openssl_san.cnf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C = CN
ST = State
L = City
O = MCS-IoT
CN = $DOMAIN

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = $DOMAIN
IP.1 = 127.0.0.1
EOF

        # 如果 DOMAIN 是 IP 地址，添加到 IP SAN
        if [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "IP.2 = $DOMAIN" >> openssl_san.cnf
        fi

        openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
            -keyout nginx/ssl/server.key -out nginx/ssl/server.crt \
            -config openssl_san.cnf

        rm openssl_san.cnf
        
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
HTTP_PORT=${HTTP_PORT}
HTTPS_PORT=${HTTPS_PORT}
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

# 配置防火墙
configure_firewall() {
    echo ""
    log_info "=== 配置系统防火墙 ==="
    
    # Ports to allow
    # SSH, HTTP, HTTPS, Backend, MQTT(TCP, MQTTS, WS)
    PORTS="22 $HTTP_PORT $HTTPS_PORT 8000 1883 8883 9001"
    
    if command -v ufw >/dev/null; then
        log_info "检测到 UFW 防火墙，正在添加规则..."
        ufw allow ssh >/dev/null
        for port in $PORTS; do
            ufw allow $port/tcp >/dev/null
            log_info "  - 已放行端口: $port/tcp"
        done
        # ufw enable # 不强制启用，以免中断连接
        log_success "UFW 规则添加完成 (如果防火墙未开启，请运行 'ufw enable')"
    elif command -v firewall-cmd >/dev/null; then
        log_info "检测到 Firewalld，正在添加规则..."
        if ! systemctl is-active --quiet firewalld; then
            log_warn "Firewalld 未运行，尝试启动..."
            systemctl start firewalld
        fi
        
        for port in $PORTS; do
            firewall-cmd --permanent --zone=public --add-port=${port}/tcp >/dev/null
            log_info "  - 已放行端口: $port/tcp"
        done
        firewall-cmd --reload >/dev/null
        log_success "Firewalld 规则添加完成"
    else
        log_warn "未检测到 UFW 或 Firewalld，请手动配置防火墙以放行以下端口:"
        echo "   $PORTS"
    fi
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
    if [ "$HTTP_PORT" == "80" ]; then
        echo -e "  - 管理后台: ${BLUE}http://${DOMAIN}:8000${NC} (或 https)"
        echo -e "  - 数据大屏: ${BLUE}http://${DOMAIN}${NC} (或 https)"
    else
        echo -e "  - 管理后台: ${BLUE}http://${DOMAIN}:8000${NC}"
        echo -e "  - 数据大屏: ${BLUE}http://${DOMAIN}:${HTTP_PORT}${NC}"
    fi
    echo ""
    echo -e "账号信息 (${RED}请务必保存!${NC}):"
    echo -e "  - 管理员账号: ${YELLOW}admin${NC}"
    echo -e "  - 管理员密码: ${YELLOW}admin123${NC} (默认) 或 ${YELLOW}${ADMIN_PASSWORD}${NC}"
    echo -e "  - 数据库密码: ${YELLOW}${DB_PASSWORD}${NC}"
    echo -e "  - MQTT 密码 : ${YELLOW}${MQTT_PASSWORD}${NC}"
    if [ "$IS_LOCAL" = true ]; then
        echo -e "  - OpenSSH 证书: ${YELLOW}mosquitto/config/ssh/id_rsa${NC} (仅开发用)"
    fi
    echo ""
    echo -e "安装目录: ${INSTALL_DIR}"
    echo "================================================================"
    echo -e "${RED}警告: 请立即登录后台修改默认密码，并妥善保管上述凭证!${NC}"
    echo -e "${YELLOW}重要提示: 请务必在云服务器提供商 (阿里云/腾讯云/AWS等) 的安全组/防火墙中放行以下端口:${NC}"
    echo -e "${YELLOW}          TCP: $HTTP_PORT, $HTTPS_PORT, 8000, 1883, 8883, 9001${NC}"
    if [ "$IS_LOCAL" = true ]; then
        echo -e "${YELLOW}提醒: 已为您生成 OpenSSH 开发证书及自签名 SSL 证书。${NC}"
        echo -e "${YELLOW}      由于使用自签名证书，浏览器可能会提示不安全，请手动信任或忽略。${NC}"
    fi
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
    configure_firewall
    start_services
    run_simulation
    show_summary
}

main
