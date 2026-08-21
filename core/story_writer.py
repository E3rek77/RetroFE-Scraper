"""
Écriture des fichiers story.txt (description affichée par RetroFE).

RetroFE détecte ces fichiers par convention dans medium_artwork/story/
sans qu'aucune ligne media.story n'existe dans settings.conf (confirmé par
inspection : ce mot-clé n'apparaît dans aucun settings.conf de référence).
"""
from __future__ import annotations

import os

from .models import Collection
from .translate.manager import TranslationManager


def write_story(collection: Collection, game_display_name: str, description: str,
                 description_lang: str, target_lang: str,
                 translator: TranslationManager | None = None) -> tuple[str, bool]:
    """
    Écrit medium_artwork/story/<jeu>.txt. Si la description n'est pas dans la
    langue cible et qu'un TranslationManager est fourni, elle est traduite
    avant écriture.

    Retourne (chemin écrit, a_ete_traduit).
    """
    story_dir = os.path.join(collection.path, "medium_artwork", "story")
    os.makedirs(story_dir, exist_ok=True)
    dest_path = os.path.join(story_dir, game_display_name + ".txt")

    text = description
    translated = False
    if description_lang and description_lang.lower() != target_lang.lower() and translator:
        result = translator.translate(description, description_lang, target_lang)
        if result:
            text = result
            translated = True

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(text)

    return dest_path, translated
