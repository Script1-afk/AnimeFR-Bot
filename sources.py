# ============================================================
# sources.py — Gestion des sources de visionnage v6.0
# Génère les liens vers Franime, Anime-Sama, VoirAnime
# ============================================================

import re
import logging
import aiohttp
import asyncio
from config import ANIME_SOURCES, DEFAULT_SOURCE

logger = logging.getLogger(__name__)


def slugify(title: str) -> str:
    """Convertit un titre en slug URL-friendly."""
    slug = title.lower().strip()
    # Remplacer les caractères spéciaux
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ýÿ]', 'y', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    # Garder uniquement lettres, chiffres, espaces
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Remplacer espaces par des tirets
    slug = re.sub(r'[\s]+', '-', slug)
    # Supprimer tirets multiples
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def generate_watch_links(titre: str, titre_original: str = "") -> dict:
    """
    Génère les liens de visionnage pour toutes les sources configurées.
    Essaie d'abord avec le titre français, puis le titre original.
    """
    slug_fr = slugify(titre)
    slug_jp = slugify(titre_original) if titre_original else slug_fr

    links = {}
    for source_name, url_template in ANIME_SOURCES.items():
        # Essayer avec le slug français d'abord
        links[source_name] = {
            "url": url_template.format(slug=slug_fr),
            "url_alt": url_template.format(slug=slug_jp) if slug_jp != slug_fr else None,
            "name": _get_source_display_name(source_name),
        }

    return links


def get_primary_watch_link(titre: str, titre_original: str = "", source: str = None) -> tuple:
    """
    Retourne le lien principal de visionnage (URL, nom_source).
    """
    source = source or DEFAULT_SOURCE
    slug = slugify(titre)
    url_template = ANIME_SOURCES.get(source, ANIME_SOURCES.get("franime"))
    url = url_template.format(slug=slug)
    display_name = _get_source_display_name(source)
    return url, display_name


def get_episode_link(titre: str, episode: int, source: str = None) -> str:
    """Génère un lien vers un épisode spécifique."""
    source = source or DEFAULT_SOURCE
    slug = slugify(titre)

    # Formats spécifiques par source
    if source == "franime":
        return f"https://franime.fr/anime/{slug}/episode-{episode}"
    elif source == "anime_sama":
        return f"https://anime-sama.fr/catalogue/{slug}/saison1/vostfr/episode{episode}"
    elif source == "voiranime":
        return f"https://voiranime.com/anime/{slug}/{episode}"
    else:
        url_template = ANIME_SOURCES.get(source, ANIME_SOURCES["franime"])
        return url_template.format(slug=slug)


async def check_source_availability(url: str) -> bool:
    """Vérifie si un lien source est accessible (HEAD request)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=10),
                                    allow_redirects=True) as resp:
                return resp.status < 400
    except Exception:
        return False


async def find_best_source(titre: str, titre_original: str = "") -> tuple:
    """
    Teste toutes les sources et retourne la première disponible.
    Retourne (url, source_name) ou (None, None) si aucune ne fonctionne.
    """
    links = generate_watch_links(titre, titre_original)

    for source_name, link_data in links.items():
        url = link_data["url"]
        if await check_source_availability(url):
            return url, link_data["name"]
        # Essayer l'URL alternative
        if link_data["url_alt"]:
            if await check_source_availability(link_data["url_alt"]):
                return link_data["url_alt"], link_data["name"]

    # Aucune source vérifiée, retourner la source par défaut
    slug = slugify(titre)
    default_url = ANIME_SOURCES[DEFAULT_SOURCE].format(slug=slug)
    return default_url, _get_source_display_name(DEFAULT_SOURCE)


def build_watch_buttons(titre: str, titre_original: str = "") -> list:
    """
    Construit la liste de boutons pour les sources de visionnage.
    Retourne une liste de tuples (texte, url).
    """
    links = generate_watch_links(titre, titre_original)
    buttons = []
    for source_name, link_data in links.items():
        emoji = _get_source_emoji(source_name)
        buttons.append((f"{emoji} {link_data['name']}", link_data["url"]))
    return buttons


def _get_source_display_name(source: str) -> str:
    """Nom d'affichage pour une source."""
    names = {
        "franime": "Franime",
        "anime_sama": "Anime-Sama",
        "voiranime": "VoirAnime",
    }
    return names.get(source, source.capitalize())


def _get_source_emoji(source: str) -> str:
    """Emoji pour une source."""
    emojis = {
        "franime": "🇫🇷",
        "anime_sama": "🎬",
        "voiranime": "👁️",
    }
    return emojis.get(source, "▶️")
