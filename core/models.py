"""Modèles de données pour RetroFE-Scraper."""
from dataclasses import dataclass, field
from typing import Optional


# Clés media.* connues dans un settings.conf RetroFE, et le sous-dossier
# correspondant sous medium_artwork/ (relatif à la collection).
KNOWN_MEDIA_KEYS = [
    "media.video",
    "media.logo",
    "media.artwork_front",
    "media.artwork_back",
    "media.screentitle",
    "media.screenshot",
    "media.bezel",
    "media.fanart",
    "media.medium_back",
    "media.medium_front",
    "media.system_artwork",
]


@dataclass
class Collection:
    """Une collection RetroFE (un système de jeu)."""
    name: str                      # ex: "Nintendo 64"
    path: str                      # chemin absolu du dossier de la collection
    roms_path: Optional[str] = None
    extensions: list[str] = field(default_factory=list)
    launcher: Optional[str] = None
    metadata_type: Optional[str] = None
    media_map: dict[str, str] = field(default_factory=dict)   # media.xxx -> chemin absolu résolu
    raw_settings: dict[str, str] = field(default_factory=dict)

    def media_dir(self, key: str) -> Optional[str]:
        """Retourne le dossier résolu pour une clé media.xxx si active, sinon None."""
        return self.media_map.get(key)


@dataclass
class RomFile:
    """Une rom détectée dans une collection."""
    filename: str          # nom de fichier tel quel
    display_name: str      # nom sans extension (ou nom de dossier)
    full_path: str
    collection: str        # nom de la collection parente
