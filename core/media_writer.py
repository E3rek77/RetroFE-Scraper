"""
Écriture des médias scrapés dans l'arborescence RetroFE, et auto-réparation
de settings.conf quand une ligne media.xxx manque ou est commentée alors que
le dossier correspondant existe (ou est sur le point d'être rempli).

C'est la formalisation du script qui a servi à réparer manuellement 63
collections de l'installation de Pierre (aucune ligne media.* dans la
plupart des settings.conf alors que medium_artwork/ était déjà rempli).
"""
from __future__ import annotations

import os
import shutil
from typing import Iterable

from .models import Collection
from .scrapers.screenscraper import RETROFE_NATIVE_KEYS

# clé media.xxx -> sous-chemin relatif à la collection (utilise "/" ; converti
# en "\\" au moment d'écrire settings.conf, comme le veut RetroFE sur Windows)
# Les 11 premières clés sont les media.xxx officiellement reconnus par
# RetroFE (cf. RETROFE_NATIVE_KEYS). Les suivantes couvrent l'intégralité
# des types de médias renvoyés par ScreenScraper (support/cartouche, manuel,
# figurine, mix Recalbox, pictogrammes...) : le fichier est bien téléchargé
# et rangé, mais aucune ligne media.xxx n'est ajoutée pour elles (RetroFE ne
# les affiche pas nativement sans un layout personnalisé).
KEY_TO_RELPATH = {
    "artwork_back": "medium_artwork/artwork_back",
    "artwork_front": "medium_artwork/artwork_front",
    "artwork_3d": "medium_artwork/artwork_3d",
    "logo": "medium_artwork/logo",
    "medium_back": "medium_artwork/medium_back",
    "medium_front": "medium_artwork/medium_front",
    "screenshot": "medium_artwork/screenshot",
    "screentitle": "medium_artwork/screentitle",
    "video": "medium_artwork/video",
    "system_artwork": "system_artwork",
    "bezel": "medium_artwork/bezel_day",

    "fanart": "medium_artwork/fanart",
    "video_normalise": "medium_artwork/video_normalise",
    "steamgrid": "medium_artwork/steamgrid",
    "logo_hd": "medium_artwork/logo_hd",
    "logo_carbon": "medium_artwork/logo_carbon",
    "logo_steel": "medium_artwork/logo_steel",
    "marquee": "medium_artwork/marquee",
    "marquee_petit": "medium_artwork/marquee_petit",
    "artwork_side": "medium_artwork/artwork_side",
    "box_texture": "medium_artwork/box_texture",
    "manual": "medium_artwork/manual",
    "support_texture": "medium_artwork/support_texture",
    "cartridge": "medium_artwork/cartridge",
    "theme_pack": "medium_artwork/theme_pack",
    "mix_v1": "medium_artwork/mix_v1",
    "mix_v2": "medium_artwork/mix_v2",
    "picto_liste": "medium_artwork/picto_liste",
    "picto_mono": "medium_artwork/picto_mono",
    "picto_couleur": "medium_artwork/picto_couleur",
    "background": "medium_artwork/background",
    "figurine": "medium_artwork/figurine",
}


def media_dir_for(collection: Collection, key: str) -> str:
    """Chemin absolu du dossier cible pour une clé media.xxx donnée."""
    rel = KEY_TO_RELPATH[key]
    return os.path.join(collection.path, *rel.split("/"))


def _has_content(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    try:
        return len(os.listdir(path)) > 0
    except OSError:
        return False


def _already_active(lines: list[str], key: str) -> bool:
    for line in lines:
        s = line.strip()
        if s.startswith(f"media.{key}") and "=" in s and not s.startswith("#"):
            return True
    return False


def _find_commented_index(lines: list[str], key: str) -> int | None:
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(f"#media.{key}") or s.startswith(f"# media.{key}"):
            return i
    return None


def ensure_media_lines(collection: Collection, keys: Iterable[str]) -> list[str]:
    """
    S'assure que settings.conf a une ligne active media.xxx pour chaque clé de
    `keys` dont le dossier a du contenu. Décommente si un template existe déjà,
    sinon ajoute la ligne. Ne touche jamais une ligne déjà active.

    Retourne la liste des clés effectivement ajoutées/activées.
    """
    settings_path = os.path.join(collection.path, "settings.conf")
    if not os.path.isfile(settings_path):
        return []

    with open(settings_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    added: list[str] = []
    for key in keys:
        if key not in KEY_TO_RELPATH:
            continue
        if key not in RETROFE_NATIVE_KEYS:
            # média téléchargé et rangé, mais RetroFE n'a pas de ligne
            # media.xxx native pour ce type -> rien à écrire dans settings.conf
            continue

        rel_folder = KEY_TO_RELPATH[key]
        target = os.path.join(collection.path, *rel_folder.split("/"))

        # repli logo -> wheel si le dossier "logo" n'existe pas mais "wheel" oui
        # (convention ES/Skraper pour le clear-logo)
        if key == "logo" and not _has_content(target):
            wheel = os.path.join(collection.path, "medium_artwork", "wheel")
            if _has_content(wheel):
                target = wheel
                rel_folder = "medium_artwork/wheel"

        if not _has_content(target):
            continue
        if _already_active(lines, key):
            continue

        value = "%BASE_MEDIA_PATH%\\%ITEM_COLLECTION_NAME%\\" + rel_folder.replace("/", "\\")
        new_line = f"media.{key.ljust(14)} = {value}"

        idx = _find_commented_index(lines, key)
        if idx is not None:
            lines[idx] = new_line
        else:
            lines.append(new_line)
        added.append(key)

    if added:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return added


def save_media_file(collection: Collection, key: str, game_display_name: str, source_path: str) -> str:
    """
    Copie un fichier média téléchargé (déjà sur disque, ex: fichier temp
    téléchargé par le scraper) vers le bon dossier de la collection, nommé
    d'après le jeu (sans extension d'origine de la rom, garde celle du média).

    Retourne le chemin final écrit. Appelle ensure_media_lines pour que
    settings.conf soit à jour après coup.
    """
    target_dir = media_dir_for(collection, key)
    os.makedirs(target_dir, exist_ok=True)

    _, ext = os.path.splitext(source_path)
    dest_path = os.path.join(target_dir, game_display_name + ext)
    shutil.copyfile(source_path, dest_path)

    ensure_media_lines(collection, [key])
    return dest_path
