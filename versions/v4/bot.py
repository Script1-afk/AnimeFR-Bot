# ============================================================
# bot.py — Fichier principal AnimeFR Bot v4.0
# ============================================================

import asyncio
import json
import logging
import os
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
    MAX_FAVORITES, MAX_POLL_OPTIONS, MAX_QUIZ_OPTIONS,
)
from formatter import (
    format_anime_post, format_anime_short, build_anime_keyboard,
    build_confirm_delete_keyboard, build_search_result_keyboard,
    build_categorie_keyboard, build_statut_keyboard, build_template_keyboard,
    build_rating_keyboard, build_sondage_keyboard, build_quiz_keyboard,
    format_notification_episode, format_log_entry, format_post_programme,
    format_stats_dashboard, format_backup_info, format_whats_new,
    format_compare, format_sondage, format_quiz, format_calendrier,
    make_star_bar, get_rank_emoji,
)
from jikan import (
    search_anime, get_anime_by_id, get_anime_characters,
    get_current_season_anime, get_upcoming_anime,
    get_top_anime, parse_jikan_anime
)

# ── Logging avec rotation ────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("backups", exist_ok=True)
os.makedirs("media", exist_ok=True)

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

# v4 states
SONDAGE_QUESTION, SONDAGE_OPTIONS = 27, 28
QUIZ_QUESTION, QUIZ_OPTIONS, QUIZ_CORRECT, QUIZ_EXPLICATION = 29, 30, 31, 32
CAL_TITRE, CAL_JOUR, CAL_HEURE = 33, 34, 35
COMPARE_A, COMPARE_B = 36, 37
FILTER_CAT, FILTER_STATUT, FILTER_NOTE, FILTER_SORT = 38, 39, 40, 41


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
    if _is_maintenance(uid):
        await update.effective_message.reply_text(MAINTENANCE_MESSAGE)
        return False
    if not db.has_permission(uid, perm):
        await update.effective_message.reply_text("⛔ Permission insuffisante.")
        return False
    db.increment_daily_stat("commands")
    return True

async def _check_admin(update: Update) -> bool:
    return await _check_perm(update, "admin")

def _truncate(text: str, limit: int = 1024) -> str:
    return text[:limit - 3] + "..." if len(text) > limit else text


# ═══════════════════════════════════════════════════════════
# /start & /help
# ═══════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = _uid(update)
    admin = db.get_admin(uid)
    role = admin["role"] if admin else "visiteur"
    text = (
        f"╔{'═' * 30}╗\n"
        f"║  🎌 <b>AnimeFR Bot v{BOT_VERSION}</b>\n"
        f"╠{'═' * 30}╣\n"
        f"║  👤 Rôle : <b>{role}</b>\n"
        f"║\n"
        f"║  📋 /help — Aide complète\n"
        f"║  🆕 /quoideneuf — Nouveautés\n"
        f"║\n"
        f"╚{'═' * 30}╝"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"╔{'═' * 32}╗\n"
        f"║  📋 <b>COMMANDES — v{BOT_VERSION}</b>\n"
        f"╠{'═' * 32}╣\n"
        f"║\n"
        f"║  📝 <b>PUBLICATION</b>\n"
        f"║  /poster — Publier un anime\n"
        f"║  /modifier <code>id</code> — Modifier\n"
        f"║  /supprimer <code>id</code> — Supprimer\n"
        f"║  /programmes — Posts programmés\n"
        f"║\n"
        f"║  🔍 <b>RECHERCHE</b>\n"
        f"║  /recherche — Rechercher sur MAL\n"
        f"║  /chercher <code>mot</code> — Recherche locale\n"
        f"║  /anime <code>id</code> — Fiche anime\n"
        f"║  /filtre — Recherche avancée\n"
        f"║  /comparer — Comparer 2 anime\n"
        f"║  /top — Top 10 MAL\n"
        f"║  /saison — Anime de la saison\n"
        f"║  /upcoming — À venir\n"
        f"║\n"
        f"║  🎯 <b>COMMUNAUTÉ</b>\n"
        f"║  /favoris — Mes favoris\n"
        f"║  /sondage — Créer un sondage\n"
        f"║  /quiz — Créer un quiz\n"
        f"║  /calendrier — Sorties de la semaine\n"
        f"║  /addcalendrier — Ajouter au calendrier\n"
        f"║\n"
        f"║  📊 <b>CLASSEMENTS</b>\n"
        f"║  /toplikes — Top likés\n"
        f"║  /topvues — Top vus\n"
        f"║  /topnotes — Top notes communauté\n"
        f"║  /categories — Par catégorie\n"
        f"║  /liste — Tous les anime\n"
        f"║\n"
        f"║  🔔 <b>NOTIFICATIONS</b>\n"
        f"║  /suivre — Suivre un anime\n"
        f"║  /suivis — Mes suivis\n"
        f"║  /arretersuivi <code>mal_id</code>\n"
        f"║\n"
        f"║  🛠️ <b>ADMIN</b>\n"
        f"║  /admins /addadmin /removeadmin\n"
        f"║  /blacklist /unblacklist /voirblacklist\n"
        f"║  /stats /logs /logsuser\n"
        f"║  /backup /backups /restore\n"
        f"║  /maintenance /templates /cleanlogs\n"
        f"║\n"
        f"║  /annuler — Annuler action en cours\n"
        f"║\n"
        f"╚{'═' * 32}╝"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════
# /quoideneuf
# ═══════════════════════════════════════════════════════════

async def whats_new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_whats_new(), parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════
# ANNULER
# ═══════════════════════════════════════════════════════════

async def annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Action annulée.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# POSTER (formulaire 16 étapes + programmation)
# ═══════════════════════════════════════════════════════════

async def poster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "poster"):
        return ConversationHandler.END
    context.user_data["anime"] = {}
    await update.message.reply_text("🎌 <b>Étape 1/16</b> — Titre de l'anime :", parse_mode=ParseMode.HTML)
    return TITRE

