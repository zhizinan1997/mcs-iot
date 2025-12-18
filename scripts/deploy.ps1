<#
.SYNOPSIS
    MCS-IoT Windows 一键部署脚本
    支持 Windows 10/11, Windows Server 2016+ (需安装 Docker Desktop 或 Docker Engine)

.DESCRIPTION
    自动化完成以下任务：
    1. 环境检测 (CPU/内存/Docker)
    2. 代码更新
    3. 配置文件生成 (自动生成高强度密码)
    4. SSL 证书生成 (自动/自签名)
    5. 服务启动
    6. 模拟器运行
#>

# ==============================================================================
# 配置区域
# ==============================================================================
$ErrorActionPreference = "Stop"
$Global:InstallDir = "C:\mcs-iot"
$Global:RepoUrl = "https://github.com/zhizinan1997/mcs-iot.git"

# ==============================================================================
# 辅助函数
# ==============================================================================
function Log-Info ($Message) { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Log-Success ($Message) { Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Log-Warn ($Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Log-Error ($Message) { Write-Host "[ERROR] $Message" -ForegroundColor Red }

function Check-Admin {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Log-Error "请以管理员身份运行 PowerShell (右键 -> 以管理员身份运行)"
        exit 1
    }
}

function Generate-Password ($Length=16) {
    # 生成安全的随机密码
    $Bytes = New-Object Byte[] $Length
    $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $Rng.GetBytes($Bytes)
    [Convert]::ToBase64String($Bytes).Substring(0, $Length).Replace('+', 'x').Replace('/', 'y').Replace('=', 'z')
}

# ==============================================================================
# 主流程步骤
# ==============================================================================

function Step-CheckSystem {
    Log-Info "正在检查系统环境..."

    # 1. 检查 Docker
    try {
        $dockerVersion = docker --version
        Log-Success "Docker 已安装: $dockerVersion"
    } catch {
        Log-Error "未检测到 Docker，请先安装 Docker Desktop for Windows: https://www.docker.com/products/docker-desktop/"
        exit 1
    }

    # 2. 检查 CPU
    $cpu = Get-CimInstance Win32_Processor
    $cores = $cpu.NumberOfLogicalProcessors
    if ($cores -lt 2) {
        Log-Warn "CPU 核心数较少 ($cores 核)，建议 2 核以上"
    } else {
        Log-Success "CPU 检查通过: $cores 核"
    }

    # 3. 检查内存
    $mem = Get-CimInstance Win32_ComputerSystem
    $totalMemGB = [math]::Round($mem.TotalPhysicalMemory / 1GB, 1)
    if ($totalMemGB -lt 2) {
        Log-Warn "内存较少 ($totalMemGB GB)，建议 2GB 以上"
    } else {
        Log-Success "内存检查通过: $totalMemGB GB"
    }
}

function Step-PrepareCode {
    Log-Info "准备代码..."
    
    # 检查 Git
    try {
        git --version | Out-Null
    } catch {
        Log-Error "未检测到 Git，请先安装 Git for Windows: https://git-scm.com/download/win"
        exit 1
    }

    if (Test-Path $Global:InstallDir) {
        Log-Warn "安装目录 $Global:InstallDir 已存在"
        $choice = Read-Host "是否覆盖更新? (y/n) [y]"
        if ($choice -eq 'n') {
            Log-Info "使用现有目录..."
            Set-Location $Global:InstallDir
            git pull
            return
        }
        # 备份
        $backupName = "${Global:InstallDir}_backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
        Rename-Item $Global:InstallDir $backupName
        Log-Info "已备份旧数据到 $backupName"
    }

    Log-Info "正在克隆代码..."
    git clone $Global:RepoUrl $Global:InstallDir
    Set-Location $Global:InstallDir
}

function Step-Configure {
    Write-Host ""
    Log-Info "=== 开始配置向导 ==="

    # 1. 域名
    # 尝试自动获取内网 IP
    $localIP = $null
    try {
        $localIP = (Get-NetIPAddress -AddressFamily IPv4 -Type Unicast | Where-Object { 
            $_.InterfaceAlias -notlike "*Loopback*" -and 
            $_.InterfaceAlias -notlike "*vEthernet*" -and 
            $_.InterfaceAlias -notlike "*Docker*" 
        } | Select-Object -First 1).IPAddress
    } catch {
        # 忽略错误
    }
    if (-not $localIP) { $localIP = "localhost" }

    $domain = Read-Host "请输入服务器域名或 IP (默认: $localIP)"
    if ([string]::IsNullOrWhiteSpace($domain)) { $domain = $localIP }

    # 检测是否为内网/本地 IP
    $isLocal = $false
    if ($domain -eq "localhost" -or $domain -eq "127.0.0.1" -or 
        $domain.StartsWith("192.168.") -or 
        $domain.StartsWith("10.") -or 
        ($domain.StartsWith("172.") -and [int]$domain.Split('.')[1] -ge 16 -and [int]$domain.Split('.')[1] -le 31)) {
        $isLocal = $true
    }

    # 2. 密码生成
    Log-Info "正在生成安全密码..."
    $dbPass = Generate-Password 16
    $mqttPass = Generate-Password 16
    $adminPass = Generate-Password 12
    $jwtSecret = Generate-Password 32

    # 3. SSL 配置
    $useSSL = "false"
    $enableSSL = "n"
    $httpPort = "80"
    $httpsPort = "443"

    New-Item -ItemType Directory -Force -Path "nginx/ssl" | Out-Null

    if ($isLocal) {
        Log-Warn "检测到本地局域网或回环地址 ($domain)。"
        Log-Info "已自动选择自签名证书模式。"
        
        # 3.1 生成 OpenSSH 开发证书
        Log-Info "正在生成 OpenSSH 开发证书 (仅用于内网开发测试)..."
        New-Item -ItemType Directory -Force -Path "mosquitto/config/ssh" | Out-Null
        
        if (Get-Command ssh-keygen -ErrorAction SilentlyContinue) {
            Remove-Item "mosquitto/config/ssh/id_rsa*" -ErrorAction SilentlyContinue
            ssh-keygen -t rsa -b 4096 -f "mosquitto/config/ssh/id_rsa" -N "" -C "mcs-iot-dev"
            Log-Success "OpenSSH 开发证书 (密钥对) 已生成: mosquitto/config/ssh/id_rsa"
        } else {
            Log-Warn "未找到 ssh-keygen，跳过 SSH 证书生成。"
        }
        
        $enableSSL = "n"
    } else {
        # ICP 备案检测
        Write-Host ""
        $isICP = Read-Host "您的域名是否已在中国大陆备案? (y/n) [y]"
        if ($isICP -eq 'n') {
            Log-Warn "检测到域名未备案，将使用自定义端口 9696 部署。"
            $httpPort = "9696"
            $httpsPort = "9697"
            Log-Info "HTTP 端口已设置为: $httpPort"
            Log-Info "HTTPS 端口已设置为: $httpsPort"
            
            Log-Warn "由于 80 端口不可用，无法自动申请 Let's Encrypt 证书。"
            Log-Info "将自动切换为自签名证书模式。"
            $enableSSL = "n"
        } else {
            $enableSSL = Read-Host "是否启用 SSL (y/n) [n] (Windows 下推荐 n，除非您熟悉证书配置)"
        }
    }

    if ($enableSSL -eq 'y') {
        Log-Info "Windows 脚本暂不支持自动申请 Let's Encrypt (需 80 端口映射等复杂操作)。"
        Log-Info "正在生成自签名证书..."
        
        # 使用 Docker 运行 OpenSSL 生成证书
        docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt -subj "/C=CN/ST=State/L=City/O=MCS-IoT/CN=$domain"
        
        Copy-Item "nginx/ssl/server.crt" "nginx/ssl/ca.crt"
        $useSSL = "true"
        Log-Success "自签名证书已生成"
    } else {
        Log-Info "生成自签名 SSL 证书 (支持 SAN)..."
        
        # 创建 OpenSSL 配置文件
        $sanConfig = @"
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
CN = $domain

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = $domain
IP.1 = 127.0.0.1
"@
        if ($domain -match "^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$") {
            $sanConfig += "`nIP.2 = $domain"
        }

        Set-Content "nginx/ssl/openssl_san.cnf" $sanConfig -Encoding UTF8
        
        # 使用 Docker 运行 OpenSSL
        docker run --rm -v "${PWD}/nginx/ssl:/certs" alpine/openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt -config /certs/openssl_san.cnf
        
        Remove-Item "nginx/ssl/openssl_san.cnf" -ErrorAction SilentlyContinue

        Copy-Item "nginx/ssl/server.crt" "nginx/ssl/ca.crt"
        $useSSL = "false"
    }

    # 4. 写入 .env
    $envContent = @"
DOMAIN=$domain
DB_HOST=timescaledb
DB_PORT=5432
DB_USER=postgres
DB_PASS=$dbPass
DB_NAME=mcs_iot

REDIS_HOST=redis
REDIS_PORT=6379

MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USER=admin
MQTT_PASS=$mqttPass

JWT_SECRET=$jwtSecret
ADMIN_INITIAL_PASSWORD=$adminPass

# SSL Config
USE_SSL=$useSSL
HTTP_PORT=$httpPort
HTTPS_PORT=$httpsPort
"@
    Set-Content .env $envContent -Encoding UTF8
    Log-Success "配置文件 .env 已生成"

    # 5. 配置 Mosquitto 密码
    Log-Info "配置 MQTT 用户..."
    New-Item -ItemType Directory -Force -Path "mosquitto/config" | Out-Null
    New-Item -ItemType Directory -Force -Path "mosquitto/data" | Out-Null
    New-Item -ItemType Directory -Force -Path "mosquitto/log" | Out-Null
    
    # 创建空密码文件
    New-Item -ItemType File -Force -Path "mosquitto/config/passwd" | Out-Null
    
    # 使用 Docker 生成密码 hash
    # 注意 Windows 路径挂载格式
    docker run --rm -v "${PWD}/mosquitto/config:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd -b -c /mosquitto/config/passwd admin "$mqttPass"
    Log-Success "MQTT 密码已配置"

    # 保存密码到变量供后续显示
    $Global:FinalDbPass = $dbPass
    $Global:FinalMqttPass = $mqttPass
    $Global:FinalAdminPass = $adminPass
    $Global:FinalDomain = $domain
    $Global:IsLocal = $isLocal
    $Global:HttpPort = $httpPort
    $Global:HttpsPort = $httpsPort
}

function Step-Firewall {
    Write-Host ""
    Log-Info "=== 配置系统防火墙 ==="
    
    $ports = @(22, $Global:HttpPort, $Global:HttpsPort, 8000, 1883, 8883, 9001)
    
    foreach ($port in $ports) {
        try {
            $ruleName = "MCS-IoT-Port-$port"
            # 检查是否已存在
            if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
                New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
                Log-Info "  - 已放行端口: $port/tcp"
            } else {
                Log-Info "  - 端口已放行: $port/tcp"
            }
        } catch {
            Log-Warn "无法自动添加防火墙规则 (端口 $port)，请手动添加。"
        }
    }
    Log-Success "Windows 防火墙规则配置完成"
}

function Step-StartServices {
    Log-Info "正在启动服务..."
    docker-compose down
    docker-compose up -d --build
    if ($LASTEXITCODE -eq 0) {
        Log-Success "服务启动成功!"
    } else {
        Log-Error "服务启动失败，请检查 Docker Desktop 是否运行正常"
        exit 1
    }
}

function Step-RunSimulation {
    Write-Host ""
    Log-Info "=== 模拟测试 ==="
    $runSim = Read-Host "是否启动 30 个模拟传感器? (y/n) [y]"
    if ($runSim -ne 'n') {
        # 生成 mqtt_config.json
        $jsonContent = @"
{
    "device_user": "admin",
    "device_pass": "$Global:FinalMqttPass"
}
"@
        Set-Content "scripts/mqtt_config.json" $jsonContent -Encoding UTF8

        # 检查 Python
        try {
            python --version | Out-Null
            Log-Info "正在启动模拟器..."
            # Windows 下使用 Start-Process 后台运行
            Start-Process python -ArgumentList "scripts/simulator.py -n 30" -WindowStyle Minimized
            Log-Success "模拟器已在后台启动 (最小化窗口)"
        } catch {
            Log-Warn "未检测到 Python，跳过模拟器启动。请安装 Python 3 后手动运行 scripts/simulator.py"
        }
    }
}

function Show-Summary {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "   MCS-IoT 部署完成! (Windows)" -ForegroundColor Green
    Write-Host "================================================================"
    Write-Host ""
    Write-Host "访问地址:"
    if ($Global:HttpPort -eq "80") {
        Write-Host "  - 管理后台: http://$($Global:FinalDomain):8000" -ForegroundColor Cyan
        Write-Host "  - 数据大屏: http://$($Global:FinalDomain)" -ForegroundColor Cyan
    } else {
        Write-Host "  - 管理后台: http://$($Global:FinalDomain):8000" -ForegroundColor Cyan
        Write-Host "  - 数据大屏: http://$($Global:FinalDomain):$($Global:HttpPort)" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "账号信息 (请截图保存):"
    Write-Host "  - 管理员账号: admin" -ForegroundColor Yellow
    Write-Host "  - 管理员密码: $($Global:FinalAdminPass)" -ForegroundColor Yellow
    Write-Host "  - 数据库密码: $($Global:FinalDbPass)" -ForegroundColor Yellow
    Write-Host "  - MQTT 密码 : $($Global:FinalMqttPass)" -ForegroundColor Yellow
    if ($Global:IsLocal) {
        Write-Host "  - OpenSSH 证书: mosquitto/config/ssh/id_rsa (仅开发用)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "安装目录: $Global:InstallDir"
    Write-Host "================================================================"
    Write-Host "提醒: 请务必在云服务器提供商 (阿里云/腾讯云/AWS等) 的安全组/防火墙中放行以下端口:" -ForegroundColor Yellow
    Write-Host "      TCP: $($Global:HttpPort), $($Global:HttpsPort), 8000, 1883, 8883, 9001" -ForegroundColor Yellow
    if ($Global:IsLocal) {
        Write-Host "提醒: 已为您生成 OpenSSH 开发证书及自签名 SSL 证书。" -ForegroundColor Yellow
        Write-Host "      由于使用自签名证书，浏览器可能会提示不安全，请手动信任或忽略。" -ForegroundColor Yellow
    }
    pause
}

# ==============================================================================
# 执行入口
# ==============================================================================
Clear-Host
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   MCS-IoT Windows 智能部署脚本 v1.0" -ForegroundColor Cyan
Write-Host "================================================================"
Start-Sleep -Seconds 1

Check-Admin
Step-CheckSystem
Step-PrepareCode
Step-Configure
Step-Firewall
Step-StartServices
Step-RunSimulation
Show-Summary
