# ============================================================
# formatter.py — Formatage visuel AnimeFR Bot v5.0
# Adapté mobile : textes courts, boutons compacts, lisibilité
# ============================================================

import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import VISUAL_THEME as VT, MOBILE_SYNOPSIS_LENGTH, MOBILE_MODE


# ═══════════════════════════════════════════════════════════
# HELPERS VISUELS
# ═══════════════════════════════════════════════════════════

def make_star_bar(note, max_stars=5):
    try:
        n = float(str(note).replace(",", "."))
    except (ValueError, TypeError):
        n = 0
    filled = round(n / 2)
    return VT["star_full"] * filled + VT["star_empty"] * (max_stars - filled)

def make_progress_bar(value, max_val, length=10):
    if max_val <= 0:
        return VT["bar_low"] * length
    ratio = min(value / max_val, 1.0)
    filled = round(ratio * length)
    return VT["bar_full"] * filled + VT["bar_low"] * (length - filled)

def get_statut_emoji(statut):
    return {"En cours": "🟢", "Terminé": "🔵", "À venir": "🟡",
            "En pause": "🟠", "Annulé": "🔴"}.get(statut, "⚪")

def get_note_emoji(note):
    try:
        n = float(str(note).replace(",", "."))
    except (ValueError, TypeError):
        return "⭐"
    if n >= 9:
        return "🏆"
    elif n >= 7:
        return "🔥"
    elif n >= 5:
        return "⭐"
    return "💫"

def get_rank_emoji(rank):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

def truncate(text, max_len):
    if not text:
        return ""
    return text[:max_len] + "…" if len(text) > max_len else text


# ═══════════════════════════════════════════════════════════
# FORMAT ANIME POST (7 templates)
# ═══════════════════════════════════════════════════════════

def format_anime_post(data, template=None):
    templates = {
        "standard": _fmt_standard,
        "compact": _fmt_compact,
        "premium": _fmt_premium,
        "minimal": _fmt_minimal,
        "neon": _fmt_neon,
        "mobile": _fmt_mobile,
        "elegant": _fmt_elegant,
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
        "dislikes": data.get("dislikes", 0),
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
    lines = [f"🎌 <b>{d['titre']}</b>"]
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
        lines.append(f"👥 <b>Communauté :</b> {d['score_co']}/10 ({d['nb_votes']} votes)")
    if d["likes"] or d["views"]:
        lines.append(f"❤️ {d['likes']}  │  👁️ {d['views']}")
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",") if t.strip())
        lines.append(f"🔖 {tag_str}")
    lines += ["", VT["separator"], "", "📖 <b>Synopsis</b>", d["synopsis"]]
    if d["personnages"]:
        lines += ["", VT["separator_thin"], "", "👥 <b>Personnages</b>", d["personnages"]]
    if d["avis"]:
        lines += ["", VT["separator_thin"], "", "💬 <b>Notre avis</b>", d["avis"]]
    if d["trailer_url"]:
        lines += ["", f"🎬 <a href=\"{d['trailer_url']}\">Voir le trailer</a>"]
    lines += ["", VT["separator"], "📡 <b>@animeFR2026</b> — Votre source anime 🇫🇷"]
    return "\n".join(lines)


