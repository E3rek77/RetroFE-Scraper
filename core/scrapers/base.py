"""Interface commune à tous les scrapers (ScreenScraper, TheGamesDB, ...)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class GameMatch:
    """Résultat de recherche d'un jeu chez un scraper."""
    found: bool
    game_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    description_lang: Optional[str] = None       # code langue ISO de la description ("fr", "en"...)
    media_urls: dict[str, str] = field(default_factory=dict)   # cle interne (logo, video...) -> URL


class Scraper(Protocol):
    """Un scraper doit savoir s'identifier et chercher un jeu par CRC/nom."""

    name: str

    def search_by_hash(self, system_id: str, crc: str = "", md5: str = "", sha1: str = "",
                        filename: str = "", filesize: int = 0) -> GameMatch:
        ...

    def search_by_name(self, system_id: str, name: str) -> GameMatch:
        ...

    def download_media(self, url: str, dest_path: str) -> bool:
        ...
