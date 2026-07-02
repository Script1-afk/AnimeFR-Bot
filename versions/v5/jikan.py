# ============================================================
# jikan.py — Intégration API Jikan (MyAnimeList) v5.0
# ============================================================

import asyncio
import aiohttp
from config import JIKAN_BASE_URL, JIKAN_RATE_LIMIT

_last_request = 0


async def _fetch(endpoint, params=None):
    global _last_request
    import time
    now = time.time()
    wait = JIKAN_RATE_LIMIT - (now - _last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = time.time()

    url = f"{JIKAN_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    await asyncio.sleep(2)
                    return await _fetch(endpoint, params)
                return None
    except Exception:
        return None


async def search_anime(query, limit=5):
    data = await _fetch("anime", {"q": query, "limit": limit, "sfw": "true"})
    return data.get("data", []) if data else []


async def get_anime_by_id(mal_id):
    data = await _fetch(f"anime/{mal_id}/full")
    return data.get("data") if data else None


async def get_anime_characters(mal_id, limit=5):
    data = await _fetch(f"anime/{mal_id}/characters")
    if not data:
        return []
    chars = data.get("data", [])[:limit]
    return [{"name": c["character"]["name"], "role": c["role"]} for c in chars]


async def get_current_season_anime(limit=10):
    data = await _fetch("seasons/now", {"limit": limit, "sfw": "true"})
    return data.get("data", []) if data else []


async def get_upcoming_anime(limit=10):
    data = await _fetch("seasons/upcoming", {"limit": limit, "sfw": "true"})
    return data.get("data", []) if data else []


async def get_top_anime(limit=10):
    data = await _fetch("top/anime", {"limit": limit, "sfw": "true"})
    return data.get("data", []) if data else []


async def get_anime_by_genre(genre_id, limit=10):
    data = await _fetch("anime", {"genres": str(genre_id), "limit": limit, "sfw": "true"})
    return data.get("data", []) if data else []


async def get_anime_news(mal_id, limit=3):
    data = await _fetch(f"anime/{mal_id}/news")
    return data.get("data", [])[:limit] if data else []


async def get_anime_episodes(mal_id):
    data = await _fetch(f"anime/{mal_id}/episodes")
    return data.get("data", []) if data else []


def parse_jikan_anime(data):
    if not data:
        return {}
    genres = ", ".join(g["name"] for g in data.get("genres", []))
    studios = ", ".join(s["name"] for s in data.get("studios", []))
    status_map = {"Finished Airing": "Terminé", "Currently Airing": "En cours",
                  "Not yet aired": "À venir"}
    statut = status_map.get(data.get("status", ""), data.get("status", "Inconnu"))
    image_url = ""
    images = data.get("images", {})
    if images.get("jpg"):
        image_url = images["jpg"].get("large_image_url") or images["jpg"].get("image_url", "")
    trailer_url = ""
    trailer = data.get("trailer", {})
    if trailer and trailer.get("url"):
        trailer_url = trailer["url"]
    tags = []
    for t in data.get("themes", []):
        tags.append(t["name"])
    for d in data.get("demographics", []):
        tags.append(d["name"])
    saison = ""
    if data.get("season") and data.get("year"):
        saison_map = {"winter": "Hiver", "spring": "Printemps", "summer": "Été", "fall": "Automne"}
        saison = f"{saison_map.get(data['season'], data['season'])} {data['year']}"

    return {
        "titre": data.get("title", ""),
        "titre_original": data.get("title_japanese", ""),
        "synopsis": data.get("synopsis", "Aucun synopsis disponible."),
        "studio": studios or "Inconnu",
        "date_sortie": data.get("aired", {}).get("string", "Inconnue"),
        "nb_episodes": str(data.get("episodes") or "?"),
        "statut": statut,
        "genres": genres,
        "note": str(data.get("score") or "N/A"),
        "image_url": image_url,
        "lien_externe": data.get("url", ""),
        "mal_id": data.get("mal_id", 0),
        "trailer_url": trailer_url,
        "tags": ", ".join(tags),
        "saison": saison,
    }
