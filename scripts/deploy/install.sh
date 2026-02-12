#!/bin/bash

# UNIVERSAL WireGuard Dashboard Installation Script
# Works on Ubuntu AND Debian automatically
# Detects OS and uses the correct repository
# Password: Test123

set -e

echo "UNIVERSAL WIREGUARD DASHBOARD INSTALLATION"
echo "==========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Run as root: sudo bash install_universal.sh"
    exit 1
fi

# Status check function
check_status() {
    if [ $? -eq 0 ]; then
        echo "OK: $1"
    else
        echo "ERROR: $1"
        exit 1
    fi
}

# Detect operating system
echo "DETECTION: Identifying operating system..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    CODENAME=$VERSION_CODENAME
else
    echo "ERROR: Could not detect operating system"
    exit 1
fi

echo "Detected system: $OS $VERSION ($CODENAME)"

# Set variables based on OS
case $OS in
    "ubuntu")
        DOCKER_REPO="ubuntu"
        RELEASE_NAME=$(lsb_release -cs)
        ;;
    "debian")
        DOCKER_REPO="debian"
        RELEASE_NAME=$(lsb_release -cs)
        ;;
    *)
        echo "ERROR: Unsupported operating system: $OS"
        echo "Use Ubuntu or Debian"
        exit 1
        ;;
esac

echo "Configuration: Docker for $DOCKER_REPO, release: $RELEASE_NAME"

echo "CLEANUP: Removing previous installation..."
# Stop and remove existing containers
docker-compose -f /opt/wgdashboard/docker-compose.yml down 2>/dev/null || true
docker rm -f wgdashboard 2>/dev/null || true
docker rmi donaldzou/wgdashboard:latest 2>/dev/null || true

# Remove old directories
rm -rf /opt/wgdashboard
rm -rf /etc/wireguard

# Clean old Docker repositories (issues)
rm -f /etc/apt/sources.list.d/docker.list
rm -f /usr/share/keyrings/docker-archive-keyring.gpg

echo "OK: Cleanup completed"

echo "UPDATE: System..."
apt update && apt upgrade -y
check_status "System update"

echo "INSTALL: Basic dependencies..."
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    net-tools
check_status "Basic dependencies"

echo "DOCKER: Removing old versions..."
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

echo "DOCKER: Adding official repository for $DOCKER_REPO..."
curl -fsSL https://download.docker.com/linux/$DOCKER_REPO/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
check_status "Docker GPG key"

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$DOCKER_REPO $RELEASE_NAME stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
check_status "Docker repository"

echo "DOCKER: Installing..."
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
check_status "Docker installation"

systemctl start docker
systemctl enable docker
check_status "Docker enabled"

echo "DOCKER: Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
check_status "Docker Compose"

echo "NETWORK: Configuring IP forwarding..."
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.src_valid_mark=1
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-wireguard.conf
echo 'net.ipv4.conf.all.src_valid_mark=1' >> /etc/sysctl.d/99-wireguard.conf
sysctl -p /etc/sysctl.d/99-wireguard.conf
check_status "IP forwarding"

echo "FIREWALL: Configuring (universal method)..."
# Universal method without UFW (for compatibility)
# Discover main interface
MAIN_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
echo "Main interface detected: $MAIN_INTERFACE"

# Configure iptables
iptables -t nat -F POSTROUTING 2>/dev/null || true
iptables -t nat -A POSTROUTING -s 10.13.13.0/24 -o $MAIN_INTERFACE -j MASQUERADE
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o $MAIN_INTERFACE -j MASQUERADE
iptables -A FORWARD -i wg+ -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -o wg+ -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p udp --dport 51820 -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p tcp --dport 10086 -j ACCEPT 2>/dev/null || true
check_status "Network configuration"

echo "SETUP: Creating directory structure..."
mkdir -p /opt/wgdashboard/{config,app}
cd /opt/wgdashboard
check_status "Directory creation"

echo "SETUP: Creating optimized docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
services:
  wgdashboard:
    image: donaldzou/wgdashboard:latest
    container_name: wgdashboard
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    volumes:
      - ./config:/opt/wireguarddashboard/src
      - ./app:/opt/wireguarddashboard/src/static
      - /lib/modules:/lib/modules:ro
    ports:
      - "10086:10086"
      - "51820:51820/udp"
    environment:
      - ENABLE=true
      - PUID=0
      - PGID=0
    privileged: true
EOF
check_status "docker-compose.yml creation"

echo "SETUP: Configuring permissions..."
chown -R root:root /opt/wgdashboard
chmod 755 /opt/wgdashboard
check_status "Permissions configuration"

echo "WIREGUARD: Downloading and starting..."
docker-compose pull
check_status "Image download"

docker-compose up -d
check_status "Container initialization"

echo "WAITING: Full initialization (60 seconds)..."
sleep 60

