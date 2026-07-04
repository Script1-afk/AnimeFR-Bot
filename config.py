# ============================================================
# config.py — Configuration centrale AnimeFR Bot v6.1
# ============================================================

import os
import sys

# ── Chargement du fichier .env ──
def _load_env(filepath=".env"):
    """Charge les variables depuis le fichier .env"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filepath)
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    os.environ.setdefault(key, value)
        return True
    return False

_env_loaded = _load_env()

# ── Variables critiques (SANS valeurs par défaut) ──
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ── Validation au démarrage ──
def validate_config():
    """Vérifie que toutes les variables critiques sont configurées.
    Arrête le bot proprement si une variable manque."""
    errors = []

    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN manquant — Configurez-le dans .env ou en variable d'environnement")
    elif BOT_TOKEN in ("YOUR_BOT_TOKEN_HERE", "your_telegram_bot_token_here"):
        errors.append("❌ BOT_TOKEN contient encore la valeur placeholder — Remplacez-la par votre vrai token")
    elif ":" not in BOT_TOKEN:
        errors.append("❌ BOT_TOKEN semble invalide (format attendu : 123456789:ABCdefGHI...)")

    if not OPENAI_API_KEY:
        errors.append("⚠️  OPENAI_API_KEY manquante — Les fonctionnalités IA seront désactivées")
    elif OPENAI_API_KEY in ("YOUR_OPENAI_KEY_HERE", "your_openai_api_key_here"):
        errors.append("⚠️  OPENAI_API_KEY contient encore la valeur placeholder — Les fonctionnalités IA seront désactivées")

    # Afficher les erreurs
    if errors:
        print("\n╔══════════════════════════════════════════════════╗")
        print("║     ⚠️  ERREURS DE CONFIGURATION DÉTECTÉES      ║")
        print("╠══════════════════════════════════════════════════╣")
        for err in errors:
            print(f"║ {err}")
        print("╠══════════════════════════════════════════════════╣")
        if not _env_loaded:
            print("║ 💡 Fichier .env non trouvé !")
            print("║    Créez-le : cp .env.example .env")
            print("║    Puis remplissez vos clés.")
        print("╚══════════════════════════════════════════════════╝\n")

    # Erreur fatale si BOT_TOKEN manquant
    critical_errors = [e for e in errors if e.startswith("❌")]
    if critical_errors:
        print("🛑 Arrêt du bot — Corrigez les erreurs ci-dessus et relancez.")
        sys.exit(1)

    # Avertissements non-fatals (OpenAI optionnel)
    warnings = [e for e in errors if e.startswith("⚠️")]
    if warnings and not critical_errors:
        print("ℹ️  Le bot démarre avec des fonctionnalités réduites.\n")

    return len(critical_errors) == 0


# ── Détection si OpenAI est disponible ──
OPENAI_AVAILABLE = bool(OPENAI_API_KEY and OPENAI_API_KEY not in (
    "YOUR_OPENAI_KEY_HERE", "your_openai_api_key_here", ""
))

# ── Canal ──
CHANNEL_ID = "@animeFR2026"

# ── OpenAI ──
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
BOT_VERSION = "6.1"
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
AUTO_PUBLISH_INTERVAL = 3600

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
AUTO_PUBLISH_ENABLED = False
AUTO_PUBLISH_TEMPLATE = "premium"
AUTO_PUBLISH_SOURCE = "franime"