def _fmt_premium(data):
    d = _common(data)
    lines = [
        f"┌{'─' * 28}┐",
        f"│  🎌 <b>{d['titre']}</b>",
    ]
    if d["titre_original"] and d["titre_original"] != d["titre"]:
        lines.append(f"│  <i>✦ {d['titre_original']}</i>")
    lines += [f"├{'─' * 28}┤", "│"]
    if d["categorie"]:
        lines.append(f"│  📂 #{d['categorie'].replace(' ', '_')}")
    if d["genres"]:
        lines.append(f"│  🏷️ {d['genres']}")
    lines += [
        f"│  🎬 {d['studio']}", f"│  📅 {d['date_sortie']}",
        f"│  📺 {d['nb_episodes']} épisodes", f"│  {d['statut_e']} {d['statut']}",
        f"│  {d['note_e']} {d['note']}/10  {d['stars']}",
    ]
    if d["score_co"] > 0:
        lines.append(f"│  👥 Communauté : {d['score_co']}/10")
    if d["likes"] or d["views"]:
        lines.append(f"│  ❤️ {d['likes']}  │  👁️ {d['views']}")
    lines += ["│", f"├{'─' * 28}┤", "│  📖 <b>Synopsis</b>", "│"]
    for line in d["synopsis"].split("\n"):
        lines.append(f"│  {line}")
    if d["personnages"]:
        lines += ["│", "│  👥 <b>Personnages</b>"]
        for line in d["personnages"].split("\n"):
            lines.append(f"│  {line}")
    if d["avis"]:
        lines += ["│", "│  💬 <b>Avis</b>"]
        for line in d["avis"].split("\n"):
            lines.append(f"│  {line}")
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",") if t.strip())
        lines.append(f"│  🔖 {tag_str}")
    if d["trailer_url"]:
        lines.append(f"│  🎬 <a href=\"{d['trailer_url']}\">Trailer</a>")
    lines += ["│", f"├{'─' * 28}┤", f"│  📡 @animeFR2026 🇫🇷", f"└{'─' * 28}┘"]
    return "\n".join(lines)


def _fmt_compact(data):
    d = _common(data)
    syn = truncate(d["synopsis"], 180)
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
        f"▓  {truncate(d['synopsis'], 280)}",
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


def _fmt_mobile(data):
    """Template optimisé mobile : court, aéré, lisible sur petit écran."""
    d = _common(data)
    syn = truncate(d["synopsis"], MOBILE_SYNOPSIS_LENGTH)
    lines = [
        f"🎌 <b>{d['titre']}</b>",
        "",
        f"{d['statut_e']} {d['statut']} • 📺 {d['nb_episodes']} eps",
        f"{d['note_e']} {d['note']}/10 {d['stars']}",
    ]
    if d["score_co"] > 0:
        lines.append(f"👥 {d['score_co']}/10 communauté")
    lines.append("")
    if d["genres"]:
        lines.append(f"🏷️ {d['genres']}")
    lines.append(f"🎬 {d['studio']} • 📅 {d['date_sortie']}")
    lines += ["", VT["separator_short"], "", syn]
    if d["avis"]:
        lines += ["", f"💬 {truncate(d['avis'], 150)}"]
    lines += ["", f"❤️ {d['likes']} • 👎 {d['dislikes']} • 👁️ {d['views']}"]
    if d["tags"]:
        tag_str = " ".join(f"#{t.strip().replace(' ', '_')}" for t in d["tags"].split(",")[:5] if t.strip())
        lines.append(f"🔖 {tag_str}")
    lines += ["", "📡 @animeFR2026"]
    return "\n".join(lines)


