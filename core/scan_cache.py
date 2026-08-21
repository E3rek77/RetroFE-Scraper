"""
Memoire de progression d'un scan, par collection.

But : si le quota ScreenScraper du compte est atteint en plein milieu d'un
scan (tres facile a atteindre avec un compte gratuit, cf. HTTP 430), relancer
le scan plus tard ne doit pas re-consommer du quota pour les jeux deja
trouves/telecharges avec succes lors d'un run precedent.

Un fichier JSON est ecrit directement dans le dossier de la collection
(`.retrofe_scraper_cache.json`), a cote de `settings.conf`. Il est ecrit
apres CHAQUE rom traitee (pas seulement en fin de scan) pour survivre a une
interruption a n'importe quel moment.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

CACHE_FILENAME = ".retrofe_scraper_cache.json"


@dataclass
class RomCacheEntry:
    matched: bool
    media_keys_done: list[str] = field(default_factory=list)
    story_done: bool = False


def cache_path(collection_path: str) -> str:
    return os.path.join(collection_path, CACHE_FILENAME)


def load_cache(collection_path: str) -> dict[str, RomCacheEntry]:
    path = cache_path(collection_path)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    result = {}
    for fname, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        result[fname] = RomCacheEntry(
            matched=bool(entry.get("matched", False)),
            media_keys_done=list(entry.get("media_keys_done", [])),
            story_done=bool(entry.get("story_done", False)),
        )
    return result


def save_cache(collection_path: str, cache: dict[str, RomCacheEntry]) -> None:
    path = cache_path(collection_path)
    raw = {
        fname: {
            "matched": entry.matched,
            "media_keys_done": entry.media_keys_done,
            "story_done": entry.story_done,
        }
        for fname, entry in cache.items()
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
    except OSError:
        pass  # non bloquant : au pire on re-scanne cette collection au prochain run


def is_fully_done(entry: Optional[RomCacheEntry], requested_media_keys: set[str], needs_story: bool) -> bool:
    """True si cette rom n'a plus rien d'utile a demander a l'API compte tenu
    des options actuelles (memes cles media, meme besoin de story)."""
    if entry is None:
        return False
    if not entry.matched:
        # un jeu confirme "non trouve" lors d'un run precedent : pas la peine
        # de re-interroger l'API, le resultat ne va pas changer.
        return True
    media_ok = requested_media_keys.issubset(set(entry.media_keys_done))
    story_ok = (not needs_story) or entry.story_done
    return media_ok and story_ok
