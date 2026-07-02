# ============================================================
# bot.py — Fichier principal AnimeFR Bot v3
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
    MAINTENANCE_MODE, MAINTENANCE_MESSAGE, VISUAL_THEME as VT
)
from formatter import (
    format_anime_post, format_anime_short, build_anime_keyboard,
    build_confirm_delete_keyboard, build_search_result_keyboard,
    build_categorie_keyboard, build_statut_keyboard, build_template_keyboard,
    format_notification_episode, format_log_entry, format_post_programme,
    format_stats_dashboard, format_backup_info, format_whats_new,
    make_star_bar
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

logger = logging.getLogger("AnimeFR")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(
    LOG_PATH, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ── États ConversationHandler ────────────────────────────────
(
    TITRE, TITRE_ORIGINAL, SYNOPSIS, PERSONNAGES, STUDIO,
    DATE_SORTIE, NB_EPISODES, STATUT_CHOICE, GENRES, NOTE,
    AVIS, IMAGE_URL, LIEN_EXTERNE, CATEGORIE_CHOICE, TAGS_INPUT,
    TEMPLATE_CHOICE, CONFIRM_POST,
    PROGRAMME_DATE, PROGRAMME_HEURE,
    SEARCH_QUERY,
    EDIT_FIELD, EDIT_VALUE,
    ADD_ADMIN_ID, ADD_ADMIN_ROLE,
    REMOVE_ADMIN_ID,
    BLACKLIST_ID, BLACKLIST_RAISON,
    SUIVI_QUERY,
) = range(28)


# ════════════════════════════════════════════════════════════
# MIDDLEWARE : MAINTENANCE & BLACKLIST
# ════════════════════════════════════════════════════════════

def check_maintenance(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        maintenance = db.get_setting("maintenance", "0")
        if maintenance == "1":
            uid = update.effective_user.id
            if not db.has_permission(uid, "maintenance"):
                msg = db.get_setting("maintenance_msg", MAINTENANCE_MESSAGE)
                await update.message.reply_text(msg)
                return ConversationHandler.END if hasattr(func, '__wrapped__') else None
        return await func(update, context)
    return wrapper


def check_blacklist(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if db.is_blacklisted(uid):
            await update.message.reply_text("🚫 Vous êtes blacklisté.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


def require_perm(permission: str):
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            uid = update.effective_user.id
            if not db.has_permission(uid, permission):
                await update.message.reply_text(
                    f"⛔ Permission <b>{permission}</b> requise.", parse_mode=ParseMode.HTML
                )
                return ConversationHandler.END
            db.increment_daily_stat("commands")
            return await func(update, context)
        return wrapper
    return decorator


# ════════════════════════════════════════════════════════════
# /start, /help, /quoideneuf
# ════════════════════════════════════════════════════════════

@check_maintenance
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    role = db.get_role(user.id) or "visiteur"
    is_adm = db.is_admin(user.id)

    text = (
        f"╔{'═' * 30}╗\n"
        f"║  👋 Salut <b>{user.first_name}</b> !\n"
        f"║  🎌 <b>AnimeFR Bot v{BOT_VERSION}</b>\n"
        f"║  📡 @animeFR2026\n"
        f"║  👤 Rôle : <b>{role.upper()}</b>\n"
        f"╠{'═' * 30}╣\n"
    )

    if is_adm:
        text += (
            f"║\n"
            f"║  📝 <b>Publication</b>\n"
            f"║  /poster — Publier un anime\n"
            f"║  /modifier &lt;id&gt; — Modifier\n"
            f"║  /supprimer &lt;id&gt; — Supprimer\n"
            f"║  /programmes — Posts programmés\n"
            f"║\n"
            f"║  🔍 <b>Recherche</b>\n"
            f"║  /recherche &lt;titre&gt; — Chercher\n"
            f"║  /anime &lt;id&gt; — Fiche anime\n"
            f"║  /top — Top 10 MAL\n"
            f"║  /saison — Anime saison\n"
            f"║  /upcoming — À venir\n"
            f"║\n"
            f"║  📂 <b>Organisation</b>\n"
            f"║  /categories — Catégories\n"
            f"║  /liste — Anime publiés\n"
            f"║  /toplikes — Top likés\n"
            f"║  /topvues — Top vus\n"
            f"║\n"
            f"║  🔔 <b>Notifications</b>\n"
            f"║  /suivre — Suivre un anime\n"
            f"║  /suivis — Anime suivis\n"
            f"║  /arretersuivi &lt;mal_id&gt;\n"
            f"║\n"
            f"║  📊 <b>Stats &amp; Logs</b>\n"
            f"║  /stats — Dashboard\n"
            f"║  /logs — Derniers logs\n"
            f"║  /logsuser &lt;id&gt; — Logs user\n"
            f"║\n"
            f"║  👥 <b>Administration</b>\n"
            f"║  /admins — Liste admins\n"
            f"║  /addadmin — Ajouter admin\n"
            f"║  /removeadmin — Retirer admin\n"
            f"║  /blacklist — Blacklister\n"
            f"║  /unblacklist &lt;id&gt;\n"
            f"║  /voirblacklist\n"
            f"║\n"
            f"║  🔧 <b>Technique</b>\n"
            f"║  /backup — Backup BDD\n"
            f"║  /backups — Historique backups\n"
            f"║  /restore &lt;fichier&gt;\n"
            f"║  /maintenance — Mode maintenance\n"
            f"║  /templates — Templates dispo\n"
            f"║  /cleanlogs — Nettoyer logs\n"
            f"║\n"
            f"║  🆕 /quoideneuf — Nouveautés v3\n"
        )
    else:
        text += (
            f"║\n"
            f"║  /recherche &lt;titre&gt; — Chercher\n"
            f"║  /top — Top anime\n"
            f"║  /saison — Anime saison\n"
            f"║  /categories — Catégories\n"
            f"║  /quoideneuf — Nouveautés v3\n"
        )

    text += f"║\n╚{'═' * 30}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def quoideneuf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_whats_new(), parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# POSTER UN ANIME (formulaire 16 étapes avec template + tags)
# ════════════════════════════════════════════════════════════

@check_blacklist
@require_perm("poster")
async def poster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"╔{'═' * 28}╗\n"
        f"║  📝 <b>Nouveau post — v3</b>\n"
        f"╠{'═' * 28}╣\n"
        f"║  Étape 1/16\n"
        f"║  <b>Titre français</b> de l'anime :\n"
        f"║  (ou /annuler)\n"
        f"╚{'═' * 28}╝",
        parse_mode=ParseMode.HTML
    )
    return TITRE


async def get_titre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["titre"] = update.message.text.strip()
    await update.message.reply_text(
        "Étape 2/16 — <b>Titre original</b> (japonais/romaji) :\n(/passer)",
        parse_mode=ParseMode.HTML
    )
    return TITRE_ORIGINAL


async def get_titre_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["titre_original"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 3/16 — <b>Synopsis complet</b> :", parse_mode=ParseMode.HTML
    )
    return SYNOPSIS


async def get_synopsis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["synopsis"] = update.message.text.strip()
    await update.message.reply_text(
        "Étape 4/16 — <b>Personnages principaux</b>\n(/passer)", parse_mode=ParseMode.HTML
    )
    return PERSONNAGES


async def get_personnages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["personnages"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 5/16 — <b>Studio</b> :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return STUDIO


async def get_studio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["studio"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 6/16 — <b>Date de sortie</b> :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return DATE_SORTIE


async def get_date_sortie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["date_sortie"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 7/16 — <b>Nombre d'épisodes</b> :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return NB_EPISODES


async def get_nb_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["nb_episodes"] = "?" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 8/16 — <b>Statut</b> :",
        parse_mode=ParseMode.HTML, reply_markup=build_statut_keyboard()
    )
    return STATUT_CHOICE


async def get_statut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    statut = q.data.replace("statut_", "")
    context.user_data["statut"] = statut
    await q.edit_message_text(
        f"✅ Statut : <b>{statut}</b>\n\n"
        "Étape 9/16 — <b>Genres</b> :\n(ex : Action, Fantasy, Isekai)\n(/passer)",
        parse_mode=ParseMode.HTML
    )
    return GENRES


async def get_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["genres"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 10/16 — <b>Note</b> (sur 10) :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return NOTE


async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["note"] = "N/A" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 11/16 — <b>Avis personnel</b> :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return AVIS


async def get_avis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["avis"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 12/16 — <b>URL de l'image</b> de couverture :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return IMAGE_URL


async def get_image_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["image_url"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 13/16 — <b>Lien externe</b> (MAL, site...) :\n(/passer)", parse_mode=ParseMode.HTML
    )
    return LIEN_EXTERNE


async def get_lien_externe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["lien_externe"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 14/16 — <b>Catégorie</b> :",
        parse_mode=ParseMode.HTML, reply_markup=build_categorie_keyboard(CATEGORIES)
    )
    return CATEGORIE_CHOICE


async def get_categorie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat = q.data.replace("cat_", "")
    context.user_data["categorie"] = cat
    await q.edit_message_text(
        f"✅ Catégorie : <b>{cat}</b>\n\n"
        "Étape 15/16 — <b>Tags</b> (séparés par des virgules) :\n"
        "(ex : OP, Saison2, Recommandé)\n(/passer)",
        parse_mode=ParseMode.HTML
    )
    return TAGS_INPUT


async def get_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    context.user_data["tags"] = "" if t.lower() == "/passer" else t
    await update.message.reply_text(
        "Étape 16/16 — <b>Template visuel</b> :",
        parse_mode=ParseMode.HTML, reply_markup=build_template_keyboard()
    )
    return TEMPLATE_CHOICE


async def get_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tpl = q.data.replace("tpl_", "")
    context.user_data["template"] = tpl
    context.user_data.setdefault("mal_id", 0)
    context.user_data.setdefault("likes", 0)
    context.user_data.setdefault("dislikes", 0)
    context.user_data.setdefault("views", 0)

    preview = format_anime_post(context.user_data, tpl)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Publier", callback_data="pub_now"),
            InlineKeyboardButton("⏰ Programmer", callback_data="pub_later"),
        ],
        [InlineKeyboardButton("❌ Annuler", callback_data="pub_cancel")]
    ])

    text = f"📋 <b>APERÇU ({tpl.upper()}) :</b>\n\n{preview}"
    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>... (tronqué)</i>"

    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    return CONFIRM_POST


async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data

    if action == "pub_cancel":
        await q.edit_message_text("❌ Publication annulée.")
        context.user_data.clear()
        return ConversationHandler.END

    if action == "pub_now":
        await q.edit_message_text("⏳ Publication en cours...")
        await publish_anime(context, q.from_user, context.user_data.copy())
        context.user_data.clear()
        return ConversationHandler.END

    if action == "pub_later":
        await q.edit_message_text(
            "📅 <b>Programmation</b>\n\n"
            "Entrez la <b>date</b> : <b>AAAA-MM-JJ</b>\n"
            "(ou <b>aujourd'hui</b> / <b>demain</b>)",
            parse_mode=ParseMode.HTML
        )
        return PROGRAMME_DATE

    return ConversationHandler.END


async def get_programme_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip().lower()
    today = datetime.now()

    if t in ("aujourd'hui", "aujourdhui"):
        date_str = today.strftime("%Y-%m-%d")
    elif t == "demain":
        date_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(t, "%Y-%m-%d")
            date_str = t
        except ValueError:
            await update.message.reply_text("❌ Format invalide. Utilisez AAAA-MM-JJ.")
            return PROGRAMME_DATE

    context.user_data["_sched_date"] = date_str
    await update.message.reply_text(
        f"📅 Date : <b>{date_str}</b>\n⏰ Entrez l'<b>heure</b> : <b>HH:MM</b>",
        parse_mode=ParseMode.HTML
    )
    return PROGRAMME_HEURE


async def get_programme_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilisez HH:MM.")
        return PROGRAMME_HEURE

    date_str = context.user_data.pop("_sched_date", datetime.now().strftime("%Y-%m-%d"))
    scheduled_at = f"{date_str} {t}"

    if datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M") < datetime.now():
        await update.message.reply_text("⚠️ Date/heure passée. Entrez une heure future.")
        context.user_data["_sched_date"] = date_str
        return PROGRAMME_HEURE

    data = context.user_data.copy()
    data.pop("_sched_date", None)

    post_id = db.save_post_programme(data, scheduled_at, update.effective_user.id)
    db.add_log(
        update.effective_user.id, update.effective_user.username or "",
        "POST_PROGRAMME", f"#{post_id} — '{data.get('titre')}' → {scheduled_at}"
    )

    await update.message.reply_text(
        f"✅ <b>Post programmé !</b>\n\n"
        f"🆔 <code>{post_id}</code>\n"
        f"🎌 <b>{data.get('titre')}</b>\n"
        f"📅 {scheduled_at}\n\n"
        f"Voir : /programmes",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return ConversationHandler.END


# ── Publication effective ────────────────────────────────────

async def publish_anime(context: ContextTypes.DEFAULT_TYPE, user, data: dict, from_scheduler=False):
    data.setdefault("posted_by", user.id if user else 0)
    data.setdefault("message_id", None)
    data.setdefault("chat_id", CHANNEL_ID)
    data.setdefault("mal_id", 0)
    data.setdefault("likes", 0)
    data.setdefault("dislikes", 0)
    data.setdefault("views", 0)
    data.setdefault("tags", "")
    data.setdefault("template", "standard")

    template = data.get("template", "standard")
    text = format_anime_post(data, template)
    keyboard = build_anime_keyboard(0, data.get("lien_externe"), 0, 0)

    try:
        image_url = data.get("image_url", "")
        if image_url and image_url.startswith("http"):
            caption = text if len(text) <= 1024 else text[:1020] + "..."
            msg = await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=image_url,
                caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard
            )
        else:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID, text=text,
                parse_mode=ParseMode.HTML, reply_markup=keyboard
            )

        data["message_id"] = msg.message_id
        data["chat_id"] = str(CHANNEL_ID)
        anime_id = db.save_anime(data)
        db.update_message_id(anime_id, msg.message_id, CHANNEL_ID)

        new_kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0)
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=CHANNEL_ID, message_id=msg.message_id, reply_markup=new_kb
            )
        except Exception:
            pass

        who = f"@{user.username}" if user and user.username else str(user.id if user else "BOT")
        db.add_log(
            user.id if user else 0, who,
            "POST_AUTO" if from_scheduler else "POST_PUBLIE",
            f"Anime #{anime_id} — {data.get('titre')} [tpl:{template}]"
        )
        logger.info(f"Publié : {data.get('titre')} (ID {anime_id}, tpl:{template})")
        return anime_id

    except Exception as e:
        logger.error(f"Erreur publication : {e}")
        db.add_log(0, "BOT", "ERREUR_PUB", str(e), level="ERROR")
        db.increment_daily_stat("errors")
        return None


async def annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Action annulée.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════
# RECHERCHE
# ════════════════════════════════════════════════════════════

@check_maintenance
async def recherche_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = " ".join(context.args)
        await _do_search(update, context, query)
        return ConversationHandler.END
    else:
        await update.message.reply_text("🔍 Entrez le titre :")
        return SEARCH_QUERY


async def search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_search(update, context, update.message.text.strip())
    return ConversationHandler.END


async def _do_search(update, context, query):
    msg = await update.message.reply_text(f"🔍 Recherche de <b>{query}</b>...", parse_mode=ParseMode.HTML)
    results = await search_anime(query, limit=MAX_SEARCH_RESULTS)
    if not results:
        await msg.edit_text("❌ Aucun résultat.")
        return
    context.user_data["search_results"] = results
    kb = build_search_result_keyboard(results)
    await msg.edit_text(
        f"🔍 <b>Résultats : « {query} »</b>\n\nSélectionnez :",
        parse_mode=ParseMode.HTML, reply_markup=kb
    )


async def select_jikan_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    mal_id = int(q.data.replace("select_jikan_", ""))
    await q.edit_message_text("⏳ Chargement...")

    data = await get_anime_by_id(mal_id)
    if not data:
        await q.edit_message_text("❌ Erreur.")
        return

    parsed = parse_jikan_anime(data)
    text = format_anime_post(parsed, "standard")
    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>... (tronqué)</i>"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Poster (Standard)", callback_data=f"postj_standard_{mal_id}"),
            InlineKeyboardButton("💎 Poster (Premium)", callback_data=f"postj_premium_{mal_id}"),
        ],
        [
            InlineKeyboardButton("📦 Poster (Compact)", callback_data=f"postj_compact_{mal_id}"),
            InlineKeyboardButton("✨ Poster (Minimal)", callback_data=f"postj_minimal_{mal_id}"),
        ],
        [InlineKeyboardButton("❌ Fermer", callback_data="cancel_search")],
    ])
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def post_jikan_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if not db.has_permission(uid, "poster"):
        await q.edit_message_text("⛔ Permission refusée.")
        return

    parts = q.data.replace("postj_", "").split("_", 1)
    template = parts[0]
    mal_id = int(parts[1])

    await q.edit_message_text("⏳ Publication...")

    data = await get_anime_by_id(mal_id)
    if not data:
        await q.edit_message_text("❌ Erreur.")
        return

    await asyncio.sleep(0.5)
    chars = await get_anime_characters(mal_id)
    parsed = parse_jikan_anime(data)
    parsed["template"] = template

    if chars:
        perso_list = []
        for c in chars[:6]:
            ch = c.get("character", {})
            role = c.get("role", "")
            perso_list.append(f"• {ch.get('name', '')} ({role})")
        parsed["personnages"] = "\n".join(perso_list)

    parsed["posted_by"] = uid
    anime_id = await publish_anime(context, q.from_user, parsed)

    if anime_id:
        await q.edit_message_text(
            f"✅ <b>{parsed.get('titre')}</b> publié ! (Template: {template})\n"
            f"🆔 <code>{anime_id}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await q.edit_message_text("❌ Erreur publication.")


# ════════════════════════════════════════════════════════════
# /anime, /top, /saison, /upcoming
# ════════════════════════════════════════════════════════════

async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /anime &lt;id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        anime_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text(f"❌ Anime #{anime_id} introuvable.")
        return
    db.add_view(anime_id)
    tpl = anime.get("template", "standard")
    text = format_anime_post(anime, tpl)
    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>... (tronqué)</i>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Chargement...")
    results = await get_top_anime(10)
    if not results:
        await msg.edit_text("❌ Erreur.")
        return
    text = f"╔{'═' * 28}╗\n║  🏆 <b>TOP 10 ANIME (MAL)</b>\n╠{'═' * 28}╣\n"
    for i, a in enumerate(results, 1):
        score = a.get("score", "?")
        stars = make_star_bar(str(score) if score else "0")
        text += f"║  <b>{i}.</b> {a.get('title', '?')}\n║     {stars} {score}\n"
    text += f"╚{'═' * 28}╝"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def saison_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Chargement...")
    results = await get_current_season_anime(10)
    if not results:
        await msg.edit_text("❌ Erreur.")
        return
    text = f"╔{'═' * 28}╗\n║  🌸 <b>ANIME DE LA SAISON</b>\n╠{'═' * 28}╣\n"
    for a in results:
        score = a.get("score", "?")
        text += f"║  🎌 <b>{a.get('title', '?')}</b> — ⭐ {score}\n"
    text += f"╚{'═' * 28}╝"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def upcoming_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Chargement...")
    results = await get_upcoming_anime(10)
    if not results:
        await msg.edit_text("❌ Erreur.")
        return
    text = f"╔{'═' * 28}╗\n║  🔜 <b>ANIME À VENIR</b>\n╠{'═' * 28}╣\n"
    for a in results:
        aired = a.get("aired", {})
        date = aired.get("string", "?") if aired else "?"
        text += f"║  🎌 <b>{a.get('title', '?')}</b>\n║     📅 {date}\n"
    text += f"╚{'═' * 28}╝"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# CATÉGORIES, LISTE, CLASSEMENTS
# ════════════════════════════════════════════════════════════

async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 <b>Catégories :</b>", parse_mode=ParseMode.HTML,
        reply_markup=build_categorie_keyboard(CATEGORIES)
    )

