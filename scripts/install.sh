#!/usr/bin/env bash
# ============================================================
# EasyBill - Ubuntu Auto Installer
# รองรับ Ubuntu 22.04 / 24.04
# Usage:   sudo bash install.sh
# ============================================================
set -euo pipefail

# Colors
C_GREEN='\033[0;32m'
C_BLUE='\033[0;34m'
C_YELLOW='\033[0;33m'
C_RED='\033[0;31m'
C_NC='\033[0m'

log()  { echo -e "${C_BLUE}[INFO]${C_NC} $*"; }
ok()   { echo -e "${C_GREEN}[ OK ]${C_NC} $*"; }
warn() { echo -e "${C_YELLOW}[WARN]${C_NC} $*"; }
err()  { echo -e "${C_RED}[FAIL]${C_NC} $*" >&2; }

# ------------------------------------------------------------
# 0. Pre-flight checks
# ------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    err "ต้องรันด้วย sudo หรือ root"
    exit 1
fi

if ! grep -qiE "ubuntu|debian" /etc/os-release; then
    warn "ระบบนี้ไม่ใช่ Ubuntu/Debian — สคริปต์อาจทำงานไม่สมบูรณ์"
fi

# Detect project source dir (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"

# ------------------------------------------------------------
# 1. Configuration (ปรับได้)
# ------------------------------------------------------------
INSTALL_DIR="/opt/thaibill"
SERVICE_USER="thaibill"
APP_PORT="8000"

echo ""
echo "============================================================"
echo "  EasyBill - ติดตั้งระบบใบเสนอราคา บน Ubuntu"
echo "============================================================"
echo "  โฟลเดอร์ติดตั้ง: $INSTALL_DIR"
echo "  ผู้ใช้ระบบ:        $SERVICE_USER"
echo "  พอร์ตภายใน:       $APP_PORT"
echo "  ที่มาของโปรเจกต์:   $PROJECT_SRC"
echo "============================================================"
echo ""
read -p "กด Enter เพื่อเริ่มติดตั้ง หรือ Ctrl+C เพื่อยกเลิก ..." _

# ------------------------------------------------------------
# 2. ติดตั้ง dependencies จาก apt
# ------------------------------------------------------------
log "อัปเดต apt package index ..."
apt-get update -y

log "ติดตั้ง Python3 และ system packages ..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    nginx \
    git \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-thai-tlwg

ok "ติดตั้ง dependencies เรียบร้อย"

# ------------------------------------------------------------
# 3. สร้างผู้ใช้ระบบ
# ------------------------------------------------------------
if ! id "$SERVICE_USER" &>/dev/null; then
    log "สร้างผู้ใช้ระบบ: $SERVICE_USER ..."
    useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    ok "สร้างผู้ใช้ $SERVICE_USER"
else
    ok "ผู้ใช้ $SERVICE_USER มีอยู่แล้ว"
fi

# ------------------------------------------------------------
# 4. คัดลอกไฟล์โปรเจกต์ไป $INSTALL_DIR
# ------------------------------------------------------------
log "คัดลอกไฟล์โปรเจกต์ไปยัง $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
# rsync ฉลาดกว่า cp และข้าม venv/instance เดิม
if command -v rsync &>/dev/null; then
    rsync -a --delete \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'instance/thaibill.db' \
        "$PROJECT_SRC/" "$INSTALL_DIR/"
else
    apt-get install -y rsync
    rsync -a --delete \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'instance/thaibill.db' \
        "$PROJECT_SRC/" "$INSTALL_DIR/"
fi
mkdir -p "$INSTALL_DIR/instance" "$INSTALL_DIR/logs"
ok "คัดลอกไฟล์เรียบร้อย"

# ------------------------------------------------------------
# 5. สร้าง .env (SECRET_KEY แบบสุ่ม)
# ------------------------------------------------------------
ENV_FILE="$INSTALL_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    log "สร้างไฟล์ .env พร้อม SECRET_KEY แบบสุ่ม ..."
    SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat > "$ENV_FILE" <<EOF
SECRET_KEY=$SECRET
FLASK_ENV=production
EOF
    chmod 600 "$ENV_FILE"
    ok "สร้าง .env เรียบร้อย"
else
    ok "ใช้ .env เดิมที่มีอยู่"
fi

