# ============================================================
# config.py — Configuration centrale AnimeFR Bot v6.0
# ============================================================

import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = "@animeFR2026"

# ── OpenAI ──
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY_HERE")
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_MAX_TOKENS = 1500

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
JIKAN_RATE_LIMIT = 0.4

# ── Sources Anime (liens de visionnage) ──
ANIME_SOURCES = {
    "franime": "https://franime.fr/anime/{slug}",
    "anime_sama": "https://anime-sama.fr/catalogue/{slug}",
    "voiranime": "https://voiranime.com/anime/{slug}",
}
DEFAULT_SOURCE = "franime"

# ── Version ──
BOT_VERSION = "6.0"
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
        "calendrier", "favoris", "compare", "export", "import",
        "broadcast", "config", "purge", "autopublish", "ai",
    ],
    "admin": [
        "poster", "modifier", "supprimer", "programmer",
        "logs", "stats", "blacklist", "notif", "backup",
        "templates", "sondage", "quiz", "calendrier", "favoris",
        "compare", "export", "broadcast", "autopublish", "ai",
    ],
    "moderateur": [
        "modifier", "supprimer", "logs", "stats", "sondage",
        "broadcast",
    ],
    "editeur": [
        "poster", "modifier", "programmer", "templates", "ai",
    ],
}

# ── Catégories ──
CATEGORIES = [
    "Action", "Aventure", "Romance", "Isekai", "Shonen", "Seinen",
    "Shojo", "Josei", "Comédie", "Drame", "Fantasy", "Horreur",
    "Mystère", "Sci-Fi", "Slice of Life", "Sport", "Surnaturel",
    "Psychologique", "Mecha", "Musique", "Ecchi", "Thriller",
]

STATUTS = ["En cours", "Terminé", "À venir", "En pause", "Annulé"]
SAISONS = ["Hiver", "Printemps", "Été", "Automne"]

# ── Scheduler ──
SCHEDULER_INTERVAL = 30
EPISODE_CHECK_INTERVAL = 1800
CALENDAR_CHECK_INTERVAL = 3600
DAILY_STATS_HOUR = 22
WEEKLY_RECAP_DAY = 0
AUTO_PUBLISH_INTERVAL = 3600  # Vérifier les nouveaux épisodes toutes les heures

# ── Limites ──
MAX_SEARCH_RESULTS = 5
MAX_LIST_ITEMS = 20
MAX_QUIZ_OPTIONS = 4
MAX_FAVORITES = 100
MAX_POLL_OPTIONS = 10
MAX_BROADCAST_LENGTH = 4000

# ── Mobile / Affichage adaptatif ──
MOBILE_MODE = True
MOBILE_SYNOPSIS_LENGTH = 200
MOBILE_MAX_BUTTONS_ROW = 3
MOBILE_COMPACT_LISTS = True
MOBILE_SHORT_SEPARATORS = True

# ── Visuels ──
VISUAL_THEME = {
    "separator":       "━━━━━━━━━━━━━━━━━━━━━",
    "separator_thin":  "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─",
    "separator_dots":  "• • • • • • • • • • • •",
    "separator_wave":  "〰️〰️〰️〰️〰️〰️〰️〰️",
    "separator_short": "━━━━━━━━━━━━",
    "corner_tl": "┌", "corner_tr": "┐",
    "corner_bl": "└", "corner_br": "┘",
    "vertical": "│", "horizontal": "─",
    "star_full": "★", "star_empty": "☆",
    "bar_full": "█", "bar_mid": "▓", "bar_low": "░",
    "arrow": "➤", "diamond": "◆", "circle": "●",
    "fire": "🔥", "crown": "👑", "trophy": "🏆",
    "sparkle": "✦", "bolt": "⚡", "leaf": "🌿",
}

DEFAULT_TEMPLATES = {
    "standard": "standard",
    "compact": "compact",
    "premium": "premium",
    "minimal": "minimal",
    "neon": "neon",
    "mobile": "mobile",
    "elegant": "elegant",
}

# ── Export / Import ──
EXPORT_DIR = "data/exports"
IMPORT_DIR = "data/imports"

# ── Auto-Publish ──
AUTO_PUBLISH_ENABLED = False  # Activer via /autopublish
AUTO_PUBLISH_TEMPLATE = "premium"
AUTO_PUBLISH_SOURCE = "franime"