def _fmt_elegant(data):
    """Template élégant : épuré, raffiné, typographie soignée."""
    d = _common(data)
    lines = [
        f"✦ <b>{d['titre']}</b> ✦",
    ]
    if d["titre_original"] and d["titre_original"] != d["titre"]:
        lines.append(f"<i>{d['titre_original']}</i>")
    lines += [
        "",
        "─── ⋆⋅☆⋅⋆ ───",
        "",
        f"◈ Studio : {d['studio']}",
        f"◈ Sortie : {d['date_sortie']} • {d['nb_episodes']} épisodes",
        f"◈ Statut : {d['statut']}",
        f"◈ Note : {d['note']}/10 {d['stars']}",
    ]
    if d["score_co"] > 0:
        lines.append(f"◈ Communauté : {d['score_co']}/10")
    if d["genres"]:
        lines += ["", f"⟡ {d['genres']}"]
    lines += [
        "",
        "─── ⋆⋅☆⋅⋆ ───",
        "",
        d["synopsis"],
    ]
    if d["personnages"]:
        lines += ["", "─── ⋆⋅☆⋅⋆ ───", "", f"◈ Personnages : {d['personnages']}"]
    if d["avis"]:
        lines += ["", f"◈ Avis : {d['avis']}"]
    if d["trailer_url"]:
        lines.append(f"\n◈ <a href=\"{d['trailer_url']}\">Voir le trailer</a>")
    lines += ["", "─── ⋆⋅☆⋅⋆ ───", "", "✦ @animeFR2026 ✦"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# FORMAT COURT (listes)
# ═══════════════════════════════════════════════════════════

def format_anime_short(anime, rank=None):
    titre = anime.get("titre", "?")
    note = anime.get("note", "?")
    statut = anime.get("statut", "?")
    likes = anime.get("likes", 0)
    views = anime.get("views", 0)
    rank_str = f"{get_rank_emoji(rank)} " if rank else ""
    return f"{rank_str}<b>{titre}</b>\n   {get_statut_emoji(statut)} {statut} │ ⭐ {note}/10 │ ❤️ {likes} │ 👁️ {views}"

def format_anime_short_mobile(anime, rank=None):
    """Version mobile ultra-compacte pour les listes."""
    titre = truncate(anime.get("titre", "?"), 25)
    note = anime.get("note", "?")
    likes = anime.get("likes", 0)
    rank_str = f"{get_rank_emoji(rank)} " if rank else "• "
    return f"{rank_str}<b>{titre}</b> ⭐{note} ❤️{likes}"


# ═══════════════════════════════════════════════════════════
# FORMATS COMMUNAUTÉ
# ═══════════════════════════════════════════════════════════

def format_compare(anime_a, anime_b):
    def _side(a):
        return {
            "titre": a.get("titre", "?"),
            "note": a.get("note", "?"),
            "likes": a.get("likes", 0),
            "views": a.get("views", 0),
            "statut": a.get("statut", "?"),
            "score_co": a.get("score_communaute", 0),
        }
    a, b = _side(anime_a), _side(anime_b)
    max_likes = max(a["likes"], b["likes"]) or 1
    max_views = max(a["views"], b["views"]) or 1
    return (
        f"⚔️ <b>COMPARAISON</b>\n\n"
        f"🅰️ <b>{a['titre']}</b>\n"
        f"   ⭐ {a['note']}/10 │ 👥 {a['score_co']}/10\n"
        f"   ❤️ {make_progress_bar(a['likes'], max_likes, 8)} {a['likes']}\n"
        f"   👁️ {make_progress_bar(a['views'], max_views, 8)} {a['views']}\n\n"
        f"🅱️ <b>{b['titre']}</b>\n"
        f"   ⭐ {b['note']}/10 │ 👥 {b['score_co']}/10\n"
        f"   ❤️ {make_progress_bar(b['likes'], max_likes, 8)} {b['likes']}\n"
        f"   👁️ {make_progress_bar(b['views'], max_views, 8)} {b['views']}\n\n"
        f"📡 @animeFR2026"
    )

def format_sondage(question, options, results=None, total_votes=0):
    lines = [f"📊 <b>SONDAGE</b>\n", f"❓ <b>{question}</b>\n"]
    emojis = ["🅰️", "🅱️", "🅲", "🅳", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i+1}"
        if results:
            count = next((r["cnt"] for r in results if r["option_idx"] == i), 0)
            pct = round(count / total_votes * 100) if total_votes > 0 else 0
            bar = make_progress_bar(count, total_votes, 8)
            lines.append(f"{e} {opt}\n   {bar} {pct}% ({count})")
        else:
            lines.append(f"{e} {opt}")
    if total_votes:
        lines.append(f"\n👥 {total_votes} votes")
    return "\n".join(lines)

def format_quiz(question, options, correct_idx=None, explication=None, stats=None):
    lines = [f"🧠 <b>QUIZ</b>\n", f"❓ <b>{question}</b>\n"]
    emojis = ["🅰️", "🅱️", "🅲", "🅳"]
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i+1}"
        marker = " ✅" if correct_idx is not None and i == correct_idx else ""
        lines.append(f"{e} {opt}{marker}")
    if explication:
        lines.append(f"\n💡 {explication}")
    if stats:
        lines.append(f"\n📊 {stats['correct']}/{stats['total']} correct ({stats['rate']}%)")
    return "\n".join(lines)

