#!/bin/bash
# ============================================================
# deploy_to_github.sh
# สคริปต์ push EasyBill ขึ้น GitHub (one-shot)
#
# วิธีใช้:
#   GITHUB_TOKEN="ghp_xxx" bash scripts/deploy_to_github.sh
#
# หรือกำหนดทั้งหมด:
#   GITHUB_USER=yourname \
#   REPO_NAME=easybill \
#   GITHUB_TOKEN="ghp_xxx" \
#   bash scripts/deploy_to_github.sh
# ============================================================

set -e  # exit on error

# ---------- Color helpers ----------
G='\033[0;32m'  # green
Y='\033[1;33m'  # yellow
R='\033[0;31m'  # red
B='\033[0;34m'  # blue
N='\033[0m'     # no color

echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${B}  📤 Deploy EasyBill → GitHub${N}"
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo

# ---------- Run from project root ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJ_DIR"

if [ ! -f "wsgi.py" ] || [ ! -d "app" ]; then
    echo -e "${R}❌ ต้องรันสคริปต์นี้จากโฟลเดอร์โปรเจกต์ EasyBill${N}"
    echo -e "   ปัจจุบันอยู่: $(pwd)"
    exit 1
fi

if [ ! -f ".gitignore" ]; then
    echo -e "${R}❌ ไม่พบ .gitignore — ระบบจะหยุดเพื่อกัน DB/uploads หลุดขึ้น GitHub${N}"
    exit 1
fi

# ---------- Get credentials ----------
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${Y}Personal Access Token จาก GitHub (ขึ้นต้นด้วย ghp_):${N}"
    read -rs GITHUB_TOKEN
    echo
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${R}❌ ต้องใส่ Token${N}"
    exit 1
fi

if [ -z "$GITHUB_USER" ]; then
    read -p "GitHub username: " GITHUB_USER
fi

if [ -z "$REPO_NAME" ]; then
    read -p "Repository name [easybill]: " REPO_NAME
    REPO_NAME=${REPO_NAME:-easybill}
fi

COMMIT_MSG="${COMMIT_MSG:-🎉 Initial commit: EasyBill v2.0}"

echo
echo -e "  ${B}User:${N}   $GITHUB_USER"
echo -e "  ${B}Repo:${N}   $REPO_NAME"
echo -e "  ${B}Token:${N}  ${GITHUB_TOKEN:0:7}...${GITHUB_TOKEN: -4}"
echo -e "  ${B}Msg:${N}    $COMMIT_MSG"
echo

read -p "ดำเนินการต่อ? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${Y}ยกเลิก${N}"
    exit 0
fi

# ---------- Install git if missing ----------
if ! command -v git &> /dev/null; then
    echo -e "${Y}📦 ติดตั้ง git...${N}"
    sudo apt update && sudo apt install -y git
fi

# ---------- Set git identity ----------
if [ -z "$(git config --global user.email)" ]; then
    git config --global user.email "${GITHUB_USER}@users.noreply.github.com"
    git config --global user.name "$GITHUB_USER"
    echo -e "${G}✓ ตั้ง git identity${N}"
fi

# ---------- Fix permissions (กรณีโฟลเดอร์เป็นของ thaibill user) ----------
if [ "$(stat -c %U .)" != "$USER" ]; then
    echo -e "${Y}🔧 เปลี่ยน owner ให้ user ปัจจุบัน...${N}"
    sudo chown -R "$USER:$USER" .
fi

# ---------- Init repo ----------
if [ ! -d ".git" ]; then
    echo -e "${G}🔧 git init...${N}"
    git init -b main 2>/dev/null || (git init && git checkout -b main 2>/dev/null || true)
else
    echo -e "${G}✓ git repo มีอยู่แล้ว${N}"
fi

# ---------- Configure remote (with token inline) ----------
REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
CLEAN_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

if git remote get-url origin &> /dev/null; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi
echo -e "${G}✓ ตั้ง remote origin${N}"

# ---------- Stage + commit ----------
echo -e "${B}📦 git add ...${N}"
git add .

# แสดงไฟล์ที่จะ commit (สั้น ๆ)
echo
echo -e "${B}ไฟล์ที่จะถูก push:${N}"
git diff --cached --stat | tail -20
echo

if git diff --cached --quiet; then
    echo -e "${Y}ℹ️  ไม่มีอะไรใหม่ — ข้าม commit${N}"
else
    git commit -m "$COMMIT_MSG"
    echo -e "${G}✓ commit สำเร็จ${N}"
fi

# ---------- Push ----------
echo
echo -e "${B}🚀 push to GitHub...${N}"
echo

git branch -M main 2>/dev/null || true

if git push -u origin main; then
    PUSH_OK=1
else
    PUSH_OK=0
fi

# ---------- Cleanup: remove token from remote ----------
git remote set-url origin "$CLEAN_URL"
echo -e "${G}✓ ลบ token ออกจาก git config แล้ว${N}"

echo
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
if [ "$PUSH_OK" = "1" ]; then
    echo -e "${G}✅ Push สำเร็จ!${N}"
    echo
    echo -e "  🌐 ดูได้ที่: ${B}https://github.com/${GITHUB_USER}/${REPO_NAME}${N}"
    echo
    echo -e "${Y}⚠️  สำคัญ — ทำต่อทันที:${N}"
    echo -e "  1. ${R}Revoke token นี้${N} ที่ ${B}https://github.com/settings/tokens${N}"
    echo -e "     (เพราะคุณส่งให้ผ่านแชต Claude ไปแล้ว → ถือว่า expose)"
    echo -e "  2. สร้าง token ใหม่ถ้าต้องใช้ push อีก"
    echo -e "  3. push ครั้งต่อไปใช้:"
    echo -e "     ${B}cd $PROJ_DIR && git add . && git commit -m 'msg' && git push${N}"
    echo -e "     (จะถามรหัสครั้งแรกแล้วจำไว้ — ใช้ \`git config --global credential.helper store\`)"
else
    echo -e "${R}❌ Push ไม่สำเร็จ${N}"
    echo
    echo -e "${Y}สาเหตุที่อาจเป็นไปได้:${N}"
    echo -e "  • Token ผิด / หมดอายุ → ตรวจที่ ${B}https://github.com/settings/tokens${N}"
    echo -e "  • Token ไม่มี scope ${B}repo${N} → สร้างใหม่พร้อม scope นี้"
    echo -e "  • ยังไม่ได้สร้าง repo บน GitHub → ไปสร้างที่ ${B}https://github.com/new${N}"
    echo -e "    (ชื่อ: ${B}${REPO_NAME}${N}, เลือก Private)"
    echo -e "  • Repo มีอยู่แล้วและมี commit ค้าง → ลอง ${B}git pull origin main --rebase${N} ก่อน push"
    exit 1
fi
echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
