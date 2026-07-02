# ============================================================
# formatter.py — Formatage des posts et visuels (v4)
# ============================================================

import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import VISUAL_THEME as VT


# ═══════════════════════════════════════════════════════════
# BARRES VISUELLES
# ═══════════════════════════════════════════════════════════

def make_star_bar(note_str, max_stars=5):
    try:
        val = float(str(note_str).replace(",", "."))
        filled = max(0, min(round(val / 2), max_stars))
        return VT["star_full"] * filled + VT["star_empty"] * (max_stars - filled)
    except Exception:
        return VT["star_empty"] * max_stars

def make_progress_bar(value, max_val=100, length=10):
    if max_val <= 0:
        return VT["bar_low"] * length
    ratio = min(value / max_val, 1.0)
    filled = round(ratio * length)
    return VT["bar_full"] * filled + VT["bar_low"] * (length - filled)

def get_note_emoji(note_str):
    try:
        val = float(str(note_str).replace(",", "."))
        if val >= 9.0: return "🏆"
        if val >= 8.0: return "🌟"
        if val >= 7.0: return "⭐"
        if val >= 5.0: return "💫"
        return "⚠️"
    except Exception:
        return "📊"

def get_statut_emoji(statut):
    return {"En cours": "🟢", "Terminé": "✅", "À venir": "🔜", "En pause": "⏸️"}.get(statut, "❓")

def get_rank_emoji(rank):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"<b>{rank}.</b>")


# ═══════════════════════════════════════════════════════════
# TEMPLATES DE POSTS
# ═══════════════════════════════════════════════════════════

def format_anime_post(data, template="standard"):
    templates = {
        "standard": _fmt_standard,
        "compact": _fmt_compact,
        "premium": _fmt_premium,
        "minimal": _fmt_minimal,
        "neon": _fmt_neon,
    }
    return templates.get(template or "standard", _fmt_standard)(data)

def _common(data):
    return {
        "titre": data.get("titre", "Inconnu"),
        "titre_original": data.get("titre_original", ""),
        "synopsis": data.get("synopsis", "Aucun synopsis."),
        "personnages": data.get("personnages", ""),
        "studio": data.get("studio", "Inconnu"),
        "date_sortie": data.get("date_sortie", "Inconnue"),
        "nb_episodes": data.get("nb_episodes", "?"),
        "statut": data.get("statut", "Inconnu"),
        "genres": data.get("genres", ""),
        "note": data.get("note", "N/A"),
        "avis": data.get("avis", ""),
        "categorie": data.get("categorie", ""),
        "tags": data.get("tags", ""),
        "likes": data.get("likes", 0),
        "views": data.get("views", 0),
        "trailer_url": data.get("trailer_url", ""),
        "score_co": data.get("score_communaute", 0),
        "nb_votes": data.get("nb_votes_communaute", 0),
        "stars": make_star_bar(data.get("note", "0")),
        "statut_e": get_statut_emoji(data.get("statut", "")),
        "note_e": get_note_emoji(data.get("note", "0")),
    }