async def get_titre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["titre"] = update.message.text.strip()
    await update.message.reply_text("✦ <b>Étape 2/16</b> — Titre original (japonais) :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return TITRE_ORIGINAL

async def get_titre_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["titre_original"] = "" if t == "-" else t
    await update.message.reply_text("📖 <b>Étape 3/16</b> — Synopsis :", parse_mode=ParseMode.HTML)
    return SYNOPSIS

async def get_synopsis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["synopsis"] = update.message.text.strip()
    await update.message.reply_text("👥 <b>Étape 4/16</b> — Personnages principaux :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return PERSONNAGES

async def get_personnages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["personnages"] = "" if t == "-" else t
    await update.message.reply_text("🎬 <b>Étape 5/16</b> — Studio :", parse_mode=ParseMode.HTML)
    return STUDIO

async def get_studio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["studio"] = update.message.text.strip()
    await update.message.reply_text("📅 <b>Étape 6/16</b> — Date de sortie :", parse_mode=ParseMode.HTML)
    return DATE_SORTIE

async def get_date_sortie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["date_sortie"] = update.message.text.strip()
    await update.message.reply_text("📺 <b>Étape 7/16</b> — Nombre d'épisodes :", parse_mode=ParseMode.HTML)
    return NB_EPISODES

async def get_nb_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["nb_episodes"] = update.message.text.strip()
    await update.message.reply_text("📌 <b>Étape 8/16</b> — Statut :", parse_mode=ParseMode.HTML,
                                     reply_markup=build_statut_keyboard())
    return STATUT_CHOICE

async def get_statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["anime"]["statut"] = query.data.replace("statut_", "")
    await query.edit_message_text("🏷️ <b>Étape 9/16</b> — Genres (séparés par des virgules) :", parse_mode=ParseMode.HTML)
    return GENRES

async def get_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["genres"] = update.message.text.strip()
    await update.message.reply_text("⭐ <b>Étape 10/16</b> — Note /10 :", parse_mode=ParseMode.HTML)
    return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["anime"]["note"] = update.message.text.strip()
    await update.message.reply_text("💬 <b>Étape 11/16</b> — Votre avis :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return AVIS

async def get_avis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["avis"] = "" if t == "-" else t
    await update.message.reply_text("🖼️ <b>Étape 12/16</b> — URL de l'image :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return IMAGE_URL

async def get_image_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["image_url"] = "" if t == "-" else t
    await update.message.reply_text("🔗 <b>Étape 13/16</b> — Lien externe (MAL, etc.) :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return LIEN_EXTERNE

async def get_lien_externe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["lien_externe"] = "" if t == "-" else t
    await update.message.reply_text("📂 <b>Étape 14/16</b> — Catégorie :", parse_mode=ParseMode.HTML,
                                     reply_markup=build_categorie_keyboard(CATEGORIES))
    return CATEGORIE_CHOICE

async def get_categorie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["anime"]["categorie"] = query.data.replace("cat_", "")
    await query.edit_message_text("🔖 <b>Étape 15/16</b> — Tags (séparés par des virgules) :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return TAGS_INPUT

async def get_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["anime"]["tags"] = "" if t == "-" else t
    await update.message.reply_text("🎨 <b>Étape 16/16</b> — Choisissez un template :", parse_mode=ParseMode.HTML,
                                     reply_markup=build_template_keyboard())
    return TEMPLATE_CHOICE

async def get_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tpl = query.data.replace("tpl_", "")
    context.user_data["anime"]["template"] = tpl
    data = context.user_data["anime"]
    data.setdefault("mal_id", 0)
    data.setdefault("trailer_url", "")
    data.setdefault("saison", "")
    data.setdefault("likes", 0)
    data.setdefault("views", 0)
    data.setdefault("score_communaute", 0)
    data.setdefault("nb_votes_communaute", 0)
    preview = format_anime_post(data, tpl)
    preview = _truncate(preview, 4000)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Publier maintenant", callback_data="pub_now")],
        [InlineKeyboardButton("⏰ Programmer", callback_data="pub_schedule")],
        [InlineKeyboardButton("❌ Annuler", callback_data="pub_cancel")],
    ])
    await query.edit_message_text(f"📋 <b>Aperçu :</b>\n\n{preview}", parse_mode=ParseMode.HTML, reply_markup=kb)
    return CONFIRM_POST

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "pub_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Publication annulée.")
        return ConversationHandler.END

    if choice == "pub_schedule":
        await query.edit_message_text("📅 Date de publication (format YYYY-MM-DD) :", parse_mode=ParseMode.HTML)
        return PROGRAMME_DATE

    # pub_now
    data = context.user_data["anime"]
    data["posted_by"] = _uid(update)
    data["message_id"] = None
    data["chat_id"] = CHANNEL_ID
    tpl = data.get("template", "standard")
    text = format_anime_post(data, tpl)
    text = _truncate(text, 1024)

    try:
        if data.get("image_url") and data["image_url"].startswith("http"):
            msg = await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=data["image_url"],
                caption=text, parse_mode=ParseMode.HTML,
                reply_markup=build_anime_keyboard(0, data.get("lien_externe"), 0, 0)
            )
        else:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                reply_markup=build_anime_keyboard(0, data.get("lien_externe"), 0, 0)
            )
        data["message_id"] = msg.message_id
        anime_id = db.save_anime(data)
        db.update_message_id(anime_id, msg.message_id, CHANNEL_ID)
        # Update keyboard with real anime_id
        try:
            if data.get("image_url") and data["image_url"].startswith("http"):
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID, message_id=msg.message_id,
                    reply_markup=build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0)
                )
            else:
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID, message_id=msg.message_id,
                    reply_markup=build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0)
                )
        except Exception:
            pass
        db.add_log(_uid(update), _uname(update), "POSTER", f"Anime #{anime_id}: {data['titre']}")
        await query.edit_message_text(f"✅ <b>{data['titre']}</b> publié ! (ID: {anime_id})", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Erreur publication: {e}")
        db.add_log(_uid(update), _uname(update), "ERREUR_POST", str(e), level="ERROR")
        db.increment_daily_stat("errors")
        await query.edit_message_text(f"❌ Erreur : {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def get_programme_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        datetime.strptime(t, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilisez YYYY-MM-DD :")
        return PROGRAMME_DATE
    context.user_data["programme_date"] = t
    await update.message.reply_text("🕐 Heure de publication (format HH:MM) :", parse_mode=ParseMode.HTML)
    return PROGRAMME_HEURE

async def get_programme_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilisez HH:MM :")
        return PROGRAMME_HEURE
    scheduled_at = f"{context.user_data['programme_date']} {t}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if scheduled_at <= now_str:
        await update.message.reply_text("❌ La date doit être dans le futur. Réessayez (YYYY-MM-DD) :")
        return PROGRAMME_DATE
    data = context.user_data["anime"]
    data["posted_by"] = _uid(update)
    pid = db.save_post_programme(data, scheduled_at, _uid(update))
    db.add_log(_uid(update), _uname(update), "PROGRAMMER", f"Post #{pid} pour {scheduled_at}")
    await update.message.reply_text(f"⏰ Post programmé pour <b>{scheduled_at}</b> (ID: {pid})", parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# MODIFIER
# ═══════════════════════════════════════════════════════════

async def modifier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "modifier"):
        return ConversationHandler.END
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /modifier <id>")
        return ConversationHandler.END
    try:
        anime_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return ConversationHandler.END
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text("❌ Anime introuvable.")
        return ConversationHandler.END
    context.user_data["edit_id"] = anime_id
    fields = ["titre", "synopsis", "personnages", "studio", "date_sortie",
              "nb_episodes", "statut", "genres", "note", "avis",
              "image_url", "lien_externe", "categorie", "tags", "template", "trailer_url"]
    buttons = [[InlineKeyboardButton(f, callback_data=f"edit_{f}")] for f in fields]
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="edit_cancel")])
    await update.message.reply_text(
        f"✏️ Modifier <b>{anime['titre']}</b> — Choisissez le champ :",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    return EDIT_FIELD

async def edit_field_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "edit_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Modification annulée.")
        return ConversationHandler.END
    field = query.data.replace("edit_", "")
    context.user_data["edit_field"] = field
    await query.edit_message_text(f"📝 Nouvelle valeur pour <b>{field}</b> :", parse_mode=ParseMode.HTML)
    return EDIT_VALUE

async def edit_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    anime_id = context.user_data.get("edit_id")
    field = context.user_data.get("edit_field")
    new_val = update.message.text.strip()
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text("❌ Anime introuvable.")
        context.user_data.clear()
        return ConversationHandler.END
    anime[field] = new_val
    db.update_anime(anime_id, anime, _uid(update))
    db.add_log(_uid(update), _uname(update), "MODIFIER", f"#{anime_id} {field}={new_val[:50]}")
    await update.message.reply_text(f"✅ <b>{field}</b> mis à jour pour #{anime_id}.", parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# SUPPRIMER
# ═══════════════════════════════════════════════════════════

async def supprimer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "supprimer"):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /supprimer <id>")
        return
    try:
        anime_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text("❌ Anime introuvable.")
        return
    await update.message.reply_text(
        f"⚠️ Supprimer <b>{anime['titre']}</b> (ID:{anime_id}) ?",
        parse_mode=ParseMode.HTML, reply_markup=build_confirm_delete_keyboard(anime_id))


