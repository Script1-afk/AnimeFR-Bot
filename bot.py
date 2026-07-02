# ============================================================
# bot.py — Fichier principal AnimeFR Bot v6.0
# ============================================================

import asyncio
import json
import logging
import os
import math
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

import database as db
from config import (
    BOT_TOKEN, CHANNEL_ID, CATEGORIES, STATUTS, ROLES, PERMISSIONS,
    BOT_VERSION, SCHEDULER_INTERVAL, MAX_SEARCH_RESULTS, MAX_LIST_ITEMS,
    LOG_PATH, LOG_MAX_SIZE, LOG_BACKUP_COUNT, BACKUP_INTERVAL,
    MAINTENANCE_MESSAGE, VISUAL_THEME as VT, EPISODE_CHECK_INTERVAL,
    MAX_FAVORITES, MAX_POLL_OPTIONS, MAX_QUIZ_OPTIONS, MAX_BROADCAST_LENGTH,
    MOBILE_MODE, AUTO_PUBLISH_INTERVAL, AUTO_PUBLISH_ENABLED,
    AUTO_PUBLISH_TEMPLATE, AUTO_PUBLISH_SOURCE, ANIME_SOURCES,
)
from formatter import (
    format_anime_post, format_anime_short, format_anime_short_mobile,
    build_anime_keyboard, build_confirm_delete_keyboard, build_search_result_keyboard,
    build_categorie_keyboard, build_statut_keyboard, build_template_keyboard,
    build_rating_keyboard, build_sondage_keyboard, build_quiz_keyboard,
    build_admin_menu_keyboard, build_pagination_keyboard,
    format_notification_episode, format_log_entry, format_post_programme,
    format_stats_dashboard, format_backup_info, format_whats_new,
    format_compare, format_sondage, format_quiz, format_calendrier,
    format_broadcast, format_edit_history,
    make_star_bar, get_rank_emoji, truncate,
)
from jikan import (
    search_anime, get_anime_by_id, get_anime_characters,
    get_current_season_anime, get_upcoming_anime,
    get_top_anime, parse_jikan_anime, get_anime_episodes
)
from openai_helper import (
    generate_anime_description, generate_episode_notification,
    generate_weekly_recap, suggest_similar_animes
)
from sources import (
    generate_watch_links, get_primary_watch_link, get_episode_link,
    build_watch_buttons, find_best_source, slugify
)

# ── Logging avec rotation ────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("backups", exist_ok=True)
os.makedirs("media", exist_ok=True)
os.makedirs("data/exports", exist_ok=True)
os.makedirs("data/imports", exist_ok=True)

logger = logging.getLogger("AnimeFR")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(
    LOG_PATH, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

# ── Conversation states ──────────────────────────────────────
(TITRE, TITRE_ORIGINAL, SYNOPSIS, PERSONNAGES, STUDIO, DATE_SORTIE,
 NB_EPISODES, STATUT_CHOICE, GENRES, NOTE, AVIS, IMAGE_URL,
 LIEN_EXTERNE, CATEGORIE_CHOICE, TAGS_INPUT, TEMPLATE_CHOICE,
 CONFIRM_POST, PROGRAMME_DATE, PROGRAMME_HEURE) = range(19)

EDIT_FIELD, EDIT_VALUE = 19, 20
SEARCH_QUERY = 21
ADD_ADMIN_ID, ADD_ADMIN_ROLE = 22, 23
REMOVE_ADMIN_ID = 24
BLACKLIST_ID, BLACKLIST_RAISON = 25, 26

SONDAGE_QUESTION, SONDAGE_OPTIONS = 27, 28
QUIZ_QUESTION, QUIZ_OPTIONS, QUIZ_CORRECT, QUIZ_EXPLICATION = 29, 30, 31, 32
CAL_TITRE, CAL_JOUR, CAL_HEURE = 33, 34, 35
COMPARE_A, COMPARE_B = 36, 37
FILTER_CAT, FILTER_STATUT, FILTER_NOTE, FILTER_SORT = 38, 39, 40, 41
BROADCAST_MSG = 42
AUTO_TITRE = 43
AUTO_CONFIRM = 44


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _uid(update: Update) -> int:
    return update.effective_user.id

def _uname(update: Update) -> str:
    u = update.effective_user
    return u.username or u.first_name or str(u.id)

def _is_maintenance(user_id: int) -> bool:
    mode = db.get_setting("maintenance", "0")
    if mode == "1":
        admin = db.get_admin(user_id)
        return not (admin and admin["role"] == "superadmin")
    return False

async def _check_perm(update: Update, perm: str) -> bool:
    uid = _uid(update)
    if db.is_blacklisted(uid):
        await update.effective_message.reply_text("🚫 Vous êtes blacklisté.")
        return False
    admin = db.get_admin(uid)
    if not admin:
        await update.effective_message.reply_text("🔒 Accès refusé.")
        return False
    role = admin["role"]
    if perm not in PERMISSIONS.get(role, []):
        await update.effective_message.reply_text(f"🔒 Permission '{perm}' requise.")
        return False
    return True

async def _send_or_reply(update: Update, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    msg = update.effective_message
    # Tronquer si trop long pour Telegram (4096 chars)
    if len(text) > 4000:
        text = text[:3997] + "…"
    await msg.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup,
                         disable_web_page_preview=True)


# ═══════════════════════════════════════════════════════════
# COMMANDES DE BASE
# ═══════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return
    db.update_user_profile(_uid(update), _uname(update))
    text = (
        f"🎌 <b>AnimeFR Bot v{BOT_VERSION}</b>\n\n"
        f"Bienvenue ! Ce bot gère le canal @animeFR2026.\n\n"
        f"📱 <b>Commandes rapides :</b>\n"
        f"/help — Aide complète\n"
        f"/quoideneuf — Nouveautés v6\n"
        f"/panel — Menu admin rapide\n"
        f"/recherche — Chercher un anime\n"
        f"/toplikes — Classement\n\n"
        f"📡 @animeFR2026"
    )
    await _send_or_reply(update, text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return
    text = (
        f"📖 <b>AIDE — AnimeFR Bot v{BOT_VERSION}</b>\n\n"
        f"<b>📝 Publication</b>\n"
        f"/poster — Publier un anime\n"
        f"/modifier ID — Modifier\n"
        f"/supprimer ID — Supprimer\n"
        f"/programmes — Posts programmés\n\n"
        f"<b>🔍 Recherche</b>\n"
        f"/recherche — Chercher sur MAL\n"
        f"/chercher MOT — Recherche locale\n"
        f"/filtre — Recherche avancée\n"
        f"/anime ID — Fiche complète\n"
        f"/comparer — Comparer 2 anime\n\n"
        f"<b>📊 Classements</b>\n"
        f"/toplikes — Top likes\n"
        f"/topvues — Top vues\n"
        f"/topnotes — Top communauté\n"
        f"/categories — Par catégorie\n\n"
        f"<b>👥 Communauté</b>\n"
        f"/favoris — Mes favoris\n"
        f"/sondage — Créer un sondage\n"
        f"/quiz — Créer un quiz\n"
        f"/calendrier — Sorties\n\n"
        f"<b>🔔 Suivi</b>\n"
        f"/suivre TITRE — Suivre\n"
        f"/suivis — Mes suivis\n"
        f"/arretersuivi ID — Arrêter\n\n"
        f"<b>🛠️ Admin</b>\n"
        f"/panel — Menu rapide\n"
        f"/stats — Dashboard\n"
        f"/broadcast — Annonce\n"
        f"/export — Exporter les données\n"
        f"/import — Importer\n"
        f"/purge — Nettoyer\n"
        f"/epingler ID — Épingler\n"
        f"/historique ID — Historique edits\n\n"
        f"<b>🤖 IA & Auto-publication (v6)</b>\n"
        f"/auto TITRE — Publier un anime automatiquement (IA)\n"
        f"/autopublish — Activer/désactiver l'auto-publication\n"
        f"/aisuggest ID — Suggestions similaires (IA)\n"
        f"/airecap — Récap hebdo généré par IA\n"
        f"/sources TITRE — Liens de visionnage\n"
    )
    await _send_or_reply(update, text)

async def whats_new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_or_reply(update, format_whats_new())


# ═══════════════════════════════════════════════════════════
# PANEL ADMIN (menu rapide mobile)
# ═══════════════════════════════════════════════════════════

async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "stats"):
        return
    text = f"🛠️ <b>Panel Admin — v{BOT_VERSION}</b>\n\nSélectionnez une action :"
    await _send_or_reply(update, text, reply_markup=build_admin_menu_keyboard())


# ═══════════════════════════════════════════════════════════
# POSTER UN ANIME (conversation 16 étapes)
# ═══════════════════════════════════════════════════════════

async def poster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return ConversationHandler.END
    if not await _check_perm(update, "poster"):
        return ConversationHandler.END
    context.user_data["anime"] = {}
    await _send_or_reply(update, "🎌 <b>Nouveau post</b>\n\n1/16 — Titre de l'anime :")
    return TITRE

async def poster_titre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["titre"] = update.message.text.strip()
    await _send_or_reply(update, "2/16 — Titre original (japonais) :\n<i>Envoyez - pour passer</i>")
    return TITRE_ORIGINAL

async def poster_titre_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["titre_original"] = "" if val == "-" else val
    await _send_or_reply(update, "3/16 — Synopsis :")
    return SYNOPSIS

async def poster_synopsis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["synopsis"] = update.message.text.strip()
    await _send_or_reply(update, "4/16 — Personnages principaux :\n<i>Envoyez - pour passer</i>")
    return PERSONNAGES

async def poster_personnages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["personnages"] = "" if val == "-" else val
    await _send_or_reply(update, "5/16 — Studio d'animation :")
    return STUDIO

async def poster_studio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["studio"] = update.message.text.strip()
    await _send_or_reply(update, "6/16 — Date de sortie :")
    return DATE_SORTIE

async def poster_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["date_sortie"] = update.message.text.strip()
    await _send_or_reply(update, "7/16 — Nombre d'épisodes :")
    return NB_EPISODES

async def poster_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["nb_episodes"] = update.message.text.strip()
    await _send_or_reply(update, "8/16 — Statut :", reply_markup=build_statut_keyboard())
    return STATUT_CHOICE

async def poster_statut_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    statut = query.data.replace("statut_", "")
    context.user_data["anime"]["statut"] = statut
    await query.edit_message_text(f"✅ Statut : {statut}\n\n9/16 — Genres (séparés par des virgules) :",
                                   parse_mode=ParseMode.HTML)
    return GENRES

async def poster_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["genres"] = update.message.text.strip()
    await _send_or_reply(update, "10/16 — Note /10 :")
    return NOTE

async def poster_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["note"] = update.message.text.strip()
    await _send_or_reply(update, "11/16 — Votre avis :\n<i>Envoyez - pour passer</i>")
    return AVIS

async def poster_avis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["avis"] = "" if val == "-" else val
    await _send_or_reply(update, "12/16 — URL de l'image :\n<i>Envoyez - pour passer</i>")
    return IMAGE_URL

async def poster_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["image_url"] = "" if val == "-" else val
    await _send_or_reply(update, "13/16 — Lien externe (MAL, AniList...) :\n<i>Envoyez - pour passer</i>")
    return LIEN_EXTERNE

async def poster_lien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["lien_externe"] = "" if val == "-" else val
    await _send_or_reply(update, "14/16 — Catégorie :", reply_markup=build_categorie_keyboard(CATEGORIES))
    return CATEGORIE_CHOICE

async def poster_categorie_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("cat_", "")
    context.user_data["anime"]["categorie"] = cat
    await query.edit_message_text(f"✅ Catégorie : {cat}\n\n15/16 — Tags (séparés par des virgules) :\n<i>Envoyez - pour passer</i>",
                                   parse_mode=ParseMode.HTML)
    return TAGS_INPUT

async def poster_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["anime"]["tags"] = "" if val == "-" else val
    await _send_or_reply(update, "16/16 — Template :", reply_markup=build_template_keyboard())
    return TEMPLATE_CHOICE

async def poster_template_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tpl = query.data.replace("tpl_", "")
    context.user_data["anime"]["template"] = tpl
    data = context.user_data["anime"]
    preview = format_anime_post(data, tpl)
    if len(preview) > 3500:
        preview = preview[:3500] + "…"
    text = f"📋 <b>APERÇU</b>\n\n{preview}\n\n━━━━━━━━━━━━\n\n✅ Publier maintenant\n⏰ Programmer\n❌ Annuler"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Publier", callback_data="post_now"),
         InlineKeyboardButton("⏰ Programmer", callback_data="post_schedule")],
        [InlineKeyboardButton("❌ Annuler", callback_data="post_cancel")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb,
                                   disable_web_page_preview=True)
    return CONFIRM_POST

