"""
Traduction via LibreTranslate (open-source, auto-hébergeable ou instances
publiques comme https://libretranslate.com avec clé API gratuite limitée).
Sert de repli gratuit quand aucune clé DeepL n'est fournie.

NOTE : non testé en conditions réelles (pas d'accès réseau sortant depuis le
bac à sable de développement).
"""
from __future__ import annotations

import requests


class LibreTranslateTranslator:
    name = "libretranslate"

    def __init__(self, base_url: str = "https://libretranslate.com", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def translate(self, text: str, source_lang: str, target_lang: str) -> str | None:
        if not text:
            return None
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        try:
            resp = requests.post(f"{self.base_url}/translate", data=payload, timeout=30)
            resp.raise_for_status()
        except requests.RequestException:
            return None
        data = resp.json()
        return data.get("translatedText")