# ═══════════════════════════════════════════════════════════
# RECHERCHE MAL
# ═══════════════════════════════════════════════════════════

async def recherche_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "poster"):
        return ConversationHandler.END
    await update.message.reply_text("🔍 Entrez le nom de l'anime à rechercher :")
    return SEARCH_QUERY

async def search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    await update.message.reply_text("🔄 Recherche en cours...")
    results = await search_anime(query_text, MAX_SEARCH_RESULTS)
    if not results:
        await update.message.reply_text("❌ Aucun résultat.")
        return ConversationHandler.END
    context.user_data["search_results"] = results
    await update.message.reply_text(
        "📋 Résultats :", reply_markup=build_search_result_keyboard(results))
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# RECHERCHE LOCALE & FILTRE
# ═══════════════════════════════════════════════════════════

async def chercher_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /chercher <mot-clé>")
        return
    query = " ".join(args)
    results = db.search_animes_local(query)
    if not results:
        await update.message.reply_text("❌ Aucun résultat local.")
        return
    text = f"🔍 <b>Résultats pour \"{query}\"</b>\n\n"
    for a in results[:MAX_LIST_ITEMS]:
        text += format_anime_short(a) + "\n\n"
    await update.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)

async def filtre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["filtre"] = {}
    kb = build_categorie_keyboard(CATEGORIES)
    await update.message.reply_text("📂 <b>Filtre — Catégorie</b> (ou ⏭️ pour passer) :", parse_mode=ParseMode.HTML, reply_markup=kb)
    return FILTER_CAT

async def filtre_cat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("cat_", "")
    context.user_data["filtre"]["categorie"] = None if cat == "Autre" else cat
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(s, callback_data=f"fstatut_{s}")] for s in STATUTS]
        + [[InlineKeyboardButton("⏭️ Passer", callback_data="fstatut_skip")]]
    )
    await query.edit_message_text("📌 <b>Filtre — Statut</b> :", parse_mode=ParseMode.HTML, reply_markup=kb)
    return FILTER_STATUT

async def filtre_statut_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    val = query.data.replace("fstatut_", "")
    context.user_data["filtre"]["statut"] = None if val == "skip" else val
    await query.edit_message_text("⭐ <b>Filtre — Note minimale</b> (1-10, ou 0 pour passer) :", parse_mode=ParseMode.HTML)
    return FILTER_NOTE

async def filtre_note_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        val = float(t)
        context.user_data["filtre"]["min_note"] = val if val > 0 else None
    except ValueError:
        context.user_data["filtre"]["min_note"] = None
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ Likes", callback_data="fsort_likes"),
         InlineKeyboardButton("👁️ Vues", callback_data="fsort_views")],
        [InlineKeyboardButton("⭐ Note", callback_data="fsort_note"),
         InlineKeyboardButton("📅 Date", callback_data="fsort_posted_at")],
    ])
    await update.message.reply_text("📊 <b>Trier par</b> :", parse_mode=ParseMode.HTML, reply_markup=kb)
    return FILTER_SORT

async def filtre_sort_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sort_by = query.data.replace("fsort_", "")
    f = context.user_data.get("filtre", {})
    results = db.get_animes_filtered(f.get("categorie"), f.get("statut"), f.get("min_note"), sort_by)
    if not results:
        await query.edit_message_text("❌ Aucun résultat avec ces filtres.")
    else:
        text = f"🔍 <b>Résultats filtrés ({len(results)})</b>\n\n"
        for a in results[:MAX_LIST_ITEMS]:
            text += format_anime_short(a) + "\n\n"
        await query.edit_message_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)
    context.user_data.pop("filtre", None)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# COMPARER
# ═══════════════════════════════════════════════════════════

async def comparer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚔️ <b>Comparaison</b> — ID du premier anime :", parse_mode=ParseMode.HTML)
    return COMPARE_A

async def compare_a_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        aid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return COMPARE_A
    anime = db.get_anime(aid)
    if not anime:
        await update.message.reply_text("❌ Anime introuvable.")
        return COMPARE_A
    context.user_data["compare_a"] = anime
    await update.message.reply_text(f"✅ <b>{anime['titre']}</b> sélectionné.\n\nID du deuxième anime :", parse_mode=ParseMode.HTML)
    return COMPARE_B

async def compare_b_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return COMPARE_B
    anime_b = db.get_anime(bid)
    if not anime_b:
        await update.message.reply_text("❌ Anime introuvable.")
        return COMPARE_B
    anime_a = context.user_data.get("compare_a")
    text = format_compare(anime_a, anime_b)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    context.user_data.pop("compare_a", None)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# FAVORIS
# ═══════════════════════════════════════════════════════════

async def favoris_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = _uid(update)
    favs = db.get_favoris(uid)
    if not favs:
        await update.message.reply_text("💛 Vous n'avez aucun favori. Appuyez sur 🤍 Favori sous un post !")
        return
    text = f"💛 <b>Vos favoris ({len(favs)})</b>\n\n"
    for a in favs[:MAX_LIST_ITEMS]:
        text += format_anime_short(a) + "\n\n"
    await update.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════
# SONDAGE
# ═══════════════════════════════════════════════════════════

async def sondage_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "sondage"):
        return ConversationHandler.END
    await update.message.reply_text("📊 <b>Créer un sondage</b>\n\nEntrez la question :", parse_mode=ParseMode.HTML)
    return SONDAGE_QUESTION

async def sondage_get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sondage_question"] = update.message.text.strip()
    await update.message.reply_text(
        f"📊 Options (une par ligne, max {MAX_POLL_OPTIONS}) :\n<i>Envoyez chaque option sur une ligne séparée</i>",
        parse_mode=ParseMode.HTML)
    return SONDAGE_OPTIONS

async def sondage_get_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = [o.strip() for o in update.message.text.strip().split("\n") if o.strip()]
    if len(options) < 2:
        await update.message.reply_text("❌ Minimum 2 options. Réessayez :")
        return SONDAGE_OPTIONS
    options = options[:MAX_POLL_OPTIONS]
    question = context.user_data["sondage_question"]
    sondage_data = {"question": question, "options": json.dumps(options, ensure_ascii=False)}
    text = format_sondage(sondage_data, {}, 0)
    kb = build_sondage_keyboard(0, options)
    try:
        msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        sid = db.create_sondage(question, options, _uid(update), msg.message_id, CHANNEL_ID)
        # Update keyboard with real sondage_id
        kb = build_sondage_keyboard(sid, options)
        await context.bot.edit_message_reply_markup(chat_id=CHANNEL_ID, message_id=msg.message_id, reply_markup=kb)
        db.add_log(_uid(update), _uname(update), "SONDAGE", f"Sondage #{sid}: {question[:50]}")
        await update.message.reply_text(f"✅ Sondage publié ! (ID: {sid})", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Erreur sondage: {e}")
        await update.message.reply_text(f"❌ Erreur : {e}")
    context.user_data.clear()
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# QUIZ
# ═══════════════════════════════════════════════════════════

async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "quiz"):
        return ConversationHandler.END
    await update.message.reply_text("🧠 <b>Créer un quiz</b>\n\nEntrez la question :", parse_mode=ParseMode.HTML)
    return QUIZ_QUESTION

async def quiz_get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz_question"] = update.message.text.strip()
    await update.message.reply_text(
        f"🧠 Options (une par ligne, max {MAX_QUIZ_OPTIONS}) :", parse_mode=ParseMode.HTML)
    return QUIZ_OPTIONS