async def poster_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "post_cancel":
        await query.edit_message_text("❌ Publication annulée.")
        return ConversationHandler.END

    if action == "post_schedule":
        await query.edit_message_text("📅 Date de publication (YYYY-MM-DD) :", parse_mode=ParseMode.HTML)
        return PROGRAMME_DATE

    # post_now
    data = context.user_data["anime"]
    data["posted_by"] = _uid(update)
    tpl = data.get("template", "standard")
    text = format_anime_post(data, tpl)

    try:
        if data.get("image_url") and data["image_url"].startswith("http"):
            caption = text[:1024] if len(text) > 1024 else text
            msg = await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=data["image_url"],
                caption=caption, parse_mode=ParseMode.HTML
            )
        else:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        data["message_id"] = msg.message_id
        data["chat_id"] = str(msg.chat_id)
        anime_id = db.save_anime(data)

        # Ajouter les boutons
        nb_favs = db.count_favoris(anime_id)
        kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0, 0, False, nb_favs)
        if data.get("image_url") and data["image_url"].startswith("http"):
            await msg.edit_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await msg.edit_reply_markup(reply_markup=kb)

        db.add_log(_uid(update), _uname(update), "POST", f"Anime #{anime_id}: {data['titre']}")
        db.record_daily_stats()
        await query.edit_message_text(f"✅ Publié ! ID: <code>{anime_id}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Erreur publication: {e}")
        await query.edit_message_text(f"❌ Erreur : {e}")

    return ConversationHandler.END

async def poster_programme_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await _send_or_reply(update, "❌ Format invalide. Utilisez YYYY-MM-DD :")
        return PROGRAMME_DATE
    context.user_data["schedule_date"] = date_str
    await _send_or_reply(update, "⏰ Heure de publication (HH:MM) :")
    return PROGRAMME_HEURE

async def poster_programme_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    heure_str = update.message.text.strip()
    try:
        datetime.strptime(heure_str, "%H:%M")
    except ValueError:
        await _send_or_reply(update, "❌ Format invalide. Utilisez HH:MM :")
        return PROGRAMME_HEURE

    date_str = context.user_data["schedule_date"]
    scheduled_at = f"{date_str} {heure_str}"

    # Vérifier que c'est dans le futur
    if datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M") <= datetime.now():
        await _send_or_reply(update, "❌ La date doit être dans le futur. Nouvelle date (YYYY-MM-DD) :")
        return PROGRAMME_DATE

    data = context.user_data["anime"]
    data["posted_by"] = _uid(update)
    post_id = db.add_post_programme(data, scheduled_at, _uid(update))
    db.add_log(_uid(update), _uname(update), "PROGRAMME", f"Post #{post_id} pour {scheduled_at}")
    await _send_or_reply(update, f"⏰ Programmé pour <b>{scheduled_at}</b>\nID: <code>{post_id}</code>")
    return ConversationHandler.END

async def poster_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_or_reply(update, "❌ Publication annulée.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# MODIFIER UN ANIME
# ═══════════════════════════════════════════════════════════

async def modifier_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "modifier"):
        return ConversationHandler.END
    args = context.args
    if not args:
        await _send_or_reply(update, "Usage : /modifier <ID>")
        return ConversationHandler.END
    try:
        anime_id = int(args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return ConversationHandler.END
    anime = db.get_anime(anime_id)
    if not anime:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return ConversationHandler.END
    context.user_data["edit_id"] = anime_id
    fields = [
        "titre", "titre_original", "synopsis", "personnages", "studio",
        "date_sortie", "nb_episodes", "statut", "genres", "note",
        "avis", "image_url", "lien_externe", "categorie", "tags", "template"
    ]
    buttons = []
    row = []
    for f in fields:
        row.append(InlineKeyboardButton(f, callback_data=f"editf_{f}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="editf_cancel")])
    await _send_or_reply(update, f"✏️ Modifier <b>{anime['titre']}</b>\n\nChoisissez le champ :",
                         reply_markup=InlineKeyboardMarkup(buttons))
    return EDIT_FIELD

async def modifier_field_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("editf_", "")
    if field == "cancel":
        await query.edit_message_text("❌ Modification annulée.")
        return ConversationHandler.END
    context.user_data["edit_field"] = field
    await query.edit_message_text(f"✏️ Nouvelle valeur pour <b>{field}</b> :", parse_mode=ParseMode.HTML)
    return EDIT_VALUE

async def modifier_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    anime_id = context.user_data["edit_id"]
    field = context.user_data["edit_field"]
    value = update.message.text.strip()
    db.update_anime(anime_id, field, value, _uid(update))
    db.add_log(_uid(update), _uname(update), "EDIT", f"#{anime_id} {field} → {value[:50]}")
    await _send_or_reply(update, f"✅ <b>{field}</b> mis à jour pour l'anime #{anime_id}.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# RECHERCHE MAL
# ═══════════════════════════════════════════════════════════

async def recherche_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return ConversationHandler.END
    await _send_or_reply(update, "🔍 Rechercher un anime sur MAL :\n<i>Tapez le titre</i>")
    return SEARCH_QUERY

async def recherche_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    results = await search_anime(query_text, MAX_SEARCH_RESULTS)
    if not results:
        await _send_or_reply(update, "❌ Aucun résultat.")
        return ConversationHandler.END
    context.user_data["search_results"] = results
    kb = build_search_result_keyboard(results)
    await _send_or_reply(update, "📋 <b>Résultats :</b>", reply_markup=kb)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# ADMIN : AJOUTER / RETIRER
# ═══════════════════════════════════════════════════════════

async def addadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "admin"):
        return ConversationHandler.END
    await _send_or_reply(update, "👤 ID Telegram du nouvel admin :")
    return ADD_ADMIN_ID

async def addadmin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return ConversationHandler.END
    context.user_data["new_admin_id"] = uid
    roles = ["admin", "moderateur", "editeur"]
    buttons = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in roles]
    await _send_or_reply(update, "Rôle :", reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_ADMIN_ROLE

async def addadmin_role_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.replace("role_", "")
    uid = context.user_data["new_admin_id"]
    db.add_admin(uid, f"user_{uid}", role, _uid(update))
    db.add_log(_uid(update), _uname(update), "ADD_ADMIN", f"ID {uid} → {role}")
    await query.edit_message_text(f"✅ Admin ajouté : {uid} ({role})")
    return ConversationHandler.END

async def removeadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "admin"):
        return
    args = context.args
    if not args:
        await _send_or_reply(update, "Usage : /removeadmin <ID>")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    db.remove_admin(uid)
    db.add_log(_uid(update), _uname(update), "REMOVE_ADMIN", f"ID {uid}")
    await _send_or_reply(update, f"✅ Admin {uid} retiré.")


# ═══════════════════════════════════════════════════════════
# BLACKLIST
# ═══════════════════════════════════════════════════════════

async def blacklist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return ConversationHandler.END
    await _send_or_reply(update, "🚫 ID Telegram à blacklister :")
    return BLACKLIST_ID

async def blacklist_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return ConversationHandler.END
    context.user_data["bl_id"] = uid
    await _send_or_reply(update, "Raison :")
    return BLACKLIST_RAISON

async def blacklist_raison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = context.user_data["bl_id"]
    raison = update.message.text.strip()
    db.add_blacklist(uid, f"user_{uid}", raison, _uid(update))
    db.add_log(_uid(update), _uname(update), "BLACKLIST", f"ID {uid}: {raison}")
    await _send_or_reply(update, f"🚫 {uid} blacklisté.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# SONDAGE
# ═══════════════════════════════════════════════════════════

async def sondage_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "sondage"):
        return ConversationHandler.END
    await _send_or_reply(update, "📊 Question du sondage :")
    return SONDAGE_QUESTION

async def sondage_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sondage_q"] = update.message.text.strip()
    await _send_or_reply(update, f"Options (une par ligne, max {MAX_POLL_OPTIONS}) :")
    return SONDAGE_OPTIONS

async def sondage_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = [o.strip() for o in update.message.text.strip().split("\n") if o.strip()][:MAX_POLL_OPTIONS]
    if len(options) < 2:
        await _send_or_reply(update, "❌ Minimum 2 options.")
        return SONDAGE_OPTIONS
    question = context.user_data["sondage_q"]
    sondage_id = db.create_sondage(question, options, _uid(update))
    text = format_sondage(question, options)
    kb = build_sondage_keyboard(sondage_id, options)
    msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=text,
                                          parse_mode=ParseMode.HTML, reply_markup=kb)
    db.add_log(_uid(update), _uname(update), "SONDAGE", f"#{sondage_id}: {question}")
    await _send_or_reply(update, f"✅ Sondage #{sondage_id} publié !")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# QUIZ
# ═══════════════════════════════════════════════════════════

async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "quiz"):
        return ConversationHandler.END
    await _send_or_reply(update, "🧠 Question du quiz :")
    return QUIZ_QUESTION

