# ============================================================
# database.py — Base de données SQLite v4.0
# ============================================================

import sqlite3
import json
import shutil
import os
import glob
from datetime import datetime
from config import DB_PATH, BACKUP_DIR, MAX_BACKUPS

_pool = {}


def get_connection():
    """Connexion réutilisable par thread (pseudo-pool)."""
    tid = id(os.getpid())
    if tid not in _pool or _pool[tid] is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")  # 8 Mo cache
        _pool[tid] = conn
    return _pool[tid]


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ── Tables existantes (v3) ──
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY, username TEXT,
        role TEXT DEFAULT 'editeur', added_by INTEGER,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS animes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL, titre_original TEXT,
        synopsis TEXT, personnages TEXT, studio TEXT,
        date_sortie TEXT, nb_episodes TEXT, statut TEXT,
        genres TEXT, note TEXT, avis TEXT, image_url TEXT,
        lien_externe TEXT, categorie TEXT, tags TEXT DEFAULT '',
        mal_id INTEGER DEFAULT 0, message_id INTEGER,
        chat_id TEXT, template TEXT DEFAULT 'standard',
        posted_by INTEGER, posted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        modifie_par INTEGER, modifie_at TEXT,
        likes INTEGER DEFAULT 0, dislikes INTEGER DEFAULT 0,
        views INTEGER DEFAULT 0, trailer_url TEXT DEFAULT '',
        saison TEXT DEFAULT '', score_communaute REAL DEFAULT 0,
        nb_votes_communaute INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts_programmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_json TEXT NOT NULL, scheduled_at TEXT NOT NULL,
        created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        publie INTEGER DEFAULT 0, publie_at TEXT, erreur TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, action TEXT,
        details TEXT, level TEXT DEFAULT 'INFO',
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS blacklist (
        user_id INTEGER PRIMARY KEY, username TEXT,
        raison TEXT, added_by INTEGER,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS whitelist (
        user_id INTEGER PRIMARY KEY, username TEXT,
        added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS suivis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mal_id INTEGER NOT NULL, titre TEXT,
        dernier_ep INTEGER DEFAULT 0, actif INTEGER DEFAULT 1,
        added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER, user_id INTEGER, type TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(anime_id, user_id, type))""")

    c.execute("""CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, description TEXT,
        format_str TEXT NOT NULL, created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        is_default INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, posts INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0, commands INTEGER DEFAULT 0,
        errors INTEGER DEFAULT 0, UNIQUE(date))""")

    c.execute("""CREATE TABLE IF NOT EXISTS backup_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, size_bytes INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'ok')""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ── Nouvelles tables v4 ──

    c.execute("""CREATE TABLE IF NOT EXISTS favoris (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, anime_id INTEGER NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, anime_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, anime_id INTEGER NOT NULL,
        score REAL NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, anime_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS sondages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL, options TEXT NOT NULL,
        created_by INTEGER, message_id INTEGER,
        chat_id TEXT, actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS sondage_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sondage_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        option_idx INTEGER NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(sondage_id, user_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL, options TEXT NOT NULL,
        correct_idx INTEGER NOT NULL, explication TEXT,
        created_by INTEGER, message_id INTEGER,
        chat_id TEXT, actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        answer_idx INTEGER NOT NULL, correct INTEGER DEFAULT 0,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(quiz_id, user_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS calendrier (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_titre TEXT NOT NULL, jour TEXT NOT NULL,
        heure TEXT DEFAULT '', mal_id INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        total_likes INTEGER DEFAULT 0,
        total_quiz_correct INTEGER DEFAULT 0,
        total_quiz_total INTEGER DEFAULT 0,
        last_active TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ── Index pour performances ──
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_categorie ON animes(categorie)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_statut ON animes(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_likes ON animes(likes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_views ON animes(views DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_mal_id ON animes(mal_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_favoris_user ON favoris(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_votes_anime ON votes(anime_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ratings_anime ON user_ratings(anime_id)")

    _init_default_templates(c)
    conn.commit()
    print("✅ Base de données v4 initialisée.")


def _init_default_templates(cursor):
    defaults = [
        ("standard", "Format standard complet", "standard", 1),
        ("compact", "Format compact pour listes", "compact", 0),
        ("premium", "Format premium encadré", "premium", 0),
        ("minimal", "Format minimal épuré", "minimal", 0),
        ("neon", "Format neon cyberpunk", "neon", 0),
    ]
    for name, desc, fmt, is_def in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO templates (name, description, format_str, created_by, is_default) "
            "VALUES (?, ?, ?, 0, ?)", (name, desc, fmt, is_def))


# ═══════════════════════════════════════════════════════════
# ADMINS
# ═══════════════════════════════════════════════════════════

def add_admin(user_id, username, role, added_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO admins (user_id, username, role, added_by) VALUES (?,?,?,?)",
                 (user_id, username, role, added_by))
    conn.commit()

def remove_admin(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()

def get_admin(user_id):
    row = get_connection().execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else None

def get_all_admins():
    rows = get_connection().execute("SELECT * FROM admins ORDER BY role").fetchall()
    return [dict(r) for r in rows]

def is_admin(user_id):
    return get_admin(user_id) is not None

def get_role(user_id):
    a = get_admin(user_id)
    return a["role"] if a else None

def has_permission(user_id, permission):
    from config import PERMISSIONS
    role = get_role(user_id)
    return permission in PERMISSIONS.get(role, []) if role else False


# ═══════════════════════════════════════════════════════════
# ANIME
# ═══════════════════════════════════════════════════════════

def save_anime(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO animes (titre, titre_original, synopsis, personnages, studio,
        date_sortie, nb_episodes, statut, genres, note, avis, image_url,
        lien_externe, categorie, tags, mal_id, message_id, chat_id, template,
        posted_by, trailer_url, saison)
        VALUES (:titre, :titre_original, :synopsis, :personnages, :studio,
        :date_sortie, :nb_episodes, :statut, :genres, :note, :avis, :image_url,
        :lien_externe, :categorie, :tags, :mal_id, :message_id, :chat_id, :template,
        :posted_by, :trailer_url, :saison)""", data)
    aid = c.lastrowid
    conn.commit()
    increment_daily_stat("posts")
    return aid