async def list_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat = q.data.replace("list_cat_", "")
    animes = db.get_animes_by_categorie(cat)
    if not animes:
        await q.edit_message_text(f"📂 Aucun anime dans <b>{cat}</b>.", parse_mode=ParseMode.HTML)
        return
    text = f"📂 <b>{cat}</b>\n\n"
    for a in animes[:MAX_LIST_ITEMS]:
        text += format_anime_short(a) + "\n\n"
    await q.edit_message_text(text, parse_mode=ParseMode.HTML)

async def liste_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_all_animes()
    if not animes:
        await update.message.reply_text("📋 Aucun anime publié.")
        return
    text = f"📋 <b>Anime publiés ({len(animes)})</b>\n\n"
    for a in animes[:MAX_LIST_ITEMS]:
        text += f"🆔 <code>{a['id']}</code> — <b>{a['titre']}</b> ({a.get('statut', '?')}) ❤️{a.get('likes', 0)} 👁️{a.get('views', 0)}\n"
    if len(animes) > MAX_LIST_ITEMS:
        text += f"\n... et {len(animes) - MAX_LIST_ITEMS} autres."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def toplikes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_top_liked(10)
    if not animes:
        await update.message.reply_text("❤️ Aucun anime liké.")
        return
    text = f"╔{'═' * 28}╗\n║  ❤️ <b>TOP LIKÉS</b>\n╠{'═' * 28}╣\n"
    for i, a in enumerate(animes, 1):
        text += f"║  <b>{i}.</b> {a['titre']} — ❤️ {a.get('likes', 0)}\n"
    text += f"╚{'═' * 28}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def topvues_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animes = db.get_top_viewed(10)
    if not animes:
        await update.message.reply_text("👁️ Aucune vue.")
        return
    text = f"╔{'═' * 28}╗\n║  👁️ <b>TOP VUS</b>\n╠{'═' * 28}╣\n"
    for i, a in enumerate(animes, 1):
        text += f"║  <b>{i}.</b> {a['titre']} — 👁️ {a.get('views', 0)}\n"
    text += f"╚{'═' * 28}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# MODIFIER UN POST
