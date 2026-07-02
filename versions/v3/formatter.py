# ============================================================
# formatter.py — Formatage des posts et visuels (v3)
# ============================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import VISUAL_THEME as VT


# ════════════════════════════════════════════════════════════
# BARRES VISUELLES
# ════════════════════════════════════════════════════════════

def make_star_bar(note_str: str, max_stars: int = 5) -> str:
    """Génère une barre d'étoiles visuelles ★★★★☆"""
    try:
        val = float(str(note_str).replace(",", "."))
        filled = round(val / 2)  # note sur 10 → étoiles sur 5
        filled = max(0, min(filled, max_stars))
        return VT["star_full"] * filled + VT["star_empty"] * (max_stars - filled)
    except Exception:
        return VT["star_empty"] * max_stars


def make_progress_bar(value: int, max_val: int = 100, length: int = 10) -> str:
    """Génère une barre de progression █████░░░░░"""
    if max_val <= 0:
        return VT["bar_low"] * length
    ratio = min(value / max_val, 1.0)
    filled = round(ratio * length)
    return VT["bar_full"] * filled + VT["bar_low"] * (length - filled)


def get_note_emoji(note_str: str) -> str:
    try:
        val = float(str(note_str).replace(",", "."))
        if val >= 9.0: return "🏆"
        if val >= 8.0: return "🌟"
        if val >= 7.0: return "⭐"
        if val >= 5.0: return "💫"
        return "⚠️"
    except Exception:
        return "📊"


def get_statut_emoji(statut: str) -> str:
    return {
        "En cours": "🟢", "Terminé": "✅", "À venir": "🔜", "En pause": "⏸️"
    }.get(statut, "❓")


# ════════════════════════════════════════════════════════════
# TEMPLATES DE POSTS
# ════════════════════════════════════════════════════════════

def format_anime_post(data: dict, template: str = "standard") -> str:
    """Formate un anime selon le template choisi."""
    templates = {
        "standard": _format_standard,
        "compact": _format_compact,
        "premium": _format_premium,
        "minimal": _format_minimal,
    }
    formatter = templates.get(template or "standard", _format_standard)
    return formatter(data)


def _format_standard(data: dict) -> str:
    titre           = data.get("titre", "Inconnu")
    titre_original  = data.get("titre_original", "")
    synopsis        = data.get("synopsis", "Aucun synopsis.")
    personnages     = data.get("personnages", "")
    studio          = data.get("studio", "Inconnu")
    date_sortie     = data.get("date_sortie", "Inconnue")
    nb_episodes     = data.get("nb_episodes", "?")
    statut          = data.get("statut", "Inconnu")
    genres          = data.get("genres", "")
    note            = data.get("note", "N/A")
    avis            = data.get("avis", "")
    categorie       = data.get("categorie", "")
    tags            = data.get("tags", "")
    likes           = data.get("likes", 0)
    views           = data.get("views", 0)

    stars = make_star_bar(note)
    statut_e = get_statut_emoji(statut)
    note_e = get_note_emoji(note)

    lines = []
    lines.append(f"🎌 <b>{titre}</b>")
    if titre_original and titre_original != titre:
        lines.append(f"<i>✦ {titre_original}</i>")
    lines.append("")
    lines.append(VT["separator"])
    lines.append("")

    if categorie:
        lines.append(f"📂 <b>Catégorie :</b> #{categorie.replace(' ', '_')}")
    if genres:
        lines.append(f"🏷️ <b>Genres :</b> {genres}")
    lines.append(f"🎬 <b>Studio :</b> {studio}")
    lines.append(f"📅 <b>Sortie :</b> {date_sortie}")
    lines.append(f"📺 <b>Épisodes :</b> {nb_episodes}")
    lines.append(f"{statut_e} <b>Statut :</b> {statut}")
    lines.append(f"{note_e} <b>Note :</b> <b>{note}</b>/10  {stars}")
    if likes or views:
        lines.append(f"❤️ {likes}  │  👁️ {views}")
    if tags:
        tag_str = " ".join([f"#{t.strip().replace(' ', '_')}" for t in tags.split(",") if t.strip()])
        lines.append(f"🔖 {tag_str}")

    lines.append("")
    lines.append(VT["separator"])
    lines.append("")
    lines.append("📖 <b>Synopsis</b>")
    lines.append(synopsis)

    if personnages:
        lines.append("")
        lines.append(VT["separator_thin"])
        lines.append("")
        lines.append("👥 <b>Personnages principaux</b>")
        lines.append(personnages)

    if avis:
        lines.append("")
        lines.append(VT["separator_thin"])
        lines.append("")
        lines.append("💬 <b>Notre avis</b>")
        lines.append(avis)

    lines.append("")
    lines.append(VT["separator"])
    lines.append(f"📡 <b>@animeFR2026</b> — Votre source anime 🇫🇷")

    return "\n".join(lines)