def update_anime(anime_id, data: dict, modifie_par: int):
    conn = get_connection()
    data["id"] = anime_id
    data["modifie_par"] = modifie_par
    data["modifie_at"] = datetime.now().isoformat()
    conn.execute("""UPDATE animes SET titre=:titre, synopsis=:synopsis, personnages=:personnages,
        studio=:studio, date_sortie=:date_sortie, nb_episodes=:nb_episodes,
        statut=:statut, genres=:genres, note=:note, avis=:avis,
        image_url=:image_url, lien_externe=:lien_externe, categorie=:categorie,
        tags=:tags, template=:template, trailer_url=:trailer_url, saison=:saison,
        modifie_par=:modifie_par, modifie_at=:modifie_at WHERE id=:id""", data)
    conn.commit()

def delete_anime(anime_id):
    conn = get_connection()
    conn.execute("DELETE FROM animes WHERE id=?", (anime_id,))
    conn.execute("DELETE FROM favoris WHERE anime_id=?", (anime_id,))
    conn.execute("DELETE FROM user_ratings WHERE anime_id=?", (anime_id,))
    conn.execute("DELETE FROM votes WHERE anime_id=?", (anime_id,))
    conn.commit()

def get_anime(anime_id):
    row = get_connection().execute("SELECT * FROM animes WHERE id=?", (anime_id,)).fetchone()
    return dict(row) if row else None

def get_anime_by_mal(mal_id):
    row = get_connection().execute("SELECT * FROM animes WHERE mal_id=?", (mal_id,)).fetchone()
    return dict(row) if row else None

def get_all_animes():
    rows = get_connection().execute("SELECT * FROM animes ORDER BY posted_at DESC").fetchall()
    return [dict(r) for r in rows]

def get_animes_by_categorie(cat):
    rows = get_connection().execute(
        "SELECT * FROM animes WHERE categorie=? ORDER BY posted_at DESC", (cat,)).fetchall()
    return [dict(r) for r in rows]