async def quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz_q"] = update.message.text.strip()
    await _send_or_reply(update, f"Options (une par ligne, max {MAX_QUIZ_OPTIONS}) :")
    return QUIZ_OPTIONS

async def quiz_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = [o.strip() for o in update.message.text.strip().split("\n") if o.strip()][:MAX_QUIZ_OPTIONS]
    if len(options) < 2:
        await _send_or_reply(update, "❌ Minimum 2 options.")
        return QUIZ_OPTIONS
    context.user_data["quiz_opts"] = options
    emojis = ["🅰️", "🅱️", "🅲", "🅳"]
    opts_text = "\n".join(f"{emojis[i]} {o}" for i, o in enumerate(options))
    await _send_or_reply(update, f"Bonne réponse (numéro 1-{len(options)}) :\n\n{opts_text}")
    return QUIZ_CORRECT

async def quiz_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text.strip()) - 1
    except ValueError:
        await _send_or_reply(update, "❌ Numéro invalide.")
        return QUIZ_CORRECT
    options = context.user_data["quiz_opts"]
    if idx < 0 or idx >= len(options):
        await _send_or_reply(update, "❌ Hors limites.")
        return QUIZ_CORRECT
    context.user_data["quiz_correct"] = idx
    await _send_or_reply(update, "💡 Explication (optionnel, envoyez - pour passer) :")
    return QUIZ_EXPLICATION

async def quiz_explication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    explication = "" if val == "-" else val
    question = context.user_data["quiz_q"]
    options = context.user_data["quiz_opts"]
    correct = context.user_data["quiz_correct"]
    quiz_id = db.create_quiz(question, options, correct, explication, _uid(update))
    text = format_quiz(question, options)
    kb = build_quiz_keyboard(quiz_id, options)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=text,
                                    parse_mode=ParseMode.HTML, reply_markup=kb)
    db.add_log(_uid(update), _uname(update), "QUIZ", f"#{quiz_id}: {question}")
    await _send_or_reply(update, f"✅ Quiz #{quiz_id} publié !")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# CALENDRIER
# ═══════════════════════════════════════════════════════════

async def addcalendrier_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "calendrier"):
        return ConversationHandler.END
    await _send_or_reply(update, "📅 Titre de l'anime :")
    return CAL_TITRE

async def cal_titre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cal_titre"] = update.message.text.strip()
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    buttons = [[InlineKeyboardButton(j, callback_data=f"calj_{j}")] for j in jours]
    await _send_or_reply(update, "Jour de diffusion :", reply_markup=InlineKeyboardMarkup(buttons))
    return CAL_JOUR

async def cal_jour_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jour = query.data.replace("calj_", "")
    context.user_data["cal_jour"] = jour
    await query.edit_message_text(f"✅ {jour}\n\nHeure de diffusion (HH:MM) :\n<i>Envoyez - pour passer</i>",
                                   parse_mode=ParseMode.HTML)
    return CAL_HEURE

async def cal_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    heure = "" if val == "-" else val
    titre = context.user_data["cal_titre"]
    jour = context.user_data["cal_jour"]
    db.add_calendrier(titre, jour, heure, added_by=_uid(update))
    db.add_log(_uid(update), _uname(update), "CALENDRIER", f"{titre} → {jour} {heure}")
    await _send_or_reply(update, f"✅ {titre} ajouté au calendrier ({jour} {heure})")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# COMPARER
# ═══════════════════════════════════════════════════════════

async def comparer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return ConversationHandler.END
    await _send_or_reply(update, "⚔️ ID du premier anime :")
    return COMPARE_A

async def comparer_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["compare_a"] = int(update.message.text.strip())
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return ConversationHandler.END
    await _send_or_reply(update, "ID du second anime :")
    return COMPARE_B

async def comparer_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        id_b = int(update.message.text.strip())
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return ConversationHandler.END
    anime_a = db.get_anime(context.user_data["compare_a"])
    anime_b = db.get_anime(id_b)
    if not anime_a or not anime_b:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return ConversationHandler.END
    text = format_compare(anime_a, anime_b)
    await _send_or_reply(update, text)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# FILTRE (recherche avancée)
# ═══════════════════════════════════════════════════════════

async def filtre_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_maintenance(_uid(update)):
        await _send_or_reply(update, MAINTENANCE_MESSAGE)
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(c, callback_data=f"fcat_{c}")] for c in CATEGORIES[:10]]
    buttons.append([InlineKeyboardButton("⏭️ Toutes", callback_data="fcat_all")])
    await _send_or_reply(update, "🔍 <b>Filtre</b>\n\nCatégorie :", reply_markup=InlineKeyboardMarkup(buttons))
    return FILTER_CAT

async def filtre_cat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("fcat_", "")
    context.user_data["filter_cat"] = None if cat == "all" else cat
    buttons = [[InlineKeyboardButton(s, callback_data=f"fstat_{s}")] for s in STATUTS]
    buttons.append([InlineKeyboardButton("⏭️ Tous", callback_data="fstat_all")])
    await query.edit_message_text("Statut :", reply_markup=InlineKeyboardMarkup(buttons))
    return FILTER_STATUT

async def filtre_statut_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stat = query.data.replace("fstat_", "")
    context.user_data["filter_statut"] = None if stat == "all" else stat
    await query.edit_message_text("Note minimum (1-10) :\n<i>Envoyez 0 pour ignorer</i>", parse_mode=ParseMode.HTML)
    return FILTER_NOTE

async def filtre_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = float(update.message.text.strip())
    except ValueError:
        n = 0
    context.user_data["filter_note"] = n if n > 0 else None
    buttons = [
        [InlineKeyboardButton("❤️ Likes", callback_data="fsort_likes"),
         InlineKeyboardButton("👁️ Vues", callback_data="fsort_views")],
        [InlineKeyboardButton("⭐ Note", callback_data="fsort_note"),
         InlineKeyboardButton("📅 Date", callback_data="fsort_date")],
        [InlineKeyboardButton("👥 Communauté", callback_data="fsort_communaute")],
    ]
    await _send_or_reply(update, "Trier par :", reply_markup=InlineKeyboardMarkup(buttons))
    return FILTER_SORT