def _format_premium(data: dict) -> str:
    titre           = data.get("titre", "Inconnu")
    titre_original  = data.get("titre_original", "")
    synopsis        = data.get("synopsis", "Aucun synopsis.")
    personnages     = data.get("personnages", "")
    studio          = data.get("studio", "Inconnu")
    date_sortie     = data.get("date_sortie", "Inconnue")
    nb_episodes     = data.get("nb_episodes", "?")
    statut          = data.get("statut", "Inconnu")
    genres          = data.get("genres", "")
    note            = data.get("note", "N/A")
    avis            = data.get("avis", "")
    categorie       = data.get("categorie", "")
    tags            = data.get("tags", "")
    likes           = data.get("likes", 0)
    views           = data.get("views", 0)

    stars = make_star_bar(note)
    statut_e = get_statut_emoji(statut)
    note_e = get_note_emoji(note)

    lines = []
    lines.append(f"╔{'═' * 30}╗")
    lines.append(f"║  🎌 <b>{titre}</b>")
    if titre_original and titre_original != titre:
        lines.append(f"║  <i>✦ {titre_original}</i>")
    lines.append(f"╠{'═' * 30}╣")
    lines.append(f"║")
    if categorie:
        lines.append(f"║  📂 #{categorie.replace(' ', '_')}")
    if genres:
        lines.append(f"║  🏷️ {genres}")
    lines.append(f"║  🎬 {studio}")
    lines.append(f"║  📅 {date_sortie}")
    lines.append(f"║  📺 {nb_episodes} épisodes")
    lines.append(f"║  {statut_e} {statut}")
    lines.append(f"║  {note_e} {note}/10  {stars}")
    if likes or views:
        lines.append(f"║  ❤️ {likes}  │  👁️ {views}")
    lines.append(f"║")
    lines.append(f"╠{'═' * 30}╣")
    lines.append(f"║  📖 <b>Synopsis</b>")
    lines.append(f"║")
    for line in synopsis.split("\n"):
        lines.append(f"║  {line}")

    if personnages:
        lines.append(f"║")
        lines.append(f"║  👥 <b>Personnages</b>")
        for line in personnages.split("\n"):
            lines.append(f"║  {line}")

    if avis:
        lines.append(f"║")
        lines.append(f"║  💬 <b>Avis</b>")
        for line in avis.split("\n"):
            lines.append(f"║  {line}")

    if tags:
        tag_str = " ".join([f"#{t.strip().replace(' ', '_')}" for t in tags.split(",") if t.strip()])
        lines.append(f"║  🔖 {tag_str}")

    lines.append(f"║")
    lines.append(f"╠{'═' * 30}╣")
    lines.append(f"║  📡 @animeFR2026 🇫🇷")
    lines.append(f"╚{'═' * 30}╝")

    return "\n".join(lines)


def _format_compact(data: dict) -> str:
    titre       = data.get("titre", "Inconnu")
    statut      = data.get("statut", "?")
    note        = data.get("note", "N/A")
    genres      = data.get("genres", "")
    nb_episodes = data.get("nb_episodes", "?")
    synopsis    = data.get("synopsis", "")
    likes       = data.get("likes", 0)
    stars       = make_star_bar(note)

    syn_short = synopsis[:200] + "..." if len(synopsis) > 200 else synopsis

    return (
        f"🎌 <b>{titre}</b>\n"
        f"{get_statut_emoji(statut)} {statut} │ 📺 {nb_episodes} eps │ {stars} {note}/10\n"
        f"🏷️ {genres}\n"
        f"❤️ {likes}\n\n"
        f"{syn_short}\n\n"
        f"📡 @animeFR2026"
    )


def _format_minimal(data: dict) -> str:
    titre   = data.get("titre", "Inconnu")
    note    = data.get("note", "N/A")
    statut  = data.get("statut", "?")
    genres  = data.get("genres", "")
    stars   = make_star_bar(note)

    return (
        f"<b>{titre}</b>\n"
        f"{stars} {note}/10 • {statut}\n"
        f"{genres}\n\n"
        f"@animeFR2026"
    )


# ════════════════════════════════════════════════════════════
# FORMAT COURT
# ════════════════════════════════════════════════════════════