# ------------------------------------------------------------
# 6. สร้าง virtualenv + ติดตั้ง Python packages
# ------------------------------------------------------------
log "สร้าง Python virtualenv ..."
sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv"

log "อัปเดต pip ..."
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel setuptools

log "ติดตั้ง Python packages (อาจใช้เวลา 1-3 นาที) ..."
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
ok "ติดตั้ง Python packages เรียบร้อย"

# ------------------------------------------------------------
# 7. ตั้งค่าสิทธิ์ไฟล์
# ------------------------------------------------------------
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod 750 "$INSTALL_DIR"
ok "ตั้งค่าสิทธิ์ไฟล์เรียบร้อย"

# ------------------------------------------------------------
# 8. รัน seed.py สร้างผู้ใช้ admin
# ------------------------------------------------------------
log "สร้างฐานข้อมูลและผู้ใช้เริ่มต้น ..."
sudo -u "$SERVICE_USER" bash -c "cd '$INSTALL_DIR' && '$INSTALL_DIR/venv/bin/python' scripts/seed.py"
ok "ฐานข้อมูลเริ่มต้นเรียบร้อย"

# ------------------------------------------------------------
# 9. ติดตั้ง systemd service
# ------------------------------------------------------------
log "ติดตั้ง systemd service ..."
cp "$INSTALL_DIR/scripts/thaibill.service" /etc/systemd/system/thaibill.service
systemctl daemon-reload
systemctl enable thaibill
systemctl restart thaibill
sleep 2

if systemctl is-active --quiet thaibill; then
    ok "thaibill service ทำงานแล้ว"
else
    err "thaibill service ไม่สามารถเริ่มได้ — ตรวจสอบด้วย: journalctl -u thaibill -n 50"
    exit 1
fi

# ------------------------------------------------------------
# 10. ติดตั้ง nginx site
# ------------------------------------------------------------
log "ติดตั้ง nginx config ..."
cp "$INSTALL_DIR/scripts/thaibill.nginx" /etc/nginx/sites-available/thaibill
ln -sf /etc/nginx/sites-available/thaibill /etc/nginx/sites-enabled/thaibill

# ลบ default site ถ้ายังอยู่ (อาจชนกัน)
if [[ -L /etc/nginx/sites-enabled/default ]]; then
    rm /etc/nginx/sites-enabled/default
    log "ลบ default nginx site"
fi

if nginx -t 2>/dev/null; then
    systemctl reload nginx
    ok "nginx รีโหลดเรียบร้อย"
else
    err "nginx config ไม่ถูกต้อง — รัน 'nginx -t' เพื่อดูรายละเอียด"
    exit 1
fi

# ------------------------------------------------------------
# 11. เปิด firewall (ถ้ามี ufw)
# ------------------------------------------------------------
if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
    log "เปิด firewall พอร์ต 80/443 ..."
    ufw allow 'Nginx Full' || true
fi

# ------------------------------------------------------------
# 12. สรุปผล
# ------------------------------------------------------------
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================================"
echo -e "  ${C_GREEN}✓ ติดตั้ง EasyBill สำเร็จ${C_NC}"
echo "============================================================"
echo ""
echo "  เข้าใช้งานที่:  http://${SERVER_IP}/"
echo "  หรือ:           http://localhost/  (ถ้าเข้าจากเครื่องเดียวกัน)"
echo ""
echo "  ชื่อผู้ใช้:      admin"
echo "  รหัสผ่าน:       admin1234"
echo ""
echo -e "  ${C_YELLOW}** กรุณาเปลี่ยนรหัสผ่าน admin หลังเข้าใช้ครั้งแรก **${C_NC}"
echo ""
echo "  คำสั่งที่ใช้บ่อย:"
echo "    systemctl status thaibill      # ตรวจสถานะ"
echo "    systemctl restart thaibill     # รีสตาร์ท"
echo "    journalctl -u thaibill -f      # ดู log"
echo "    nginx -t && systemctl reload nginx"
echo ""
echo "  ไฟล์ระบบ:"
echo "    โปรแกรม:    $INSTALL_DIR"
echo "    ฐานข้อมูล:   $INSTALL_DIR/instance/thaibill.db"
echo "    Log:        $INSTALL_DIR/logs/"
echo "    Config:     $ENV_FILE"
echo ""
echo "============================================================"