async def quiz_get_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = [o.strip() for o in update.message.text.strip().split("\n") if o.strip()]
    if len(options) < 2:
        await update.message.reply_text("❌ Minimum 2 options. Réessayez :")
        return QUIZ_OPTIONS
    options = options[:MAX_QUIZ_OPTIONS]
    context.user_data["quiz_options"] = options
    text = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(options))
    await update.message.reply_text(
        f"🧠 Options :\n{text}\n\nNuméro de la bonne réponse (1-{len(options)}) :", parse_mode=ParseMode.HTML)
    return QUIZ_CORRECT

async def quiz_get_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text.strip()) - 1
        options = context.user_data["quiz_options"]
        if idx < 0 or idx >= len(options):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Numéro invalide. Réessayez :")
        return QUIZ_CORRECT
    context.user_data["quiz_correct"] = idx
    await update.message.reply_text("🧠 Explication (affichée après la réponse) :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return QUIZ_EXPLICATION

async def quiz_get_explication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    explication = "" if t == "-" else t
    question = context.user_data["quiz_question"]
    options = context.user_data["quiz_options"]
    correct_idx = context.user_data["quiz_correct"]
    quiz_data = {"question": question, "options": json.dumps(options, ensure_ascii=False)}
    text = format_quiz(quiz_data)
    kb = build_quiz_keyboard(0, options)
    try:
        msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        qid = db.create_quiz(question, options, correct_idx, explication, _uid(update))
        kb = build_quiz_keyboard(qid, options)
        await context.bot.edit_message_reply_markup(chat_id=CHANNEL_ID, message_id=msg.message_id, reply_markup=kb)
        db.add_log(_uid(update), _uname(update), "QUIZ", f"Quiz #{qid}: {question[:50]}")
        await update.message.reply_text(f"✅ Quiz publié ! (ID: {qid})", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Erreur quiz: {e}")
        await update.message.reply_text(f"❌ Erreur : {e}")
    context.user_data.clear()
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# CALENDRIER
# ═══════════════════════════════════════════════════════════

async def calendrier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entries = db.get_calendrier_semaine()
    if not entries:
        await update.message.reply_text("📅 Le calendrier est vide. Utilisez /addcalendrier pour ajouter des anime.")
        return
    text = format_calendrier(entries)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def addcalendrier_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "calendrier"):
        return ConversationHandler.END
    await update.message.reply_text("📅 <b>Ajouter au calendrier</b>\n\nTitre de l'anime :", parse_mode=ParseMode.HTML)
    return CAL_TITRE

async def cal_get_titre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cal_titre"] = update.message.text.strip()
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(j, callback_data=f"calj_{j}")] for j in jours])
    await update.message.reply_text("📅 Jour de diffusion :", reply_markup=kb)
    return CAL_JOUR

async def cal_get_jour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["cal_jour"] = query.data.replace("calj_", "")
    await query.edit_message_text("🕐 Heure de diffusion (HH:MM) :\n<i>Envoyez - pour passer</i>", parse_mode=ParseMode.HTML)
    return CAL_HEURE