def format_anime_short(data: dict) -> str:
    titre       = data.get("titre", "Inconnu")
    statut      = data.get("statut", "?")
    note        = data.get("note", "N/A")
    nb_episodes = data.get("nb_episodes", "?")
    likes       = data.get("likes", 0)
    views       = data.get("views", 0)
    anime_id    = data.get("id", "")

    return (
        f"🎌 <b>{titre}</b> <code>[ID:{anime_id}]</code>\n"
        f"{get_statut_emoji(statut)} {statut} │ 📺 {nb_episodes} │ ⭐ {note} │ ❤️ {likes} │ 👁️ {views}"
    )


# ════════════════════════════════════════════════════════════
# CLAVIERS INTERACTIFS
# ════════════════════════════════════════════════════════════

def build_anime_keyboard(anime_id: int, lien_externe: str = None, likes: int = 0, views: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([
        InlineKeyboardButton(f"❤️ ({likes})", callback_data=f"like_{anime_id}"),
        InlineKeyboardButton(f"👎", callback_data=f"dislike_{anime_id}"),
        InlineKeyboardButton(f"👁️ ({views})", callback_data=f"view_{anime_id}"),
    ])
    buttons.append([
        InlineKeyboardButton("📊 Infos", callback_data=f"info_{anime_id}"),
        InlineKeyboardButton("🔍 Similaires", callback_data=f"similar_{anime_id}"),
        InlineKeyboardButton("📂 Catégorie", callback_data=f"category_{anime_id}"),
    ])
    if lien_externe and lien_externe.startswith("http"):
        buttons.append([
            InlineKeyboardButton("🌐 Voir sur MAL", url=lien_externe)
        ])
    buttons.append([
        InlineKeyboardButton("📡 @animeFR2026", url="https://t.me/animeFR2026")
    ])
    return InlineKeyboardMarkup(buttons)


def build_confirm_delete_keyboard(anime_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"confirm_delete_{anime_id}"),
        InlineKeyboardButton("❌ Annuler", callback_data=f"cancel_delete_{anime_id}"),
    ]])


def build_search_result_keyboard(results: list) -> InlineKeyboardMarkup:
    buttons = []
    for i, anime in enumerate(results[:5]):
        titre = anime.get("title", "Inconnu")[:35]
        mal_id = anime.get("mal_id", 0)
        score = anime.get("score") or "?"
        buttons.append([
            InlineKeyboardButton(f"{i+1}. {titre} ⭐{score}", callback_data=f"select_jikan_{mal_id}")
        ])
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    return InlineKeyboardMarkup(buttons)


def build_categorie_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⏭️ Passer", callback_data="cat_Autre")])
    return InlineKeyboardMarkup(buttons)


def build_statut_keyboard() -> InlineKeyboardMarkup:
    from config import STATUTS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(s, callback_data=f"statut_{s}")] for s in STATUTS
    ])


def build_template_keyboard() -> InlineKeyboardMarkup:
    templates = [
        ("📋 Standard", "tpl_standard"),
        ("📦 Compact", "tpl_compact"),
        ("💎 Premium", "tpl_premium"),
        ("✨ Minimal", "tpl_minimal"),
    ]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=cb)] for label, cb in templates
    ])


# ════════════════════════════════════════════════════════════
# FORMATS SPÉCIAUX
# ════════════════════════════════════════════════════════════

def format_notification_episode(titre: str, episode: int, date: str = "") -> str:
    return (
        f"╔{'═' * 28}╗\n"
        f"║  🔔 <b>NOUVEL ÉPISODE !</b>\n"
        f"╠{'═' * 28}╣\n"
        f"║  🎌 <b>{titre}</b>\n"
        f"║  📺 Épisode <b>{episode}</b>\n"
        + (f"║  📅 {date}\n" if date else "")
        + f"╠{'═' * 28}╣\n"
        f"║  📡 @animeFR2026\n"
        f"╚{'═' * 28}╝"
    )


def format_log_entry(log: dict) -> str:
    ts = log.get("timestamp", "")[:16]
    level = log.get("level", "INFO")
    level_emoji = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌", "DEBUG": "🔧"}.get(level, "📋")
    return (
        f"{level_emoji} <code>{ts}</code> │ "
        f"👤 @{log.get('username', '?')} │ "
        f"⚡ <b>{log['action']}</b>\n"
        f"   📝 {log.get('details', '')}"
    )


def format_post_programme(post: dict) -> str:
    import json
    data = {}
    try:
        data = json.loads(post.get("data_json", "{}"))
    except Exception:
        pass
    titre = data.get("titre", "Inconnu")
    scheduled = post.get("scheduled_at", "?")
    publie = "✅ Publié" if post.get("publie") else "⏳ En attente"
    erreur = post.get("erreur", "")
    text = (
        f"🆔 <code>{post['id']}</code> — <b>{titre}</b>\n"
        f"⏰ {scheduled}\n"
        f"📌 {publie}"
    )
    if erreur:
        text += f"\n❌ {erreur}"
    return text