def get_animes_by_tag(tag):
    rows = get_connection().execute(
        "SELECT * FROM animes WHERE tags LIKE ? ORDER BY posted_at DESC", (f"%{tag}%",)).fetchall()
    return [dict(r) for r in rows]

def search_animes_local(query):
    q = f"%{query}%"
    rows = get_connection().execute(
        "SELECT * FROM animes WHERE titre LIKE ? OR titre_original LIKE ? OR genres LIKE ? OR tags LIKE ? ORDER BY likes DESC LIMIT 20",
        (q, q, q, q)).fetchall()
    return [dict(r) for r in rows]

def get_animes_filtered(categorie=None, statut=None, min_note=None, sort_by="posted_at"):
    sql = "SELECT * FROM animes WHERE 1=1"
    params = []
    if categorie:
        sql += " AND categorie=?"
        params.append(categorie)
    if statut:
        sql += " AND statut=?"
        params.append(statut)
    if min_note:
        sql += " AND CAST(note AS REAL) >= ?"
        params.append(float(min_note))
    sort_map = {"likes": "likes DESC", "views": "views DESC", "note": "CAST(note AS REAL) DESC", "posted_at": "posted_at DESC"}
    sql += f" ORDER BY {sort_map.get(sort_by, 'posted_at DESC')} LIMIT 30"
    rows = get_connection().execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def update_message_id(anime_id, message_id, chat_id=None):
    conn = get_connection()
    if chat_id:
        conn.execute("UPDATE animes SET message_id=?, chat_id=? WHERE id=?", (message_id, str(chat_id), anime_id))
    else:
        conn.execute("UPDATE animes SET message_id=? WHERE id=?", (message_id, anime_id))
    conn.commit()

