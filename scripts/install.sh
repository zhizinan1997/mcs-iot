#!/bin/bash
# MCS-IoT One-Click Installation Script
# Supports: Ubuntu 20.04+, Debian 11+

set -e

echo "================================================"
echo "   MCS-IoT Installation Script"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Unsupported operating system"
    exit 1
fi

echo "Detected OS: $OS"

# Install Docker if not present
install_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        echo "Docker installed successfully"
    else
        echo "Docker already installed"
    fi
}

# Install Docker Compose if not present
install_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        echo "Docker Compose installed successfully"
    else
        echo "Docker Compose already installed"
    fi
}

# Create installation directory
setup_directory() {
    INSTALL_DIR="/opt/mcs-iot"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "Installation directory already exists. Backing up..."
        mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%Y%m%d%H%M%S)"
    fi
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    echo "Installation directory: $INSTALL_DIR"
}

# Generate production configuration
generate_config() {
    echo "Generating configuration..."
    
    # Generate random passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 20)
    JWT_SECRET=$(openssl rand -base64 32)
    
    # Create .env file
    cat > .env << EOF
# Database
DB_HOST=timescaledb
DB_PORT=5432
DB_USER=postgres
DB_PASS=${DB_PASSWORD}
DB_NAME=mcs_iot

# Redis
REDIS_HOST=redis

# MQTT
MQTT_HOST=mosquitto
MQTT_PORT=1883

# API
JWT_SECRET=${JWT_SECRET}

# R2 Storage (Optional - for data archiving)
R2_ENDPOINT=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=mcs-iot-archive

# License
DEV_MODE=false
LICENSE_VERIFY_URL=https://license.metachip-iot.com/verify
EOF
    
    echo "Configuration generated"
    echo "Database Password: ${DB_PASSWORD}"
    echo "(Save this securely!)"
}

# Generate SSL certificates
generate_ssl() {
    echo "Generating SSL certificates..."
    
    mkdir -p nginx/ssl
    
    openssl genrsa -out nginx/ssl/ca.key 2048
    openssl req -new -x509 -days 3650 -key nginx/ssl/ca.key -out nginx/ssl/ca.crt \
        -subj "/C=CN/ST=Shanghai/L=Shanghai/O=Metachip/CN=MCS-IoT-CA"
    
    openssl genrsa -out nginx/ssl/server.key 2048
    openssl req -new -key nginx/ssl/server.key -out nginx/ssl/server.csr \
        -subj "/C=CN/ST=Shanghai/L=Shanghai/O=Metachip/CN=localhost"
    
    openssl x509 -req -days 365 -in nginx/ssl/server.csr \
        -CA nginx/ssl/ca.crt -CAkey nginx/ssl/ca.key -CAcreateserial \
        -out nginx/ssl/server.crt
    
    echo "SSL certificates generated"
}

# Pull and start containers
start_services() {
    echo "Starting services..."
    
    docker-compose pull
    docker-compose up -d
    
    echo "Waiting for services to start..."
    sleep 10
    
    docker-compose ps
}

# Main installation flow
main() {
    echo ""
    echo "Step 1: Installing Docker..."
    install_docker
    
    echo ""
    echo "Step 2: Installing Docker Compose..."
    install_docker_compose
    
    echo ""
    echo "Step 3: Setting up installation directory..."
    setup_directory
    
    echo ""
    echo "Step 4: Generating configuration..."
    generate_config
    
    echo ""
    echo "Step 5: Generating SSL certificates..."
    generate_ssl
    
    echo ""
    echo "Step 6: Starting services..."
    # Assuming docker-compose.yml is copied to INSTALL_DIR before running this script
    # start_services
    
    echo ""
    echo "================================================"
    echo "   Installation Complete!"
    echo "================================================"
    echo ""
    echo "Next steps:"
    echo "1. Copy docker-compose.yml and source code to $INSTALL_DIR"
    echo "2. Run: docker-compose up -d"
    echo "3. Access Admin: http://localhost:8000"
    echo "4. Access Dashboard: http://localhost:5173"
    echo ""
    echo "Default login: admin / admin123"
    echo "(Change this immediately in production!)"
    echo ""
}

main