def format_stats_dashboard(stats: dict, daily: list) -> str:
    """Dashboard de statistiques avancé avec barres visuelles."""
    text = (
        f"╔{'═' * 32}╗\n"
        f"║  📊 <b>DASHBOARD — AnimeFR v3</b>\n"
        f"╠{'═' * 32}╣\n"
        f"║\n"
        f"║  🎌 Anime publiés : <b>{stats['total_animes']}</b>\n"
        f"║  ❤️ Likes totaux  : <b>{stats['total_likes']}</b>\n"
        f"║  👁️ Vues totales  : <b>{stats['total_views']}</b>\n"
        f"║  👥 Admins        : <b>{stats['total_admins']}</b>\n"
        f"║  ⏰ Posts en file  : <b>{stats['posts_en_attente']}</b>\n"
        f"║  🔔 Anime suivis  : <b>{stats['total_suivis']}</b>\n"
        f"║  📋 Templates     : <b>{stats['total_templates']}</b>\n"
        f"║  🚫 Blacklistés   : <b>{stats['total_blacklisted']}</b>\n"
        f"║  📋 Logs          : <b>{stats['total_logs']}</b>\n"
        f"║\n"
        f"╠{'═' * 32}╣\n"
        f"║  📈 <b>Activité des 7 derniers jours</b>\n"
        f"║\n"
    )

    if daily:
        max_posts = max((d.get("posts", 0) for d in daily), default=1) or 1
        for d in reversed(daily):
            date_short = d.get("date", "?")[5:]  # MM-DD
            posts = d.get("posts", 0)
            likes = d.get("likes", 0)
            bar = make_progress_bar(posts, max_posts, 8)
            text += f"║  {date_short} {bar} {posts}p/{likes}❤️\n"
    else:
        text += f"║  <i>Pas encore de données</i>\n"

    text += (
        f"║\n"
        f"╚{'═' * 32}╝"
    )
    return text


def format_backup_info(filepath: str, size: int) -> str:
    size_kb = size / 1024
    return (
        f"💾 <b>Backup créé avec succès</b>\n\n"
        f"📁 Fichier : <code>{filepath}</code>\n"
        f"📏 Taille : <b>{size_kb:.1f} Ko</b>\n"
        f"🕐 Date : {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


def format_whats_new() -> str:
    return (
        f"╔{'═' * 32}╗\n"
        f"║  🆕 <b>QUOI DE NEUF — v3.0</b>\n"
        f"╠{'═' * 32}╣\n"
        f"║\n"
        f"║  🎨 <b>VISUEL</b>\n"
        f"║  ● 4 templates de posts\n"
        f"║    (Standard, Compact, Premium, Minimal)\n"
        f"║  ● Barres d'étoiles visuelles ★★★★☆\n"
        f"║  ● Barres de progression █████░░░\n"
        f"║  ● Encadrés visuels ╔═══╗\n"
        f"║  ● Compteur de vues 👁️\n"
        f"║  ● Bouton 👎 dislike\n"
        f"║  ● Tags personnalisés #tag\n"
        f"║\n"
        f"║  🛠️ <b>ADMIN & TECHNIQUE</b>\n"
        f"║  ● Dashboard stats avancé avec graphes\n"
        f"║  ● Backup auto BDD (24h) + manuel\n"
        f"║  ● Restauration de backup\n"
        f"║  ● Mode maintenance ON/OFF\n"
        f"║  ● Nettoyage auto des vieux logs\n"
        f"║  ● Logs par niveau (INFO/WARN/ERROR)\n"
        f"║  ● Logs filtrés par user ou action\n"
        f"║  ● Settings dynamiques (clé/valeur)\n"
        f"║  ● Classement top likés / top vus\n"
        f"║  ● Système de tags personnalisés\n"
        f"║  ● Templates personnalisables\n"
        f"║  ● Historique des backups\n"
        f"║  ● Stats journalières auto\n"
        f"║  ● Rotation des logs\n"
        f"║\n"
        f"║  ⚡ <b>OPTIMISATIONS</b>\n"
        f"║  ● WAL mode SQLite (plus rapide)\n"
        f"║  ● Meilleure gestion mémoire\n"
        f"║  ● Code refactorisé et modulaire\n"
        f"║\n"
        f"╠{'═' * 32}╣\n"
        f"║  📡 @animeFR2026 — Bot v3.0\n"
        f"╚{'═' * 32}╝"
    )