# Check if container is running
if ! docker ps | grep -q wgdashboard; then
    echo "ERROR: Container is not running. Trying simplified version..."
    docker-compose down

    # Create ultra-simple version without issues
    cat > docker-compose.yml << 'EOF'
services:
  wgdashboard:
    image: donaldzou/wgdashboard:latest
    container_name: wgdashboard
    restart: unless-stopped
    privileged: true
    volumes:
      - ./config:/opt/wireguarddashboard/src
    ports:
      - "10086:10086"
      - "51820:51820/udp"
    environment:
      - ENABLE=true
EOF

    echo "RETRY: Restarting with simplified configuration..."
    docker-compose up -d
    sleep 45

    if ! docker ps | grep -q wgdashboard; then
        echo "ERROR: Still having issues. Logs:"
        docker-compose logs
        exit 1
    fi
fi

echo "CONFIG: Setting password Test123..."
sleep 30

# Multiple methods to configure password
echo "Attempting to configure password Test123..."

# Method 1: Dashboard CLI
docker exec wgdashboard bash -c "
cd /opt/wireguarddashboard/src
timeout 30 python3 main.py --username admin --password Test123 2>/dev/null
" 2>/dev/null && echo "OK: Password configured via CLI" || echo "CLI method failed, trying SQLite..."

# Method 2: Direct SQLite
docker exec wgdashboard bash -c "
cd /opt/wireguarddashboard/src
python3 -c \"
import bcrypt
import sqlite3
import time

try:
    time.sleep(5)
    password = 'Test123'
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = sqlite3.connect('/opt/wireguarddashboard/src/wgdashboard.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Account (username TEXT PRIMARY KEY, password TEXT NOT NULL)''')
    cursor.execute('''INSERT OR REPLACE INTO Account (username, password) VALUES (?, ?)''', ('admin', hashed))

    conn.commit()
    conn.close()
    print('OK: Password Test123 configured via SQLite')
except Exception as e:
    print(f'Error: {e}')
\"
" 2>/dev/null || echo "WARNING: Configure manually: admin/Test123"

echo "FINALIZING: Restart..."
docker-compose restart
sleep 30

# Create persistence script for iptables
cat > /etc/rc.local << EOF
#!/bin/bash
# Restore iptables rules for WireGuard
sleep 10
MAIN_INTERFACE=\$(ip route | grep default | awk '{print \$5}' | head -1)
iptables -t nat -F POSTROUTING 2>/dev/null || true
iptables -t nat -A POSTROUTING -s 10.13.13.0/24 -o \$MAIN_INTERFACE -j MASQUERADE
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o \$MAIN_INTERFACE -j MASQUERADE
iptables -A FORWARD -i wg+ -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -o wg+ -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p udp --dport 51820 -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p tcp --dport 10086 -j ACCEPT 2>/dev/null || true
exit 0
EOF
chmod +x /etc/rc.local

# Final verification
if docker ps | grep -q wgdashboard; then
    echo "OK: WireGuard Dashboard running!"
else
    echo "ERROR: Initialization problem"
    docker-compose logs --tail 50
    exit 1
fi

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "YOUR_PUBLIC_IP")

echo
echo "UNIVERSAL INSTALLATION COMPLETED!"
echo "=================================="
echo
echo "SYSTEM: $OS $VERSION ($CODENAME)"
echo "DASHBOARD ACCESS:"
echo "   URL: http://$PUBLIC_IP:10086"
echo "   Username: admin"
echo "   Password: Test123"
echo
echo "REQUIRED INITIAL CONFIGURATION:"
echo "   1. Access the dashboard"
echo "   2. Go to 'Server Configuration'"
echo "   3. Configure:"
echo "      - Endpoint: $PUBLIC_IP:51820"
echo "      - Address: 10.13.13.1/24"
echo "      - Listen Port: 51820"
echo "      - DNS: 8.8.8.8, 8.8.4.4"
echo "   4. Save the configuration"
echo "   5. Create a peer to test"
echo
echo "USEFUL COMMANDS:"
echo "   # View logs:"
echo "   cd /opt/wgdashboard && docker-compose logs -f"
echo
echo "   # Restart:"
echo "   cd /opt/wgdashboard && docker-compose restart"
echo
echo "   # Status:"
echo "   docker ps | grep wgdashboard"
echo
echo "   # Check WireGuard:"
echo "   docker exec wgdashboard wg show"
echo
echo "CURRENT STATUS:"
echo "==============="
echo "System: $OS $VERSION"
echo "Container: $(docker ps --format 'table {{.Names}}\t{{.Status}}' | grep wgdashboard)"
echo "IP Forwarding: $(sysctl -n net.ipv4.ip_forward)"
echo "Interface: $MAIN_INTERFACE"
echo
echo "ACCESS NOW: http://$PUBLIC_IP:10086"
echo "Login: admin / Test123"
