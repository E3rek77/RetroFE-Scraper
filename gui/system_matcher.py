"""
Association automatique (approximative) entre un nom de collection RetroFE
(ex: "Sega Genesis") et un nom de systeme ScreenScraper (ex: "Megadrive").

ScreenScraper utilise ses propres noms, souvent tres differents des noms
RetroFE/No-Intro. On donne un dictionnaire d'alias pour les cas frequents,
puis on retombe sur une comparaison floue (difflib) pour le reste.
"""
from __future__ import annotations

import difflib
import re

# alias connus : fragment (minuscule) du nom de collection RetroFE ->
# fragment (minuscule) attendu dans le nom ScreenScraper
ALIASES = {
    "sega genesis": "megadrive",
    "sega megadrive": "megadrive",
    "sega master system": "master system",
    "sega game gear": "game gear",
    "sega saturn": "saturn",
    "sega dreamcast": "dreamcast",
    "sega cd": "mega-cd",
    "sega 32x": "32x",
    "sony playstation vita": "playstation vita",
    "sony playstation 2": "playstation 2",
    "sony playstation 3": "playstation 3",
    "sony playstation 4": "playstation 4",
    "sony playstation 5": "playstation 5",
    "sony playstation": "playstation",
    "sony psp": "playstation portable",
    "nintendo entertainment system": "nes",
    "nintendo famicom": "famicom",
    "super nintendo entertainment system": "super nintendo",
    "nintendo super famicom": "super famicom",
    "nintendo game boy advance": "game boy advance",
    "nintendo game boy color": "game boy color",
    "nintendo game boy": "game boy",
    "nintendo gamecube": "gamecube",
    "nintendo 64": "nintendo 64",
    "nintendo ds": "nintendo ds",
    "nintendo 3ds": "nintendo 3ds",
    "nintendo wii u": "wii u",
    "nintendo wii": "wii",
    "nintendo switch": "switch",
    "microsoft xbox 360": "xbox 360",
    "microsoft xbox": "xbox",
    "atari 2600": "atari 2600",
    "atari 5200": "atari 5200",
    "atari 7800": "atari 7800",
    "atari lynx": "atari lynx",
    "atari jaguar": "atari jaguar",
    "mame": "mame",
    "final burn alpha": "fba",
    "colecovision": "colecovision",
    "nec pc engine cd": "pc engine cd",
    "nec pc engine": "pc engine",
    "wonderswan color": "wonderswan color",
    "mattel intellivision": "intellivision",
    "snk neo geo cd": "neo geo cd",
    "commodore 64": "commodore 64",
}


def _normalize(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def suggest_match(collection_name: str, ss_systems: dict[str, str]) -> tuple[str, str, float]:
    """Retourne (systemeid, nom_ss, score) le meilleur candidat pour ce nom de
    collection, ou ("", "", 0.0) si rien de plausible n'a ete trouve.

    ss_systems : dict systemeid -> nom ScreenScraper (sortie de fetch_systems_list()).
    """
    norm_coll = _normalize(collection_name)

    # 1. alias explicite
    target_fragment = ALIASES.get(norm_coll)
    if target_fragment:
        for sid, ss_name in ss_systems.items():
            if _normalize(ss_name) == target_fragment:
                return sid, ss_name, 1.0
        for sid, ss_name in ss_systems.items():
            if target_fragment in _normalize(ss_name):
                return sid, ss_name, 0.9

    # 2. comparaison floue directe sur le nom complet
    best_sid, best_name, best_score = "", "", 0.0
    for sid, ss_name in ss_systems.items():
        score = difflib.SequenceMatcher(None, norm_coll, _normalize(ss_name)).ratio()
        if score > best_score:
            best_sid, best_name, best_score = sid, ss_name, score

    if best_score >= 0.55:
        return best_sid, best_name, best_score
    return "", "", 0.0


def build_system_map(collection_names: list[str], ss_systems: dict[str, str]) -> dict[str, dict]:
    """Pour chaque nom de collection, retourne les infos de suggestion :
    {collection_name: {"systemeid": str, "ss_name": str, "score": float}}"""
    result = {}
    for name in collection_names:
        sid, ss_name, score = suggest_match(name, ss_systems)
        result[name] = {"systemeid": sid, "ss_name": ss_name, "score": score}
    return result