def format_calendrier(cal_data):
    jours_emojis = {"Lundi": "1️⃣", "Mardi": "2️⃣", "Mercredi": "3️⃣",
                    "Jeudi": "4️⃣", "Vendredi": "5️⃣", "Samedi": "6️⃣", "Dimanche": "7️⃣"}
    lines = ["📅 <b>CALENDRIER DES SORTIES</b>", "", VT["separator_short"], ""]
    for jour, entries in cal_data.items():
        if entries:
            e = jours_emojis.get(jour, "📌")
            lines.append(f"{e} <b>{jour}</b>")
            for entry in entries:
                heure = entry.get("heure", "")
                h_str = f" à {heure}" if heure else ""
                lines.append(f"   🎌 {entry.get('anime_titre', '?')}{h_str}")
            lines.append("")
    lines += [VT["separator_short"], "📡 @animeFR2026"]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLAVIERS (adaptés mobile)
# ═══════════════════════════════════════════════════════════

def build_anime_keyboard(anime_id, lien_externe=None, likes=0, dislikes=0, views=0, is_fav=False, nb_favs=0):
    fav_text = f"💛 ({nb_favs})" if is_fav else f"🤍 ({nb_favs})"
    # Ligne 1 : interactions principales (compact pour mobile)
    buttons = [
        [
            InlineKeyboardButton(f"❤️ {likes}", callback_data=f"like_{anime_id}"),
            InlineKeyboardButton(f"👎 {dislikes}", callback_data=f"dislike_{anime_id}"),
            InlineKeyboardButton(f"👁️ {views}", callback_data=f"view_{anime_id}"),
        ],
        [
            InlineKeyboardButton(fav_text, callback_data=f"fav_{anime_id}"),
            InlineKeyboardButton("⭐ Noter", callback_data=f"rate_{anime_id}"),
            InlineKeyboardButton("📊", callback_data=f"info_{anime_id}"),
        ],
        [
            InlineKeyboardButton("🔍 Similaires", callback_data=f"similar_{anime_id}"),
            InlineKeyboardButton("📂 Catégorie", callback_data=f"category_{anime_id}"),
        ],
    ]
    if lien_externe and lien_externe.startswith("http"):
        buttons.append([InlineKeyboardButton("🌐 MAL", url=lien_externe)])
    buttons.append([InlineKeyboardButton("📡 @animeFR2026", url="https://t.me/animeFR2026")])
    return InlineKeyboardMarkup(buttons)

def build_confirm_delete_keyboard(anime_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Supprimer", callback_data=f"confirm_delete_{anime_id}"),
        InlineKeyboardButton("❌ Annuler", callback_data=f"cancel_delete_{anime_id}"),
    ]])

