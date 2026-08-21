"""
Scanner de structure RetroFE.

Détecte un dossier racine RetroFE (celui qui contient collections/, RetroFE.exe
ou CORE.exe, settings.conf...) et parse chaque collections/<Nom>/settings.conf
pour en extraire :
  - le chemin des roms (list.path)
  - les extensions gérées (list.extensions)
  - les mappings media.* actifs (non commentés), résolus en chemins absolus

Notes sur les variables RetroFE dans settings.conf :
  %BASE_MEDIA_PATH%     -> se résout, empiriquement, au dossier de la
                            collection elle-même (medium_artwork y vit
                            directement, ex: collections/MAME/medium_artwork/)
  %ITEM_COLLECTION_NAME% -> nom de la collection (ex: "MAME")
"""
from __future__ import annotations

import ntpath
import os
import re
from dataclasses import dataclass
from typing import Optional

from .models import Collection, KNOWN_MEDIA_KEYS

SKIP_COLLECTIONS = {"Main", "COMPUTERS", "COMPUTERS.bak", "_common", "LAUNCHERS"}


def _parse_conf_file(path: str) -> dict[str, str]:
    """Parse un fichier .conf style RetroFE (clé = valeur, # commentaire)."""
    values: dict[str, str] = {}
    if not os.path.isfile(path):
        return values
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # coupe un commentaire en fin de ligne (" # ...")
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            values[key] = value
    return values


def _resolve_media_path(raw_value: str, collections_dir: str, collection_name: str) -> str:
    """Substitue les variables RetroFE connues dans une valeur media.xxx.

    %BASE_MEDIA_PATH% se résout au dossier collections/ lui-même (pas au
    dossier de la collection) : le template complet est habituellement
    "%BASE_MEDIA_PATH%\\%ITEM_COLLECTION_NAME%\\medium_artwork\\..." ce qui
    donne bien collections/<Nom>/medium_artwork/... une fois les deux
    variables substituées.
    """
    resolved = raw_value
    resolved = resolved.replace("%BASE_MEDIA_PATH%", collections_dir)
    resolved = resolved.replace("%ITEM_COLLECTION_NAME%", collection_name)
    return resolved


def parse_collection_settings(
    collection_path: str, collection_name: str, retrofe_root: Optional[str] = None
) -> Collection:
    """Parse le settings.conf d'une collection et retourne un objet Collection.

    retrofe_root permet de résoudre les list.path relatifs (ex: MAME dont le
    romset réel vit dans emulators/mame/roms, hors de collections/).
    """
    settings_path = os.path.join(collection_path, "settings.conf")
    raw = _parse_conf_file(settings_path)

    roms_path = raw.get("list.path")
    if roms_path and not ntpath.isabs(roms_path) and retrofe_root:
        # les chemins RetroFE sont toujours au format Windows, même si ce
        # script tourne ailleurs pour les tests -> jointure via ntpath
        roms_path = ntpath.join(retrofe_root, roms_path)

    extensions_raw = raw.get("list.extensions", "")
    extensions = [e.strip().lower() for e in extensions_raw.split(",") if e.strip()]

    collections_dir = os.path.dirname(collection_path)
    media_map: dict[str, str] = {}
    for key in KNOWN_MEDIA_KEYS:
        if key in raw:  # présent et non commenté = actif
            resolved = _resolve_media_path(raw[key], collections_dir, collection_name)
            media_map[key] = resolved

    return Collection(
        name=collection_name,
        path=collection_path,
        roms_path=roms_path,
        extensions=extensions,
        launcher=raw.get("launcher"),
        metadata_type=raw.get("metadata.type"),
        media_map=media_map,
        raw_settings=raw,
    )


RETROFE_MARKERS = ("RetroFE.exe", "CORE.exe", "retrofe", "core.exe")


def _looks_like_retrofe_root(path: str) -> bool:
    """Un vrai dossier racine RetroFE a collections/ ET un exécutable RetroFE/CORE
    (ou un layouts/ + settings.conf) -- évite les faux positifs sur un simple
    dossier nommé "collections" imbriqué (montages réseau, raccourcis, etc.)."""
    if not os.path.isdir(os.path.join(path, "collections")):
        return False
    try:
        entries_lower = {e.lower() for e in os.listdir(path)}
    except OSError:
        return False
    has_exe_marker = any(m.lower() in entries_lower for m in RETROFE_MARKERS)
    has_layouts = "layouts" in entries_lower
    has_root_settings = "settings.conf" in entries_lower
    return has_exe_marker or (has_layouts and has_root_settings)


def find_retrofe_root(start_path: str) -> Optional[str]:
    """Remonte depuis start_path pour trouver la vraie racine RetroFE."""
    current = os.path.abspath(start_path)
    for _ in range(8):
        if _looks_like_retrofe_root(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def scan_collections(retrofe_root: str, skip: Optional[set[str]] = None) -> list[Collection]:
    """Scanne collections/ sous la racine RetroFE et retourne la liste des Collection valides."""
    skip = skip if skip is not None else SKIP_COLLECTIONS
    collections_dir = os.path.join(retrofe_root, "collections")
    result: list[Collection] = []
    if not os.path.isdir(collections_dir):
        return result

    for name in sorted(os.listdir(collections_dir)):
        if name in skip:
            continue
        full = os.path.join(collections_dir, name)
        if not os.path.isdir(full):
            continue
        settings_path = os.path.join(full, "settings.conf")
        if not os.path.isfile(settings_path):
            continue
        coll = parse_collection_settings(full, name, retrofe_root=retrofe_root)
        result.append(coll)

    return result


def count_roms(collection: Collection) -> int:
    """Compte rapidement les fichiers/dossiers de roms d'une collection (sans stat)."""
    if not collection.roms_path or not os.path.isdir(collection.roms_path):
        return 0
    try:
        names = os.listdir(collection.roms_path)
    except OSError:
        return 0
    # filtre les dossiers de médias connus qui trainent parfois dans roms/
    skip_names = {"video", "images", "media"}
    count = 0
    for n in names:
        if n in skip_names:
            continue
        if collection.extensions:
            _, ext = os.path.splitext(n)
            ext = ext.lower().lstrip(".")
            if ext and ext not in collection.extensions and "." in n:
                # on garde quand même les dossiers (systèmes "un dossier par jeu")
                if "." in n:
                    continue
        count += 1
    return count