def _fmt_standard(data):
    d = _common(data)
    lines = [
        f"🎌 <b>{d['titre']}</b>",
    ]
    if d["titre_original"] and d["titre_original"] != d["titre"]:
        lines.append(f"<i>✦ {d['titre_original']}</i>")
    lines += ["", VT["separator"], ""]
    if d["categorie"]:
        lines.append(f"📂 <b>Catégorie :</b> #{d['categorie'].replace(' ', '_')}")
    if d["genres"]:
        lines.append(f"🏷️ <b>Genres :</b> {d['genres']}")
    lines.append(f"🎬 <b>Studio :</b> {d['studio']}")
    lines.append(f"📅 <b>Sortie :</b> {d['date_sortie']}")
    lines.append(f"📺 <b>Épisodes :</b> {d['nb_episodes']}")
    lines.append(f"{d['statut_e']} <b>Statut :</b> {d['statut']}")
    lines.append(f"{d['note_e']} <b>Note :</b> <b>{d['note']}</b>/10  {d['stars']}")
    if d["score_co"] > 0:
        lines.append(f"👥 <b>Note communauté :</b> {d['score_co']}/10 ({d['nb_votes']} votes)")
    if d["likes"] or d["views"]:
        lines.append(f"❤️ {d['likes']}  │  👁️ {d['views']}")
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",") if t.strip())
        lines.append(f"🔖 {tag_str}")
    lines += ["", VT["separator"], "", "📖 <b>Synopsis</b>", d["synopsis"]]
    if d["personnages"]:
        lines += ["", VT["separator_thin"], "", "👥 <b>Personnages principaux</b>", d["personnages"]]
    if d["avis"]:
        lines += ["", VT["separator_thin"], "", "💬 <b>Notre avis</b>", d["avis"]]
    if d["trailer_url"]:
        lines += ["", f"🎬 <a href=\"{d['trailer_url']}\">Voir le trailer</a>"]
    lines += ["", VT["separator"], "📡 <b>@animeFR2026</b> — Votre source anime 🇫🇷"]
    return "\n".join(lines)

def _fmt_premium(data):
    d = _common(data)
    w = 30
    lines = [f"╔{'═' * w}╗", f"║  🎌 <b>{d['titre']}</b>"]
    if d["titre_original"] and d["titre_original"] != d["titre"]:
        lines.append(f"║  <i>✦ {d['titre_original']}</i>")
    lines += [f"╠{'═' * w}╣", "║"]
    if d["categorie"]:
        lines.append(f"║  📂 #{d['categorie'].replace(' ', '_')}")
    if d["genres"]:
        lines.append(f"║  🏷️ {d['genres']}")
    lines += [
        f"║  🎬 {d['studio']}", f"║  📅 {d['date_sortie']}",
        f"║  📺 {d['nb_episodes']} épisodes", f"║  {d['statut_e']} {d['statut']}",
        f"║  {d['note_e']} {d['note']}/10  {d['stars']}",
    ]
    if d["score_co"] > 0:
        lines.append(f"║  👥 Communauté : {d['score_co']}/10")
    if d["likes"] or d["views"]:
        lines.append(f"║  ❤️ {d['likes']}  │  👁️ {d['views']}")
    lines += ["║", f"╠{'═' * w}╣", "║  📖 <b>Synopsis</b>", "║"]
    for line in d["synopsis"].split("\n"):
        lines.append(f"║  {line}")
    if d["personnages"]:
        lines += ["║", "║  👥 <b>Personnages</b>"]
        for line in d["personnages"].split("\n"):
            lines.append(f"║  {line}")
    if d["avis"]:
        lines += ["║", "║  💬 <b>Avis</b>"]
        for line in d["avis"].split("\n"):
            lines.append(f"║  {line}")
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",") if t.strip())
        lines.append(f"║  🔖 {tag_str}")
    if d["trailer_url"]:
        lines.append(f"║  🎬 Trailer : {d['trailer_url']}")
    lines += ["║", f"╠{'═' * w}╣", f"║  📡 @animeFR2026 🇫🇷", f"╚{'═' * w}╝"]
    return "\n".join(lines)

def _fmt_compact(data):
    d = _common(data)
    syn = d["synopsis"][:200] + "..." if len(d["synopsis"]) > 200 else d["synopsis"]
    return (
        f"🎌 <b>{d['titre']}</b>\n"
        f"{d['statut_e']} {d['statut']} │ 📺 {d['nb_episodes']} eps │ {d['stars']} {d['note']}/10\n"
        f"🏷️ {d['genres']}\n❤️ {d['likes']} │ 👁️ {d['views']}\n\n{syn}\n\n📡 @animeFR2026"
    )