async def filtre_sort_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sort = query.data.replace("fsort_", "")
    results = db.filter_animes(
        categorie=context.user_data.get("filter_cat"),
        statut=context.user_data.get("filter_statut"),
        note_min=context.user_data.get("filter_note"),
        sort_by=sort
    )
    if not results:
        await query.edit_message_text("❌ Aucun résultat.")
        return ConversationHandler.END
    lines = [f"🔍 <b>Résultats ({len(results)})</b>\n"]
    for i, a in enumerate(results[:15], 1):
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a, i))
        else:
            lines.append(format_anime_short(a, i))
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# BROADCAST (v5)
# ═══════════════════════════════════════════════════════════

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "broadcast"):
        return ConversationHandler.END
    await _send_or_reply(update, f"📢 Message à diffuser (max {MAX_BROADCAST_LENGTH} caractères) :")
    return BROADCAST_MSG

async def broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    if len(message) > MAX_BROADCAST_LENGTH:
        await _send_or_reply(update, f"❌ Trop long ({len(message)}/{MAX_BROADCAST_LENGTH}).")
        return BROADCAST_MSG
    text = format_broadcast(message, _uname(update))
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
        db.save_broadcast(message, _uid(update))
        db.add_log(_uid(update), _uname(update), "BROADCAST", message[:100])
        await _send_or_reply(update, "✅ Annonce diffusée !")
    except Exception as e:
        await _send_or_reply(update, f"❌ Erreur : {e}")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# COMMANDES SIMPLES
# ═══════════════════════════════════════════════════════════

async def supprimer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "supprimer"):
        return
    args = context.args
    if not args:
        await _send_or_reply(update, "Usage : /supprimer <ID>")
        return
    try:
        anime_id = int(args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return
    kb = build_confirm_delete_keyboard(anime_id)
    await _send_or_reply(update, f"⚠️ Supprimer <b>{anime['titre']}</b> ?", reply_markup=kb)

async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await _send_or_reply(update, "Usage : /anime <ID>")
        return
    try:
        anime_id = int(args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return
    tpl = anime.get("template", "standard")
    text = format_anime_post(anime, tpl)
    nb_favs = db.count_favoris(anime_id)
    is_fav = db.is_favori(_uid(update), anime_id)
    kb = build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"],
                              anime["dislikes"], anime["views"], is_fav, nb_favs)
    await _send_or_reply(update, text, reply_markup=kb)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = await get_top_anime(10)
    if not results:
        await _send_or_reply(update, "❌ Erreur API.")
        return
    lines = ["🏆 <b>TOP 10 — MyAnimeList</b>\n"]
    for i, a in enumerate(results, 1):
        titre = truncate(a.get("title", "?"), 30)
        score = a.get("score") or "?"
        lines.append(f"{get_rank_emoji(i)} <b>{titre}</b> ⭐ {score}")
    await _send_or_reply(update, "\n".join(lines))

async def saison_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = await get_current_season_anime(10)
    if not results:
        await _send_or_reply(update, "❌ Aucun résultat.")
        return
    lines = ["📺 <b>ANIME DE LA SAISON</b>\n"]
    for i, a in enumerate(results, 1):
        titre = truncate(a.get("title", "?"), 30)
        score = a.get("score") or "?"
        lines.append(f"{i}. <b>{titre}</b> ⭐ {score}")
    await _send_or_reply(update, "\n".join(lines))

async def upcoming_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = await get_upcoming_anime(10)
    if not results:
        await _send_or_reply(update, "❌ Aucun résultat.")
        return
    lines = ["🔮 <b>ANIME À VENIR</b>\n"]
    for i, a in enumerate(results, 1):
        titre = truncate(a.get("title", "?"), 30)
        lines.append(f"{i}. <b>{titre}</b>")
    await _send_or_reply(update, "\n".join(lines))

async def toplikes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = db.get_top_animes("likes", 10)
    if not results:
        await _send_or_reply(update, "📭 Aucun anime publié.")
        return
    lines = ["❤️ <b>TOP 10 — Likes</b>\n"]
    for i, a in enumerate(results, 1):
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a, i))
        else:
            lines.append(format_anime_short(a, i))
    await _send_or_reply(update, "\n".join(lines))

async def topvues_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = db.get_top_animes("views", 10)
    if not results:
        await _send_or_reply(update, "📭 Aucun anime publié.")
        return
    lines = ["👁️ <b>TOP 10 — Vues</b>\n"]
    for i, a in enumerate(results, 1):
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a, i))
        else:
            lines.append(format_anime_short(a, i))
    await _send_or_reply(update, "\n".join(lines))

async def topnotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = db.get_top_animes("communaute", 10)
    if not results:
        await _send_or_reply(update, "📭 Aucun anime noté.")
        return
    lines = ["⭐ <b>TOP 10 — Notes communauté</b>\n"]
    for i, a in enumerate(results, 1):
        titre = truncate(a.get("titre", "?"), 25)
        score = a.get("score_communaute", 0)
        nb = a.get("nb_votes_communaute", 0)
        lines.append(f"{get_rank_emoji(i)} <b>{titre}</b> — {score}/10 ({nb} votes)")
    await _send_or_reply(update, "\n".join(lines))

async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = []
    row = []
    for cat in CATEGORIES:
        row.append(InlineKeyboardButton(cat, callback_data=f"listcat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await _send_or_reply(update, "📂 <b>Catégories</b>\n\nChoisissez :", reply_markup=InlineKeyboardMarkup(buttons))

async def liste_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
        except ValueError:
            pass
    per_page = 10
    all_animes = db.get_all_animes(limit=per_page, offset=(page - 1) * per_page)
    total = db.get_stats()["total_animes"]
    total_pages = max(1, math.ceil(total / per_page))
    if not all_animes:
        await _send_or_reply(update, "📭 Aucun anime publié.")
        return
    lines = [f"📋 <b>LISTE</b> (page {page}/{total_pages})\n"]
    for a in all_animes:
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a))
        else:
            lines.append(format_anime_short(a))
    kb = build_pagination_keyboard(page, total_pages, "listpage")
    await _send_or_reply(update, "\n".join(lines), reply_markup=kb)

async def chercher_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await _send_or_reply(update, "Usage : /chercher <mot-clé>")
        return
    query = " ".join(context.args)
    results = db.search_animes_local(query)
    if not results:
        await _send_or_reply(update, "❌ Aucun résultat local.")
        return
    lines = [f"🔍 <b>Résultats pour \"{query}\"</b>\n"]
    for i, a in enumerate(results, 1):
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a, i))
        else:
            lines.append(format_anime_short(a, i))
    await _send_or_reply(update, "\n".join(lines))

async def favoris_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favs = db.get_favoris(_uid(update))
    if not favs:
        await _send_or_reply(update, "💛 Aucun favori. Utilisez le bouton 🤍 sous un post !")
        return
    lines = [f"💛 <b>Mes favoris ({len(favs)})</b>\n"]
    for a in favs[:20]:
        if MOBILE_MODE:
            lines.append(format_anime_short_mobile(a))
        else:
            lines.append(format_anime_short(a))
    await _send_or_reply(update, "\n".join(lines))

async def calendrier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cal = db.get_calendrier_semaine()
    text = format_calendrier(cal)
    await _send_or_reply(update, text)

async def suivre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await _send_or_reply(update, "Usage : /suivre <titre>")
        return
    titre = " ".join(context.args)
    results = await search_anime(titre, 1)
    if not results:
        await _send_or_reply(update, "❌ Anime non trouvé sur MAL.")
        return
    anime = results[0]
    mal_id = anime.get("mal_id")
    titre_found = anime.get("title", titre)
    result = db.add_suivi(mal_id, titre_found, _uid(update))
    if result:
        await _send_or_reply(update, f"🔔 <b>{titre_found}</b> suivi !")
    else:
        await _send_or_reply(update, f"ℹ️ <b>{titre_found}</b> est déjà suivi.")

async def suivis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    if not suivis:
        await _send_or_reply(update, "🔔 Aucun anime suivi.")
        return
    lines = ["🔔 <b>Anime suivis</b>\n"]
    for s in suivis:
        lines.append(f"• <b>{s['titre']}</b> (ep {s['dernier_ep']}) — MAL #{s['mal_id']}")
    await _send_or_reply(update, "\n".join(lines))

async def arretersuivi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await _send_or_reply(update, "Usage : /arretersuivi <mal_id>")
        return
    try:
        mal_id = int(context.args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    db.stop_suivi(mal_id)
    await _send_or_reply(update, f"✅ Suivi arrêté pour MAL #{mal_id}.")

async def programmes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "programmer"):
        return
    posts = db.get_posts_programmes(20)
    if not posts:
        await _send_or_reply(update, "⏰ Aucun post programmé.")
        return
    lines = ["⏰ <b>Posts programmés</b>\n"]
    for p in posts:
        lines.append(format_post_programme(p))
        lines.append("")
    await _send_or_reply(update, "\n".join(lines))

async def admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = db.get_all_admins()
    if not admins:
        await _send_or_reply(update, "👥 Aucun admin.")
        return
    lines = ["👥 <b>Admins</b>\n"]
    for a in admins:
        lines.append(f"• <b>{a['username']}</b> — {a['role']} (ID: <code>{a['user_id']}</code>)")
    await _send_or_reply(update, "\n".join(lines))

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "stats"):
        return
    stats = db.get_stats()
    daily = db.get_daily_stats(7)
    text = format_stats_dashboard(stats, daily)
    await _send_or_reply(update, text)

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    level = context.args[0].upper() if context.args else None
    logs = db.get_logs(15, level)
    if not logs:
        await _send_or_reply(update, "📋 Aucun log.")
        return
    lines = ["📋 <b>Logs récents</b>\n"]
    for l in logs:
        lines.append(format_log_entry(l))
    await _send_or_reply(update, "\n".join(lines))

