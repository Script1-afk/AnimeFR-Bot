#!/bin/bash
# ============================================================
# start.sh — Démarrage AnimeFR Bot v4
# ============================================================

echo "🚀 AnimeFR Bot v4 — Démarrage..."

mkdir -p data logs backups media

pip3 install -r requirements.txt --quiet

python3 bot.py