def _fmt_minimal(data):
    d = _common(data)
    return (
        f"<b>{d['titre']}</b>\n{d['stars']} {d['note']}/10 • {d['statut']}\n"
        f"{d['genres']}\n\n@animeFR2026"
    )

def _fmt_neon(data):
    d = _common(data)
    lines = [
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓",
        f"▓  ⚡ <b>{d['titre']}</b>",
    ]
    if d["titre_original"] and d["titre_original"] != d["titre"]:
        lines.append(f"▓  <i>» {d['titre_original']}</i>")
    lines += [
        "▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░",
        f"▓  🎬 {d['studio']} │ 📅 {d['date_sortie']}",
        f"▓  📺 {d['nb_episodes']} eps │ {d['statut_e']} {d['statut']}",
        f"▓  ⚡ {d['note']}/10  {d['stars']}",
    ]
    if d["score_co"] > 0:
        lines.append(f"▓  👥 {d['score_co']}/10 communauté")
    if d["genres"]:
        lines.append(f"▓  🏷️ {d['genres']}")
    lines += [
        "▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░",
        f"▓  {d['synopsis'][:300]}{'...' if len(d['synopsis']) > 300 else ''}",
    ]
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",") if t.strip())
        lines.append(f"▓  {tag_str}")
    lines += [
        "▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░",
        f"▓  ❤️ {d['likes']} │ 👁️ {d['views']}",
        "▓  📡 @animeFR2026 ⚡",
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# FORMAT COURT
# ═══════════════════════════════════════════════════════════

def format_anime_short(data):
    return (
        f"🎌 <b>{data.get('titre', '?')}</b> <code>[ID:{data.get('id', '')}]</code>\n"
        f"{get_statut_emoji(data.get('statut', ''))} {data.get('statut', '?')} │ "
        f"📺 {data.get('nb_episodes', '?')} │ ⭐ {data.get('note', '?')} │ "
        f"❤️ {data.get('likes', 0)} │ 👁️ {data.get('views', 0)}"
    )


# ═══════════════════════════════════════════════════════════
# COMPARAISON
# ═══════════════════════════════════════════════════════════

def format_compare(a, b):
    def _bar(val_a, val_b, label):
        total = (val_a or 0) + (val_b or 0)
        if total == 0:
            return f"  {label}: 0 ═══════ 0"
        ratio = (val_a or 0) / total
        left = round(ratio * 10)
        right = 10 - left
        return f"  {label}: {val_a} {'█' * left}{'░' * right} {val_b}"

    lines = [
        f"╔{'═' * 32}╗",
        f"║  ⚔️ <b>COMPARAISON</b>",
        f"╠{'═' * 32}╣",
        f"║  🅰️ <b>{a.get('titre', '?')}</b>",
        f"║  🅱️ <b>{b.get('titre', '?')}</b>",
        f"╠{'═' * 32}╣",
        f"║{_bar(a.get('likes', 0), b.get('likes', 0), '❤️ Likes')}",
        f"║{_bar(a.get('views', 0), b.get('views', 0), '👁️ Vues ')}",
        f"║",
        f"║  ⭐ Note MAL  : {a.get('note', '?')} vs {b.get('note', '?')}",
        f"║  👥 Communauté: {a.get('score_communaute', 0)} vs {b.get('score_communaute', 0)}",
        f"║  📺 Épisodes  : {a.get('nb_episodes', '?')} vs {b.get('nb_episodes', '?')}",
        f"║  🎬 Studio    : {a.get('studio', '?')} vs {b.get('studio', '?')}",
        f"║  {get_statut_emoji(a.get('statut', ''))} {a.get('statut', '?')} vs "
        f"{get_statut_emoji(b.get('statut', ''))} {b.get('statut', '?')}",
        f"╠{'═' * 32}╣",
        f"║  📡 @animeFR2026",
        f"╚{'═' * 32}╝",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# SONDAGE
# ═══════════════════════════════════════════════════════════

def format_sondage(sondage, results=None, total=0):
    options = json.loads(sondage.get("options", "[]"))
    lines = [
        f"╔{'═' * 28}╗",
        f"║  📊 <b>SONDAGE</b>",
        f"╠{'═' * 28}╣",
        f"║  {sondage.get('question', '?')}",
        f"║",
    ]
    for i, opt in enumerate(options):
        votes = (results or {}).get(i, 0)
        pct = round(votes / total * 100) if total > 0 else 0
        bar = make_progress_bar(votes, max(total, 1), 8)
        lines.append(f"║  {i + 1}. {opt}  — {votes} ({pct}%)")
        lines.append(f"║     {bar}")
    lines += [f"║", f"║  Total : {total} votes", f"╚{'═' * 28}╝"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# QUIZ
# ═══════════════════════════════════════════════════════════

def format_quiz(quiz_data):
    options = json.loads(quiz_data.get("options", "[]"))
    lines = [
        f"╔{'═' * 28}╗",
        f"║  🧠 <b>QUIZ ANIME</b>",
        f"╠{'═' * 28}╣",
        f"║  {quiz_data.get('question', '?')}",
        f"║",
    ]
    emojis = ["🅰️", "🅱️", "🅲", "🅳"]
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i + 1}."
        lines.append(f"║  {e} {opt}")
    lines += [f"║", f"╚{'═' * 28}╝"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CALENDRIER
# ═══════════════════════════════════════════════════════════

def format_calendrier(entries):
    jours_order = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    by_jour = {}
    for e in entries:
        j = e.get("jour", "?")
        by_jour.setdefault(j, []).append(e)

    lines = [f"╔{'═' * 30}╗", f"║  📅 <b>CALENDRIER DE LA SEMAINE</b>", f"╠{'═' * 30}╣"]
    for jour in jours_order:
        if jour in by_jour:
            lines.append(f"║")
            lines.append(f"║  📌 <b>{jour}</b>")
            for e in by_jour[jour]:
                heure = e.get("heure", "")
                h_str = f" à {heure}" if heure else ""
                lines.append(f"║    🎌 {e.get('anime_titre', '?')}{h_str}")
    lines += [f"║", f"╠{'═' * 30}╣", f"║  📡 @animeFR2026", f"╚{'═' * 30}╝"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLAVIERS
# ═══════════════════════════════════════════════════════════

def build_anime_keyboard(anime_id, lien_externe=None, likes=0, views=0, is_fav=False):
    fav_text = "💛 Favori" if is_fav else "🤍 Favori"
    buttons = [
        [
            InlineKeyboardButton(f"❤️ ({likes})", callback_data=f"like_{anime_id}"),
            InlineKeyboardButton("👎", callback_data=f"dislike_{anime_id}"),
            InlineKeyboardButton(f"👁️ ({views})", callback_data=f"view_{anime_id}"),
        ],
        [
            InlineKeyboardButton(fav_text, callback_data=f"fav_{anime_id}"),
            InlineKeyboardButton("⭐ Noter", callback_data=f"rate_{anime_id}"),
        ],
        [
            InlineKeyboardButton("📊 Infos", callback_data=f"info_{anime_id}"),
            InlineKeyboardButton("🔍 Similaires", callback_data=f"similar_{anime_id}"),
            InlineKeyboardButton("📂 Catégorie", callback_data=f"category_{anime_id}"),
        ],
    ]
    if lien_externe and lien_externe.startswith("http"):
        buttons.append([InlineKeyboardButton("🌐 Voir sur MAL", url=lien_externe)])
    buttons.append([InlineKeyboardButton("📡 @animeFR2026", url="https://t.me/animeFR2026")])
    return InlineKeyboardMarkup(buttons)

def build_confirm_delete_keyboard(anime_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"confirm_delete_{anime_id}"),
        InlineKeyboardButton("❌ Annuler", callback_data=f"cancel_delete_{anime_id}"),
    ]])

def build_search_result_keyboard(results):
    buttons = []
    for i, a in enumerate(results[:5]):
        titre = a.get("title", "?")[:35]
        mal_id = a.get("mal_id", 0)
        score = a.get("score") or "?"
        buttons.append([InlineKeyboardButton(f"{i + 1}. {titre} ⭐{score}", callback_data=f"select_jikan_{mal_id}")])
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    return InlineKeyboardMarkup(buttons)

def build_categorie_keyboard(categories):
    buttons, row = [], []
    for cat in categories:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⏭️ Passer", callback_data="cat_Autre")])
    return InlineKeyboardMarkup(buttons)

def build_statut_keyboard():
    from config import STATUTS
    return InlineKeyboardMarkup([[InlineKeyboardButton(s, callback_data=f"statut_{s}")] for s in STATUTS])

def build_template_keyboard():
    templates = [
        ("📋 Standard", "tpl_standard"), ("📦 Compact", "tpl_compact"),
        ("💎 Premium", "tpl_premium"), ("✨ Minimal", "tpl_minimal"),
        ("⚡ Neon", "tpl_neon"),
    ]
    return InlineKeyboardMarkup([[InlineKeyboardButton(l, callback_data=c)] for l, c in templates])

def build_rating_keyboard(anime_id):
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"rating_{anime_id}_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    return InlineKeyboardMarkup(buttons)

def build_sondage_keyboard(sondage_id, options):
    emojis = ["🅰️", "🅱️", "🅲", "🅳", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    buttons = []
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i + 1}"
        buttons.append([InlineKeyboardButton(f"{e} {opt[:30]}", callback_data=f"svote_{sondage_id}_{i}")])
    buttons.append([InlineKeyboardButton("📊 Résultats", callback_data=f"sresult_{sondage_id}")])
    return InlineKeyboardMarkup(buttons)

def build_quiz_keyboard(quiz_id, options):
    emojis = ["🅰️", "🅱️", "🅲", "🅳"]
    buttons = []
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i + 1}"
        buttons.append([InlineKeyboardButton(f"{e} {opt[:30]}", callback_data=f"qanswer_{quiz_id}_{i}")])
    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════
