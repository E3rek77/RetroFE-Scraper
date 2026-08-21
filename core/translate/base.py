"""Interface commune aux moteurs de traduction."""
from __future__ import annotations

from typing import Protocol


class Translator(Protocol):
    name: str

    def translate(self, text: str, source_lang: str, target_lang: str) -> str | None:
        """Retourne le texte traduit, ou None en cas d'échec."""
        ...