async def logsuser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /logsuser <ID>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    logs = db.get_logs_user(uid, 15)
    if not logs:
        await _send_or_reply(update, "📋 Aucun log pour cet utilisateur.")
        return
    lines = [f"📋 <b>Logs de {uid}</b>\n"]
    for l in logs:
        lines.append(format_log_entry(l))
    await _send_or_reply(update, "\n".join(lines))

async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    filepath, size = db.create_backup()
    text = format_backup_info(filepath, size)
    db.add_log(_uid(update), _uname(update), "BACKUP", filepath)
    await _send_or_reply(update, text)

async def backups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    history = db.get_backup_history(10)
    if not history:
        await _send_or_reply(update, "💾 Aucun backup.")
        return
    lines = ["💾 <b>Historique backups</b>\n"]
    for b in history:
        lines.append(f"📁 <code>{b['filepath']}</code>\n   📏 {b['size']/1024:.1f} Ko — {b['created_at'][:16]}")
    await _send_or_reply(update, "\n".join(lines))

async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /restore <fichier>")
        return
    filepath = context.args[0]
    if db.restore_backup(filepath):
        db.init_db()
        db.add_log(_uid(update), _uname(update), "RESTORE", filepath)
        await _send_or_reply(update, f"✅ Restauré depuis {filepath}")
    else:
        await _send_or_reply(update, "❌ Fichier non trouvé.")

async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "maintenance"):
        return
    current = db.get_setting("maintenance", "0")
    new_val = "0" if current == "1" else "1"
    db.set_setting("maintenance", new_val)
    status = "🟢 Désactivé" if new_val == "0" else "🔴 Activé"
    db.add_log(_uid(update), _uname(update), "MAINTENANCE", status)
    await _send_or_reply(update, f"🔧 Mode maintenance : <b>{status}</b>")

async def templates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tpls = ["📋 Standard", "📦 Compact", "💎 Premium", "✨ Minimal",
            "⚡ Neon", "📱 Mobile", "🌿 Elegant"]
    text = "🎨 <b>Templates disponibles</b>\n\n" + "\n".join(tpls)
    await _send_or_reply(update, text)

async def cleanlogs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass
    count = db.clean_logs(days)
    await _send_or_reply(update, f"🗑️ {count} logs supprimés (> {days} jours).")

async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /unblacklist <ID>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    db.remove_blacklist(uid)
    db.add_log(_uid(update), _uname(update), "UNBLACKLIST", str(uid))
    await _send_or_reply(update, f"✅ {uid} retiré de la blacklist.")

async def voirblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return
    bl = db.get_blacklist()
    if not bl:
        await _send_or_reply(update, "🚫 Blacklist vide.")
        return
    lines = ["🚫 <b>Blacklist</b>\n"]
    for b in bl:
        lines.append(f"• <code>{b['user_id']}</code> — {b.get('raison', 'N/A')}")
    await _send_or_reply(update, "\n".join(lines))


# ═══════════════════════════════════════════════════════════
# COMMANDES v5 : EXPORT, IMPORT, PURGE, ÉPINGLER, HISTORIQUE
# ═══════════════════════════════════════════════════════════

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "export"):
        return
    filepath = db.export_animes_json()
    db.add_log(_uid(update), _uname(update), "EXPORT", filepath)
    await _send_or_reply(update, f"📤 Export créé :\n<code>{filepath}</code>")

async def import_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "import"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /import <fichier.json>")
        return
    filepath = context.args[0]
    count = db.import_animes_json(filepath)
    db.add_log(_uid(update), _uname(update), "IMPORT", f"{count} anime importés depuis {filepath}")
    await _send_or_reply(update, f"📥 {count} anime importés !")

async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "purge"):
        return
    days = 90
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass
    deleted = db.purge_old_data(days)
    total = sum(deleted.values())
    details = " │ ".join(f"{k}: {v}" for k, v in deleted.items())
    db.add_log(_uid(update), _uname(update), "PURGE", f"{total} éléments ({details})")
    await _send_or_reply(update, f"🗑️ <b>Purge effectuée</b>\n\n{details}\n\nTotal : {total} éléments supprimés (> {days} jours)")

async def epingler_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "poster"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /epingler <ID> [priorité]")
        return
    try:
        anime_id = int(context.args[0])
        priority = int(context.args[1]) if len(context.args) > 1 else 1
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return
    if anime.get("is_pinned"):
        db.unpin_anime(anime_id)
        await _send_or_reply(update, f"📌 <b>{anime['titre']}</b> désépinglé.")
    else:
        db.pin_anime(anime_id, priority)
        await _send_or_reply(update, f"📌 <b>{anime['titre']}</b> épinglé (priorité {priority}).")