# ════════════════════════════════════════════════════════════

@require_perm("modifier")
async def modifier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /modifier &lt;id&gt;", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    try:
        anime_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return ConversationHandler.END
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text(f"❌ Anime #{anime_id} introuvable.")
        return ConversationHandler.END

    context.user_data["edit_anime_id"] = anime_id
    fields = [
        ("titre", "Titre"), ("synopsis", "Synopsis"), ("personnages", "Personnages"),
        ("studio", "Studio"), ("date_sortie", "Date sortie"), ("nb_episodes", "Nb épisodes"),
        ("statut", "Statut"), ("genres", "Genres"), ("note", "Note"), ("avis", "Avis"),
        ("image_url", "Image URL"), ("lien_externe", "Lien externe"),
        ("categorie", "Catégorie"), ("tags", "Tags"), ("template", "Template"),
    ]
    buttons = [[InlineKeyboardButton(label, callback_data=f"edit_{key}")] for key, label in fields]
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="edit_cancel")])

    await update.message.reply_text(
        f"✏️ <b>Modifier : {anime['titre']}</b>\n\nQuel champ ?",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons)
    )
    return EDIT_FIELD

async def edit_field_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "edit_cancel":
        await q.edit_message_text("❌ Annulé.")
        return ConversationHandler.END
    field = q.data.replace("edit_", "")
    context.user_data["edit_field"] = field
    await q.edit_message_text(f"✏️ Nouvelle valeur pour <b>{field}</b> :", parse_mode=ParseMode.HTML)
    return EDIT_VALUE

