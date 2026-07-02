# ============================================================
# config.py — Configuration centrale AnimeFR Bot v4.0
# ============================================================

import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = "@animeFR2026"

# ── Base de données ──
DB_PATH = "data/animefr.db"

# ── Logs ──
LOG_PATH = "logs/bot.log"
LOG_MAX_SIZE = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# ── Backups ──
BACKUP_DIR = "backups"
BACKUP_INTERVAL = 86400
MAX_BACKUPS = 14

# ── API ──
JIKAN_BASE_URL = "https://api.jikan.moe/v4"
JIKAN_RATE_LIMIT = 0.4  # secondes entre requêtes

# ── Version ──
BOT_VERSION = "4.0"
BOT_NAME = "AnimeFR Bot"

# ── Maintenance ──
MAINTENANCE_MESSAGE = "🔧 Le bot est en maintenance. Revenez bientôt !"

# ── Rôles & Permissions ──
ROLES = {
    "superadmin": 0,
    "admin": 1,
    "moderateur": 2,
    "editeur": 3,
}

PERMISSIONS = {
    "superadmin": [
        "poster", "modifier", "supprimer", "programmer", "admin",
        "logs", "stats", "blacklist", "notif", "maintenance",
        "backup", "templates", "dashboard", "sondage", "quiz",
        "calendrier", "favoris", "compare",
    ],
    "admin": [
        "poster", "modifier", "supprimer", "programmer",
        "logs", "stats", "blacklist", "notif", "backup",
        "templates", "sondage", "quiz", "calendrier", "favoris", "compare",
    ],
    "moderateur": [
        "modifier", "supprimer", "logs", "stats", "sondage",
    ],
    "editeur": [
        "poster", "modifier", "programmer", "templates",
    ],
}

# ── Catégories ──
CATEGORIES = [
    "Action", "Aventure", "Romance", "Isekai", "Shonen", "Seinen",
    "Shojo", "Josei", "Comédie", "Drame", "Fantasy", "Horreur",
    "Mystère", "Sci-Fi", "Slice of Life", "Sport", "Surnaturel",
    "Psychologique", "Mecha", "Musique",
]

STATUTS = ["En cours", "Terminé", "À venir", "En pause"]
SAISONS = ["Hiver", "Printemps", "Été", "Automne"]

# ── Scheduler ──
SCHEDULER_INTERVAL = 30
EPISODE_CHECK_INTERVAL = 1800
CALENDAR_CHECK_INTERVAL = 3600

# ── Limites ──
MAX_SEARCH_RESULTS = 5
MAX_LIST_ITEMS = 20
MAX_QUIZ_OPTIONS = 4
MAX_FAVORITES = 50
MAX_POLL_OPTIONS = 10

# ── Visuels ──
VISUAL_THEME = {
    "separator":      "═══════════════════════",
    "separator_thin":  "───────────────────────",
    "separator_dots":  "• • • • • • • • • • • •",
    "separator_wave":  "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️",
    "corner_tl": "╔", "corner_tr": "╗",
    "corner_bl": "╚", "corner_br": "╝",
    "vertical": "║", "horizontal": "═",
    "star_full": "★", "star_empty": "☆",
    "bar_full": "█", "bar_mid": "▓", "bar_low": "░",
    "arrow": "➤", "diamond": "◆", "circle": "●",
    "fire": "🔥", "crown": "👑", "trophy": "🏆",
}

DEFAULT_TEMPLATES = {
    "standard": "standard",
    "compact": "compact",
    "premium": "premium",
    "minimal": "minimal",
    "neon": "neon",
}