async def cal_get_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    heure = "" if t == "-" else t
    titre = context.user_data["cal_titre"]
    jour = context.user_data["cal_jour"]
    db.add_calendrier(titre, jour, heure, added_by=_uid(update))
    db.add_log(_uid(update), _uname(update), "CALENDRIER", f"{titre} → {jour} {heure}")
    await update.message.reply_text(
        f"✅ <b>{titre}</b> ajouté au calendrier : {jour} {heure}", parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# CALLBACK QUERIES (likes, dislikes, views, favoris, rating, sondage, quiz, etc.)
# ═══════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id

    # ── Like toggle ──
    if data.startswith("like_"):
        await query.answer()
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            return
        if db.has_voted(anime_id, uid, "like"):
            db.remove_vote(anime_id, uid, "like")
            db.remove_like(anime_id)
        else:
            if db.has_voted(anime_id, uid, "dislike"):
                db.remove_vote(anime_id, uid, "dislike")
                anime = db.get_anime(anime_id)
                if anime:
                    conn = db.get_connection()
                    conn.execute("UPDATE animes SET dislikes=MAX(dislikes-1,0) WHERE id=?", (anime_id,))
                    conn.commit()
            db.add_vote(anime_id, uid, "like")
            db.add_like(anime_id)
        anime = db.get_anime(anime_id)
        if anime:
            is_fav = db.is_favori(uid, anime_id)
            try:
                await query.edit_message_reply_markup(
                    reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))
            except Exception:
                pass

    # ── Dislike toggle ──
    elif data.startswith("dislike_"):
        await query.answer()
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            return
        if db.has_voted(anime_id, uid, "dislike"):
            db.remove_vote(anime_id, uid, "dislike")
            conn = db.get_connection()
            conn.execute("UPDATE animes SET dislikes=MAX(dislikes-1,0) WHERE id=?", (anime_id,))
            conn.commit()
        else:
            if db.has_voted(anime_id, uid, "like"):
                db.remove_vote(anime_id, uid, "like")
                db.remove_like(anime_id)
            db.add_vote(anime_id, uid, "dislike")
            db.add_dislike(anime_id)
        anime = db.get_anime(anime_id)
        if anime:
            is_fav = db.is_favori(uid, anime_id)
            try:
                await query.edit_message_reply_markup(
                    reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))
            except Exception:
                pass

    # ── View ──
    elif data.startswith("view_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        db.add_view(anime_id)
        anime = db.get_anime(anime_id)
        if anime:
            is_fav = db.is_favori(uid, anime_id)
            try:
                await query.edit_message_reply_markup(
                    reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))
            except Exception:
                pass
        await query.answer(f"👁️ {anime['views']} vues" if anime else "👁️")

    # ── Favori toggle ──
    elif data.startswith("fav_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        if db.is_favori(uid, anime_id):
            db.remove_favori(uid, anime_id)
            await query.answer("💔 Retiré des favoris")
        else:
            if db.add_favori(uid, anime_id):
                await query.answer("💛 Ajouté aux favoris !")
            else:
                await query.answer("❌ Déjà en favoris")
        anime = db.get_anime(anime_id)
        if anime:
            is_fav = db.is_favori(uid, anime_id)
            try:
                await query.edit_message_reply_markup(
                    reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))
            except Exception:
                pass

    # ── Rating ──
    elif data.startswith("rate_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        await query.answer()
        try:
            await query.message.reply_text(
                f"⭐ Notez cet anime (1-10) :", reply_markup=build_rating_keyboard(anime_id))
        except Exception:
            pass

    elif data.startswith("rating_"):
        parts = data.split("_")
        try:
            anime_id = int(parts[1])
            score = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("❌ Erreur")
            return
        db.add_user_rating(uid, anime_id, score)
        anime = db.get_anime(anime_id)
        await query.answer(f"✅ Note {score}/10 enregistrée !")
        try:
            await query.edit_message_text(
                f"⭐ Vous avez noté <b>{anime['titre'] if anime else '?'}</b> : {score}/10\n"
                f"👥 Moyenne communauté : {anime['score_communaute']}/10 ({anime['nb_votes_communaute']} votes)" if anime else "✅ Noté !",
                parse_mode=ParseMode.HTML)
        except Exception:
            pass

    # ── Info ──
    elif data.startswith("info_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        anime = db.get_anime(anime_id)
        if anime:
            fav_count = db.count_favoris(anime_id)
            text = (
                f"📊 <b>Infos — {anime['titre']}</b>\n\n"
                f"❤️ Likes : {anime['likes']}\n👁️ Vues : {anime['views']}\n"
                f"💛 Favoris : {fav_count}\n"
                f"⭐ Note MAL : {anime['note']}/10\n"
                f"👥 Note communauté : {anime.get('score_communaute', 0)}/10 ({anime.get('nb_votes_communaute', 0)} votes)\n"
                f"📅 Publié le : {anime.get('posted_at', '?')[:10]}"
            )
            await query.answer()
            try:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("❌ Introuvable")

    # ── Similar ──
    elif data.startswith("similar_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        anime = db.get_anime(anime_id)
        if anime and anime.get("categorie"):
            similar = db.get_animes_by_categorie(anime["categorie"])
            similar = [a for a in similar if a["id"] != anime_id][:5]
            if similar:
                text = f"🔍 <b>Similaires à {anime['titre']}</b>\n\n"
                for a in similar:
                    text += format_anime_short(a) + "\n\n"
                await query.answer()
                try:
                    await query.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)
                except Exception:
                    pass
            else:
                await query.answer("Aucun anime similaire trouvé")
        else:
            await query.answer("❌")

    # ── Category ──
    elif data.startswith("category_"):
        try:
            anime_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer()
            return
        anime = db.get_anime(anime_id)
        if anime and anime.get("categorie"):
            animes = db.get_animes_by_categorie(anime["categorie"])[:10]
            text = f"📂 <b>{anime['categorie']}</b> ({len(animes)} anime)\n\n"
            for a in animes:
                text += format_anime_short(a) + "\n\n"
            await query.answer()
            try:
                await query.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("❌")

    # ── Sondage vote ──
    elif data.startswith("svote_"):
        parts = data.split("_")
        try:
            sondage_id = int(parts[1])
            option_idx = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("❌")
            return
        if db.vote_sondage(sondage_id, uid, option_idx):
            await query.answer("✅ Vote enregistré !")
        else:
            await query.answer("❌ Vous avez déjà voté")
        # Update sondage display
        sondage = db.get_sondage(sondage_id)
        if sondage:
            results = db.get_sondage_results(sondage_id)
            total = db.get_sondage_total_votes(sondage_id)
            options = json.loads(sondage.get("options", "[]"))
            text = format_sondage(sondage, results, total)
            kb = build_sondage_keyboard(sondage_id, options)
            try:
                await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                pass

    # ── Sondage results ──
    elif data.startswith("sresult_"):
        try:
            sondage_id = int(data.split("_")[1])
        except (ValueError, IndexError):
            await query.answer("❌")
            return
        sondage = db.get_sondage(sondage_id)
        if sondage:
            results = db.get_sondage_results(sondage_id)
            total = db.get_sondage_total_votes(sondage_id)
            text = format_sondage(sondage, results, total)
            await query.answer()
            try:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("❌ Sondage introuvable")

    # ── Quiz answer ──
    elif data.startswith("qanswer_"):
        parts = data.split("_")
        try:
            quiz_id = int(parts[1])
            answer_idx = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("❌")
            return
        quiz_data = db.get_quiz(quiz_id)
        if not quiz_data:
            await query.answer("❌ Quiz introuvable")
            return
        correct = answer_idx == quiz_data["correct_idx"]
        if db.answer_quiz(quiz_id, uid, answer_idx, correct):
            options = json.loads(quiz_data.get("options", "[]"))
            correct_opt = options[quiz_data["correct_idx"]] if quiz_data["correct_idx"] < len(options) else "?"
            if correct:
                text = f"✅ <b>Bonne réponse !</b>\n\n🎉 La réponse était : <b>{correct_opt}</b>"
            else:
                text = f"❌ <b>Mauvaise réponse !</b>\n\n✅ La bonne réponse était : <b>{correct_opt}</b>"
            if quiz_data.get("explication"):
                text += f"\n\n💡 {quiz_data['explication']}"
            stats = db.get_quiz_stats(quiz_id)
            pct = round(stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            text += f"\n\n📊 {stats['correct']}/{stats['total']} bonnes réponses ({pct}%)"
            await query.answer("✅ Correct !" if correct else "❌ Raté !")
            try:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            await query.answer("❌ Vous avez déjà répondu")

    # ── Confirm delete ──
    elif data.startswith("confirm_delete_"):
        try:
            anime_id = int(data.replace("confirm_delete_", ""))
        except ValueError:
            await query.answer("❌")
            return
        anime = db.get_anime(anime_id)
        if anime:
            db.delete_anime(anime_id)
            db.add_log(uid, query.from_user.username or "?", "SUPPRIMER", f"#{anime_id}: {anime['titre']}")
            await query.edit_message_text(f"🗑️ <b>{anime['titre']}</b> supprimé.", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ Anime introuvable.")

    elif data.startswith("cancel_delete_"):
        await query.edit_message_text("❌ Suppression annulée.")

    # ── Select from Jikan search ──
    elif data.startswith("select_jikan_"):
        try:
            mal_id = int(data.replace("select_jikan_", ""))
        except ValueError:
            await query.answer("❌")
            return
        await query.answer("🔄 Chargement...")
        jikan_data = await get_anime_by_id(mal_id)
        if not jikan_data:
            await query.edit_message_text("❌ Impossible de charger l'anime.")
            return
        parsed = parse_jikan_anime(jikan_data)
        # Fetch characters
        chars = await get_anime_characters(mal_id)
        if chars:
            char_names = [c["character"]["name"] for c in chars[:8] if "character" in c]
            parsed["personnages"] = ", ".join(char_names)
        context.user_data["anime"] = parsed
        preview = format_anime_post(parsed, "standard")
        preview = _truncate(preview, 3500)
        kb = build_template_keyboard()
        await query.edit_message_text(
            f"📋 <b>Aperçu :</b>\n\n{preview}\n\n🎨 Choisissez un template :",
            parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "cancel_search":
        await query.edit_message_text("❌ Recherche annulée.")

    # ── Delete programme ──
    elif data.startswith("delprog_"):
        try:
            pid = int(data.replace("delprog_", ""))
        except ValueError:
            await query.answer("❌")
            return
        db.delete_post_programme(pid)
        db.add_log(uid, query.from_user.username or "?", "DEL_PROGRAMME", f"Post programmé #{pid}")
        await query.answer("✅ Supprimé")
        await query.edit_message_text(f"🗑️ Post programmé #{pid} supprimé.")

    # ── Template choice from search ──
    elif data.startswith("tpl_") and "anime" in context.user_data:
        tpl = data.replace("tpl_", "")
        context.user_data["anime"]["template"] = tpl
        anime_data = context.user_data["anime"]
        anime_data["posted_by"] = uid
        anime_data["chat_id"] = CHANNEL_ID
        anime_data["message_id"] = None
        text = format_anime_post(anime_data, tpl)
        text = _truncate(text, 1024)
        try:
            if anime_data.get("image_url") and anime_data["image_url"].startswith("http"):
                msg = await context.bot.send_photo(
                    chat_id=CHANNEL_ID, photo=anime_data["image_url"],
                    caption=text, parse_mode=ParseMode.HTML,
                    reply_markup=build_anime_keyboard(0, anime_data.get("lien_externe"), 0, 0))
            else:
                msg = await context.bot.send_message(
                    chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                    reply_markup=build_anime_keyboard(0, anime_data.get("lien_externe"), 0, 0))
            anime_data["message_id"] = msg.message_id
            anime_id = db.save_anime(anime_data)
            db.update_message_id(anime_id, msg.message_id, CHANNEL_ID)
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID, message_id=msg.message_id,
                    reply_markup=build_anime_keyboard(anime_id, anime_data.get("lien_externe"), 0, 0))
            except Exception:
                pass
            db.add_log(uid, query.from_user.username or "?", "POSTER_MAL", f"#{anime_id}: {anime_data['titre']}")
            await query.edit_message_text(f"✅ <b>{anime_data['titre']}</b> publié ! (ID: {anime_id})", parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Erreur pub MAL: {e}")
            await query.edit_message_text(f"❌ Erreur : {e}")
        context.user_data.clear()


# ═══════════════════════════════════════════════════════════
# COMMANDES CLASSEMENTS & LISTES
# ═══════════════════════════════════════════════════════════

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Chargement du top MAL...")
    results = await get_top_anime(10)
    if not results:
        await update.message.reply_text("❌ Erreur API.")
        return
    text = f"🏆 <b>Top 10 MAL</b>\n\n"
    for i, a in enumerate(results, 1):
        e = get_rank_emoji(i)
        text += f"{e} <b>{a.get('title', '?')}</b> — ⭐ {a.get('score', '?')}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def saison_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Chargement...")
    results = await get_current_season_anime(10)
    if not results:
        await update.message.reply_text("❌ Erreur API.")
        return
    text = f"📺 <b>Anime de la saison</b>\n\n"
    for i, a in enumerate(results, 1):
        text += f"{i}. <b>{a.get('title', '?')}</b> — ⭐ {a.get('score', '?')}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def upcoming_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Chargement...")
    results = await get_upcoming_anime(10)
    if not results:
        await update.message.reply_text("❌ Erreur API.")
        return
    text = f"🔜 <b>Anime à venir</b>\n\n"
    for i, a in enumerate(results, 1):
        text += f"{i}. <b>{a.get('title', '?')}</b>\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def toplikes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_top_liked(10)
    if not animes:
        await update.message.reply_text("❌ Aucun anime publié.")
        return
    text = f"❤️ <b>Top Likés</b>\n\n"
    for i, a in enumerate(animes, 1):
        text += f"{get_rank_emoji(i)} <b>{a['titre']}</b> — ❤️ {a['likes']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def topvues_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_top_viewed(10)
    if not animes:
        await update.message.reply_text("❌ Aucun anime publié.")
        return
    text = f"👁️ <b>Top Vus</b>\n\n"
    for i, a in enumerate(animes, 1):
        text += f"{get_rank_emoji(i)} <b>{a['titre']}</b> — 👁️ {a['views']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def topnotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_top_rated(10)
    if not animes:
        await update.message.reply_text("❌ Aucune note communautaire.")
        return
    text = f"⭐ <b>Top Notes Communauté</b>\n\n"
    for i, a in enumerate(animes, 1):
        text += f"{get_rank_emoji(i)} <b>{a['titre']}</b> — ⭐ {a['score_communaute']}/10 ({a['nb_votes_communaute']} votes)\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"📂 <b>Catégories</b>\n\n"
    for cat in CATEGORIES:
        count = len(db.get_animes_by_categorie(cat))
        if count > 0:
            text += f"● <b>{cat}</b> — {count} anime\n"
    text += "\nUtilisez /chercher ou /filtre pour filtrer."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def liste_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_all_animes()
    if not animes:
        await update.message.reply_text("❌ Aucun anime publié.")
        return
    text = f"📋 <b>Tous les anime ({len(animes)})</b>\n\n"
    for a in animes[:MAX_LIST_ITEMS]:
        text += format_anime_short(a) + "\n\n"
    if len(animes) > MAX_LIST_ITEMS:
        text += f"<i>... et {len(animes) - MAX_LIST_ITEMS} de plus</i>"
    await update.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)

async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /anime <id>")
        return
    try:
        anime_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text("❌ Anime introuvable.")
        return
    text = format_anime_post(anime, anime.get("template", "standard"))
    is_fav = db.is_favori(_uid(update), anime_id)
    if anime.get("image_url") and anime["image_url"].startswith("http"):
        await update.message.reply_photo(
            photo=anime["image_url"], caption=_truncate(text, 1024),
            parse_mode=ParseMode.HTML,
            reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))
    else:
        await update.message.reply_text(
            _truncate(text, 4000), parse_mode=ParseMode.HTML,
            reply_markup=build_anime_keyboard(anime_id, anime.get("lien_externe"), anime["likes"], anime["views"], is_fav))


# ═══════════════════════════════════════════════════════════
# SUIVIS / NOTIFICATIONS
# ═══════════════════════════════════════════════════════════

async def suivre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "notif"):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /suivre <titre>")
        return
    query_text = " ".join(args)
    results = await search_anime(query_text, 1)
    if not results:
        await update.message.reply_text("❌ Anime introuvable sur MAL.")
        return
    a = results[0]
    mal_id = a.get("mal_id", 0)
    titre = a.get("title", "?")
    eps = a.get("episodes") or 0
    db.add_suivi(mal_id, titre, eps, _uid(update))
    db.add_log(_uid(update), _uname(update), "SUIVRE", f"{titre} (MAL:{mal_id})")
    await update.message.reply_text(f"🔔 <b>{titre}</b> suivi ! Vous serez notifié des nouveaux épisodes.", parse_mode=ParseMode.HTML)

