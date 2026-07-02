# ============================================================
# database.py — Base de données SQLite v5.0
# ============================================================

import sqlite3
import json
import shutil
import os
import glob
from datetime import datetime, timedelta
from config import DB_PATH, BACKUP_DIR, MAX_BACKUPS, EXPORT_DIR, IMPORT_DIR

_pool = {}


def get_connection():
    """Connexion réutilisable par thread (pseudo-pool)."""
    tid = id(os.getpid())
    if tid not in _pool or _pool[tid] is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")
        _pool[tid] = conn
    return _pool[tid]


def init_db():
    conn = get_connection()
    c = conn.cursor()

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
        nb_votes_communaute INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts_programmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_json TEXT NOT NULL, scheduled_at TEXT NOT NULL,
        created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        publie INTEGER DEFAULT 0, publie_at TEXT, erreur TEXT,
        repeat_mode TEXT DEFAULT 'none',
        repeat_until TEXT)""")

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
        anime_id INTEGER, user_id INTEGER,
        vote_type TEXT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(anime_id, user_id, vote_type))""")

    c.execute("""CREATE TABLE IF NOT EXISTS templates (
        name TEXT PRIMARY KEY, description TEXT,
        is_default INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_stats (
        date TEXT PRIMARY KEY, posts INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
        new_followers INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS backup_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, size INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS favoris (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, anime_id INTEGER,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, anime_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, anime_id INTEGER,
        score INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, anime_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS sondages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT, options_json TEXT,
        created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        message_id INTEGER, chat_id TEXT, closed INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS sondage_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sondage_id INTEGER, user_id INTEGER, option_idx INTEGER,
        UNIQUE(sondage_id, user_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT, options_json TEXT, correct_idx INTEGER,
        explication TEXT, created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        message_id INTEGER, chat_id TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER, user_id INTEGER, answer_idx INTEGER,
        is_correct INTEGER, UNIQUE(quiz_id, user_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS calendrier (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_titre TEXT, mal_id INTEGER DEFAULT 0,
        jour TEXT, heure TEXT, actif INTEGER DEFAULT 1,
        added_by INTEGER, added_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY, username TEXT,
        first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT, total_interactions INTEGER DEFAULT 0,
        preferred_categories TEXT DEFAULT '',
        language TEXT DEFAULT 'fr')""")

    # v5 : Broadcasts
    c.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL, sent_by INTEGER,
        sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
        target TEXT DEFAULT 'all')""")

    # v5 : Historique des modifications
    c.execute("""CREATE TABLE IF NOT EXISTS edit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER, field TEXT, old_value TEXT,
        new_value TEXT, edited_by INTEGER,
        edited_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # v5 : Sessions admin (pour multi-device)
    c.execute("""CREATE TABLE IF NOT EXISTS admin_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, device_info TEXT,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT, is_active INTEGER DEFAULT 1)""")

    # ── Index pour performances ──
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_categorie ON animes(categorie)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_statut ON animes(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_likes ON animes(likes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_views ON animes(views DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_mal ON animes(mal_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_posted ON animes(posted_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_score ON animes(score_communaute DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_animes_priority ON animes(priority DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(timestamp DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_favoris_user ON favoris(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_votes_anime ON votes(anime_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ratings_anime ON user_ratings(anime_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_edit_history ON edit_history(anime_id)")

    conn.commit()
    _init_default_templates(c, conn)
    print("✅ Base de données v5 initialisée.")


def _init_default_templates(c, conn):
    defaults = [
        ("standard", "Format classique complet"),
        ("compact", "Format court, synopsis tronqué"),
        ("premium", "Encadré avec bordures"),
        ("minimal", "Ultra-épuré"),
        ("neon", "Style cyberpunk"),
        ("mobile", "Optimisé petit écran"),
        ("elegant", "Style épuré et raffiné"),
    ]
    for name, desc in defaults:
        c.execute("INSERT OR IGNORE INTO templates (name, description, is_default) VALUES (?, ?, 1)", (name, desc))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# ADMINS
# ═══════════════════════════════════════════════════════════

def add_admin(user_id, username, role, added_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO admins (user_id, username, role, added_by) VALUES (?, ?, ?, ?)",
                 (user_id, username, role, added_by))
    conn.commit()

def remove_admin(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()

def get_admin(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None

def get_all_admins():
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM admins ORDER BY role").fetchall()]


# ═══════════════════════════════════════════════════════════
# ANIMES
# ═══════════════════════════════════════════════════════════

def save_anime(data):
    conn = get_connection()
    c = conn.execute("""INSERT INTO animes (titre, titre_original, synopsis, personnages,
        studio, date_sortie, nb_episodes, statut, genres, note, avis, image_url,
        lien_externe, categorie, tags, mal_id, message_id, chat_id, template,
        posted_by, trailer_url, saison, priority)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("titre"), data.get("titre_original"), data.get("synopsis"),
         data.get("personnages"), data.get("studio"), data.get("date_sortie"),
         data.get("nb_episodes"), data.get("statut"), data.get("genres"),
         data.get("note"), data.get("avis"), data.get("image_url"),
         data.get("lien_externe"), data.get("categorie"), data.get("tags", ""),
         data.get("mal_id", 0), data.get("message_id"), data.get("chat_id"),
         data.get("template", "standard"), data.get("posted_by"),
         data.get("trailer_url", ""), data.get("saison", ""),
         data.get("priority", 0)))
    conn.commit()
    return c.lastrowid

def update_anime(anime_id, field, value, edited_by=None):
    conn = get_connection()
    # Sauvegarder l'historique
    old = conn.execute(f"SELECT {field} FROM animes WHERE id = ?", (anime_id,)).fetchone()
    if old:
        old_val = old[0] if old else ""
        conn.execute("INSERT INTO edit_history (anime_id, field, old_value, new_value, edited_by) VALUES (?,?,?,?,?)",
                     (anime_id, field, str(old_val), str(value), edited_by))
    conn.execute(f"UPDATE animes SET {field} = ?, modifie_par = ?, modifie_at = ? WHERE id = ?",
                 (value, edited_by, datetime.now().isoformat(), anime_id))
    conn.commit()

def delete_anime(anime_id):
    conn = get_connection()
    conn.execute("DELETE FROM animes WHERE id = ?", (anime_id,))
    conn.execute("DELETE FROM favoris WHERE anime_id = ?", (anime_id,))
    conn.execute("DELETE FROM user_ratings WHERE anime_id = ?", (anime_id,))
    conn.execute("DELETE FROM votes WHERE anime_id = ?", (anime_id,))
    conn.execute("DELETE FROM edit_history WHERE anime_id = ?", (anime_id,))
    conn.commit()

def get_anime(anime_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM animes WHERE id = ?", (anime_id,)).fetchone()
    return dict(row) if row else None

def get_anime_by_message(message_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM animes WHERE message_id = ?", (message_id,)).fetchone()
    return dict(row) if row else None

def get_all_animes(limit=50, offset=0):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM animes ORDER BY posted_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()]

def get_animes_by_categorie(cat, limit=20):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM animes WHERE categorie = ? ORDER BY posted_at DESC LIMIT ?", (cat, limit)).fetchall()]

def search_animes_local(query, limit=10):
    conn = get_connection()
    q = f"%{query}%"
    return [dict(r) for r in conn.execute(
        """SELECT * FROM animes WHERE titre LIKE ? OR titre_original LIKE ?
        OR genres LIKE ? OR tags LIKE ? ORDER BY likes DESC LIMIT ?""",
        (q, q, q, q, limit)).fetchall()]

def filter_animes(categorie=None, statut=None, note_min=None, sort_by="likes", limit=20):
    conn = get_connection()
    conditions, params = [], []
    if categorie:
        conditions.append("categorie = ?")
        params.append(categorie)
    if statut:
        conditions.append("statut = ?")
        params.append(statut)
    if note_min:
        conditions.append("CAST(note AS REAL) >= ?")
        params.append(float(note_min))
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sort_map = {"likes": "likes DESC", "views": "views DESC", "note": "CAST(note AS REAL) DESC",
                "date": "posted_at DESC", "communaute": "score_communaute DESC"}
    order = sort_map.get(sort_by, "likes DESC")
    params.append(limit)
    return [dict(r) for r in conn.execute(
        f"SELECT * FROM animes {where} ORDER BY {order} LIMIT ?", params).fetchall()]

def get_top_animes(sort_by="likes", limit=10):
    conn = get_connection()
    sort_map = {"likes": "likes DESC", "views": "views DESC",
                "communaute": "score_communaute DESC", "date": "posted_at DESC"}
    order = sort_map.get(sort_by, "likes DESC")
    return [dict(r) for r in conn.execute(
        f"SELECT * FROM animes ORDER BY {order} LIMIT ?", (limit,)).fetchall()]

def get_pinned_animes():
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM animes WHERE is_pinned = 1 ORDER BY priority DESC").fetchall()]

def pin_anime(anime_id, priority=1):
    conn = get_connection()
    conn.execute("UPDATE animes SET is_pinned = 1, priority = ? WHERE id = ?", (priority, anime_id))
    conn.commit()

def unpin_anime(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET is_pinned = 0, priority = 0 WHERE id = ?", (anime_id,))
    conn.commit()

def get_anime_edit_history(anime_id, limit=10):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM edit_history WHERE anime_id = ? ORDER BY edited_at DESC LIMIT ?",
        (anime_id, limit)).fetchall()]


# ═══════════════════════════════════════════════════════════
# VOTES & LIKES
# ═══════════════════════════════════════════════════════════

def toggle_vote(anime_id, user_id, vote_type):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM votes WHERE anime_id = ? AND user_id = ? AND vote_type = ?",
                            (anime_id, user_id, vote_type)).fetchone()
    if existing:
        conn.execute("DELETE FROM votes WHERE id = ?", (existing[0],))
        if vote_type == "like":
            conn.execute("UPDATE animes SET likes = MAX(0, likes - 1) WHERE id = ?", (anime_id,))
        else:
            conn.execute("UPDATE animes SET dislikes = MAX(0, dislikes - 1) WHERE id = ?", (anime_id,))
        conn.commit()
        return False
    else:
        # Retirer le vote opposé si existe
        opposite = "dislike" if vote_type == "like" else "like"
        opp_existing = conn.execute("SELECT id FROM votes WHERE anime_id = ? AND user_id = ? AND vote_type = ?",
                                    (anime_id, user_id, opposite)).fetchone()
        if opp_existing:
            conn.execute("DELETE FROM votes WHERE id = ?", (opp_existing[0],))
            if opposite == "like":
                conn.execute("UPDATE animes SET likes = MAX(0, likes - 1) WHERE id = ?", (anime_id,))
            else:
                conn.execute("UPDATE animes SET dislikes = MAX(0, dislikes - 1) WHERE id = ?", (anime_id,))
        conn.execute("INSERT INTO votes (anime_id, user_id, vote_type) VALUES (?, ?, ?)",
                     (anime_id, user_id, vote_type))
        if vote_type == "like":
            conn.execute("UPDATE animes SET likes = likes + 1 WHERE id = ?", (anime_id,))
        else:
            conn.execute("UPDATE animes SET dislikes = dislikes + 1 WHERE id = ?", (anime_id,))
        conn.commit()
        return True

def increment_views(anime_id):
    conn = get_connection()
    conn.execute("UPDATE animes SET views = views + 1 WHERE id = ?", (anime_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# FAVORIS
# ═══════════════════════════════════════════════════════════

def add_favori(user_id, anime_id):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO favoris (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_favori(user_id, anime_id):
    conn = get_connection()
    conn.execute("DELETE FROM favoris WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
    conn.commit()

def is_favori(user_id, anime_id):
    conn = get_connection()
    return conn.execute("SELECT 1 FROM favoris WHERE user_id = ? AND anime_id = ?",
                        (user_id, anime_id)).fetchone() is not None

def get_favoris(user_id, limit=50):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        """SELECT a.* FROM animes a JOIN favoris f ON a.id = f.anime_id
        WHERE f.user_id = ? ORDER BY f.added_at DESC LIMIT ?""", (user_id, limit)).fetchall()]

def count_favoris(anime_id):
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM favoris WHERE anime_id = ?", (anime_id,)).fetchone()
    return row[0] if row else 0


# ═══════════════════════════════════════════════════════════
# RATINGS COMMUNAUTÉ
# ═══════════════════════════════════════════════════════════

def rate_anime(user_id, anime_id, score):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO user_ratings (user_id, anime_id, score) VALUES (?, ?, ?)",
                 (user_id, anime_id, score))
    # Recalculer la moyenne
    row = conn.execute("SELECT AVG(score), COUNT(*) FROM user_ratings WHERE anime_id = ?",
                       (anime_id,)).fetchone()
    avg_score = round(row[0], 1) if row[0] else 0
    nb_votes = row[1] if row[1] else 0
    conn.execute("UPDATE animes SET score_communaute = ?, nb_votes_communaute = ? WHERE id = ?",
                 (avg_score, nb_votes, anime_id))
    conn.commit()
    return avg_score, nb_votes

def get_user_rating(user_id, anime_id):
    conn = get_connection()
    row = conn.execute("SELECT score FROM user_ratings WHERE user_id = ? AND anime_id = ?",
                       (user_id, anime_id)).fetchone()
    return row[0] if row else None


# ═══════════════════════════════════════════════════════════
# SONDAGES
# ═══════════════════════════════════════════════════════════

def create_sondage(question, options, created_by, message_id=None, chat_id=None):
    conn = get_connection()
    c = conn.execute("INSERT INTO sondages (question, options_json, created_by, message_id, chat_id) VALUES (?,?,?,?,?)",
                     (question, json.dumps(options), created_by, message_id, chat_id))
    conn.commit()
    return c.lastrowid

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
    conn = get_connection()
    row = conn.execute("SELECT * FROM sondages WHERE id = ?", (sondage_id,)).fetchone()
    return dict(row) if row else None

def get_sondage_results(sondage_id):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT option_idx, COUNT(*) as cnt FROM sondage_votes WHERE sondage_id = ? GROUP BY option_idx",
        (sondage_id,)).fetchall()]

def close_sondage(sondage_id):
    conn = get_connection()
    conn.execute("UPDATE sondages SET closed = 1 WHERE id = ?", (sondage_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# QUIZ
# ═══════════════════════════════════════════════════════════

def create_quiz(question, options, correct_idx, explication, created_by):
    conn = get_connection()
    c = conn.execute(
        "INSERT INTO quiz (question, options_json, correct_idx, explication, created_by) VALUES (?,?,?,?,?)",
        (question, json.dumps(options), correct_idx, explication, created_by))
    conn.commit()
    return c.lastrowid

def answer_quiz(quiz_id, user_id, answer_idx):
    conn = get_connection()
    quiz = conn.execute("SELECT correct_idx FROM quiz WHERE id = ?", (quiz_id,)).fetchone()
    if not quiz:
        return None
    is_correct = 1 if answer_idx == quiz[0] else 0
    try:
        conn.execute("INSERT INTO quiz_answers (quiz_id, user_id, answer_idx, is_correct) VALUES (?,?,?,?)",
                     (quiz_id, user_id, answer_idx, is_correct))
        conn.commit()
        return bool(is_correct)
    except sqlite3.IntegrityError:
        return None

def get_quiz(quiz_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,)).fetchone()
    return dict(row) if row else None

def get_quiz_stats(quiz_id):
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM quiz_answers WHERE quiz_id = ?", (quiz_id,)).fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM quiz_answers WHERE quiz_id = ? AND is_correct = 1",
                           (quiz_id,)).fetchone()[0]
    return {"total": total, "correct": correct, "rate": round(correct / total * 100, 1) if total > 0 else 0}


# ═══════════════════════════════════════════════════════════
# CALENDRIER
# ═══════════════════════════════════════════════════════════

def add_calendrier(anime_titre, jour, heure, mal_id=0, added_by=None):
    conn = get_connection()
    c = conn.execute("INSERT INTO calendrier (anime_titre, mal_id, jour, heure, added_by) VALUES (?,?,?,?,?)",
                     (anime_titre, mal_id, jour, heure, added_by))
    conn.commit()
    return c.lastrowid

def get_calendrier_semaine():
    conn = get_connection()
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    result = {}
    for jour in jours:
        entries = conn.execute("SELECT * FROM calendrier WHERE jour = ? AND actif = 1 ORDER BY heure",
                               (jour,)).fetchall()
        result[jour] = [dict(e) for e in entries]
    return result

def remove_calendrier(cal_id):
    conn = get_connection()
    conn.execute("DELETE FROM calendrier WHERE id = ?", (cal_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# POSTS PROGRAMMÉS
# ═══════════════════════════════════════════════════════════

def add_post_programme(data_json, scheduled_at, created_by, repeat_mode="none", repeat_until=None):
    conn = get_connection()
    c = conn.execute(
        "INSERT INTO posts_programmes (data_json, scheduled_at, created_by, repeat_mode, repeat_until) VALUES (?,?,?,?,?)",
        (json.dumps(data_json), scheduled_at, created_by, repeat_mode, repeat_until))
    conn.commit()
    return c.lastrowid

def get_posts_programmes_dus():
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return [dict(r) for r in conn.execute(
        "SELECT * FROM posts_programmes WHERE publie = 0 AND scheduled_at <= ?", (now,)).fetchall()]

def mark_post_publie(post_id, erreur=None):
    conn = get_connection()
    conn.execute("UPDATE posts_programmes SET publie = 1, publie_at = ?, erreur = ? WHERE id = ?",
                 (datetime.now().isoformat(), erreur, post_id))
    conn.commit()

def get_posts_programmes(limit=20):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM posts_programmes ORDER BY scheduled_at DESC LIMIT ?", (limit,)).fetchall()]

def delete_post_programme(post_id):
    conn = get_connection()
    conn.execute("DELETE FROM posts_programmes WHERE id = ?", (post_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# SUIVIS
# ═══════════════════════════════════════════════════════════

def add_suivi(mal_id, titre, added_by):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM suivis WHERE mal_id = ? AND actif = 1", (mal_id,)).fetchone()
    if existing:
        return None
    c = conn.execute("INSERT INTO suivis (mal_id, titre, added_by) VALUES (?,?,?)", (mal_id, titre, added_by))
    conn.commit()
    return c.lastrowid

def get_suivis_actifs():
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM suivis WHERE actif = 1").fetchall()]

def update_suivi_ep(mal_id, episode):
    conn = get_connection()
    conn.execute("UPDATE suivis SET dernier_ep = ? WHERE mal_id = ? AND actif = 1", (episode, mal_id))
    conn.commit()

def stop_suivi(mal_id):
    conn = get_connection()
    conn.execute("UPDATE suivis SET actif = 0 WHERE mal_id = ?", (mal_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# BLACKLIST / WHITELIST
# ═══════════════════════════════════════════════════════════

def add_blacklist(user_id, username, raison, added_by):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO blacklist (user_id, username, raison, added_by) VALUES (?,?,?,?)",
                 (user_id, username, raison, added_by))
    conn.commit()

def remove_blacklist(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    conn.commit()

def is_blacklisted(user_id):
    conn = get_connection()
    return conn.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,)).fetchone() is not None

def get_blacklist():
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM blacklist").fetchall()]


# ═══════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════

def add_log(user_id, username, action, details="", level="INFO"):
    conn = get_connection()
    conn.execute("INSERT INTO logs (user_id, username, action, details, level) VALUES (?,?,?,?,?)",
                 (user_id, username, action, details, level))
    conn.commit()

def get_logs(limit=20, level=None):
    conn = get_connection()
    if level:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM logs WHERE level = ? ORDER BY timestamp DESC LIMIT ?", (level, limit)).fetchall()]
    return [dict(r) for r in conn.execute(
        "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()]

def get_logs_user(user_id, limit=20):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)).fetchall()]

def clean_logs(days=30):
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    conn.commit()
    return c.rowcount


# ═══════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()


# ═══════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════

def record_daily_stats():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute("SELECT COUNT(*) FROM animes WHERE DATE(posted_at) = ?", (today,)).fetchone()
    posts = row[0] if row else 0
    row = conn.execute("SELECT SUM(likes) FROM animes WHERE DATE(posted_at) = ?", (today,)).fetchone()
    likes = row[0] if row else 0
    row = conn.execute("SELECT SUM(views) FROM animes WHERE DATE(posted_at) = ?", (today,)).fetchone()
    views = row[0] if row else 0
    conn.execute("INSERT OR REPLACE INTO daily_stats (date, posts, likes, views) VALUES (?,?,?,?)",
                 (today, posts, likes or 0, views or 0))
    conn.commit()

def get_daily_stats(days=7):
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [dict(r) for r in conn.execute(
        "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date DESC", (cutoff,)).fetchall()]

def get_stats():
    conn = get_connection()
    stats = {}
    stats["total_animes"] = conn.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    stats["total_likes"] = conn.execute("SELECT COALESCE(SUM(likes), 0) FROM animes").fetchone()[0]
    stats["total_views"] = conn.execute("SELECT COALESCE(SUM(views), 0) FROM animes").fetchone()[0]
    stats["total_admins"] = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    stats["posts_en_attente"] = conn.execute("SELECT COUNT(*) FROM posts_programmes WHERE publie = 0").fetchone()[0]
    stats["total_suivis"] = conn.execute("SELECT COUNT(*) FROM suivis WHERE actif = 1").fetchone()[0]
    stats["total_templates"] = conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
    stats["total_blacklisted"] = conn.execute("SELECT COUNT(*) FROM blacklist").fetchone()[0]
    stats["total_favoris"] = conn.execute("SELECT COUNT(*) FROM favoris").fetchone()[0]
    stats["total_sondages"] = conn.execute("SELECT COUNT(*) FROM sondages").fetchone()[0]
    stats["total_quiz"] = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
    stats["total_logs"] = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    stats["total_ratings"] = conn.execute("SELECT COUNT(*) FROM user_ratings").fetchone()[0]
    stats["total_broadcasts"] = conn.execute("SELECT COUNT(*) FROM broadcasts").fetchone()[0]
    stats["total_edits"] = conn.execute("SELECT COUNT(*) FROM edit_history").fetchone()[0]
    return stats


# ═══════════════════════════════════════════════════════════
# BACKUPS
# ═══════════════════════════════════════════════════════════

def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
    shutil.copy2(DB_PATH, filepath)
    size = os.path.getsize(filepath)
    conn = get_connection()
    conn.execute("INSERT INTO backup_history (filepath, size) VALUES (?, ?)", (filepath, size))
    conn.commit()
    # Rotation
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "backup_*.db")))
    while len(backups) > MAX_BACKUPS:
        os.remove(backups.pop(0))
    return filepath, size

def get_backup_history(limit=10):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM backup_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]

def restore_backup(filepath):
    if os.path.exists(filepath):
        global _pool
        _pool = {}
        shutil.copy2(filepath, DB_PATH)
        return True
    return False


# ═══════════════════════════════════════════════════════════
# BROADCASTS (v5)
# ═══════════════════════════════════════════════════════════

def save_broadcast(message, sent_by, target="all"):
    conn = get_connection()
    c = conn.execute("INSERT INTO broadcasts (message, sent_by, target) VALUES (?,?,?)",
                     (message, sent_by, target))
    conn.commit()
    return c.lastrowid

def get_broadcasts(limit=10):
    conn = get_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM broadcasts ORDER BY sent_at DESC LIMIT ?", (limit,)).fetchall()]


# ═══════════════════════════════════════════════════════════
# EXPORT / IMPORT (v5)
# ═══════════════════════════════════════════════════════════

def export_animes_json():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    animes = get_all_animes(limit=9999)
    filepath = os.path.join(EXPORT_DIR, f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)
    return filepath

def import_animes_json(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        animes = json.load(f)
    count = 0
    for anime in animes:
        try:
            save_anime(anime)
            count += 1
        except Exception:
            continue
    return count


# ═══════════════════════════════════════════════════════════
# USER PROFILES (v5)
# ═══════════════════════════════════════════════════════════

def update_user_profile(user_id, username):
    conn = get_connection()
    now = datetime.now().isoformat()
    existing = conn.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        conn.execute("UPDATE user_profiles SET username = ?, last_active = ?, total_interactions = total_interactions + 1 WHERE user_id = ?",
                     (username, now, user_id))
    else:
        conn.execute("INSERT INTO user_profiles (user_id, username, last_active, total_interactions) VALUES (?,?,?,1)",
                     (user_id, username, now))
    conn.commit()

def get_user_profile(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════
# PURGE (v5)
# ═══════════════════════════════════════════════════════════

def purge_old_data(days=90):
    """Purge les données anciennes (logs, quiz, sondages fermés)."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    deleted = {}
    c = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    deleted["logs"] = c.rowcount
    c = conn.execute("DELETE FROM sondages WHERE closed = 1 AND created_at < ?", (cutoff,))
    deleted["sondages"] = c.rowcount
    c = conn.execute("DELETE FROM daily_stats WHERE date < ?", (cutoff[:10],))
    deleted["daily_stats"] = c.rowcount
    conn.commit()
    return deleted
