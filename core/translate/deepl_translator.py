"""
Traduction via l'API DeepL (gratuite jusqu'à 500 000 caractères/mois avec un
compte "DeepL API Free", inscription sur https://www.deepl.com/pro-api).

NOTE : non testé en conditions réelles (pas d'accès réseau sortant depuis le
bac à sable de développement). Contrat d'API basé sur la documentation
officielle DeepL (stable depuis plusieurs années).
"""
from __future__ import annotations

import requests


class DeepLTranslator:
    name = "deepl"

    def __init__(self, api_key: str, free_tier: bool = True):
        self.api_key = api_key
        self.endpoint = (
            "https://api-free.deepl.com/v2/translate" if free_tier
            else "https://api.deepl.com/v2/translate"
        )

    def translate(self, text: str, source_lang: str, target_lang: str) -> str | None:
        if not text:
            return None
        try:
            resp = requests.post(
                self.endpoint,
                data={
                    "auth_key": self.api_key,
                    "text": text,
                    "source_lang": source_lang.upper(),
                    "target_lang": target_lang.upper(),
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException:
            return None
        data = resp.json()
        translations = data.get("translations", [])
        if not translations:
            return None
        return translations[0].get("text")
