#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# OpenCyclo OS — One-Shot Provisioning Script
# ──────────────────────────────────────────────────────────────────────────
# Target platforms:
#   - NVIDIA Jetson Nano 4GB (JetPack 6.x / Ubuntu 22.04 aarch64)
#   - Raspberry Pi 5 (Raspberry Pi OS Bookworm / Ubuntu 24.04 arm64)
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/xaviercallens/OpenCycloInitiative/main/software/opencyclo_os/deploy/setup.sh | bash
#
# What this script does:
#   1. Installs system-level dependencies (I2C tools, GPIO, camera)
#   2. Creates a Python virtual environment
#   3. Installs pinned Python dependencies
#   4. Installs the systemd service unit
#   5. Enables I2C and camera kernel modules
#   6. Creates the log directory
#   7. Prints next-step instructions
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
AMBER='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="/opt/opencyclo"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="/var/log/opencyclo"
SERVICE_NAME="opencyclo.service"

# ─── Header ────────────────────────────────────────────────────────────
echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     🌿 OpenCyclo OS — Provisioning       ║"
echo "  ║     V0.1-alpha Setup Script              ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Pre-flight checks ────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (sudo).${NC}"
    exit 1
fi

# Detect platform
PLATFORM="unknown"
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    if echo "$MODEL" | grep -qi "jetson"; then
        PLATFORM="jetson"
    elif echo "$MODEL" | grep -qi "raspberry"; then
        PLATFORM="rpi"
    fi
fi
echo -e "${GREEN}[1/7] Detected platform: ${PLATFORM}${NC}"

# ─── Step 1: System dependencies ──────────────────────────────────────
echo -e "${CYAN}[2/7] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    i2c-tools \
    v4l-utils \
    libopencv-dev \
    libatlas-base-dev \
    git

# Platform-specific GPIO
if [ "$PLATFORM" = "jetson" ]; then
    apt-get install -y -qq python3-jetson-gpio || true
    # Enable I2C buses 0 and 1 via device tree
    echo -e "${AMBER}  Jetson: Ensure I2C buses are enabled via jetson-io.py${NC}"
elif [ "$PLATFORM" = "rpi" ]; then
    apt-get install -y -qq python3-rpi.gpio || true
    # Enable I2C and camera via raspi-config non-interactive
    raspi-config nonint do_i2c 0 2>/dev/null || true
    raspi-config nonint do_camera 0 2>/dev/null || true
    echo -e "${GREEN}  RPi: I2C and Camera interfaces enabled${NC}"
fi

# ─── Step 2: Create install directory ─────────────────────────────────
echo -e "${CYAN}[3/7] Creating installation directory...${NC}"
mkdir -p "${INSTALL_DIR}"
mkdir -p "${LOG_DIR}"

# Copy source files (assume we're running from the repo root or deploy dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_DIR}/config.py" ]; then
    cp -r "${REPO_DIR}"/*.py "${INSTALL_DIR}/"
    cp -r "${REPO_DIR}/utils" "${INSTALL_DIR}/"
    cp "${REPO_DIR}/requirements.txt" "${INSTALL_DIR}/"
    echo -e "${GREEN}  Source files copied to ${INSTALL_DIR}${NC}"
else
    echo -e "${AMBER}  Source files not found locally, skipping copy.${NC}"
    echo -e "${AMBER}  Clone the repo into ${INSTALL_DIR} manually.${NC}"
fi

# ─── Step 3: Python virtual environment ───────────────────────────────
echo -e "${CYAN}[4/7] Creating Python virtual environment...${NC}"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

# Upgrade pip
pip install --upgrade pip setuptools wheel -q

# Install core dependencies
if [ -f "${INSTALL_DIR}/requirements.txt" ]; then
    # Install only the garage profile deps (skip optional industrial deps)
    grep -v "^#" "${INSTALL_DIR}/requirements.txt" | \
    grep -v "ultralytics" | \
    grep -v "pymodbus" | \
    grep -v "smbus2" | \
    pip install -r /dev/stdin -q 2>/dev/null || true

    # Try smbus2 (may fail on non-Linux)
    pip install smbus2 -q 2>/dev/null || true
fi

echo -e "${GREEN}  Python environment ready at ${VENV_DIR}${NC}"

# ─── Step 4: Install systemd service ──────────────────────────────────
echo -e "${CYAN}[5/7] Installing systemd service...${NC}"

cat > "/etc/systemd/system/${SERVICE_NAME}" << EOF
[Unit]
Description=OpenCyclo OS — Bioreactor Control Daemon
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python3 ${INSTALL_DIR}/main_loop.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

# Watchdog: restart if no heartbeat in 120s
WatchdogSec=120

# Resource limits
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
echo -e "${GREEN}  Service installed and enabled (will start on boot)${NC}"

# ─── Step 5: I2C permissions ──────────────────────────────────────────
echo -e "${CYAN}[6/7] Configuring I2C permissions...${NC}"
if ! getent group i2c >/dev/null 2>&1; then
    groupadd i2c
fi
usermod -aG i2c root 2>/dev/null || true

# Create udev rule for I2C access
cat > /etc/udev/rules.d/99-i2c.rules << 'EOF'
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660"
EOF
udevadm control --reload-rules 2>/dev/null || true

echo -e "${GREEN}  I2C group and udev rules configured${NC}"

# ─── Step 6: Verify ──────────────────────────────────────────────────
echo -e "${CYAN}[7/7] Verifying installation...${NC}"

# Test I2C
if command -v i2cdetect &>/dev/null; then
    echo -e "  I2C bus 1 scan:"
    i2cdetect -y 1 2>/dev/null || echo -e "${AMBER}  (I2C bus 1 not available on this platform)${NC}"
fi

# Test camera
if command -v v4l2-ctl &>/dev/null; then
    v4l2-ctl --list-devices 2>/dev/null || echo -e "${AMBER}  (No camera devices detected)${NC}"
fi

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ OpenCyclo OS provisioning complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Install dir:    ${CYAN}${INSTALL_DIR}${NC}"
echo -e "  Log dir:        ${CYAN}${LOG_DIR}${NC}"
echo -e "  Python venv:    ${CYAN}${VENV_DIR}${NC}"
echo -e "  Service:        ${CYAN}${SERVICE_NAME}${NC}"
echo ""
echo -e "  ${AMBER}Next steps:${NC}"
echo -e "    1. Run calibration:  ${CYAN}sudo ${VENV_DIR}/bin/python3 ${INSTALL_DIR}/deploy/calibration.py${NC}"
echo -e "    2. Start the daemon: ${CYAN}sudo systemctl start ${SERVICE_NAME}${NC}"
echo -e "    3. View live logs:   ${CYAN}journalctl -u ${SERVICE_NAME} -f${NC}"
echo ""
