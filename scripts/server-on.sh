#!/bin/bash
# Menyalakan Human GVC sebagai server. Jalankan dari folder utama proyek: bash scripts/server-on.sh
set -e
cd "$(dirname "$0")/.."
mkdir -p logs
source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate human-gvc

if ! lsof -i :5432 >/dev/null 2>&1; then
  echo "PostgreSQL belum menyala di port 5432. Nyalakan dulu (Postgres.app / service Postgres), lalu jalankan ulang."; exit 1
fi

(cd backend && nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 \
  --proxy-headers --forwarded-allow-ips="127.0.0.1" > ../logs/backend.log 2>&1 &)
(cd frontend && npm run build > ../logs/build.log 2>&1 && nohup npm run start > ../logs/frontend.log 2>&1 &)

sleep 3
echo "Backend & frontend dinyalakan (log di folder logs/)."
echo "Sekarang nyalakan akses internet:  tailscale funnel 3000"
caffeinate -dimsu &   # cegah Mac tidur selama server hidup
echo $! > logs/caffeinate.pid