# FORMATS SPÉCIAUX
# ═══════════════════════════════════════════════════════════

def format_notification_episode(titre, episode, date=""):
    return (
        f"╔{'═' * 28}╗\n║  🔔 <b>NOUVEL ÉPISODE !</b>\n╠{'═' * 28}╣\n"
        f"║  🎌 <b>{titre}</b>\n║  📺 Épisode <b>{episode}</b>\n"
        + (f"║  📅 {date}\n" if date else "")
        + f"╠{'═' * 28}╣\n║  📡 @animeFR2026\n╚{'═' * 28}╝"
    )

def format_log_entry(log):
    ts = log.get("timestamp", "")[:16]
    level = log.get("level", "INFO")
    le = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌", "DEBUG": "🔧"}.get(level, "📋")
    return (
        f"{le} <code>{ts}</code> │ 👤 @{log.get('username', '?')} │ "
        f"⚡ <b>{log['action']}</b>\n   📝 {log.get('details', '')}"
    )

def format_post_programme(post):
    data = {}
    try:
        data = json.loads(post.get("data_json", "{}"))
    except Exception:
        pass
    titre = data.get("titre", "Inconnu")
    scheduled = post.get("scheduled_at", "?")
    publie = "✅ Publié" if post.get("publie") else "⏳ En attente"
    text = f"🆔 <code>{post['id']}</code> — <b>{titre}</b>\n⏰ {scheduled}\n📌 {publie}"
    if post.get("erreur"):
        text += f"\n❌ {post['erreur']}"
    return text

