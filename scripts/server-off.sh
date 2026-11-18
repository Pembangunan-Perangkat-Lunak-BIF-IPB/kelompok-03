#!/bin/bash
cd "$(dirname "$0")/.."
tailscale funnel reset 2>/dev/null
pkill -f "uvicorn app.main:app"
pkill -f "next start"
[ -f logs/caffeinate.pid ] && kill "$(cat logs/caffeinate.pid)" 2>/dev/null
echo "Server dimatikan."