def build_search_result_keyboard(results):
    buttons = []
    for i, a in enumerate(results[:5]):
        titre = truncate(a.get("title", "?"), 30)
        mal_id = a.get("mal_id", 0)
        score = a.get("score") or "?"
        buttons.append([InlineKeyboardButton(f"{i+1}. {titre} ⭐{score}", callback_data=f"select_jikan_{mal_id}")])
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
    buttons = []
    row = []
    for s in STATUTS:
        row.append(InlineKeyboardButton(s, callback_data=f"statut_{s}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def build_template_keyboard():
    templates = [
        ("📋 Standard", "tpl_standard"), ("📦 Compact", "tpl_compact"),
        ("💎 Premium", "tpl_premium"), ("✨ Minimal", "tpl_minimal"),
        ("⚡ Neon", "tpl_neon"), ("📱 Mobile", "tpl_mobile"),
        ("🌿 Elegant", "tpl_elegant"),
    ]
    buttons = []
    row = []
    for label, data in templates:
        row.append(InlineKeyboardButton(label, callback_data=data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def build_rating_keyboard(anime_id):
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"rating_{anime_id}_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_rating")])
    return InlineKeyboardMarkup(buttons)

def build_sondage_keyboard(sondage_id, options):
    emojis = ["🅰️", "🅱️", "🅲", "🅳", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    buttons = []
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i+1}"
        buttons.append([InlineKeyboardButton(f"{e} {truncate(opt, 25)}", callback_data=f"svote_{sondage_id}_{i}")])
    buttons.append([InlineKeyboardButton("📊 Résultats", callback_data=f"sresult_{sondage_id}")])
    return InlineKeyboardMarkup(buttons)

def build_quiz_keyboard(quiz_id, options):
    emojis = ["🅰️", "🅱️", "🅲", "🅳"]
    buttons = []
    for i, opt in enumerate(options):
        e = emojis[i] if i < len(emojis) else f"{i+1}"
        buttons.append([InlineKeyboardButton(f"{e} {truncate(opt, 25)}", callback_data=f"qanswer_{quiz_id}_{i}")])
    return InlineKeyboardMarkup(buttons)

def build_admin_menu_keyboard():
    """Menu admin rapide accessible depuis mobile."""
    buttons = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton("📋 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
         InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maint")],
        [InlineKeyboardButton("📤 Export", callback_data="admin_export"),
         InlineKeyboardButton("🗑️ Purge", callback_data="admin_purge")],
        [InlineKeyboardButton("👥 Admins", callback_data="admin_list"),
         InlineKeyboardButton("🚫 Blacklist", callback_data="admin_bl")],
        [InlineKeyboardButton("❌ Fermer", callback_data="admin_close")],
    ]
    return InlineKeyboardMarkup(buttons)

def build_pagination_keyboard(current_page, total_pages, prefix="page"):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}_{current_page - 1}"))
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}_{current_page + 1}"))
    return InlineKeyboardMarkup([buttons])


# ═══════════════════════════════════════════════════════════
# FORMATS SPÉCIAUX
# ═══════════════════════════════════════════════════════════

def format_notification_episode(titre, episode, date=""):
    return (
        f"🔔 <b>NOUVEL ÉPISODE !</b>\n\n"
        f"🎌 <b>{titre}</b>\n"
        f"📺 Épisode <b>{episode}</b>\n"
        + (f"📅 {date}\n" if date else "")
        + f"\n📡 @animeFR2026"
    )

def format_log_entry(log):
    ts = log.get("timestamp", "")[:16]
    level = log.get("level", "INFO")
    le = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌", "DEBUG": "🔧"}.get(level, "📋")
    return f"{le} <code>{ts}</code>\n   👤 @{log.get('username', '?')} │ {log['action']}\n   📝 {log.get('details', '')}"

def format_post_programme(post):
    data = {}
    try:
        data = json.loads(post.get("data_json", "{}"))
    except Exception:
        pass
    titre = data.get("titre", "Inconnu")
    scheduled = post.get("scheduled_at", "?")
    publie = "✅ Publié" if post.get("publie") else "⏳ En attente"
    repeat = post.get("repeat_mode", "none")
    repeat_str = f"\n🔄 Répétition : {repeat}" if repeat != "none" else ""
    return f"🆔 <code>{post['id']}</code> — <b>{titre}</b>\n⏰ {scheduled}\n📌 {publie}{repeat_str}"

