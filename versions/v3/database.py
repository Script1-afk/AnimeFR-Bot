# ============================================================
# database.py — Base de données SQLite v3
# ============================================================

import sqlite3
import json
import shutil
import os
import glob
from datetime import datetime
from config import DB_PATH, BACKUP_DIR, MAX_BACKUPS


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            role        TEXT DEFAULT 'editeur',
            added_by    INTEGER,
            added_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS animes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titre           TEXT NOT NULL,
            titre_original  TEXT,
            synopsis        TEXT,
            personnages     TEXT,
            studio          TEXT,
            date_sortie     TEXT,
            nb_episodes     TEXT,
            statut          TEXT,
            genres          TEXT,
            note            TEXT,
            avis            TEXT,
            image_url       TEXT,
            lien_externe    TEXT,
            categorie       TEXT,
            tags            TEXT DEFAULT '',
            mal_id          INTEGER DEFAULT 0,
            message_id      INTEGER,
            chat_id         TEXT,
            template        TEXT DEFAULT 'standard',
            posted_by       INTEGER,
            posted_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            modifie_par     INTEGER,
            modifie_at      TEXT,
            likes           INTEGER DEFAULT 0,
            dislikes        INTEGER DEFAULT 0,
            views           INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS posts_programmes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            data_json       TEXT NOT NULL,
            scheduled_at    TEXT NOT NULL,
            created_by      INTEGER,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            publie          INTEGER DEFAULT 0,
            publie_at       TEXT,
            erreur          TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT,
            action      TEXT,
            details     TEXT,
            level       TEXT DEFAULT 'INFO',
            timestamp   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            raison      TEXT,
            added_by    INTEGER,
            added_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            added_by    INTEGER,
            added_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS suivis (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mal_id      INTEGER NOT NULL,
            titre       TEXT,
            dernier_ep  INTEGER DEFAULT 0,
            actif       INTEGER DEFAULT 1,
            added_by    INTEGER,
            added_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id    INTEGER,
            user_id     INTEGER,
            type        TEXT,
            timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(anime_id, user_id, type)
        )
    """)

    # v3 : Templates personnalisés
    c.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            description TEXT,
            format_str  TEXT NOT NULL,
            created_by  INTEGER,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            is_default  INTEGER DEFAULT 0
        )
    """)

    # v3 : Statistiques journalières
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            posts       INTEGER DEFAULT 0,
            likes       INTEGER DEFAULT 0,
            commands    INTEGER DEFAULT 0,
            errors      INTEGER DEFAULT 0,
            UNIQUE(date)
        )
    """)

    # v3 : Historique des backups
    c.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            size_bytes  INTEGER,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            status      TEXT DEFAULT 'ok'
        )
    """)

    # v3 : Settings dynamiques (clé/valeur)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT PRIMARY KEY,
            value       TEXT,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insérer les templates par défaut s'ils n'existent pas
    _init_default_templates(c)

    conn.commit()
    conn.close()
    print("✅ Base de données v3 initialisée.")


def _init_default_templates(cursor):
    defaults = [
        ("standard", "Format standard avec tous les champs", "standard", 1),
        ("compact", "Format compact pour les listes", "compact", 0),
        ("premium", "Format premium avec encadré visuel", "premium", 0),
        ("minimal", "Format minimal épuré", "minimal", 0),
    ]
    for name, desc, fmt, is_def in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO templates (name, description, format_str, created_by, is_default) "
            "VALUES (?, ?, ?, 0, ?)",
            (name, desc, fmt, is_def)
        )


# ── ADMINS ──────────────────────────────────────────────────

