# 🐳 คู่มือติดตั้ง EasyBill ด้วย Docker

> รันได้ทุก OS — Linux, macOS, Windows (ผ่าน Docker Desktop)

[← กลับไปหน้าหลัก](../README.md)

---

## 📑 สารบัญ

1. [สิ่งที่ต้องมี](#1-สิ่งที่ต้องมี)
2. [Quick Start (3 บรรทัด)](#2-quick-start-3-บรรทัด)
3. [Docker Compose (แนะนำ)](#3-docker-compose-แนะนำ)
4. [Build เอง](#4-build-เอง)
5. [Volumes (เก็บข้อมูล)](#5-volumes-เก็บข้อมูล)
6. [Production ด้วย Nginx + SSL](#6-production-ด้วย-nginx--ssl)
7. [Backup และ Restore](#7-backup-และ-restore)
8. [อัปเดต](#8-อัปเดต)
9. [แก้ปัญหา](#9-แก้ปัญหา)

---

## 1. สิ่งที่ต้องมี

- **Docker** 20.10+ → [Install Docker](https://docs.docker.com/engine/install/)
- **Docker Compose** v2+ (มากับ Docker Desktop)

### ติดตั้ง Docker บน Ubuntu

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# logout / login ใหม่
docker --version
docker compose version
```

---

## 2. Quick Start (3 บรรทัด)

```bash
git clone https://github.com/maxspeedcom/easybill.git
cd easybill
docker compose up -d
```

เสร็จ! เข้าใช้งานที่ http://localhost:8000

**Login ครั้งแรก:**
- Username: `admin`
- Password: `admin1234`

---

## 3. Docker Compose (แนะนำ)

### 3.1 Clone + ตั้งค่า

```bash
git clone https://github.com/maxspeedcom/easybill.git
cd easybill

# (ขั้นแนะนำ) สร้างไฟล์ .env กำหนด SECRET_KEY
cat > .env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
EOF
```

### 3.2 Build + Run

```bash
docker compose up -d --build
```

ตรวจสถานะ:
```bash
docker compose ps
```

ดู logs:
```bash
docker compose logs -f easybill
```

### 3.3 หยุด / รีสตาร์ท

```bash
docker compose stop          # หยุด
docker compose start         # เริ่ม
docker compose restart       # รีสตาร์ท
docker compose down          # หยุด + ลบ container (data ยังอยู่ใน volumes)
```

---

## 4. Build เอง

ถ้าไม่ใช้ compose:

```bash
# Build
docker build -t easybill:latest .

# Run
docker run -d \
  --name easybill \
  --restart unless-stopped \
  -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -v $(pwd)/data/instance:/app/instance \
  -v $(pwd)/data/uploads:/app/app/static/uploads \
  -v $(pwd)/data/logs:/app/logs \
  easybill:latest
```

---

## 5. Volumes (เก็บข้อมูล)

ข้อมูลถูกเก็บใน `./data/` ที่โฮสต์ — ปลอดภัยจากการลบ container

```
data/
├── instance/        ← SQLite database (thaibill.db)
├── uploads/         ← โลโก้, ลายเซ็น, ไฟล์แนบ
└── logs/            ← application logs
```

> ⚠️ **อย่าลบโฟลเดอร์ `data/`** = ข้อมูลทั้งหมดหาย

### Backup โฟลเดอร์ data

```bash
tar czf easybill-backup-$(date +%Y%m%d).tar.gz data/
```

### Restore

```bash
docker compose down
tar xzf easybill-backup-20251115.tar.gz
docker compose up -d
```

---

## 6. Production ด้วย Nginx + SSL

### 6.1 เพิ่ม nginx ใน compose

ใช้ profile `with-nginx`:

```bash
docker compose --profile with-nginx up -d
```

### 6.2 สร้าง nginx config

```bash
mkdir -p nginx/conf.d nginx/ssl
cat > nginx/conf.d/easybill.conf <<'EOF'
upstream easybill_app {
    server easybill:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://easybill_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF
```

### 6.3 SSL ด้วย Let's Encrypt (วิธีง่าย)

ถ้าโดเมนชี้มาที่เซิร์ฟเวอร์แล้ว:

```bash
# ติดตั้ง certbot บน host
sudo apt install -y certbot

# Stop nginx ใน docker ก่อน
docker compose stop nginx

# ออก cert (standalone mode)
sudo certbot certonly --standalone -d your-domain.com

# copy cert ไป nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/*.pem

# Start nginx อีกครั้ง
docker compose --profile with-nginx up -d
```

### 6.4 ทางเลือก: Cloudflare Tunnel (ไม่ต้อง SSL)

ถ้าใช้ Cloudflare Tunnel — เพิ่ม service ใน compose:

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token ${CF_TUNNEL_TOKEN}
    environment:
      CF_TUNNEL_TOKEN: ${CF_TUNNEL_TOKEN}
    depends_on:
      - easybill
```

ตั้ง `CF_TUNNEL_TOKEN` ใน `.env` แล้วชี้ tunnel ไปที่ `http://easybill:8000`

---

## 7. Backup และ Restore

### Backup อัตโนมัติด้วย cron + Docker

```bash
sudo crontab -e
```

เพิ่ม:
```cron
# Backup ทุกวันตอน 02:00
0 2 * * * cd /path/to/easybill && tar czf /backup/easybill-$(date +\%Y\%m\%d).tar.gz data/
0 3 * * * find /backup -name "easybill-*.tar.gz" -mtime +30 -delete
```

### Restore จาก backup

```bash
docker compose down
tar xzf /backup/easybill-20251115.tar.gz
docker compose up -d
```

---

## 8. อัปเดต

### Pull โค้ดใหม่ + rebuild

```bash
cd /path/to/easybill
git pull
docker compose up -d --build
```

Container ใหม่จะแทนที่ตัวเก่า แต่ data ใน volumes ยังอยู่ — migration script รันอัตโนมัติตอน start

### Rollback ถ้ามีปัญหา

```bash
git checkout <previous-commit>
docker compose up -d --build
```

---

## 9. แก้ปัญหา

### Container ไม่ start

```bash
docker compose logs easybill --tail 100
```

ปัญหาที่พบบ่อย:

**Port 8000 ใช้อยู่:**
```bash
# เปลี่ยน port ใน docker-compose.yml
ports:
  - "8001:8000"  # ใช้ 8001 บน host
```

**Permission denied บน volumes:**
```bash
sudo chown -R 1000:1000 data/
```

### เข้า shell ใน container เพื่อ debug

```bash
docker compose exec easybill bash
```

จากนั้นรันคำสั่ง Python:
```bash
python -c "from app import create_app; app = create_app('production'); print('OK')"
```

### Reset password admin

```bash
docker compose exec easybill python -c "
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

### ลบทุกอย่างเริ่มใหม่

```bash
docker compose down -v       # ลบ container + volumes (เสีย data!)
rm -rf data/                 # ลบโฟลเดอร์ data
docker rmi easybill:latest   # ลบ image
docker compose up -d --build # เริ่มใหม่
```

> ⚠️ **อันตราย** — ลบข้อมูลทั้งหมด ใช้เฉพาะตอน setup test environment

### PDF ภาษาไทยไม่ออก

ฟอนต์ไทย (Sarabun) อยู่ใน image แล้ว — ถ้ายังขึ้นกล่อง:

```bash
docker compose exec easybill fc-list | grep -i thai
# ถ้าว่าง → ตอน build ฟอนต์ไม่ติด → rebuild
docker compose up -d --build --force-recreate
```

---

<div align="center">

[← กลับไปหน้าหลัก](../README.md) · [คู่มือใช้งาน](USER_GUIDE.md) · [Ubuntu](INSTALL_UBUNTU.md)

</div>