def format_backup_info(filepath, size):
    from datetime import datetime
    return (
        f"💾 <b>Backup créé</b>\n\n"
        f"📁 <code>{filepath}</code>\n"
        f"📏 <b>{size / 1024:.1f} Ko</b>\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

def format_stats_dashboard(stats, daily):
    text = (
        f"📊 <b>DASHBOARD — AnimeFR v5</b>\n"
        f"{VT['separator_short']}\n\n"
        f"🎌 Anime : <b>{stats['total_animes']}</b>\n"
        f"❤️ Likes : <b>{stats['total_likes']}</b>\n"
        f"👁️ Vues : <b>{stats['total_views']}</b>\n"
        f"👥 Admins : <b>{stats['total_admins']}</b>\n"
        f"⏰ En file : <b>{stats['posts_en_attente']}</b>\n"
        f"🔔 Suivis : <b>{stats['total_suivis']}</b>\n"
        f"💛 Favoris : <b>{stats['total_favoris']}</b>\n"
        f"📊 Sondages : <b>{stats['total_sondages']}</b>\n"
        f"🧠 Quiz : <b>{stats['total_quiz']}</b>\n"
        f"⭐ Notes : <b>{stats['total_ratings']}</b>\n"
        f"📝 Edits : <b>{stats['total_edits']}</b>\n"
        f"📢 Broadcasts : <b>{stats['total_broadcasts']}</b>\n"
        f"📋 Logs : <b>{stats['total_logs']}</b>\n"
        f"\n{VT['separator_short']}\n"
        f"📈 <b>7 derniers jours</b>\n\n"
    )
    if daily:
        mx = max((d.get("posts", 0) for d in daily), default=1) or 1
        for d in reversed(daily):
            ds = d.get("date", "?")[5:]
            p = d.get("posts", 0)
            l = d.get("likes", 0)
            text += f"  {ds} {make_progress_bar(p, mx, 6)} {p}p/{l}❤️\n"
    else:
        text += "  <i>Pas encore de données</i>\n"
    text += f"\n{VT['separator_short']}"
    return text

def format_whats_new():
    return (
        f"🆕 <b>QUOI DE NEUF — v5.0</b>\n"
        f"{VT['separator_short']}\n\n"
        f"📱 <b>MOBILE</b>\n"
        f"• Template Mobile optimisé\n"
        f"• Template Elegant raffiné\n"
        f"• Boutons compacts adaptés\n"
        f"• Listes courtes pour mobile\n"
        f"• Pagination sur toutes les listes\n"
        f"• Menu admin rapide /panel\n\n"
        f"🛠️ <b>ADMIN & TECHNIQUE</b>\n"
        f"• Export/Import JSON complet\n"
        f"• Broadcast vers le canal\n"
        f"• Purge des anciennes données\n"
        f"• Historique des modifications\n"
        f"• Épingler des anime (priorité)\n"
        f"• Posts récurrents (répétition)\n"
        f"• Profils utilisateurs\n"
        f"• Sessions admin multi-device\n\n"
        f"🎨 <b>VISUEL</b>\n"
        f"• Nouveau template Mobile 📱\n"
        f"• Nouveau template Elegant 🌿\n"
        f"• Dashboard allégé et lisible\n"
        f"• Notifications épurées\n"
        f"• Compteur dislikes visible\n"
        f"• Compteur favoris sur bouton\n\n"
        f"⚡ <b>OPTIMISATIONS</b>\n"
        f"• PRAGMA mmap_size (256 Mo)\n"
        f"• PRAGMA temp_store MEMORY\n"
        f"• Votes mutuellement exclusifs\n"
        f"• Historique auto des edits\n"
        f"• Purge auto données anciennes\n"
        f"• Pagination mémoire-efficace\n\n"
        f"{VT['separator_short']}\n"
        f"📡 @animeFR2026 — Bot v5.0"
    )

def format_broadcast(message, sent_by_name="Admin"):
    return (
        f"📢 <b>ANNONCE</b>\n"
        f"{VT['separator_short']}\n\n"
        f"{message}\n\n"
        f"{VT['separator_short']}\n"
        f"👤 {sent_by_name} │ 📡 @animeFR2026"
    )

def format_edit_history(edits):
    if not edits:
        return "📝 Aucune modification enregistrée."
    lines = ["📝 <b>HISTORIQUE DES MODIFICATIONS</b>\n"]
    for e in edits[:10]:
        ts = e.get("edited_at", "?")[:16]
        field = e.get("field", "?")
        lines.append(f"  <code>{ts}</code> │ <b>{field}</b>\n   {truncate(str(e.get('old_value', '')), 40)} → {truncate(str(e.get('new_value', '')), 40)}")
    return "\n".join(lines)