def add_admin(user_id, username, role, added_by):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO admins (user_id, username, role, added_by) VALUES (?, ?, ?, ?)",
        (user_id, username, role, added_by)
    )
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_admin(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_admins():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM admins ORDER BY role").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def is_admin(user_id):
    return get_admin(user_id) is not None

def get_role(user_id):
    admin = get_admin(user_id)
    return admin["role"] if admin else None

def has_permission(user_id, permission):
    from config import PERMISSIONS
    role = get_role(user_id)
    if not role:
        return False
    return permission in PERMISSIONS.get(role, [])


# ── ANIME ────────────────────────────────────────────────────

def save_anime(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO animes (titre, titre_original, synopsis, personnages, studio,
            date_sortie, nb_episodes, statut, genres, note, avis, image_url,
            lien_externe, categorie, tags, mal_id, message_id, chat_id, template, posted_by)
        VALUES (:titre, :titre_original, :synopsis, :personnages, :studio,
            :date_sortie, :nb_episodes, :statut, :genres, :note, :avis, :image_url,
            :lien_externe, :categorie, :tags, :mal_id, :message_id, :chat_id, :template, :posted_by)
    """, data)
    anime_id = c.lastrowid
    conn.commit()
    conn.close()
    increment_daily_stat("posts")
    return anime_id

def update_anime(anime_id, data: dict, modifie_par: int):
    conn = get_connection()
    data["id"] = anime_id
    data["modifie_par"] = modifie_par
    data["modifie_at"] = datetime.now().isoformat()
    conn.execute("""
        UPDATE animes SET titre=:titre, synopsis=:synopsis, personnages=:personnages,
            studio=:studio, date_sortie=:date_sortie, nb_episodes=:nb_episodes,
            statut=:statut, genres=:genres, note=:note, avis=:avis,
            image_url=:image_url, lien_externe=:lien_externe, categorie=:categorie,
            tags=:tags, template=:template,
            modifie_par=:modifie_par, modifie_at=:modifie_at
        WHERE id=:id
    """, data)
    conn.commit()
    conn.close()

def delete_anime(anime_id):
    conn = get_connection()
    conn.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
    conn.commit()
    conn.close()

def get_anime(anime_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM animes WHERE id = ?", (anime_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_animes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM animes ORDER BY posted_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_animes_by_categorie(categorie):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM animes WHERE categorie = ? ORDER BY posted_at DESC", (categorie,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_animes_by_tag(tag):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM animes WHERE tags LIKE ? ORDER BY posted_at DESC", (f"%{tag}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_message_id(anime_id, message_id, chat_id=None):
    conn = get_connection()
    if chat_id:
        conn.execute(
            "UPDATE animes SET message_id = ?, chat_id = ? WHERE id = ?",
            (message_id, str(chat_id), anime_id)
        )
    else:
        conn.execute("UPDATE animes SET message_id = ? WHERE id = ?", (message_id, anime_id))
    conn.commit()
    conn.close()

def add_like(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET likes = likes + 1 WHERE id = ?", (anime_id,))
    conn.commit()
    conn.close()
    increment_daily_stat("likes")

def add_dislike(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET dislikes = dislikes + 1 WHERE id = ?", (anime_id,))
    conn.commit()
    conn.close()

def add_view(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET views = views + 1 WHERE id = ?", (anime_id,))
    conn.commit()
    conn.close()

def get_likes(anime_id):
    conn = get_connection()
    row = conn.execute("SELECT likes FROM animes WHERE id = ?", (anime_id,)).fetchone()
    conn.close()
    return row[0] if row else 0

def add_vote(anime_id, user_id, vote_type):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO votes (anime_id, user_id, type) VALUES (?, ?, ?)",
            (anime_id, user_id, vote_type)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def remove_vote(anime_id, user_id, vote_type):
    conn = get_connection()
    conn.execute(
        "DELETE FROM votes WHERE anime_id = ? AND user_id = ? AND type = ?",
        (anime_id, user_id, vote_type)
    )
    conn.commit()
    conn.close()

def get_top_liked(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM animes ORDER BY likes DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_top_viewed(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM animes ORDER BY views DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── POSTS PROGRAMMÉS ─────────────────────────────────────────

def save_post_programme(data_json: dict, scheduled_at: str, created_by: int) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO posts_programmes (data_json, scheduled_at, created_by) VALUES (?, ?, ?)",
        (json.dumps(data_json, ensure_ascii=False), scheduled_at, created_by)
    )
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_posts_programmes_dus():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM posts_programmes WHERE publie = 0 AND scheduled_at <= ?",
        (now_str,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_post_publie(post_id: int, erreur: str = None):
    conn = get_connection()
    conn.execute(
        "UPDATE posts_programmes SET publie = 1, publie_at = ?, erreur = ? WHERE id = ?",
        (datetime.now().isoformat(), erreur, post_id)
    )
    conn.commit()
    conn.close()

def delete_post_programme(post_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM posts_programmes WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def get_all_posts_programmes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM posts_programmes ORDER BY scheduled_at DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_posts_programmes_pending():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM posts_programmes WHERE publie = 0 ORDER BY scheduled_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── LOGS ─────────────────────────────────────────────────────

def add_log(user_id, username, action, details="", level="INFO"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO logs (user_id, username, action, details, level) VALUES (?, ?, ?, ?, ?)",
        (user_id, username or "bot", action, details, level)
    )
    conn.commit()
    conn.close()

def get_logs(limit=50, level=None):
    conn = get_connection()
    if level:
        rows = conn.execute(
            "SELECT * FROM logs WHERE level = ? ORDER BY timestamp DESC LIMIT ?", (level, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_logs_by_user(user_id, limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_logs_by_action(action, limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM logs WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
        (action, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_old_logs(days=30):
    conn = get_connection()
    conn.execute(
        "DELETE FROM logs WHERE timestamp < datetime('now', ?)", (f"-{days} days",)
    )
    conn.commit()
    conn.close()


# ── BLACKLIST / WHITELIST ────────────────────────────────────

def blacklist_user(user_id, username, raison, added_by):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO blacklist (user_id, username, raison, added_by) VALUES (?, ?, ?, ?)",
        (user_id, username, raison, added_by)
    )
    conn.commit()
    conn.close()

def unblacklist_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_blacklisted(user_id):
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None

def is_whitelisted(user_id):
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None

def get_blacklist():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM blacklist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SUIVIS ───────────────────────────────────────────────────

def add_suivi(mal_id, titre, dernier_ep, added_by):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO suivis (mal_id, titre, dernier_ep, added_by) VALUES (?, ?, ?, ?)",
        (mal_id, titre, dernier_ep, added_by)
    )
    conn.commit()
    conn.close()

def get_suivis_actifs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM suivis WHERE actif = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_suivi_ep(mal_id, dernier_ep):
    conn = get_connection()
    conn.execute("UPDATE suivis SET dernier_ep = ? WHERE mal_id = ?", (dernier_ep, mal_id))
    conn.commit()
    conn.close()

def remove_suivi(mal_id):
    conn = get_connection()
    conn.execute("DELETE FROM suivis WHERE mal_id = ?", (mal_id,))
    conn.commit()
    conn.close()


# ── TEMPLATES ────────────────────────────────────────────────

def get_template(name):
    conn = get_connection()
    row = conn.execute("SELECT * FROM templates WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_templates():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM templates ORDER BY is_default DESC, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_template(name, description, format_str, created_by):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO templates (name, description, format_str, created_by) VALUES (?, ?, ?, ?)",
        (name, description, format_str, created_by)
    )
    conn.commit()
    conn.close()

def delete_template(name):
    conn = get_connection()
    conn.execute("DELETE FROM templates WHERE name = ? AND is_default = 0", (name,))
    conn.commit()
    conn.close()


# ── SETTINGS ─────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, str(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ── DAILY STATS ──────────────────────────────────────────────

def increment_daily_stat(field):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        f"INSERT INTO daily_stats (date, {field}) VALUES (?, 1) "
        f"ON CONFLICT(date) DO UPDATE SET {field} = {field} + 1",
        (today,)
    )
    conn.commit()
    conn.close()

def get_daily_stats(days=7):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (days,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_connection()
    total_animes = conn.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    total_admins = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    posts_en_attente = conn.execute(
        "SELECT COUNT(*) FROM posts_programmes WHERE publie = 0"
    ).fetchone()[0]
    total_logs = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    total_likes = conn.execute("SELECT SUM(likes) FROM animes").fetchone()[0] or 0
    total_views = conn.execute("SELECT SUM(views) FROM animes").fetchone()[0] or 0
    total_suivis = conn.execute("SELECT COUNT(*) FROM suivis WHERE actif = 1").fetchone()[0]
    total_templates = conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
    total_blacklisted = conn.execute("SELECT COUNT(*) FROM blacklist").fetchone()[0]
    conn.close()
    return {
        "total_animes": total_animes,
        "total_admins": total_admins,
        "posts_en_attente": posts_en_attente,
        "total_logs": total_logs,
        "total_likes": total_likes,
        "total_views": total_views,
        "total_suivis": total_suivis,
        "total_templates": total_templates,
        "total_blacklisted": total_blacklisted,
    }


# ── BACKUP ───────────────────────────────────────────────────

def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"animefr_backup_{timestamp}.db")
    try:
        shutil.copy2(DB_PATH, backup_file)
        size = os.path.getsize(backup_file)
        conn = get_connection()
        conn.execute(
            "INSERT INTO backup_history (filename, size_bytes, status) VALUES (?, ?, 'ok')",
            (backup_file, size)
        )
        conn.commit()
        conn.close()
        _cleanup_old_backups()
        return backup_file, size
    except Exception as e:
        conn = get_connection()
        conn.execute(
            "INSERT INTO backup_history (filename, size_bytes, status) VALUES (?, 0, ?)",
            (backup_file, str(e))
        )
        conn.commit()
        conn.close()
        return None, 0

def _cleanup_old_backups():
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "animefr_backup_*.db")))
    while len(files) > MAX_BACKUPS:
        os.remove(files.pop(0))

def get_backup_history(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM backup_history ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def restore_backup(backup_file):
    if not os.path.exists(backup_file):
        return False
    try:
        shutil.copy2(backup_file, DB_PATH)
        return True
    except Exception:
        return False