async def edit_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_val = update.message.text.strip()
    anime_id = context.user_data.get("edit_anime_id")
    field = context.user_data.get("edit_field")
    user = update.effective_user

    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text("❌ Introuvable.")
        return ConversationHandler.END

    anime[field] = new_val
    db.update_anime(anime_id, anime, user.id)
    db.add_log(user.id, user.username or "", "MODIFICATION", f"#{anime_id} — '{field}'")

    if anime.get("message_id"):
        try:
            tpl = anime.get("template", "standard")
            new_text = format_anime_post(anime, tpl)
            new_kb = build_anime_keyboard(anime_id, anime.get("lien_externe"), anime.get("likes", 0), anime.get("views", 0))
            if anime.get("image_url"):
                caption = new_text if len(new_text) <= 1024 else new_text[:1020] + "..."
                await context.bot.edit_message_caption(
                    chat_id=CHANNEL_ID, message_id=anime["message_id"],
                    caption=caption, parse_mode=ParseMode.HTML, reply_markup=new_kb
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=CHANNEL_ID, message_id=anime["message_id"],
                    text=new_text, parse_mode=ParseMode.HTML, reply_markup=new_kb
                )
        except Exception as e:
            logger.warning(f"Erreur edit canal : {e}")

    await update.message.reply_text(
        f"✅ <b>{field}</b> mis à jour !", parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════
# SUPPRIMER
# ════════════════════════════════════════════════════════════

@require_perm("supprimer")
async def supprimer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /supprimer &lt;id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        anime_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    anime = db.get_anime(anime_id)
    if not anime:
        await update.message.reply_text(f"❌ Introuvable.")
        return
    await update.message.reply_text(
        f"⚠️ Supprimer <b>{anime['titre']}</b> (ID: {anime_id}) ?",
        parse_mode=ParseMode.HTML, reply_markup=build_confirm_delete_keyboard(anime_id)
    )

async def confirm_delete_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("cancel_delete_"):
        await q.edit_message_text("✅ Annulé.")
        return
    anime_id = int(q.data.replace("confirm_delete_", ""))
    anime = db.get_anime(anime_id)
    if not anime:
        await q.edit_message_text("❌ Introuvable.")
        return
    if anime.get("message_id"):
        try:
            await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=anime["message_id"])
        except Exception as e:
            logger.warning(f"Erreur suppression canal : {e}")
    db.delete_anime(anime_id)
    db.add_log(q.from_user.id, q.from_user.username or "", "SUPPRESSION", f"#{anime_id} — {anime.get('titre')}")
    await q.edit_message_text(f"🗑️ <b>{anime.get('titre')}</b> supprimé.", parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# PROGRAMMES
# ════════════════════════════════════════════════════════════

@require_perm("programmer")
async def programmes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = db.get_all_posts_programmes()
    if not posts:
        await update.message.reply_text("📋 Aucun post programmé.")
        return
    text = f"╔{'═' * 28}╗\n║  📋 <b>POSTS PROGRAMMÉS</b>\n╠{'═' * 28}╣\n║\n"
    for p in posts:
        text += "║  " + format_post_programme(p).replace("\n", "\n║  ") + "\n║\n"
    text += f"╚{'═' * 28}╝"
    if len(text) > 4000:
        text = text[:4000] + "\n... (tronqué)"

    buttons = []
    pending = [p for p in posts if not p.get("publie")]
    for p in pending[:5]:
        buttons.append([InlineKeyboardButton(f"🗑️ #{p['id']}", callback_data=f"del_prog_{p['id']}")])
    kb = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def del_programme_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.replace("del_prog_", ""))
    db.delete_post_programme(post_id)
    db.add_log(q.from_user.id, q.from_user.username or "", "DEL_PROGRAMME", f"#{post_id}")
    await q.edit_message_text(f"🗑️ Post #{post_id} supprimé.")