async def suivis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    if not suivis:
        await update.message.reply_text("🔔 Aucun anime suivi.")
        return
    text = f"🔔 <b>Anime suivis ({len(suivis)})</b>\n\n"
    for s in suivis:
        text += f"● <b>{s['titre']}</b> (MAL:{s['mal_id']}) — Ep {s['dernier_ep']}\n"
    text += "\n/arretersuivi <mal_id> pour arrêter."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def arretersuivi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /arretersuivi <mal_id>")
        return
    try:
        mal_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    db.remove_suivi(mal_id)
    await update.message.reply_text(f"✅ Suivi arrêté pour MAL:{mal_id}")


# ═══════════════════════════════════════════════════════════
# PROGRAMMES
# ═══════════════════════════════════════════════════════════

async def programmes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "programmer"):
        return
    posts = db.get_posts_programmes_pending()
    if not posts:
        await update.message.reply_text("⏰ Aucun post programmé en attente.")
        return
    text = f"⏰ <b>Posts programmés ({len(posts)})</b>\n\n"
    buttons = []
    for p in posts[:10]:
        text += format_post_programme(p) + "\n\n"
        buttons.append([InlineKeyboardButton(f"🗑️ Supprimer #{p['id']}", callback_data=f"delprog_{p['id']}")])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)


# ═══════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════

async def admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "admin"):
        return
    admins = db.get_all_admins()
    if not admins:
        await update.message.reply_text("👥 Aucun admin.")
        return
    text = f"👥 <b>Admins ({len(admins)})</b>\n\n"
    for a in admins:
        text += f"● <b>@{a['username']}</b> ({a['user_id']}) — {a['role']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def addadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("👤 ID Telegram du nouvel admin :")
    return ADD_ADMIN_ID

async def addadmin_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return ADD_ADMIN_ID
    context.user_data["new_admin_id"] = uid
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(r, callback_data=f"role_{r}")]
        for r in ["admin", "moderateur", "editeur"]
    ])
    await update.message.reply_text("📋 Rôle :", reply_markup=kb)
    return ADD_ADMIN_ROLE

async def addadmin_get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.replace("role_", "")
    uid = context.user_data.get("new_admin_id")
    db.add_admin(uid, str(uid), role, _uid(update))
    db.add_log(_uid(update), _uname(update), "ADD_ADMIN", f"{uid} → {role}")
    await query.edit_message_text(f"✅ Admin ajouté : {uid} ({role})")
    context.user_data.clear()
    return ConversationHandler.END

async def removeadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("👤 ID Telegram de l'admin à retirer :")
    return REMOVE_ADMIN_ID