async def historique_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    if not context.args:
        await _send_or_reply(update, "Usage : /historique <ID>")
        return
    try:
        anime_id = int(context.args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    edits = db.get_anime_edit_history(anime_id)
    text = format_edit_history(edits)
    await _send_or_reply(update, text)


# ═══════════════════════════════════════════════════════════
# CALLBACK HANDLER (boutons)
# ═══════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id

    # Track user
    db.update_user_profile(uid, query.from_user.username or str(uid))

    # ── Likes / Dislikes ──
    if data.startswith("like_"):
        anime_id = int(data.replace("like_", ""))
        added = db.toggle_vote(anime_id, uid, "like")
        anime = db.get_anime(anime_id)
        if anime:
            nb_favs = db.count_favoris(anime_id)
            is_fav = db.is_favori(uid, anime_id)
            kb = build_anime_keyboard(anime_id, anime.get("lien_externe"),
                                      anime["likes"], anime["dislikes"], anime["views"], is_fav, nb_favs)
            try:
                await query.edit_message_reply_markup(reply_markup=kb)
            except Exception:
                pass
        msg = "❤️ Liké !" if added else "💔 Like retiré."
        await query.answer(msg)

    elif data.startswith("dislike_"):
        anime_id = int(data.replace("dislike_", ""))
        added = db.toggle_vote(anime_id, uid, "dislike")
        anime = db.get_anime(anime_id)
        if anime:
            nb_favs = db.count_favoris(anime_id)
            is_fav = db.is_favori(uid, anime_id)
            kb = build_anime_keyboard(anime_id, anime.get("lien_externe"),
                                      anime["likes"], anime["dislikes"], anime["views"], is_fav, nb_favs)
            try:
                await query.edit_message_reply_markup(reply_markup=kb)
            except Exception:
                pass
        msg = "👎 Disliké." if added else "👎 Dislike retiré."
        await query.answer(msg)

    elif data.startswith("view_"):
        anime_id = int(data.replace("view_", ""))
        db.increment_views(anime_id)
        anime = db.get_anime(anime_id)
        if anime:
            nb_favs = db.count_favoris(anime_id)
            is_fav = db.is_favori(uid, anime_id)
            kb = build_anime_keyboard(anime_id, anime.get("lien_externe"),
                                      anime["likes"], anime["dislikes"], anime["views"], is_fav, nb_favs)
            try:
                await query.edit_message_reply_markup(reply_markup=kb)
            except Exception:
                pass
        await query.answer(f"👁️ {anime['views']} vues" if anime else "👁️")

    # ── Favoris ──
    elif data.startswith("fav_"):
        anime_id = int(data.replace("fav_", ""))
        if db.is_favori(uid, anime_id):
            db.remove_favori(uid, anime_id)
            msg = "🤍 Retiré des favoris."
        else:
            db.add_favori(uid, anime_id)
            msg = "💛 Ajouté aux favoris !"
        anime = db.get_anime(anime_id)
        if anime:
            nb_favs = db.count_favoris(anime_id)
            is_fav = db.is_favori(uid, anime_id)
            kb = build_anime_keyboard(anime_id, anime.get("lien_externe"),
                                      anime["likes"], anime["dislikes"], anime["views"], is_fav, nb_favs)
            try:
                await query.edit_message_reply_markup(reply_markup=kb)
            except Exception:
                pass
        await query.answer(msg)

    # ── Rating ──
    elif data.startswith("rate_"):
        anime_id = int(data.replace("rate_", ""))
        kb = build_rating_keyboard(anime_id)
        await query.answer()
        try:
            await query.message.reply_text("⭐ Votre note (1-10) :", reply_markup=kb)
        except Exception:
            pass

    elif data.startswith("rating_"):
        parts = data.split("_")
        anime_id = int(parts[1])
        score = int(parts[2])
        avg, nb = db.rate_anime(uid, anime_id, score)
        await query.answer(f"✅ Noté {score}/10 ! Moyenne : {avg}/10 ({nb} votes)")
        try:
            await query.message.delete()
        except Exception:
            pass

    # ── Info ──
    elif data.startswith("info_"):
        anime_id = int(data.replace("info_", ""))
        anime = db.get_anime(anime_id)
        if anime:
            nb_favs = db.count_favoris(anime_id)
            user_rate = db.get_user_rating(uid, anime_id)
            text = (
                f"📊 <b>Infos — {anime['titre']}</b>\n\n"
                f"❤️ Likes : {anime['likes']}\n"
                f"👎 Dislikes : {anime['dislikes']}\n"
                f"👁️ Vues : {anime['views']}\n"
                f"💛 Favoris : {nb_favs}\n"
                f"⭐ Communauté : {anime.get('score_communaute', 0)}/10 ({anime.get('nb_votes_communaute', 0)} votes)\n"
                f"📝 Votre note : {user_rate}/10" if user_rate else
                f"📊 <b>Infos — {anime['titre']}</b>\n\n"
                f"❤️ Likes : {anime['likes']}\n"
                f"👎 Dislikes : {anime['dislikes']}\n"
                f"👁️ Vues : {anime['views']}\n"
                f"💛 Favoris : {nb_favs}\n"
                f"⭐ Communauté : {anime.get('score_communaute', 0)}/10 ({anime.get('nb_votes_communaute', 0)} votes)\n"
                f"📝 Pas encore noté"
            )
            await query.answer()
            try:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("❌ Anime non trouvé.")

    # ── Similaires ──
    elif data.startswith("similar_"):
        anime_id = int(data.replace("similar_", ""))
        anime = db.get_anime(anime_id)
        if anime and anime.get("categorie"):
            similaires = db.get_animes_by_categorie(anime["categorie"], 5)
            similaires = [s for s in similaires if s["id"] != anime_id][:5]
            if similaires:
                lines = [f"🔍 <b>Similaires à {anime['titre']}</b>\n"]
                for s in similaires:
                    lines.append(format_anime_short_mobile(s))
                await query.answer()
                try:
                    await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
                except Exception:
                    pass
            else:
                await query.answer("Aucun anime similaire trouvé.")
        else:
            await query.answer("Pas de catégorie définie.")

    # ── Catégorie ──
    elif data.startswith("category_"):
        anime_id = int(data.replace("category_", ""))
        anime = db.get_anime(anime_id)
        if anime and anime.get("categorie"):
            animes = db.get_animes_by_categorie(anime["categorie"], 10)
            lines = [f"📂 <b>{anime['categorie']}</b> ({len(animes)} anime)\n"]
            for a in animes:
                lines.append(format_anime_short_mobile(a))
            await query.answer()
            try:
                await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("Pas de catégorie.")

    # ── Catégorie depuis /categories ──
    elif data.startswith("listcat_"):
        cat = data.replace("listcat_", "")
        animes = db.get_animes_by_categorie(cat, 15)
        if animes:
            lines = [f"📂 <b>{cat}</b> ({len(animes)} anime)\n"]
            for a in animes:
                lines.append(format_anime_short_mobile(a))
            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(f"📂 Aucun anime dans {cat}.")

    # ── Pagination ──
    elif data.startswith("listpage_"):
        page = int(data.replace("listpage_", ""))
        per_page = 10
        all_animes = db.get_all_animes(limit=per_page, offset=(page - 1) * per_page)
        total = db.get_stats()["total_animes"]
        total_pages = max(1, math.ceil(total / per_page))
        lines = [f"📋 <b>LISTE</b> (page {page}/{total_pages})\n"]
        for a in all_animes:
            if MOBILE_MODE:
                lines.append(format_anime_short_mobile(a))
            else:
                lines.append(format_anime_short(a))
        kb = build_pagination_keyboard(page, total_pages, "listpage")
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=kb)

    # ── Sondage votes ──
    elif data.startswith("svote_"):
        parts = data.split("_")
        sondage_id = int(parts[1])
        option_idx = int(parts[2])
        success = db.vote_sondage(sondage_id, uid, option_idx)
        if success:
            await query.answer("✅ Vote enregistré !")
        else:
            await query.answer("⚠️ Vous avez déjà voté.")

    elif data.startswith("sresult_"):
        sondage_id = int(data.replace("sresult_", ""))
        sondage = db.get_sondage(sondage_id)
        if sondage:
            options = json.loads(sondage["options_json"])
            results = db.get_sondage_results(sondage_id)
            total = sum(r["cnt"] for r in results)
            text = format_sondage(sondage["question"], options, results, total)
            await query.answer()
            try:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass

    # ── Quiz answers ──
    elif data.startswith("qanswer_"):
        parts = data.split("_")
        quiz_id = int(parts[1])
        answer_idx = int(parts[2])
        result = db.answer_quiz(quiz_id, uid, answer_idx)
        if result is None:
            await query.answer("⚠️ Déjà répondu ou quiz invalide.")
        elif result:
            await query.answer("✅ Bonne réponse ! 🎉")
        else:
            quiz = db.get_quiz(quiz_id)
            correct = ""
            if quiz:
                opts = json.loads(quiz["options_json"])
                correct = opts[quiz["correct_idx"]] if quiz["correct_idx"] < len(opts) else ""
            await query.answer(f"❌ Mauvaise réponse. Correct : {correct}")

    # ── Confirm delete ──
    elif data.startswith("confirm_delete_"):
        anime_id = int(data.replace("confirm_delete_", ""))
        anime = db.get_anime(anime_id)
        if anime:
            # Supprimer le message du canal
            try:
                if anime.get("message_id") and anime.get("chat_id"):
                    await context.bot.delete_message(chat_id=anime["chat_id"],
                                                     message_id=anime["message_id"])
            except Exception:
                pass
            db.delete_anime(anime_id)
            db.add_log(uid, query.from_user.username or str(uid), "DELETE", f"#{anime_id}: {anime['titre']}")
            await query.edit_message_text(f"✅ <b>{anime['titre']}</b> supprimé.", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ Anime non trouvé.")

    elif data.startswith("cancel_delete_"):
        await query.edit_message_text("❌ Suppression annulée.")

    # ── Jikan select ──
    elif data.startswith("select_jikan_"):
        mal_id = int(data.replace("select_jikan_", ""))
        anime_data = await get_anime_by_id(mal_id)
        if anime_data:
            parsed = parse_jikan_anime(anime_data)
            text = format_anime_post(parsed, "mobile" if MOBILE_MODE else "compact")
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            await query.edit_message_text("❌ Erreur API.")

    elif data == "cancel_search" or data == "cancel_rating":
        try:
            await query.message.delete()
        except Exception:
            await query.answer("❌ Annulé.")

    # ── Admin panel buttons ──
    elif data == "admin_stats":
        stats = db.get_stats()
        daily = db.get_daily_stats(7)
        text = format_stats_dashboard(stats, daily)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

    elif data == "admin_logs":
        logs = db.get_logs(10)
        lines = ["📋 <b>Logs récents</b>\n"]
        for l in logs:
            lines.append(format_log_entry(l))
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif data == "admin_backup":
        filepath, size = db.create_backup()
        text = format_backup_info(filepath, size)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

    elif data == "admin_maint":
        current = db.get_setting("maintenance", "0")
        new_val = "0" if current == "1" else "1"
        db.set_setting("maintenance", new_val)
        status = "🟢 Désactivé" if new_val == "0" else "🔴 Activé"
        await query.edit_message_text(f"🔧 Maintenance : <b>{status}</b>", parse_mode=ParseMode.HTML)

    elif data == "admin_export":
        filepath = db.export_animes_json()
        await query.edit_message_text(f"📤 Export : <code>{filepath}</code>", parse_mode=ParseMode.HTML)

    elif data == "admin_purge":
        deleted = db.purge_old_data(90)
        total = sum(deleted.values())
        await query.edit_message_text(f"🗑️ Purge : {total} éléments supprimés.", parse_mode=ParseMode.HTML)

    elif data == "admin_list":
        admins = db.get_all_admins()
        lines = ["👥 <b>Admins</b>\n"]
        for a in admins:
            lines.append(f"• {a['username']} — {a['role']}")
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif data == "admin_bl":
        bl = db.get_blacklist()
        if bl:
            lines = ["🚫 <b>Blacklist</b>\n"]
            for b in bl:
                lines.append(f"• <code>{b['user_id']}</code> — {b.get('raison', 'N/A')}")
            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("🚫 Blacklist vide.")

    elif data == "admin_close":
        await query.edit_message_text("✅ Panel fermé.")

    elif data == "noop":
        await query.answer()



# ═══════════════════════════════════════════════════════════
# COMMANDES v6 : IA & SOURCES
# ═══════════════════════════════════════════════════════════

async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Publication automatique : /auto <titre> — recherche MAL + génère tout via IA"""
    if not await _check_perm(update, "poster"):
        return
    if not context.args:
        await _send_or_reply(update, "❓ Usage : /auto <titre de l'anime>")
        return
    titre = " ".join(context.args)
    await _send_or_reply(update, f"🤖 Recherche de <b>{titre}</b> sur MAL...")

    # Recherche MAL
    results = await search_anime(titre, 1)
    if not results:
        await _send_or_reply(update, "❌ Anime non trouvé sur MAL.")
        return

    mal_anime = results[0]
    parsed = parse_jikan_anime(mal_anime)

    await _send_or_reply(update, f"✅ Trouvé : <b>{parsed['titre']}</b>\n🤖 Génération IA en cours...")

    # Génération IA
    ai_data = await generate_anime_description(
        titre=parsed["titre"],
        titre_original=parsed.get("titre_original", ""),
        genres=parsed.get("genres", ""),
        studio=parsed.get("studio", ""),
        nb_episodes=parsed.get("nb_episodes", ""),
        synopsis_en=mal_anime.get("synopsis", "")
    )

    # Fusionner données MAL + IA
    data = {
        "titre": parsed["titre"],
        "titre_original": parsed.get("titre_original", ""),
        "synopsis": ai_data.get("synopsis", parsed.get("synopsis", "")),
        "personnages": ai_data.get("personnages", ""),
        "studio": parsed.get("studio", ""),
        "date_sortie": parsed.get("date_sortie", ""),
        "nb_episodes": parsed.get("nb_episodes", ""),
        "statut": parsed.get("statut", "En cours"),
        "genres": parsed.get("genres", ""),
        "note": str(mal_anime.get("score", "") or ""),
        "avis": ai_data.get("avis", ""),
        "image_url": parsed.get("image_url", ""),
        "lien_externe": parsed.get("mal_url", ""),
        "categorie": _detect_category(parsed.get("genres", "")),
        "tags": ai_data.get("tags", ""),
        "template": AUTO_PUBLISH_TEMPLATE,
        "posted_by": _uid(update),
        "accroche": ai_data.get("accroche", ""),
    }

    # Générer les liens de visionnage
    watch_links = generate_watch_links(parsed["titre"])

    # Formater et publier
    tpl = data["template"]
    text = format_anime_post(data, tpl)

    # Ajouter accroche IA
    if data.get("accroche"):
        text = f"💬 <i>{data['accroche']}</i>\n\n{text}"

    # Ajouter liens de visionnage
    if watch_links:
        links_text = "\n".join([f"▶️ <a href=\"{url}\">{name}</a>" for name, url in watch_links[:3]])
        text += f"\n\n🎬 <b>Regarder :</b>\n{links_text}"

    try:
        if data.get("image_url") and data["image_url"].startswith("http"):
            caption = text[:1024] if len(text) > 1024 else text
            msg = await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=data["image_url"],
                caption=caption, parse_mode=ParseMode.HTML
            )
        else:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        data["message_id"] = msg.message_id
        data["chat_id"] = str(msg.chat_id)
        anime_id = db.save_anime(data)

        nb_favs = db.count_favoris(anime_id)
        kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0, 0, False, nb_favs)
        if data.get("image_url") and data["image_url"].startswith("http"):
            await msg.edit_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await msg.edit_reply_markup(reply_markup=kb)

        db.add_log(_uid(update), _uname(update), "AUTO_POST", f"Anime #{anime_id}: {data['titre']}")
        db.record_daily_stats()
        await _send_or_reply(update, f"✅ Publié automatiquement ! ID: <code>{anime_id}</code>")
    except Exception as e:
        logger.error(f"Erreur auto_cmd: {e}")
        await _send_or_reply(update, f"❌ Erreur : {e}")


def _detect_category(genres: str) -> str:
    """Détecte la catégorie principale depuis les genres"""
    genres_lower = genres.lower()
    for cat in CATEGORIES:
        if cat.lower() in genres_lower:
            return cat
    if "fantasy" in genres_lower or "isekai" in genres_lower:
        return "Isekai"
    if "romance" in genres_lower:
        return "Romance"
    if "action" in genres_lower:
        return "Action"
    if "comedy" in genres_lower or "comédie" in genres_lower:
        return "Comédie"
    return "Autre"


async def autopublish_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activer/désactiver l'auto-publication de la saison en cours"""
    if not await _check_perm(update, "admin"):
        return
    current = db.get_setting("auto_publish", "0")
    new_val = "0" if current == "1" else "1"
    db.set_setting("auto_publish", new_val)
    status = "🟢 Activé" if new_val == "1" else "🔴 Désactivé"
    db.add_log(_uid(update), _uname(update), "AUTO_PUBLISH", status)
    await _send_or_reply(update, f"🤖 Auto-publication : <b>{status}</b>\n\n"
                         f"Le bot publiera automatiquement les anime de la saison.")


async def aisuggest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suggestions IA basées sur un anime"""
    if not context.args:
        await _send_or_reply(update, "❓ Usage : /aisuggest <ID>")
        return
    try:
        anime_id = int(context.args[0])
    except ValueError:
        await _send_or_reply(update, "❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await _send_or_reply(update, "❌ Anime non trouvé.")
        return
    await _send_or_reply(update, "🤖 Génération des suggestions...")
    suggestions = await suggest_similar_animes(
        titre=anime["titre"],
        genres=anime.get("genres", ""),
        synopsis=anime.get("synopsis", "")
    )
    text = f"🎯 <b>Si tu as aimé {anime['titre']}, tu aimeras :</b>\n\n{suggestions}"
    await _send_or_reply(update, text)


async def airecap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Récap hebdomadaire généré par IA"""
    if not await _check_perm(update, "poster"):
        return
    recent = db.get_all_animes(limit=10, offset=0)
    if not recent:
        await _send_or_reply(update, "📭 Aucun anime récent.")
        return
    await _send_or_reply(update, "🤖 Génération du récap...")
    titres = [a["titre"] for a in recent]
    recap = await generate_weekly_recap(titres)
    text = f"📰 <b>Récap de la semaine</b>\n\n{recap}"
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
        db.add_log(_uid(update), _uname(update), "AI_RECAP", "Récap publié")
        await _send_or_reply(update, "✅ Récap publié dans le canal !")
    except Exception as e:
        await _send_or_reply(update, f"❌ Erreur : {e}")


async def sources_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Afficher les liens de visionnage pour un anime"""
    if not context.args:
        await _send_or_reply(update, "❓ Usage : /sources <titre>")
        return
    titre = " ".join(context.args)
    links = generate_watch_links(titre)
    if not links:
        await _send_or_reply(update, "❌ Aucune source trouvée.")
        return
    lines = [f"🎬 <b>Sources pour {titre}</b>\n"]
    for name, url in links:
        lines.append(f"▶️ <a href=\"{url}\">{name}</a>")
    await _send_or_reply(update, "\n".join(lines))



# ═══════════════════════════════════════════════════════════
# SCHEDULERS
# ═══════════════════════════════════════════════════════════

async def scheduler_posts(context: ContextTypes.DEFAULT_TYPE):
    posts = db.get_posts_programmes_dus()
    for post in posts:
        try:
            data = json.loads(post["data_json"])
            tpl = data.get("template", "standard")
            text = format_anime_post(data, tpl)
            if data.get("image_url") and data["image_url"].startswith("http"):
                caption = text[:1024] if len(text) > 1024 else text
                msg = await context.bot.send_photo(
                    chat_id=CHANNEL_ID, photo=data["image_url"],
                    caption=caption, parse_mode=ParseMode.HTML
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            data["message_id"] = msg.message_id
            data["chat_id"] = str(msg.chat_id)
            anime_id = db.save_anime(data)
            nb_favs = db.count_favoris(anime_id)
            kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0, 0, False, nb_favs)
            if data.get("image_url") and data["image_url"].startswith("http"):
                await msg.edit_caption(caption=text[:1024], parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await msg.edit_reply_markup(reply_markup=kb)
            db.mark_post_publie(post["id"])
            db.record_daily_stats()
            logger.info(f"Post programmé #{post['id']} publié : {data.get('titre', '?')}")
        except Exception as e:
            db.mark_post_publie(post["id"], str(e))
            logger.error(f"Erreur post programmé #{post['id']}: {e}")

async def scheduler_episodes(context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    for suivi in suivis:
        try:
            episodes = await get_anime_episodes(suivi["mal_id"])
            if episodes:
                latest = len(episodes)
                if latest > suivi["dernier_ep"]:
                    db.update_suivi_ep(suivi["mal_id"], latest)
                    text = format_notification_episode(suivi["titre"], latest)
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
                    logger.info(f"Notif épisode: {suivi['titre']} ep {latest}")
        except Exception as e:
            logger.error(f"Erreur check épisode {suivi['titre']}: {e}")
        await asyncio.sleep(1)

async def scheduler_backup(context: ContextTypes.DEFAULT_TYPE):
    try:
        filepath, size = db.create_backup()
        db.record_daily_stats()
        logger.info(f"Backup auto: {filepath} ({size/1024:.1f} Ko)")
    except Exception as e:
        logger.error(f"Erreur backup auto: {e}")


async def scheduler_auto_publish(context: ContextTypes.DEFAULT_TYPE):
    """Auto-publie les anime de la saison en cours (si activé)"""
    enabled = db.get_setting("auto_publish", "0")
    if enabled != "1":
        return
    try:
        season_animes = await get_current_season_anime(5)
        if not season_animes:
            return
        for mal_anime in season_animes:
            parsed = parse_jikan_anime(mal_anime)
            # Vérifier si déjà publié
            existing = db.search_animes_local(parsed["titre"])
            if existing:
                continue
            # Générer via IA
            ai_data = await generate_anime_description(
                titre=parsed["titre"],
                titre_original=parsed.get("titre_original", ""),
                genres=parsed.get("genres", ""),
                studio=parsed.get("studio", ""),
                nb_episodes=parsed.get("nb_episodes", ""),
                synopsis_en=mal_anime.get("synopsis", "")
            )
            data = {
                "titre": parsed["titre"],
                "titre_original": parsed.get("titre_original", ""),
                "synopsis": ai_data.get("synopsis", ""),
                "personnages": ai_data.get("personnages", ""),
                "studio": parsed.get("studio", ""),
                "date_sortie": parsed.get("date_sortie", ""),
                "nb_episodes": parsed.get("nb_episodes", ""),
                "statut": parsed.get("statut", "En cours"),
                "genres": parsed.get("genres", ""),
                "note": str(mal_anime.get("score", "") or ""),
                "avis": ai_data.get("avis", ""),
                "image_url": parsed.get("image_url", ""),
                "lien_externe": parsed.get("mal_url", ""),
                "categorie": _detect_category(parsed.get("genres", "")),
                "tags": ai_data.get("tags", ""),
                "template": AUTO_PUBLISH_TEMPLATE,
                "posted_by": 0,
                "accroche": ai_data.get("accroche", ""),
            }
            watch_links = generate_watch_links(parsed["titre"])
            tpl = data["template"]
            text = format_anime_post(data, tpl)
            if data.get("accroche"):
                text = f"\ud83d\udcac <i>{data['accroche']}</i>\n\n{text}"
            if watch_links:
                links_text = "\n".join([f"\u25b6\ufe0f <a href=\"{url}\">{name}</a>" for name, url in watch_links[:3]])
                text += f"\n\n\ud83c\udfac <b>Regarder :</b>\n{links_text}"
            try:
                if data.get("image_url") and data["image_url"].startswith("http"):
                    caption = text[:1024] if len(text) > 1024 else text
                    msg = await context.bot.send_photo(
                        chat_id=CHANNEL_ID, photo=data["image_url"],
                        caption=caption, parse_mode=ParseMode.HTML
                    )
                else:
                    msg = await context.bot.send_message(
                        chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                data["message_id"] = msg.message_id
                data["chat_id"] = str(msg.chat_id)
                anime_id = db.save_anime(data)
                nb_favs = db.count_favoris(anime_id)
                kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0, 0, False, nb_favs)
                if data.get("image_url") and data["image_url"].startswith("http"):
                    await msg.edit_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await msg.edit_reply_markup(reply_markup=kb)
                db.record_daily_stats()
                logger.info(f"Auto-publish: {data['titre']}")
            except Exception as e:
                logger.error(f"Erreur auto-publish {parsed['titre']}: {e}")
            await asyncio.sleep(5)  # Rate limit
    except Exception as e:
        logger.error(f"Erreur scheduler_auto_publish: {e}")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Conversations ────────────────────────────────────
    poster_conv = ConversationHandler(
        entry_points=[CommandHandler("poster", poster_start)],
        states={
            TITRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_titre)],
            TITRE_ORIGINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_titre_original)],
            SYNOPSIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_synopsis)],
            PERSONNAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_personnages)],
            STUDIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_studio)],
            DATE_SORTIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_date)],
            NB_EPISODES: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_episodes)],
            STATUT_CHOICE: [CallbackQueryHandler(poster_statut_cb, pattern=r"^statut_")],
            GENRES: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_genres)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_note)],
            AVIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_avis)],
            IMAGE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_image)],
            LIEN_EXTERNE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_lien)],
            CATEGORIE_CHOICE: [CallbackQueryHandler(poster_categorie_cb, pattern=r"^cat_")],
            TAGS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_tags)],
            TEMPLATE_CHOICE: [CallbackQueryHandler(poster_template_cb, pattern=r"^tpl_")],
            CONFIRM_POST: [CallbackQueryHandler(poster_confirm_cb, pattern=r"^post_")],
            PROGRAMME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_programme_date)],
            PROGRAMME_HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, poster_programme_heure)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    modifier_conv = ConversationHandler(
        entry_points=[CommandHandler("modifier", modifier_start)],
        states={
            EDIT_FIELD: [CallbackQueryHandler(modifier_field_cb, pattern=r"^editf_")],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, modifier_value)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    recherche_conv = ConversationHandler(
        entry_points=[CommandHandler("recherche", recherche_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, recherche_query)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    addadmin_conv = ConversationHandler(
        entry_points=[CommandHandler("addadmin", addadmin_start)],
        states={
            ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, addadmin_id)],
            ADD_ADMIN_ROLE: [CallbackQueryHandler(addadmin_role_cb, pattern=r"^role_")],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    blacklist_conv = ConversationHandler(
        entry_points=[CommandHandler("blacklist", blacklist_start)],
        states={
            BLACKLIST_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, blacklist_id)],
            BLACKLIST_RAISON: [MessageHandler(filters.TEXT & ~filters.COMMAND, blacklist_raison)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    sondage_conv = ConversationHandler(
        entry_points=[CommandHandler("sondage", sondage_start)],
        states={
            SONDAGE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, sondage_question)],
            SONDAGE_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sondage_options)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("quiz", quiz_start)],
        states={
            QUIZ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_question)],
            QUIZ_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_options)],
            QUIZ_CORRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_correct)],
            QUIZ_EXPLICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_explication)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    calendrier_conv = ConversationHandler(
        entry_points=[CommandHandler("addcalendrier", addcalendrier_start)],
        states={
            CAL_TITRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cal_titre)],
            CAL_JOUR: [CallbackQueryHandler(cal_jour_cb, pattern=r"^calj_")],
            CAL_HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cal_heure)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    comparer_conv = ConversationHandler(
        entry_points=[CommandHandler("comparer", comparer_start)],
        states={
            COMPARE_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, comparer_a)],
            COMPARE_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, comparer_b)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    filtre_conv = ConversationHandler(
        entry_points=[CommandHandler("filtre", filtre_start)],
        states={
            FILTER_CAT: [CallbackQueryHandler(filtre_cat_cb, pattern=r"^fcat_")],
            FILTER_STATUT: [CallbackQueryHandler(filtre_statut_cb, pattern=r"^fstat_")],
            FILTER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_note)],
            FILTER_SORT: [CallbackQueryHandler(filtre_sort_cb, pattern=r"^fsort_")],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg)],
        },
        fallbacks=[CommandHandler("cancel", poster_cancel)],
        per_message=False,
    )

    # ── Enregistrement handlers ──────────────────────────
    app.add_handler(poster_conv)
    app.add_handler(modifier_conv)
    app.add_handler(recherche_conv)
    app.add_handler(addadmin_conv)
    app.add_handler(blacklist_conv)
    app.add_handler(sondage_conv)
    app.add_handler(quiz_conv)
    app.add_handler(calendrier_conv)
    app.add_handler(comparer_conv)
    app.add_handler(filtre_conv)
    app.add_handler(broadcast_conv)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("quoideneuf", whats_new_cmd))
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CommandHandler("supprimer", supprimer_cmd))
    app.add_handler(CommandHandler("anime", anime_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("saison", saison_cmd))
    app.add_handler(CommandHandler("upcoming", upcoming_cmd))
    app.add_handler(CommandHandler("toplikes", toplikes_cmd))
    app.add_handler(CommandHandler("topvues", topvues_cmd))
    app.add_handler(CommandHandler("topnotes", topnotes_cmd))
    app.add_handler(CommandHandler("categories", categories_cmd))
    app.add_handler(CommandHandler("liste", liste_cmd))
    app.add_handler(CommandHandler("chercher", chercher_cmd))
    app.add_handler(CommandHandler("favoris", favoris_cmd))
    app.add_handler(CommandHandler("calendrier", calendrier_cmd))
    app.add_handler(CommandHandler("suivre", suivre_cmd))
    app.add_handler(CommandHandler("suivis", suivis_cmd))
    app.add_handler(CommandHandler("arretersuivi", arretersuivi_cmd))
    app.add_handler(CommandHandler("programmes", programmes_cmd))
    app.add_handler(CommandHandler("admins", admins_cmd))
    app.add_handler(CommandHandler("removeadmin", removeadmin_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("logsuser", logsuser_cmd))
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("backups", backups_cmd))
    app.add_handler(CommandHandler("restore", restore_cmd))
    app.add_handler(CommandHandler("maintenance", maintenance_cmd))
    app.add_handler(CommandHandler("templates", templates_cmd))
    app.add_handler(CommandHandler("cleanlogs", cleanlogs_cmd))
    app.add_handler(CommandHandler("unblacklist", unblacklist_cmd))
    app.add_handler(CommandHandler("voirblacklist", voirblacklist_cmd))
    app.add_handler(CommandHandler("export", export_cmd))
    app.add_handler(CommandHandler("import", import_cmd))
    app.add_handler(CommandHandler("purge", purge_cmd))
    app.add_handler(CommandHandler("epingler", epingler_cmd))
    app.add_handler(CommandHandler("historique", historique_cmd))

    # ── Commandes v6 ──────────────────────────────────────
    app.add_handler(CommandHandler("auto", auto_cmd))
    app.add_handler(CommandHandler("autopublish", autopublish_cmd))
    app.add_handler(CommandHandler("aisuggest", aisuggest_cmd))
    app.add_handler(CommandHandler("airecap", airecap_cmd))
    app.add_handler(CommandHandler("sources", sources_cmd))

    app.add_handler(CallbackQueryHandler(callback_handler))

    # ── Scheduler jobs ────────────────────────────────────
    jq = app.job_queue
    jq.run_repeating(scheduler_posts, interval=SCHEDULER_INTERVAL, first=10)
    jq.run_repeating(scheduler_episodes, interval=EPISODE_CHECK_INTERVAL, first=60)
    jq.run_repeating(scheduler_backup, interval=BACKUP_INTERVAL, first=BACKUP_INTERVAL)
    if AUTO_PUBLISH_ENABLED:
        jq.run_repeating(scheduler_auto_publish, interval=AUTO_PUBLISH_INTERVAL, first=120)

    logger.info(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré !")
    print(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré ! Ctrl+C pour arrêter.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
