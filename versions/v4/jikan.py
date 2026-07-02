# ============================================================
# jikan.py — Intégration API Jikan (MyAnimeList) v3
# ============================================================

import aiohttp
import asyncio
import logging
from config import JIKAN_BASE_URL

logger = logging.getLogger(__name__)
JIKAN_DELAY = 0.3


async def _get(url: str, params: dict = None) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params,
                timeout=aiohttp.ClientTimeout(total=12)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    logger.warning("[Jikan] Rate limit, attente 2s...")
                    await asyncio.sleep(2)
                    return {}
                else:
                    logger.warning(f"[Jikan] HTTP {resp.status} pour {url}")
                    return {}
    except asyncio.TimeoutError:
        logger.error(f"[Jikan] Timeout pour {url}")
        return {}
    except Exception as e:
        logger.error(f"[Jikan] Erreur : {e}")
        return {}


async def search_anime(query: str, limit: int = 5) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/anime", {"q": query, "limit": limit, "sfw": True})
    return data.get("data", [])


async def get_anime_by_id(mal_id: int) -> dict:
    data = await _get(f"{JIKAN_BASE_URL}/anime/{mal_id}/full")
    return data.get("data", {})


async def get_anime_characters(mal_id: int) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/anime/{mal_id}/characters")
    return data.get("data", [])


async def get_anime_episodes(mal_id: int) -> dict:
    return await _get(f"{JIKAN_BASE_URL}/anime/{mal_id}/episodes")


async def get_current_season_anime(limit: int = 10) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/seasons/now", {"limit": limit})
    return data.get("data", [])


async def get_upcoming_anime(limit: int = 10) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/seasons/upcoming", {"limit": limit})
    return data.get("data", [])


async def get_top_anime(limit: int = 10) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/top/anime", {"limit": limit})
    return data.get("data", [])


async def get_anime_by_genre(genre_id: int, limit: int = 10) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/anime", {
        "genres": genre_id, "limit": limit, "order_by": "score", "sort": "desc"
    })
    return data.get("data", [])


async def get_anime_news(mal_id: int) -> list:
    data = await _get(f"{JIKAN_BASE_URL}/anime/{mal_id}/news")
    return data.get("data", [])


def parse_jikan_anime(data: dict) -> dict:
    genres = ", ".join([g["name"] for g in data.get("genres", [])])
    studios = ", ".join([s["name"] for s in data.get("studios", [])])

    aired = data.get("aired", {})
    date_sortie = aired.get("string", "Inconnue") if aired else "Inconnue"

    statut_map = {
        "Finished Airing": "Terminé",
        "Currently Airing": "En cours",
        "Not yet aired": "À venir",
    }
    statut = statut_map.get(data.get("status", ""), data.get("status", "Inconnu"))

    nb_episodes = data.get("episodes")
    nb_episodes = str(nb_episodes) if nb_episodes else "?"

    note = data.get("score")
    note = str(note) if note else "N/A"

    image_url = ""
    images = data.get("images", {})
    if images.get("jpg"):
        image_url = images["jpg"].get("large_image_url", "")

    titre_en = data.get("title_english") or data.get("title", "Inconnu")
    titre_jp = data.get("title", "")

    # Extraire les thèmes comme tags
    themes = [t["name"] for t in data.get("themes", [])]
    demographics = [d["name"] for d in data.get("demographics", [])]
    tags = ", ".join(themes + demographics)

    # Trailer
    trailer_url = ""
    trailer = data.get("trailer", {})
    if trailer and trailer.get("url"):
        trailer_url = trailer["url"]

    # Saison
    saison = ""
    if data.get("season") and data.get("year"):
        season_map = {"winter": "Hiver", "spring": "Printemps", "summer": "\u00c9t\u00e9", "fall": "Automne"}
        saison = f"{season_map.get(data['season'], data['season'])} {data['year']}"

    return {
        "titre": titre_en,
        "titre_original": titre_jp,
        "synopsis": data.get("synopsis", ""),
        "personnages": "",
        "studio": studios,
        "date_sortie": date_sortie,
        "nb_episodes": nb_episodes,
        "statut": statut,
        "genres": genres,
        "note": note,
        "avis": "",
        "image_url": image_url,
        "lien_externe": data.get("url", ""),
        "categorie": "",
        "tags": tags,
        "mal_id": data.get("mal_id", 0),
        "message_id": None,
        "chat_id": None,
        "template": "standard",
        "posted_by": None,
        "likes": 0,
        "dislikes": 0,
        "views": 0,
        "trailer_url": trailer_url,
        "saison": saison,
    }