async def removeadmin_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return REMOVE_ADMIN_ID
    admin = db.get_admin(uid)
    if not admin:
        await update.message.reply_text("❌ Cet utilisateur n'est pas admin.")
        return ConversationHandler.END
    if admin["role"] == "superadmin":
        await update.message.reply_text("⛔ Impossible de retirer un superadmin.")
        return ConversationHandler.END
    db.remove_admin(uid)
    db.add_log(_uid(update), _uname(update), "REMOVE_ADMIN", str(uid))
    await update.message.reply_text(f"✅ Admin {uid} retiré.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
# BLACKLIST
# ═══════════════════════════════════════════════════════════

async def blacklist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return ConversationHandler.END
    await update.message.reply_text("🚫 ID Telegram à blacklister :")
    return BLACKLIST_ID

async def blacklist_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return BLACKLIST_ID
    context.user_data["bl_id"] = uid
    await update.message.reply_text("📝 Raison :")
    return BLACKLIST_RAISON

async def blacklist_get_raison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raison = update.message.text.strip()
    uid = context.user_data.get("bl_id")
    db.blacklist_user(uid, str(uid), raison, _uid(update))
    db.add_log(_uid(update), _uname(update), "BLACKLIST", f"{uid}: {raison}")
    await update.message.reply_text(f"🚫 {uid} blacklisté.")
    context.user_data.clear()
    return ConversationHandler.END

async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /unblacklist <id>")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    db.unblacklist_user(uid)
    db.add_log(_uid(update), _uname(update), "UNBLACKLIST", str(uid))
    await update.message.reply_text(f"✅ {uid} retiré de la blacklist.")

async def voirblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "blacklist"):
        return
    bl = db.get_blacklist()
    if not bl:
        await update.message.reply_text("🚫 Blacklist vide.")
        return
    text = f"🚫 <b>Blacklist ({len(bl)})</b>\n\n"
    for b in bl:
        text += f"● {b['user_id']} — {b.get('raison', '?')}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════
# STATS / LOGS / BACKUP / MAINTENANCE
# ═══════════════════════════════════════════════════════════

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "stats"):
        return
    stats = db.get_stats()
    daily = db.get_daily_stats(7)
    text = format_stats_dashboard(stats, daily)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    args = context.args
    level = args[0].upper() if args else None
    logs = db.get_logs(20, level)
    if not logs:
        await update.message.reply_text("📋 Aucun log.")
        return
    text = f"📋 <b>Logs</b>{f' ({level})' if level else ''}\n\n"
    for l in logs:
        text += format_log_entry(l) + "\n\n"
    await update.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)

async def logsuser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /logsuser <id>")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    logs = db.get_logs_by_user(uid, 20)
    if not logs:
        await update.message.reply_text(f"📋 Aucun log pour {uid}.")
        return
    text = f"📋 <b>Logs de {uid}</b>\n\n"
    for l in logs:
        text += format_log_entry(l) + "\n\n"
    await update.message.reply_text(_truncate(text, 4000), parse_mode=ParseMode.HTML)

async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    filepath, size = db.create_backup()
    if filepath:
        text = format_backup_info(filepath, size)
        db.add_log(_uid(update), _uname(update), "BACKUP", filepath)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ Erreur lors du backup.")

async def backups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    history = db.get_backup_history(10)
    if not history:
        await update.message.reply_text("💾 Aucun backup.")
        return
    text = f"💾 <b>Historique backups</b>\n\n"
    for b in history:
        text += f"● <code>{b['filename']}</code> — {b.get('size_bytes', 0) / 1024:.1f} Ko — {b['created_at'][:16]}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "backup"):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage : /restore <fichier>")
        return
    if db.restore_backup(args[0]):
        db.add_log(_uid(update), _uname(update), "RESTORE", args[0])
        await update.message.reply_text("✅ Backup restauré. Redémarrez le bot.")
    else:
        await update.message.reply_text("❌ Fichier introuvable.")

async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "maintenance"):
        return
    current = db.get_setting("maintenance", "0")
    new_val = "0" if current == "1" else "1"
    db.set_setting("maintenance", new_val)
    status = "🔧 ON" if new_val == "1" else "✅ OFF"
    db.add_log(_uid(update), _uname(update), "MAINTENANCE", status)
    await update.message.reply_text(f"Mode maintenance : <b>{status}</b>", parse_mode=ParseMode.HTML)

async def templates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "templates"):
        return
    templates = db.get_all_templates()
    text = f"🎨 <b>Templates ({len(templates)})</b>\n\n"
    for t in templates:
        default = " ⭐" if t.get("is_default") else ""
        text += f"● <b>{t['name']}</b>{default} — {t.get('description', '')}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cleanlogs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_perm(update, "logs"):
        return
    args = context.args
    days = int(args[0]) if args else 30
    db.clear_old_logs(days)
    db.add_log(_uid(update), _uname(update), "CLEANLOGS", f">{days} jours")
    await update.message.reply_text(f"🧹 Logs de plus de {days} jours supprimés.")


# ═══════════════════════════════════════════════════════════
# SCHEDULER (posts programmés, épisodes, backup auto)
# ═══════════════════════════════════════════════════════════

async def scheduler_posts(context: ContextTypes.DEFAULT_TYPE):
    posts = db.get_posts_programmes_dus()
    for post in posts:
        try:
            data = json.loads(post["data_json"])
            tpl = data.get("template", "standard")
            text = format_anime_post(data, tpl)
            text = _truncate(text, 1024)
            if data.get("image_url") and data["image_url"].startswith("http"):
                msg = await context.bot.send_photo(
                    chat_id=CHANNEL_ID, photo=data["image_url"],
                    caption=text, parse_mode=ParseMode.HTML,
                    reply_markup=build_anime_keyboard(0, data.get("lien_externe"), 0, 0))
            else:
                msg = await context.bot.send_message(
                    chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML,
                    reply_markup=build_anime_keyboard(0, data.get("lien_externe"), 0, 0))
            data["message_id"] = msg.message_id
            data["chat_id"] = CHANNEL_ID
            data["posted_by"] = data.get("posted_by", 0)
            anime_id = db.save_anime(data)
            db.update_message_id(anime_id, msg.message_id, CHANNEL_ID)
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID, message_id=msg.message_id,
                    reply_markup=build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0))
            except Exception:
                pass
            db.mark_post_publie(post["id"])
            db.add_log(0, "scheduler", "AUTO_POST", f"#{anime_id}: {data.get('titre', '?')}")
            logger.info(f"Post programmé #{post['id']} publié → anime #{anime_id}")
        except Exception as e:
            db.mark_post_publie(post["id"], str(e))
            db.increment_daily_stat("errors")
            logger.error(f"Erreur post programmé #{post['id']}: {e}")