# ════════════════════════════════════════════════════════════
# SUIVIS / NOTIFICATIONS
# ════════════════════════════════════════════════════════════

@require_perm("notif")
async def suivre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await _do_suivre(update, context, " ".join(context.args))
        return ConversationHandler.END
    else:
        await update.message.reply_text("🔔 Titre de l'anime à suivre :")
        return SUIVI_QUERY

async def suivi_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_suivre(update, context, update.message.text.strip())
    return ConversationHandler.END

async def _do_suivre(update, context, query):
    msg = await update.message.reply_text(f"🔍 Recherche de <b>{query}</b>...", parse_mode=ParseMode.HTML)
    results = await search_anime(query, limit=3)
    if not results:
        await msg.edit_text("❌ Aucun résultat.")
        return
    buttons = []
    for a in results:
        titre = a.get("title", "?")[:35]
        mal_id = a.get("mal_id", 0)
        buttons.append([InlineKeyboardButton(titre, callback_data=f"suivi_{mal_id}")])
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    await msg.edit_text("🔔 <b>Quel anime suivre ?</b>", parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(buttons))

async def suivi_select_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    mal_id = int(q.data.replace("suivi_", ""))
    data = await get_anime_by_id(mal_id)
    if not data:
        await q.edit_message_text("❌ Erreur.")
        return
    titre = data.get("title", "Inconnu")
    eps = data.get("episodes", 0) or 0
    db.add_suivi(mal_id, titre, eps, q.from_user.id)
    db.add_log(q.from_user.id, q.from_user.username or "", "SUIVI_AJOUT", f"MAL #{mal_id} — {titre}")
    await q.edit_message_text(f"🔔 <b>{titre}</b> suivi !", parse_mode=ParseMode.HTML)

async def suivis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    if not suivis:
        await update.message.reply_text("🔔 Aucun anime suivi.")
        return
    text = "🔔 <b>ANIME SUIVIS</b>\n\n"
    for s in suivis:
        text += f"🎌 <b>{s['titre']}</b> (MAL: {s['mal_id']}) — Ep: {s['dernier_ep']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def arretersuivi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /arretersuivi &lt;mal_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        mal_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    db.remove_suivi(mal_id)
    db.add_log(update.effective_user.id, update.effective_user.username or "", "SUIVI_STOP", f"MAL #{mal_id}")
    await update.message.reply_text(f"🔕 Suivi #{mal_id} arrêté.")


# ════════════════════════════════════════════════════════════
# STATS & LOGS AVANCÉS
# ════════════════════════════════════════════════════════════

@require_perm("stats")
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = db.get_stats()
    daily = db.get_daily_stats(7)
    text = format_stats_dashboard(s, daily)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@require_perm("logs")
async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level = None
    if context.args:
        level = context.args[0].upper()
    logs = db.get_logs(20, level=level)
    if not logs:
        await update.message.reply_text("📋 Aucun log.")
        return
    text = f"╔{'═' * 28}╗\n║  📋 <b>LOGS</b>"
    if level:
        text += f" ({level})"
    text += f"\n╠{'═' * 28}╣\n"
    for log in logs:
        text += "║  " + format_log_entry(log).replace("\n", "\n║  ") + "\n"
    text += f"╚{'═' * 28}╝"
    if len(text) > 4000:
        text = text[:4000] + "\n... (tronqué)"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@require_perm("logs")
