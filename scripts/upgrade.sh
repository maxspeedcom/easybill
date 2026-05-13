#!/usr/bin/env bash
# EasyBill v1 → v2 in-place upgrade
# รันจากโฟลเดอร์ที่แตก zip ใหม่ออกมา
set -euo pipefail

INSTALL_DIR="/opt/thaibill"
SERVICE_USER="thaibill"

if [[ $EUID -ne 0 ]]; then
   echo "❌ ต้องรันด้วย sudo" >&2; exit 1
fi
if [[ ! -d "$INSTALL_DIR" ]]; then
   echo "❌ ไม่พบ $INSTALL_DIR — กรุณารัน scripts/install.sh สำหรับการติดตั้งใหม่" >&2; exit 1
fi

SRC="$(cd "$(dirname "$0")/.." && pwd)"
echo "▶ อัปเกรดจาก: $SRC"
echo "▶ ปลายทาง:   $INSTALL_DIR"

# 1) สำรอง DB
echo ""
echo "── 1) สำรองฐานข้อมูล"
STAMP=$(date +%Y%m%d-%H%M%S)
if [[ -f "$INSTALL_DIR/instance/thaibill.db" ]]; then
  cp "$INSTALL_DIR/instance/thaibill.db" "$INSTALL_DIR/instance/thaibill.db.backup-$STAMP"
  echo "   ✓ สำรองไปยัง instance/thaibill.db.backup-$STAMP"
else
  echo "   ⚠ ยังไม่มี DB เดิม (ถือว่าเป็นการติดตั้งใหม่)"
fi

# 2) หยุดบริการ
echo ""
echo "── 2) หยุด systemd service"
systemctl stop thaibill || true

# 3) คัดลอกไฟล์ใหม่ (ยกเว้น instance/ และ .env)
echo ""
echo "── 3) คัดลอกไฟล์ใหม่"
rsync -a --delete \
  --exclude='instance/' \
  --exclude='.env' \
  --exclude='venv/' \
  --exclude='logs/' \
  --exclude='app/static/uploads/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  "$SRC/" "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/logs" "$INSTALL_DIR/app/static/uploads"
echo "   ✓ คัดลอกเรียบร้อย"

# 4) ติดตั้ง dependency เพิ่มเติม (เผื่อมี)
echo ""
echo "── 4) อัปเดต Python packages"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
echo "   ✓ packages ครบถ้วน"

# 5) Migrate schema
echo ""
echo "── 5) Migrate ฐานข้อมูล v1 → v2"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/venv/bin/python" \
  "$INSTALL_DIR/scripts/migrate_v1_to_v2.py"

# 6) Restart service
echo ""
echo "── 6) เริ่มบริการใหม่"
systemctl start thaibill
sleep 1
systemctl is-active thaibill && echo "   ✓ thaibill ทำงานปกติ" || {
  echo "   ❌ thaibill ไม่ขึ้น — ดู log: journalctl -u thaibill -n 50"
  exit 1
}

echo ""
echo "════════════════════════════════════════"
echo "✅ อัปเกรดเสร็จสมบูรณ์!"
echo ""
echo "เปิดเว็บ: http://$(hostname -I | awk '{print $1}')/"
echo "ตอนนี้ระบบรองรับ 5 ประเภทเอกสารแล้ว:"
echo "  • ใบเสนอราคา (QT)"
echo "  • ใบแจ้งหนี้ (IV)"
echo "  • ใบส่งของ (DO)"
echo "  • ใบกำกับภาษี (TI)"
echo "  • ใบเสร็จรับเงิน (RC)"
echo "════════════════════════════════════════"
