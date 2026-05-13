# 🐧 คู่มือติดตั้ง EasyBill บน Ubuntu / Debian

> สำหรับ Ubuntu 22.04 / 24.04 และ Debian 11 / 12

[← กลับไปหน้าหลัก](../README.md)

---

## 📑 สารบัญ

1. [ติดตั้งอัตโนมัติ (แนะนำ)](#1-ติดตั้งอัตโนมัติ-แนะนำ)
2. [ติดตั้งด้วยตนเอง (Manual)](#2-ติดตั้งด้วยตนเอง-manual)
3. [ตั้งค่า Nginx + SSL](#3-ตั้งค่า-nginx--ssl)
4. [การอัปเดต](#4-การอัปเดต)
5. [Backup และ Restore](#5-backup-และ-restore)
6. [แก้ปัญหา](#6-แก้ปัญหา)

---

## 1. ติดตั้งอัตโนมัติ (แนะนำ)

โปรเจกต์มาพร้อมสคริปต์ `install.sh` ที่ทำทุกอย่างให้:

```bash
# 1. ติดตั้ง git ก่อน (ถ้ายังไม่มี)
sudo apt update && sudo apt install -y git

# 2. Clone repo
sudo git clone https://github.com/maxspeedcom/easybill.git /opt/thaibill

# 3. รัน installer
cd /opt/thaibill
sudo bash scripts/install.sh
```

สคริปต์จะ:
- ✅ ติดตั้ง Python 3.10+, pip, venv
- ✅ ติดตั้ง dependencies ทั้งหมด (Flask, gunicorn, ReportLab ฯลฯ)
- ✅ ติดตั้งฟอนต์ไทย (Sarabun) สำหรับ PDF
- ✅ สร้าง user `thaibill` (system user, no login)
- ✅ ตั้ง permission ถูกต้อง
- ✅ Setup systemd service
- ✅ Setup nginx reverse proxy (ถ้ามี)
- ✅ เริ่ม service อัตโนมัติ

หลังเสร็จ — เข้าใช้งานที่ `http://<server-ip>` หรือ `http://<server-ip>:8000`

**Login ครั้งแรก:**
- Username: `admin`
- Password: `admin1234`

> ⚠️ **เปลี่ยนรหัสผ่านทันที** ที่ `/users/` → แก้ไข admin

---

## 2. ติดตั้งด้วยตนเอง (Manual)

ถ้าต้องการควบคุมทุกขั้น หรือสคริปต์ไม่ทำงานบนระบบของคุณ:

### 2.1 อัปเดตระบบ + ติดตั้ง dependencies

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3 python3-pip python3-venv \
    git curl \
    build-essential libffi-dev \
    fonts-thai-tlwg \
    nginx \
    sqlite3
```

### 2.2 สร้าง user สำหรับ service

```bash
sudo useradd -r -s /bin/false -d /opt/thaibill thaibill
```

### 2.3 Clone repository

```bash
sudo mkdir -p /opt/thaibill
sudo chown $USER:$USER /opt/thaibill
git clone https://github.com/maxspeedcom/easybill.git /opt/thaibill
cd /opt/thaibill
```

### 2.4 สร้าง virtual environment + ติดตั้ง packages

```bash
cd /opt/thaibill
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate
```

### 2.5 สร้างโฟลเดอร์ที่จำเป็น

```bash
mkdir -p instance logs \
    app/static/uploads/logos \
    app/static/uploads/signatures \
    app/static/uploads/attachments
```

### 2.6 ตั้ง permission ให้ thaibill user

```bash
sudo chown -R thaibill:thaibill /opt/thaibill
sudo chmod -R 755 /opt/thaibill
sudo chmod -R 770 /opt/thaibill/instance \
                  /opt/thaibill/logs \
                  /opt/thaibill/app/static/uploads
```

### 2.7 ทดสอบรันก่อน

```bash
cd /opt/thaibill
sudo -u thaibill venv/bin/python wsgi.py
```

ทดสอบเปิด `http://<server-ip>:8000` — เห็นหน้า login → กด **Ctrl+C** หยุด

### 2.8 ติดตั้ง systemd service

```bash
sudo cp /opt/thaibill/scripts/thaibill.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable thaibill
sudo systemctl start thaibill
sudo systemctl status thaibill   # ตรวจสถานะ
```

ดูล็อกถ้ามีปัญหา:
```bash
sudo journalctl -u thaibill -f
```

---

## 3. ตั้งค่า Nginx + SSL

### 3.1 ติดตั้ง Nginx config

```bash
sudo cp /opt/thaibill/scripts/thaibill.nginx /etc/nginx/sites-available/thaibill
sudo ln -sf /etc/nginx/sites-available/thaibill /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

แก้ไข `/etc/nginx/sites-available/thaibill` — เปลี่ยน `server_name` ให้ตรงกับโดเมนหรือ IP:

```nginx
server {
    listen 80;
    server_name your-domain.com;   # หรือ IP
    ...
}
```

ทดสอบและรีโหลด:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3.2 SSL ฟรีด้วย Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot จะตั้งค่า auto-renew ให้อัตโนมัติ (ตรวจที่ `/etc/cron.d/certbot`)

### 3.3 ทางเลือก: Cloudflare Tunnel (ไม่ต้องเปิด port)

ฟรี + ได้ HTTPS อัตโนมัติ — เหมาะกับเซิร์ฟเวอร์ที่อยู่หลัง NAT:

```bash
# ติดตั้ง cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Login เข้า Cloudflare
cloudflared tunnel login

# สร้าง tunnel
cloudflared tunnel create easybill
cloudflared tunnel route dns easybill easybill.your-domain.com

# Run
cloudflared tunnel --url http://localhost:8000 run easybill
```

---

## 4. การอัปเดต

ใช้สคริปต์ `upgrade.sh` ที่มากับโปรเจกต์:

```bash
cd /opt/thaibill
sudo bash scripts/upgrade.sh
sudo systemctl restart thaibill
```

หรือทำเอง:

```bash
cd /opt/thaibill
sudo -u thaibill git pull
sudo -u thaibill venv/bin/pip install -r requirements.txt
sudo -u thaibill venv/bin/python scripts/migrate_v1_to_v2.py
sudo systemctl restart thaibill
```

---

## 5. Backup และ Restore

### 5.1 Backup ด้วยมือ

```bash
# DB
sudo cp /opt/thaibill/instance/thaibill.db ~/backup-$(date +%Y%m%d).db

# Uploads
sudo tar czf ~/uploads-$(date +%Y%m%d).tar.gz \
    -C /opt/thaibill app/static/uploads
```

### 5.2 Backup อัตโนมัติด้วย cron

```bash
sudo crontab -e
```

เพิ่ม:
```cron
# Backup ทุกวันตอน 02:00
0 2 * * * tar czf /backup/easybill-$(date +\%Y\%m\%d).tar.gz /opt/thaibill/instance /opt/thaibill/app/static/uploads
# ลบ backup เก่ากว่า 30 วัน
0 3 * * * find /backup -name "easybill-*.tar.gz" -mtime +30 -delete
```

### 5.3 Restore

```bash
sudo systemctl stop thaibill
sudo cp ~/backup-20251115.db /opt/thaibill/instance/thaibill.db
sudo chown thaibill:thaibill /opt/thaibill/instance/thaibill.db
sudo systemctl start thaibill
```

---

## 6. แก้ปัญหา

### Service ไม่เริ่ม

```bash
sudo journalctl -u thaibill -n 100 --no-pager
```

ปัญหาที่พบบ่อย:
- **Permission denied**: รัน `sudo chown -R thaibill:thaibill /opt/thaibill`
- **Port already in use**: หา process ที่ใช้ port 8000 → `sudo lsof -i :8000`
- **Module not found**: รัน `sudo -u thaibill venv/bin/pip install -r requirements.txt` ใหม่

### Login ไม่ได้

Reset password admin:
```bash
cd /opt/thaibill
sudo -u thaibill venv/bin/python -c "
from app import create_app, db
from app.models import User
app = create_app('production')
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    u.set_password('newpassword123')
    db.session.commit()
    print('Reset done')
"
```

### PDF แสดงภาษาไทยเป็นกล่อง

```bash
sudo apt install -y fonts-thai-tlwg
sudo fc-cache -fv
sudo systemctl restart thaibill
```

### หน่วยความจำเซิร์ฟเวอร์น้อย

ปรับ gunicorn workers ใน `/etc/systemd/system/thaibill.service`:
```ini
ExecStart=/opt/thaibill/venv/bin/gunicorn --workers=1 --threads=2 ...
```

จากนั้น:
```bash
sudo systemctl daemon-reload
sudo systemctl restart thaibill
```

---

<div align="center">

[← กลับไปหน้าหลัก](../README.md) · [คู่มือใช้งาน](USER_GUIDE.md) · [Docker](INSTALL_DOCKER.md)

</div>
