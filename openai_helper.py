# ============================================================
# openai_helper.py — Intégration OpenAI pour AnimeFR Bot v6.0
# Génère automatiquement synopsis, avis, tags, descriptions
# ============================================================

import asyncio
import logging
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_anime_description(anime_data: dict) -> dict:
    """
    Génère automatiquement un synopsis FR, un avis, des tags et une description
    à partir des données brutes de l'anime (titre, genres, studio, etc.)
    """
    titre = anime_data.get("titre", "Inconnu")
    titre_jp = anime_data.get("titre_original", "")
    genres = anime_data.get("genres", "")
    studio = anime_data.get("studio", "")
    episodes = anime_data.get("nb_episodes", "?")
    statut = anime_data.get("statut", "")
    note_mal = anime_data.get("note", "")
    synopsis_en = anime_data.get("synopsis_en", "")

    prompt = f"""Tu es un expert en anime et un rédacteur passionné pour un canal Telegram francophone dédié aux anime.

Anime : {titre}
Titre japonais : {titre_jp}
Genres : {genres}
Studio : {studio}
Épisodes : {episodes}
Statut : {statut}
Note MAL : {note_mal}/10
Synopsis anglais : {synopsis_en}

Génère les éléments suivants en français, de manière engageante et passionnée :

1. **Synopsis** (150-250 mots) : Un résumé captivant de l'histoire, sans spoiler majeur. Donne envie de regarder.

2. **Personnages principaux** (3-5 personnages) : Nom + courte description (1 ligne chacun)

3. **Avis** (80-120 mots) : Un avis subjectif et enthousiaste, mentionne les points forts (animation, histoire, OST, personnages). Donne une ambiance.

4. **Tags** (5-8 tags) : Des mots-clés pertinents séparés par des virgules (ex: combat épique, voyage, amitié, dark fantasy)

5. **Accroche** (1 phrase) : Une phrase d'accroche courte et percutante pour donner envie.

Réponds UNIQUEMENT au format suivant (respecte exactement les balises) :
[SYNOPSIS]
(ton synopsis ici)
[PERSONNAGES]
(tes personnages ici)
[AVIS]
(ton avis ici)
[TAGS]
(tes tags ici)
[ACCROCHE]
(ton accroche ici)"""

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un rédacteur expert en anime pour un canal Telegram FR. Tu écris de manière passionnée, engageante et informative."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=OPENAI_MAX_TOKENS,
            temperature=0.8,
        )

        text = response.choices[0].message.content.strip()
        return _parse_ai_response(text)

    except Exception as e:
        logger.error(f"Erreur OpenAI: {e}")
        return {
            "synopsis": synopsis_en or "Synopsis non disponible.",
            "personnages": "Non disponible",
            "avis": "Avis non disponible.",
            "tags": genres,
            "accroche": f"Découvrez {titre} !",
            "error": str(e),
        }


async def generate_episode_notification(anime_titre: str, episode_num: int, synopsis_ep: str = "") -> str:
    """Génère un texte de notification pour un nouvel épisode."""
    prompt = f"""Écris une notification courte et excitante (2-3 lignes max) pour annoncer la sortie d'un nouvel épisode d'anime sur un canal Telegram FR.

Anime : {anime_titre}
Épisode : {episode_num}
{"Résumé épisode : " + synopsis_ep if synopsis_ep else ""}

La notification doit être engageante, avec 1-2 emojis max, et donner envie de regarder. Pas de spoiler."""

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu écris des notifications courtes et percutantes pour un canal anime Telegram."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur OpenAI notification: {e}")
        return f"🔥 {anime_titre} — Épisode {episode_num} est disponible ! Foncez le regarder !"


async def generate_weekly_recap(animes_list: list) -> str:
    """Génère un récap hebdomadaire des anime publiés."""
    titres = ", ".join([a.get("titre", "?") for a in animes_list[:10]])
    prompt = f"""Écris un récap hebdomadaire fun et engageant (5-8 lignes) pour un canal anime Telegram FR.
Anime publiés cette semaine : {titres}
Mets en avant les meilleurs, donne envie de les découvrir. Style décontracté avec quelques emojis."""

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es le community manager d'un canal anime Telegram FR."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur OpenAI recap: {e}")
        return f"📋 Récap de la semaine : {titres}"


async def suggest_similar_animes(anime_titre: str, genres: str) -> str:
    """Suggère des anime similaires via IA."""
    prompt = f"""Suggère 5 anime similaires à "{anime_titre}" (genres: {genres}).
Pour chaque anime, donne : Titre — 1 phrase de description.
Format simple, pas de numérotation complexe."""

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert anime qui fait des recommandations précises."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur OpenAI suggestions: {e}")
        return "Suggestions non disponibles pour le moment."


def _parse_ai_response(text: str) -> dict:
    """Parse la réponse structurée de l'IA."""
    result = {
        "synopsis": "",
        "personnages": "",
        "avis": "",
        "tags": "",
        "accroche": "",
    }

    sections = {
        "[SYNOPSIS]": "synopsis",
        "[PERSONNAGES]": "personnages",
        "[AVIS]": "avis",
        "[TAGS]": "tags",
        "[ACCROCHE]": "accroche",
    }

    current_key = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped in sections:
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = sections[stripped]
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    return result
