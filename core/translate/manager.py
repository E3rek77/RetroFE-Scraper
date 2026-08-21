"""
Orchestration de la traduction : essaie DeepL si une clé est fournie, sinon
retombe sur LibreTranslate. La langue cible est configurable (pas figée sur
le français) -- cf. paramètres de l'outil.
"""
from __future__ import annotations

from typing import Optional

from .deepl_translator import DeepLTranslator
from .libretranslate_translator import LibreTranslateTranslator


class TranslationManager:
    def __init__(self, deepl_api_key: str = "", libretranslate_url: str = "https://libretranslate.com",
                 libretranslate_api_key: str = ""):
        self.translators = []
        if deepl_api_key:
            self.translators.append(DeepLTranslator(deepl_api_key))
        self.translators.append(LibreTranslateTranslator(libretranslate_url, libretranslate_api_key))

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        if not text or source_lang.lower() == target_lang.lower():
            return text
        for translator in self.translators:
            result = translator.translate(text, source_lang, target_lang)
            if result:
                return result
        return None