def format_backup_info(filepath, size):
    from datetime import datetime
    return (
        f"💾 <b>Backup créé</b>\n\n📁 <code>{filepath}</code>\n"
        f"📏 <b>{size / 1024:.1f} Ko</b>\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

def format_stats_dashboard(stats, daily):
    text = (
        f"╔{'═' * 32}╗\n║  📊 <b>DASHBOARD — AnimeFR v4</b>\n╠{'═' * 32}╣\n║\n"
        f"║  🎌 Anime publiés  : <b>{stats['total_animes']}</b>\n"
        f"║  ❤️ Likes totaux   : <b>{stats['total_likes']}</b>\n"
        f"║  👁️ Vues totales   : <b>{stats['total_views']}</b>\n"
        f"║  👥 Admins         : <b>{stats['total_admins']}</b>\n"
        f"║  ⏰ Posts en file   : <b>{stats['posts_en_attente']}</b>\n"
        f"║  🔔 Anime suivis   : <b>{stats['total_suivis']}</b>\n"
        f"║  📋 Templates      : <b>{stats['total_templates']}</b>\n"
        f"║  🚫 Blacklistés    : <b>{stats['total_blacklisted']}</b>\n"
        f"║  💛 Favoris total  : <b>{stats['total_favoris']}</b>\n"
        f"║  📊 Sondages       : <b>{stats['total_sondages']}</b>\n"
        f"║  🧠 Quiz           : <b>{stats['total_quiz']}</b>\n"
        f"║  📋 Logs           : <b>{stats['total_logs']}</b>\n"
        f"║\n╠{'═' * 32}╣\n║  📈 <b>Activité (7 jours)</b>\n║\n"
    )
    if daily:
        mx = max((d.get("posts", 0) for d in daily), default=1) or 1
        for d in reversed(daily):
            ds = d.get("date", "?")[5:]
            p = d.get("posts", 0)
            l = d.get("likes", 0)
            text += f"║  {ds} {make_progress_bar(p, mx, 8)} {p}p/{l}❤️\n"
    else:
        text += "║  <i>Pas encore de données</i>\n"
    text += f"║\n╚{'═' * 32}╝"
    return text

def format_whats_new():
    return (
        f"╔{'═' * 32}╗\n║  🆕 <b>QUOI DE NEUF — v4.0</b>\n╠{'═' * 32}╣\n║\n"
        f"║  🎯 <b>COMMUNAUTÉ</b>\n"
        f"║  ● Système de favoris /favoris\n"
        f"║  ● Notes communautaires ⭐ /noter\n"
        f"║  ● Sondages interactifs /sondage\n"
        f"║  ● Quiz anime /quiz\n"
        f"║  ● Comparaison d'anime /comparer\n"
        f"║  ● Classement communauté /topnotes\n"
        f"║\n"
        f"║  📅 <b>AUTOMATISATION</b>\n"
        f"║  ● Calendrier des sorties /calendrier\n"
        f"║  ● Ajout au calendrier /addcalendrier\n"
        f"║  ● Recherche avancée /filtre\n"
        f"║  ● Recherche locale /chercher\n"
        f"║\n"
        f"║  🎨 <b>VISUEL</b>\n"
        f"║  ● Nouveau template Neon ⚡\n"
        f"║  ● Bouton Favori 💛 sur les posts\n"
        f"║  ● Bouton Noter ⭐ sur les posts\n"
        f"║  ● Barres de comparaison visuelles\n"
        f"║  ● Emojis de classement 🥇🥈🥉\n"
        f"║\n"
        f"║  ⚡ <b>OPTIMISATIONS</b>\n"
        f"║  ● Index SQLite pour performances\n"
        f"║  ● Cache SQLite 8 Mo\n"
        f"║  ● Pseudo-pool de connexions\n"
        f"║  ● Toggle like (re-clic = unlike)\n"
        f"║  ● Nettoyage cascade suppression\n"
        f"║  ● 14 backups conservés\n"
        f"║\n╠{'═' * 32}╣\n║  📡 @animeFR2026 — Bot v4.0\n╚{'═' * 32}╝"
    )