def add_like(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET likes=likes+1 WHERE id=?", (anime_id,))
    conn.commit()
    increment_daily_stat("likes")

def remove_like(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET likes=MAX(likes-1,0) WHERE id=?", (anime_id,))
    conn.commit()

def add_dislike(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET dislikes=dislikes+1 WHERE id=?", (anime_id,))
    conn.commit()

def add_view(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET views=views+1 WHERE id=?", (anime_id,))
    conn.commit()

def add_vote(anime_id, user_id, vote_type):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO votes (anime_id, user_id, type) VALUES (?,?,?)",
                     (anime_id, user_id, vote_type))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_vote(anime_id, user_id, vote_type):
    conn = get_connection()
    conn.execute("DELETE FROM votes WHERE anime_id=? AND user_id=? AND type=?",
                 (anime_id, user_id, vote_type))
    conn.commit()

def has_voted(anime_id, user_id, vote_type):
    row = get_connection().execute(
        "SELECT 1 FROM votes WHERE anime_id=? AND user_id=? AND type=?",
        (anime_id, user_id, vote_type)).fetchone()
    return row is not None

def get_top_liked(limit=10):
    rows = get_connection().execute("SELECT * FROM animes ORDER BY likes DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def get_top_viewed(limit=10):
    rows = get_connection().execute("SELECT * FROM animes ORDER BY views DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def get_top_rated(limit=10):
    rows = get_connection().execute(
        "SELECT * FROM animes WHERE score_communaute > 0 ORDER BY score_communaute DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# USER RATINGS (notes communautaires)
# ═══════════════════════════════════════════════════════════

def add_user_rating(user_id, anime_id, score):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO user_ratings (user_id, anime_id, score) VALUES (?,?,?)",
                     (user_id, anime_id, score))
    except sqlite3.IntegrityError:
        conn.execute("UPDATE user_ratings SET score=?, timestamp=? WHERE user_id=? AND anime_id=?",
                     (score, datetime.now().isoformat(), user_id, anime_id))
    conn.commit()
    _recalc_community_score(anime_id)

def _recalc_community_score(anime_id):
    conn = get_connection()
    row = conn.execute("SELECT AVG(score) as avg, COUNT(*) as cnt FROM user_ratings WHERE anime_id=?",
                       (anime_id,)).fetchone()
    if row:
        conn.execute("UPDATE animes SET score_communaute=?, nb_votes_communaute=? WHERE id=?",
                     (round(row[0] or 0, 2), row[1], anime_id))
        conn.commit()

def get_user_rating(user_id, anime_id):
    row = get_connection().execute(
        "SELECT score FROM user_ratings WHERE user_id=? AND anime_id=?",
        (user_id, anime_id)).fetchone()
    return row[0] if row else None


# ═══════════════════════════════════════════════════════════
# FAVORIS
# ═══════════════════════════════════════════════════════════

def add_favori(user_id, anime_id):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO favoris (user_id, anime_id) VALUES (?,?)", (user_id, anime_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_favori(user_id, anime_id):
    conn = get_connection()
    conn.execute("DELETE FROM favoris WHERE user_id=? AND anime_id=?", (user_id, anime_id))
    conn.commit()

def get_favoris(user_id):
    rows = get_connection().execute(
        "SELECT a.* FROM animes a JOIN favoris f ON a.id=f.anime_id WHERE f.user_id=? ORDER BY f.added_at DESC",
        (user_id,)).fetchall()
    return [dict(r) for r in rows]

def is_favori(user_id, anime_id):
    row = get_connection().execute(
        "SELECT 1 FROM favoris WHERE user_id=? AND anime_id=?", (user_id, anime_id)).fetchone()
    return row is not None

def count_favoris(anime_id):
    row = get_connection().execute(
        "SELECT COUNT(*) FROM favoris WHERE anime_id=?", (anime_id,)).fetchone()
    return row[0] if row else 0


# ═══════════════════════════════════════════════════════════
# SONDAGES
# ═══════════════════════════════════════════════════════════

def create_sondage(question, options, created_by, message_id=None, chat_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sondages (question, options, created_by, message_id, chat_id) VALUES (?,?,?,?,?)",
              (question, json.dumps(options, ensure_ascii=False), created_by, message_id, chat_id))
    sid = c.lastrowid
    conn.commit()
    return sid

def vote_sondage(sondage_id, user_id, option_idx):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO sondage_votes (sondage_id, user_id, option_idx) VALUES (?,?,?)",
                     (sondage_id, user_id, option_idx))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_sondage(sondage_id):
    row = get_connection().execute("SELECT * FROM sondages WHERE id=?", (sondage_id,)).fetchone()
    return dict(row) if row else None

def get_sondage_results(sondage_id):
    rows = get_connection().execute(
        "SELECT option_idx, COUNT(*) as cnt FROM sondage_votes WHERE sondage_id=? GROUP BY option_idx",
        (sondage_id,)).fetchall()
    return {r[0]: r[1] for r in rows}

def get_sondage_total_votes(sondage_id):
    row = get_connection().execute(
        "SELECT COUNT(*) FROM sondage_votes WHERE sondage_id=?", (sondage_id,)).fetchone()
    return row[0] if row else 0


# ═══════════════════════════════════════════════════════════
# QUIZ
# ═══════════════════════════════════════════════════════════

def create_quiz(question, options, correct_idx, explication, created_by):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO quiz (question, options, correct_idx, explication, created_by) VALUES (?,?,?,?,?)",
              (question, json.dumps(options, ensure_ascii=False), correct_idx, explication, created_by))
    qid = c.lastrowid
    conn.commit()
    return qid

def answer_quiz(quiz_id, user_id, answer_idx, correct):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO quiz_answers (quiz_id, user_id, answer_idx, correct) VALUES (?,?,?,?)",
                     (quiz_id, user_id, answer_idx, 1 if correct else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_quiz(quiz_id):
    row = get_connection().execute("SELECT * FROM quiz WHERE id=?", (quiz_id,)).fetchone()
    return dict(row) if row else None

def get_quiz_stats(quiz_id):
    row = get_connection().execute(
        "SELECT COUNT(*) as total, SUM(correct) as ok FROM quiz_answers WHERE quiz_id=?",
        (quiz_id,)).fetchone()
    return {"total": row[0] or 0, "correct": row[1] or 0}


# ═══════════════════════════════════════════════════════════
# CALENDRIER
# ═══════════════════════════════════════════════════════════

def add_calendrier(anime_titre, jour, heure="", mal_id=0, added_by=0):
    conn = get_connection()
    conn.execute("INSERT INTO calendrier (anime_titre, jour, heure, mal_id, added_by) VALUES (?,?,?,?,?)",
                 (anime_titre, jour, heure, mal_id, added_by))
    conn.commit()

def get_calendrier_jour(jour):
    rows = get_connection().execute(
        "SELECT * FROM calendrier WHERE jour=? AND actif=1 ORDER BY heure", (jour,)).fetchall()
    return [dict(r) for r in rows]

def get_calendrier_semaine():
    rows = get_connection().execute(
        "SELECT * FROM calendrier WHERE actif=1 ORDER BY CASE jour "
        "WHEN 'Lundi' THEN 1 WHEN 'Mardi' THEN 2 WHEN 'Mercredi' THEN 3 "
        "WHEN 'Jeudi' THEN 4 WHEN 'Vendredi' THEN 5 WHEN 'Samedi' THEN 6 "
        "WHEN 'Dimanche' THEN 7 END, heure").fetchall()
    return [dict(r) for r in rows]

def remove_calendrier(cal_id):
    conn = get_connection()
    conn.execute("DELETE FROM calendrier WHERE id=?", (cal_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# POSTS PROGRAMMÉS
# ═══════════════════════════════════════════════════════════

def save_post_programme(data_json, scheduled_at, created_by):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO posts_programmes (data_json, scheduled_at, created_by) VALUES (?,?,?)",
              (json.dumps(data_json, ensure_ascii=False), scheduled_at, created_by))
    pid = c.lastrowid
    conn.commit()
    return pid

def get_posts_programmes_dus():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = get_connection().execute(
        "SELECT * FROM posts_programmes WHERE publie=0 AND scheduled_at<=?", (now_str,)).fetchall()
    return [dict(r) for r in rows]

def mark_post_publie(post_id, erreur=None):
    conn = get_connection()
    conn.execute("UPDATE posts_programmes SET publie=1, publie_at=?, erreur=? WHERE id=?",
                 (datetime.now().isoformat(), erreur, post_id))
    conn.commit()

def delete_post_programme(post_id):
    conn = get_connection()
    conn.execute("DELETE FROM posts_programmes WHERE id=?", (post_id,))
    conn.commit()

def get_all_posts_programmes():
    rows = get_connection().execute(
        "SELECT * FROM posts_programmes ORDER BY scheduled_at DESC LIMIT 30").fetchall()
    return [dict(r) for r in rows]

def get_posts_programmes_pending():
    rows = get_connection().execute(
        "SELECT * FROM posts_programmes WHERE publie=0 ORDER BY scheduled_at").fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════

def add_log(user_id, username, action, details="", level="INFO"):
    conn = get_connection()
    conn.execute("INSERT INTO logs (user_id, username, action, details, level) VALUES (?,?,?,?,?)",
                 (user_id, username or "bot", action, details, level))
    conn.commit()

def get_logs(limit=50, level=None):
    conn = get_connection()
    if level:
        rows = conn.execute("SELECT * FROM logs WHERE level=? ORDER BY timestamp DESC LIMIT ?", (level, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def get_logs_by_user(user_id, limit=20):
    rows = get_connection().execute(
        "SELECT * FROM logs WHERE user_id=? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]

def clear_old_logs(days=30):
    conn = get_connection()
    conn.execute("DELETE FROM logs WHERE timestamp < datetime('now', ?)", (f"-{days} days",))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# BLACKLIST / WHITELIST
# ═══════════════════════════════════════════════════════════

def blacklist_user(user_id, username, raison, added_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO blacklist (user_id, username, raison, added_by) VALUES (?,?,?,?)",
                 (user_id, username, raison, added_by))
    conn.commit()

def unblacklist_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
    conn.commit()

def is_blacklisted(user_id):
    return get_connection().execute("SELECT 1 FROM blacklist WHERE user_id=?", (user_id,)).fetchone() is not None

def get_blacklist():
    rows = get_connection().execute("SELECT * FROM blacklist ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# SUIVIS
# ═══════════════════════════════════════════════════════════

def add_suivi(mal_id, titre, dernier_ep, added_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO suivis (mal_id, titre, dernier_ep, added_by) VALUES (?,?,?,?)",
                 (mal_id, titre, dernier_ep, added_by))
    conn.commit()

def get_suivis_actifs():
    rows = get_connection().execute("SELECT * FROM suivis WHERE actif=1").fetchall()
    return [dict(r) for r in rows]

def update_suivi_ep(mal_id, dernier_ep):
    conn = get_connection()
    conn.execute("UPDATE suivis SET dernier_ep=? WHERE mal_id=?", (dernier_ep, mal_id))
    conn.commit()

def remove_suivi(mal_id):
    conn = get_connection()
    conn.execute("DELETE FROM suivis WHERE mal_id=?", (mal_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════

def get_template(name):
    row = get_connection().execute("SELECT * FROM templates WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None

def get_all_templates():
    rows = get_connection().execute("SELECT * FROM templates ORDER BY is_default DESC, name").fetchall()
    return [dict(r) for r in rows]

def save_template(name, description, format_str, created_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO templates (name, description, format_str, created_by) VALUES (?,?,?,?)",
                 (name, description, format_str, created_by))
    conn.commit()

def delete_template(name):
    conn = get_connection()
    conn.execute("DELETE FROM templates WHERE name=? AND is_default=0", (name,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════

def get_setting(key, default=None):
    row = get_connection().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?,?,?)",
                 (key, str(value), datetime.now().isoformat()))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# DAILY STATS
# ═══════════════════════════════════════════════════════════

def increment_daily_stat(field):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        f"INSERT INTO daily_stats (date, {field}) VALUES (?, 1) "
        f"ON CONFLICT(date) DO UPDATE SET {field}={field}+1", (today,))
    conn.commit()

def get_daily_stats(days=7):
    rows = get_connection().execute(
        "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (days,)).fetchall()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_connection()
    return {
        "total_animes": conn.execute("SELECT COUNT(*) FROM animes").fetchone()[0],
        "total_admins": conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0],
        "posts_en_attente": conn.execute("SELECT COUNT(*) FROM posts_programmes WHERE publie=0").fetchone()[0],
        "total_logs": conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0],
        "total_likes": conn.execute("SELECT COALESCE(SUM(likes),0) FROM animes").fetchone()[0],
        "total_views": conn.execute("SELECT COALESCE(SUM(views),0) FROM animes").fetchone()[0],
        "total_suivis": conn.execute("SELECT COUNT(*) FROM suivis WHERE actif=1").fetchone()[0],
        "total_templates": conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0],
        "total_blacklisted": conn.execute("SELECT COUNT(*) FROM blacklist").fetchone()[0],
        "total_favoris": conn.execute("SELECT COUNT(*) FROM favoris").fetchone()[0],
        "total_sondages": conn.execute("SELECT COUNT(*) FROM sondages").fetchone()[0],
        "total_quiz": conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0],
    }


# ═══════════════════════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════════════════════

def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bf = os.path.join(BACKUP_DIR, f"animefr_backup_{ts}.db")
    try:
        shutil.copy2(DB_PATH, bf)
        size = os.path.getsize(bf)
        conn = get_connection()
        conn.execute("INSERT INTO backup_history (filename, size_bytes, status) VALUES (?,?,'ok')", (bf, size))
        conn.commit()
        _cleanup_old_backups()
        return bf, size
    except Exception as e:
        conn = get_connection()
        conn.execute("INSERT INTO backup_history (filename, size_bytes, status) VALUES (?,0,?)", (bf, str(e)))
        conn.commit()
        return None, 0

def _cleanup_old_backups():
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "animefr_backup_*.db")))
    while len(files) > MAX_BACKUPS:
        os.remove(files.pop(0))

def get_backup_history(limit=10):
    rows = get_connection().execute(
        "SELECT * FROM backup_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def restore_backup(backup_file):
    if not os.path.exists(backup_file):
        return False
    try:
        shutil.copy2(backup_file, DB_PATH)
        return True
    except Exception:
        return False
