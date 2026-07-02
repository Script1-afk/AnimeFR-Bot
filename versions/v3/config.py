# ============================================================
# config.py — Configuration centrale AnimeFR Bot v3
# ============================================================

import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = "@animeFR2026"

# Base de données
DB_PATH = "data/animefr.db"

# Logs
LOG_PATH = "logs/bot.log"
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 Mo avant rotation
LOG_BACKUP_COUNT = 3

# Backups
BACKUP_DIR = "backups"
BACKUP_INTERVAL = 86400  # Backup auto toutes les 24h (en secondes)
MAX_BACKUPS = 7  # Garder les 7 derniers backups

# Jikan API
JIKAN_BASE_URL = "https://api.jikan.moe/v4"

# Version
BOT_VERSION = "3.0"
BOT_NAME = "AnimeFR Bot"

# Mode maintenance
MAINTENANCE_MODE = False
MAINTENANCE_MESSAGE = "🔧 Le bot est en maintenance. Revenez bientôt !"

# Rôles (du plus puissant au moins puissant)
ROLES = {
    "superadmin": 0,
    "admin": 1,
    "moderateur": 2,
    "editeur": 3,
}

# Permissions par rôle
PERMISSIONS = {
    "superadmin": [
        "poster", "modifier", "supprimer", "programmer", "admin",
        "logs", "stats", "blacklist", "notif", "maintenance",
        "backup", "templates", "dashboard"
    ],
    "admin": [
        "poster", "modifier", "supprimer", "programmer",
        "logs", "stats", "blacklist", "notif", "backup", "templates"
    ],
    "moderateur": [
        "modifier", "supprimer", "logs", "stats"
    ],
    "editeur": [
        "poster", "modifier", "programmer", "templates"
    ],
}

# Catégories
CATEGORIES = [
    "Action", "Aventure", "Romance", "Isekai", "Shonen", "Seinen",
    "Shojo", "Josei", "Comédie", "Drame", "Fantasy", "Horreur",
    "Mystère", "Sci-Fi", "Slice of Life", "Sport", "Surnaturel",
    "Psychologique", "Mecha", "Musique"
]

# Statuts
STATUTS = ["En cours", "Terminé", "À venir", "En pause"]

# Saisons
SAISONS = ["Hiver", "Printemps", "Été", "Automne"]

# Scheduler
SCHEDULER_INTERVAL = 30

# Limites
MAX_SEARCH_RESULTS = 5
MAX_LIST_ITEMS = 20

# Visuels — Emojis de décoration pour les posts
VISUAL_THEME = {
    "separator": "═══════════════════════",
    "separator_thin": "───────────────────────",
    "separator_dots": "• • • • • • • • • • • •",
    "corner_tl": "╔",
    "corner_tr": "╗",
    "corner_bl": "╚",
    "corner_br": "╝",
    "vertical": "║",
    "star_full": "★",
    "star_empty": "☆",
    "bar_full": "█",
    "bar_mid": "▓",
    "bar_low": "░",
    "arrow": "➤",
    "diamond": "◆",
    "circle": "●",
}

# Templates de posts par défaut
DEFAULT_TEMPLATES = {
    "standard": "standard",
    "compact": "compact",
    "premium": "premium",
    "minimal": "minimal",
}
