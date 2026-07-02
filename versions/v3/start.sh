#!/bin/bash
# ============================================================
# start.sh — Démarrage AnimeFR Bot v3
# ============================================================

echo "🚀 AnimeFR Bot v3 — Démarrage..."

# Créer les dossiers nécessaires
mkdir -p data logs backups

# Installer les dépendances
pip3 install -r requirements.txt --quiet

# Lancer le bot
python3 bot.py