async def logsuser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /logsuser &lt;user_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    logs = db.get_logs_by_user(uid, 20)
    if not logs:
        await update.message.reply_text(f"📋 Aucun log pour {uid}.")
        return
    text = f"📋 <b>Logs de {uid}</b>\n\n"
    for log in logs:
        text += format_log_entry(log) + "\n\n"
    if len(text) > 4000:
        text = text[:4000] + "\n... (tronqué)"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# ADMINISTRATION
# ════════════════════════════════════════════════════════════

async def admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Réservé aux admins.")
        return
    admins = db.get_all_admins()
    if not admins:
        await update.message.reply_text("👥 Aucun admin.")
        return
    text = f"╔{'═' * 28}╗\n║  👥 <b>ADMINS</b>\n╠{'═' * 28}╣\n"
    for a in admins:
        text += f"║  👤 @{a.get('username', '?')} — <code>{a['user_id']}</code> — <b>{a['role'].upper()}</b>\n"
    text += f"╚{'═' * 28}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@require_perm("admin")
async def addadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 <b>ID Telegram</b> du nouvel admin :", parse_mode=ParseMode.HTML)
    return ADD_ADMIN_ID

async def addadmin_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return ADD_ADMIN_ID
    context.user_data["new_admin_id"] = target_id
    buttons = [[InlineKeyboardButton(r.upper(), callback_data=f"role_{r}")] for r in ROLES]
    await update.message.reply_text("🎭 Rôle :", reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_ADMIN_ROLE

async def addadmin_get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    role = q.data.replace("role_", "")
    target_id = context.user_data.get("new_admin_id")
    db.add_admin(target_id, str(target_id), role, q.from_user.id)
    db.add_log(q.from_user.id, q.from_user.username or "", "ADD_ADMIN", f"{target_id} → {role}")
    await q.edit_message_text(f"✅ <code>{target_id}</code> → <b>{role.upper()}</b>", parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END

@require_perm("admin")
async def removeadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 <b>ID</b> de l'admin à retirer :", parse_mode=ParseMode.HTML)
    return REMOVE_ADMIN_ID

async def removeadmin_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return REMOVE_ADMIN_ID
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ Impossible de vous retirer.")
        return ConversationHandler.END
    db.remove_admin(target_id)
    db.add_log(update.effective_user.id, update.effective_user.username or "", "REMOVE_ADMIN", f"{target_id}")
    await update.message.reply_text(f"✅ <code>{target_id}</code> retiré.", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

@require_perm("blacklist")
async def blacklist_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 <b>ID</b> à blacklister :", parse_mode=ParseMode.HTML)
    return BLACKLIST_ID

async def blacklist_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return BLACKLIST_ID
    context.user_data["blacklist_id"] = target_id
    await update.message.reply_text("📝 Raison :")
    return BLACKLIST_RAISON

async def blacklist_get_raison(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raison = update.message.text.strip()
    target_id = context.user_data.get("blacklist_id")
    db.blacklist_user(target_id, str(target_id), raison, update.effective_user.id)
    db.add_log(update.effective_user.id, update.effective_user.username or "", "BLACKLIST", f"{target_id} — {raison}")
    await update.message.reply_text(f"✅ <code>{target_id}</code> blacklisté.", parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END

async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.has_permission(update.effective_user.id, "blacklist"):
        await update.message.reply_text("⛔ Permission refusée.")
        return
    if not context.args:
        await update.message.reply_text("Usage : /unblacklist &lt;id&gt;", parse_mode=ParseMode.HTML)
        return
    target_id = int(context.args[0])
    db.unblacklist_user(target_id)
    db.add_log(update.effective_user.id, update.effective_user.username or "", "UNBLACKLIST", f"{target_id}")
    await update.message.reply_text(f"✅ <code>{target_id}</code> retiré.", parse_mode=ParseMode.HTML)

async def voirblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.has_permission(update.effective_user.id, "blacklist"):
        await update.message.reply_text("⛔ Permission refusée.")
        return
    bl = db.get_blacklist()
    if not bl:
        await update.message.reply_text("✅ Blacklist vide.")
        return
    text = "🚫 <b>BLACKLIST</b>\n\n"
    for u in bl:
        text += f"👤 <code>{u['user_id']}</code> — {u.get('raison', '?')}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════
# TECHNIQUE : BACKUP, MAINTENANCE, TEMPLATES, CLEANLOGS
# ════════════════════════════════════════════════════════════

@require_perm("backup")
async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("💾 Création du backup...")
    filepath, size = db.create_backup()
    if filepath:
        db.add_log(update.effective_user.id, update.effective_user.username or "", "BACKUP", filepath)
        await msg.edit_text(format_backup_info(filepath, size), parse_mode=ParseMode.HTML)
    else:
        await msg.edit_text("❌ Erreur lors du backup.")

@require_perm("backup")
async def backups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = db.get_backup_history(10)
    if not history:
        await update.message.reply_text("💾 Aucun backup.")
        return
    text = f"╔{'═' * 28}╗\n║  💾 <b>HISTORIQUE BACKUPS</b>\n╠{'═' * 28}╣\n"
    for b in history:
        size_kb = (b.get("size_bytes", 0) or 0) / 1024
        status = "✅" if b.get("status") == "ok" else "❌"
        text += f"║  {status} {b.get('created_at', '?')[:16]} — {size_kb:.1f} Ko\n"
    text += f"╚{'═' * 28}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@require_perm("backup")
async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : /restore &lt;fichier&gt;", parse_mode=ParseMode.HTML)
        return
    filepath = context.args[0]
    success = db.restore_backup(filepath)
    if success:
        db.add_log(update.effective_user.id, update.effective_user.username or "", "RESTORE", filepath)
        await update.message.reply_text(f"✅ Backup restauré depuis <code>{filepath}</code>.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ Fichier introuvable ou erreur.")

@require_perm("maintenance")
async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = db.get_setting("maintenance", "0")
    if current == "1":
        db.set_setting("maintenance", "0")
        db.add_log(update.effective_user.id, update.effective_user.username or "", "MAINTENANCE_OFF", "")
        await update.message.reply_text("✅ Mode maintenance <b>DÉSACTIVÉ</b>.", parse_mode=ParseMode.HTML)
    else:
        db.set_setting("maintenance", "1")
        db.add_log(update.effective_user.id, update.effective_user.username or "", "MAINTENANCE_ON", "")
        await update.message.reply_text(
            "🔧 Mode maintenance <b>ACTIVÉ</b>.\n"
            "Seuls les superadmins peuvent utiliser le bot.",
            parse_mode=ParseMode.HTML
        )

@require_perm("templates")
async def templates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    templates = db.get_all_templates()
    if not templates:
        await update.message.reply_text("📋 Aucun template.")
        return
    text = f"╔{'═' * 28}╗\n║  📋 <b>TEMPLATES</b>\n╠{'═' * 28}╣\n"
    for t in templates:
        default = " ⭐" if t.get("is_default") else ""
        text += f"║  📄 <b>{t['name']}</b>{default}\n║     {t.get('description', '')}\n"
    text += f"╚{'═' * 28}╝"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@require_perm("logs")
async def cleanlogs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass
    db.clear_old_logs(days)
    db.add_log(update.effective_user.id, update.effective_user.username or "", "CLEAN_LOGS", f">{days} jours")
    await update.message.reply_text(f"✅ Logs de plus de {days} jours supprimés.")


# ════════════════════════════════════════════════════════════
# CALLBACKS BOUTONS INTERACTIFS
# ════════════════════════════════════════════════════════════

async def like_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    anime_id = int(q.data.replace("like_", ""))
    is_new = db.add_vote(anime_id, q.from_user.id, "like")
    if is_new:
        db.add_like(anime_id)
        anime = db.get_anime(anime_id)
        if anime:
            new_kb = build_anime_keyboard(anime_id, anime.get("lien_externe"), anime.get("likes", 0), anime.get("views", 0))
            try:
                await q.edit_message_reply_markup(reply_markup=new_kb)
            except Exception:
                pass
        await q.answer(f"❤️ Merci !", show_alert=False)
    else:
        await q.answer("Déjà liké !", show_alert=True)

async def dislike_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    anime_id = int(q.data.replace("dislike_", ""))
    is_new = db.add_vote(anime_id, q.from_user.id, "dislike")
    if is_new:
        db.add_dislike(anime_id)
        await q.answer("👎 Noté.", show_alert=False)
    else:
        await q.answer("Déjà voté !", show_alert=True)

async def view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    anime_id = int(q.data.replace("view_", ""))
    db.add_view(anime_id)
    anime = db.get_anime(anime_id)
    if anime:
        new_kb = build_anime_keyboard(anime_id, anime.get("lien_externe"), anime.get("likes", 0), anime.get("views", 0))
        try:
            await q.edit_message_reply_markup(reply_markup=new_kb)
        except Exception:
            pass
    await q.answer(f"👁️ {anime.get('views', 0)} vues", show_alert=False)

async def info_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    anime_id = int(q.data.replace("info_", ""))
    anime = db.get_anime(anime_id)
    if not anime:
        await q.answer("❌ Introuvable.", show_alert=True)
        return
    stars = make_star_bar(str(anime.get("note", "0")))
    await q.answer(
        f"📊 {anime.get('titre')}\n"
        f"{stars} {anime.get('note', 'N/A')}/10\n"
        f"❤️ {anime.get('likes', 0)} │ 👁️ {anime.get('views', 0)}\n"
        f"📺 {anime.get('nb_episodes', '?')} eps",
        show_alert=True
    )

async def similar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    anime_id = int(q.data.replace("similar_", ""))
    anime = db.get_anime(anime_id)
    if not anime:
        await q.answer("❌ Introuvable.", show_alert=True)
        return
    genres = anime.get("genres", "")
    all_animes = db.get_all_animes()
    similar = []
    for a in all_animes:
        if a["id"] == anime_id:
            continue
        for g in genres.split(","):
            g = g.strip()
            if g and g in a.get("genres", ""):
                similar.append(a)
                break
    if not similar:
        await q.answer("Aucun similaire.", show_alert=True)
        return
    text = f"🔍 <b>Similaires à {anime.get('titre')}</b>\n\n"
    for a in similar[:5]:
        text += f"🎌 <b>{a['titre']}</b> — {a.get('genres', '')}\n"
    try:
        await context.bot.send_message(chat_id=q.from_user.id, text=text, parse_mode=ParseMode.HTML)
        await q.answer("📩 Envoyé en privé !")
    except Exception:
        await q.answer("⚠️ /start en privé d'abord.", show_alert=True)

async def category_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    anime_id = int(q.data.replace("category_", ""))
    anime = db.get_anime(anime_id)
    if not anime:
        await q.answer("❌ Introuvable.", show_alert=True)
        return
    cat = anime.get("categorie", "")
    if not cat:
        await q.answer("Pas de catégorie.", show_alert=True)
        return
    animes = db.get_animes_by_categorie(cat)
    text = f"📂 <b>{cat}</b>\n\n"
    for a in animes[:8]:
        text += f"🎌 <b>{a['titre']}</b> — ⭐ {a.get('note', '?')}\n"
    try:
        await context.bot.send_message(chat_id=q.from_user.id, text=text, parse_mode=ParseMode.HTML)
        await q.answer(f"📩 {cat} envoyé !")
    except Exception:
        await q.answer("⚠️ /start en privé d'abord.", show_alert=True)

async def cancel_search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ Annulé.")


# ════════════════════════════════════════════════════════════
# TÂCHES PLANIFIÉES
# ════════════════════════════════════════════════════════════

async def check_scheduled_posts(context: ContextTypes.DEFAULT_TYPE):
    posts = db.get_posts_programmes_dus()
    for post in posts:
        try:
            data = json.loads(post["data_json"])
            data.setdefault("likes", 0)
            data.setdefault("dislikes", 0)
            data.setdefault("views", 0)
            data.setdefault("mal_id", 0)
            data.setdefault("tags", "")
            data.setdefault("template", "standard")
            data.setdefault("message_id", None)
            data.setdefault("chat_id", CHANNEL_ID)
            data.setdefault("posted_by", post.get("created_by", 0))

            template = data.get("template", "standard")
            text = format_anime_post(data, template)
            kb = build_anime_keyboard(0, data.get("lien_externe"), 0, 0)
            image_url = data.get("image_url", "")

            if image_url and image_url.startswith("http"):
                caption = text if len(text) <= 1024 else text[:1020] + "..."
                msg = await context.bot.send_photo(
                    chat_id=CHANNEL_ID, photo=image_url,
                    caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=CHANNEL_ID, text=text,
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )

            data["message_id"] = msg.message_id
            data["chat_id"] = str(CHANNEL_ID)
            anime_id = db.save_anime(data)
            db.update_message_id(anime_id, msg.message_id, CHANNEL_ID)

            new_kb = build_anime_keyboard(anime_id, data.get("lien_externe"), 0, 0)
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID, message_id=msg.message_id, reply_markup=new_kb
                )
            except Exception:
                pass

            db.mark_post_publie(post["id"])
            db.add_log(0, "BOT", "POST_AUTO", f"#{post['id']} — {data.get('titre')}")
            logger.info(f"[Scheduler] #{post['id']} publié : {data.get('titre')}")

        except Exception as e:
            db.mark_post_publie(post["id"], erreur=str(e))
            db.add_log(0, "BOT", "ERREUR_SCHEDULER", str(e), level="ERROR")
            db.increment_daily_stat("errors")
            logger.error(f"[Scheduler] Erreur #{post['id']} : {e}")


async def check_new_episodes(context: ContextTypes.DEFAULT_TYPE):
    suivis = db.get_suivis_actifs()
    for s in suivis:
        try:
            await asyncio.sleep(1)
            data = await get_anime_by_id(s["mal_id"])
            if not data:
                continue
            current_eps = data.get("episodes") or 0
            if current_eps > s["dernier_ep"] and s["dernier_ep"] > 0:
                for ep in range(s["dernier_ep"] + 1, current_eps + 1):
                    notif = format_notification_episode(s["titre"], ep)
                    try:
                        await context.bot.send_message(
                            chat_id=CHANNEL_ID, text=notif, parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f"[Notif] Erreur : {e}")
                db.update_suivi_ep(s["mal_id"], current_eps)
                db.add_log(0, "BOT", "NOTIF_EPISODE", f"{s['titre']} — ep {current_eps}")
        except Exception as e:
            logger.error(f"[Notif] Erreur MAL #{s['mal_id']} : {e}")


async def auto_backup(context: ContextTypes.DEFAULT_TYPE):
    filepath, size = db.create_backup()
    if filepath:
        db.add_log(0, "BOT", "AUTO_BACKUP", f"{filepath} ({size} bytes)")
        logger.info(f"[Backup] Auto backup : {filepath}")
    else:
        db.add_log(0, "BOT", "BACKUP_FAIL", "", level="ERROR")
        logger.error("[Backup] Échec auto backup")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

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

    suivre_conv = ConversationHandler(
        entry_points=[CommandHandler("suivre", suivre_cmd)],
        states={
            SUIVI_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, suivi_input)],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
        allow_reentry=True,
    )

    # ── Enregistrement ────────────────────────────────────

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("quoideneuf", quoideneuf_cmd))

    app.add_handler(poster_conv)
    app.add_handler(modifier_conv)
    app.add_handler(recherche_conv)
    app.add_handler(addadmin_conv)
    app.add_handler(removeadmin_conv)
    app.add_handler(blacklist_conv)
    app.add_handler(suivre_conv)

    app.add_handler(CommandHandler("anime", anime_cmd))
    app.add_handler(CommandHandler("supprimer", supprimer_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("saison", saison_cmd))
    app.add_handler(CommandHandler("upcoming", upcoming_cmd))
    app.add_handler(CommandHandler("categories", categories_cmd))
    app.add_handler(CommandHandler("liste", liste_cmd))
    app.add_handler(CommandHandler("toplikes", toplikes_cmd))
    app.add_handler(CommandHandler("topvues", topvues_cmd))
    app.add_handler(CommandHandler("programmes", programmes_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("logsuser", logsuser_cmd))
    app.add_handler(CommandHandler("admins", admins_cmd))
    app.add_handler(CommandHandler("unblacklist", unblacklist_cmd))
    app.add_handler(CommandHandler("voirblacklist", voirblacklist_cmd))
    app.add_handler(CommandHandler("suivis", suivis_cmd))
    app.add_handler(CommandHandler("arretersuivi", arretersuivi_cmd))

    # Technique
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("backups", backups_cmd))
    app.add_handler(CommandHandler("restore", restore_cmd))
    app.add_handler(CommandHandler("maintenance", maintenance_cmd))
    app.add_handler(CommandHandler("templates", templates_cmd))
    app.add_handler(CommandHandler("cleanlogs", cleanlogs_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(confirm_delete_cb, pattern=r"^(confirm_delete_|cancel_delete_)"))
    app.add_handler(CallbackQueryHandler(select_jikan_result, pattern=r"^select_jikan_"))
    app.add_handler(CallbackQueryHandler(post_jikan_anime, pattern=r"^postj_"))
    app.add_handler(CallbackQueryHandler(cancel_search_cb, pattern=r"^cancel_search"))
    app.add_handler(CallbackQueryHandler(like_cb, pattern=r"^like_"))
    app.add_handler(CallbackQueryHandler(dislike_cb, pattern=r"^dislike_"))
    app.add_handler(CallbackQueryHandler(view_cb, pattern=r"^view_"))
    app.add_handler(CallbackQueryHandler(info_cb, pattern=r"^info_"))
    app.add_handler(CallbackQueryHandler(similar_cb, pattern=r"^similar_"))
    app.add_handler(CallbackQueryHandler(category_cb, pattern=r"^category_"))
    app.add_handler(CallbackQueryHandler(list_category_callback, pattern=r"^list_cat_"))
    app.add_handler(CallbackQueryHandler(del_programme_cb, pattern=r"^del_prog_"))
    app.add_handler(CallbackQueryHandler(suivi_select_cb, pattern=r"^suivi_"))

    # ── Jobs planifiés ────────────────────────────────────

    app.job_queue.run_repeating(check_scheduled_posts, interval=SCHEDULER_INTERVAL, first=5)
    app.job_queue.run_repeating(check_new_episodes, interval=1800, first=60)
    app.job_queue.run_repeating(auto_backup, interval=BACKUP_INTERVAL, first=300)

    # ── Démarrage ─────────────────────────────────────────

    logger.info(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré !")
    print(f"🚀 AnimeFR Bot v{BOT_VERSION} démarré ! Ctrl+C pour arrêter.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