async def scheduler_episodes(context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    for s in suivis:
        try:
            from jikan import get_anime_episodes
            ep_data = await get_anime_episodes(s["mal_id"])
            if not ep_data:
                continue
            episodes = ep_data.get("data", [])
            if episodes:
                last_ep = len(episodes)
                if last_ep > s["dernier_ep"]:
                    db.update_suivi_ep(s["mal_id"], last_ep)
                    text = format_notification_episode(s["titre"], last_ep)
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
                    db.add_log(0, "scheduler", "NOTIF_EPISODE", f"{s['titre']} ep {last_ep}")
                    logger.info(f"Nouvel épisode: {s['titre']} ep {last_ep}")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Erreur check épisode {s['titre']}: {e}")

async def scheduler_backup(context: ContextTypes.DEFAULT_TYPE):
    filepath, size = db.create_backup()
    if filepath:
        logger.info(f"Backup auto: {filepath} ({size / 1024:.1f} Ko)")
    else:
        logger.error("Erreur backup auto")
        db.increment_daily_stat("errors")


# ═══════════════════════════════════════════════════════════
# SETUP BOT COMMANDS
# ═══════════════════════════════════════════════════════════

async def post_init(application):
    commands = [
        BotCommand("start", "Menu principal"),
        BotCommand("help", "Aide complète"),
        BotCommand("quoideneuf", "Nouveautés v4"),
        BotCommand("poster", "Publier un anime"),
        BotCommand("recherche", "Rechercher sur MAL"),
        BotCommand("chercher", "Recherche locale"),
        BotCommand("filtre", "Recherche avancée"),
        BotCommand("comparer", "Comparer 2 anime"),
        BotCommand("anime", "Fiche anime"),
        BotCommand("top", "Top 10 MAL"),
        BotCommand("saison", "Anime de la saison"),
        BotCommand("upcoming", "Anime à venir"),
        BotCommand("favoris", "Mes favoris"),
        BotCommand("sondage", "Créer un sondage"),
        BotCommand("quiz", "Créer un quiz"),
        BotCommand("calendrier", "Calendrier sorties"),
        BotCommand("addcalendrier", "Ajouter au calendrier"),
        BotCommand("toplikes", "Top likés"),
        BotCommand("topvues", "Top vus"),
        BotCommand("topnotes", "Top notes communauté"),
        BotCommand("categories", "Par catégorie"),
        BotCommand("liste", "Tous les anime"),
        BotCommand("suivre", "Suivre un anime"),
        BotCommand("suivis", "Anime suivis"),
        BotCommand("arretersuivi", "Arrêter un suivi"),
        BotCommand("programmes", "Posts programmés"),
        BotCommand("stats", "Statistiques"),
        BotCommand("admins", "Liste admins"),
        BotCommand("annuler", "Annuler action"),
    ]
    await application.bot.set_my_commands(commands)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ── ConversationHandlers ──────────────────────────────

    poster_conv = ConversationHandler(
        entry_points=[CommandHandler("poster", poster_start)],
        states={
            TITRE:           [MessageHandler(filters.TEXT & ~filters.COMMAND, get_titre)],
            TITRE_ORIGINAL:  [MessageHandler(filters.TEXT, get_titre_original)],
            SYNOPSIS:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_synopsis)],
            PERSONNAGES:     [MessageHandler(filters.TEXT, get_personnages)],
            STUDIO:          [MessageHandler(filters.TEXT, get_studio)],
            DATE_SORTIE:     [MessageHandler(filters.TEXT, get_date_sortie)],
            NB_EPISODES:     [MessageHandler(filters.TEXT, get_nb_episodes)],
            STATUT_CHOICE:   [CallbackQueryHandler(get_statut, pattern=r"^statut_")],
            GENRES:          [MessageHandler(filters.TEXT, get_genres)],
            NOTE:            [MessageHandler(filters.TEXT, get_note)],
            AVIS:            [MessageHandler(filters.TEXT, get_avis)],
            IMAGE_URL:       [MessageHandler(filters.TEXT, get_image_url)],
            LIEN_EXTERNE:    [MessageHandler(filters.TEXT, get_lien_externe)],
            CATEGORIE_CHOICE:[CallbackQueryHandler(get_categorie, pattern=r"^cat_")],
            TAGS_INPUT:      [MessageHandler(filters.TEXT, get_tags)],
            TEMPLATE_CHOICE: [CallbackQueryHandler(get_template, pattern=r"^tpl_")],
            CONFIRM_POST:    [CallbackQueryHandler(confirm_post, pattern=r"^pub_")],
            PROGRAMME_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_programme_date)],
            PROGRAMME_HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_programme_heure)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
        per_message=False,
    )

    modifier_conv = ConversationHandler(
        entry_points=[CommandHandler("modifier", modifier_cmd)],
        states={
            EDIT_FIELD: [CallbackQueryHandler(edit_field_cb, pattern=r"^edit_")],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_input)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
        per_message=False,
    )

    recherche_conv = ConversationHandler(
        entry_points=[CommandHandler("recherche", recherche_cmd)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_input)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    addadmin_conv = ConversationHandler(
        entry_points=[CommandHandler("addadmin", addadmin_start)],
        states={
            ADD_ADMIN_ID:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addadmin_get_id)],
            ADD_ADMIN_ROLE: [CallbackQueryHandler(addadmin_get_role, pattern=r"^role_")],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
        per_message=False,
    )

    removeadmin_conv = ConversationHandler(
        entry_points=[CommandHandler("removeadmin", removeadmin_start)],
        states={
            REMOVE_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, removeadmin_get_id)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    blacklist_conv = ConversationHandler(
        entry_points=[CommandHandler("blacklist", blacklist_start)],
        states={
            BLACKLIST_ID:    [MessageHandler(filters.TEXT & ~filters.COMMAND, blacklist_get_id)],
            BLACKLIST_RAISON:[MessageHandler(filters.TEXT & ~filters.COMMAND, blacklist_get_raison)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    sondage_conv = ConversationHandler(
        entry_points=[CommandHandler("sondage", sondage_start)],
        states={
            SONDAGE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, sondage_get_question)],
            SONDAGE_OPTIONS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, sondage_get_options)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("quiz", quiz_start)],
        states={
            QUIZ_QUESTION:    [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_get_question)],
            QUIZ_OPTIONS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_get_options)],
            QUIZ_CORRECT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_get_correct)],
            QUIZ_EXPLICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_get_explication)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    calendrier_conv = ConversationHandler(
        entry_points=[CommandHandler("addcalendrier", addcalendrier_start)],
        states={
            CAL_TITRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cal_get_titre)],
            CAL_JOUR:  [CallbackQueryHandler(cal_get_jour, pattern=r"^calj_")],
            CAL_HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cal_get_heure)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
        per_message=False,
    )

    comparer_conv = ConversationHandler(
        entry_points=[CommandHandler("comparer", comparer_cmd)],
        states={
            COMPARE_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_a_input)],
            COMPARE_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_b_input)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    filtre_conv = ConversationHandler(
        entry_points=[CommandHandler("filtre", filtre_cmd)],
        states={
            FILTER_CAT:    [CallbackQueryHandler(filtre_cat_cb, pattern=r"^cat_")],
            FILTER_STATUT: [CallbackQueryHandler(filtre_statut_cb, pattern=r"^fstatut_")],
            FILTER_NOTE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_note_input)],
            FILTER_SORT:   [CallbackQueryHandler(filtre_sort_cb, pattern=r"^fsort_")],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
        per_message=False,
    )

    # ── Handlers ──────────────────────────────────────────

    app.add_handler(poster_conv)
    app.add_handler(modifier_conv)
    app.add_handler(recherche_conv)
    app.add_handler(addadmin_conv)
    app.add_handler(removeadmin_conv)
    app.add_handler(blacklist_conv)
    app.add_handler(sondage_conv)
    app.add_handler(quiz_conv)
    app.add_handler(calendrier_conv)
    app.add_handler(comparer_conv)
    app.add_handler(filtre_conv)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("quoideneuf", whats_new_cmd))
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

    app.add_handler(CallbackQueryHandler(callback_handler))

    # ── Scheduler jobs ────────────────────────────────────

    jq = app.job_queue
    jq.run_repeating(scheduler_posts, interval=SCHEDULER_INTERVAL, first=10)
    jq.run_repeating(scheduler_episodes, interval=EPISODE_CHECK_INTERVAL, first=60)
    jq.run_repeating(scheduler_backup, interval=BACKUP_INTERVAL, first=BACKUP_INTERVAL)

    logger.info(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré !")
    print(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré ! Ctrl+C pour arrêter.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
