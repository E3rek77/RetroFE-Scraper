"""
Client pour l'API ScreenScraper.fr (v2).

Nécessite :
  - devid / devpassword : identifiants développeur, obtenus en présentant le
    projet sur le forum WebAPI ScreenScraper (validation manuelle par un admin)
  - ssid / sspassword : identifiants d'un compte utilisateur ScreenScraper
    classique (inscription libre, immédiate)

Endpoints utilisés :
  - jeuInfos.php       recherche d'un jeu par CRC/MD5/SHA1 + nom + taille
  - systemesListe.php  liste des systèmes ScreenScraper (pour construire la
                        table de correspondance avec les collections RetroFE)

NOTE IMPORTANTE : ce module n'a pas pu être testé en conditions réelles (le
bac à sable de développement n'a pas d'accès réseau sortant vers l'API
ScreenScraper). Il est écrit strictement d'après la documentation officielle
(https://www.screenscraper.fr/webapi2.php). À valider dès que les identifiants
développeur sont obtenus -- en particulier les noms exacts des champs XML
retournés par jeuInfos.php, qui peuvent avoir légèrement changé côté serveur.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

from .base import GameMatch

# Les URLs de médias ScreenScraper pointent vers un endpoint PHP dynamique
# (ex: .../mediaJeu.php?systemeid=...&media=support-2D&crc=...) -- le chemin
# de l'URL se termine donc TOUJOURS par ".php", quel que soit le type reel du
# fichier renvoye. Deviner l'extension depuis l'URL est donc faux la plupart
# du temps (on obtenait ".php" au lieu de ".png"/".jpg"/etc). La bonne methode
# est de lire l'en-tete Content-Type de la reponse HTTP.
_EXT_FROM_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/x-icon": ".ico",
    "video/mp4": ".mp4",
    "video/x-msvideo": ".avi",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


def _fallback_ext_from_url(url: str) -> str:
    """Repli si le Content-Type est absent/inconnu : tente l'extension du
    chemin d'URL, mais ignore ".php" (jamais une vraie extension de media
    ici) au profit d'un defaut generique."""
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and ext.lower() != ".php":
        return ext
    return ".jpg"

API_BASE = "https://api.screenscraper.fr/api2"


class ScreenScraperQuotaError(Exception):
    """Levee quand ScreenScraper repond HTTP 430 (quota journalier du compte
    depasse). A distinguer d'un simple "jeu non trouve" : continuer a
    boucler sur les roms suivantes serait inutile tant que le quota n'est
    pas reinitialise (generalement le lendemain)."""
    pass

# clé interne RetroFE-Scraper -> nom de media ScreenScraper (media="...")
# Liste complète, vérifiée en conditions réelles le 20/08/2026 via
# test_game_search.py (29 types uniques renvoyés par jeuInfos.php).
SS_MEDIA_MAP = {
    "screentitle": "sstitle",
    "screenshot": "ss",
    "fanart": "fanart",
    "video": "video",
    "video_normalise": "video-normalized",
    "steamgrid": "steamgrid",
    "logo": "wheel",
    "logo_hd": "wheel-hd",
    "logo_carbon": "wheel-carbon",
    "logo_steel": "wheel-steel",
    "marquee": "screenmarquee",
    "marquee_petit": "screenmarqueesmall",
    "artwork_front": "box-2D",
    "artwork_side": "box-2D-side",
    "artwork_back": "box-2D-back",
    "box_texture": "box-texture",
    "artwork_3d": "box-3D",
    "manual": "manuel",
    "support_texture": "support-texture",
    "medium_disc": "support-2D",
    "bezel": "bezel-16-9",
    "theme_pack": "themehs",
    "mix_v1": "mixrbv1",
    "mix_v2": "mixrbv2",
    "picto_liste": "pictoliste",
    "picto_mono": "pictomonochrome",
    "picto_couleur": "pictocouleur",
    "background": "background",
    "figurine": "figurine",
    "system_artwork": "wheel",
}

# Sous-ensemble de clés que RetroFE sait afficher nativement via une ligne
# media.xxx dans settings.conf (les 11 clés officielles + bezel). Pour les
# autres, le fichier est bien téléchargé et rangé dans medium_artwork/<clé>/,
# mais aucune ligne media.xxx n'est ajoutée (RetroFE ne les affiche pas sans
# un layout personnalisé qui les référence explicitement).
RETROFE_NATIVE_KEYS = {
    "artwork_back", "artwork_front", "artwork_3d", "logo", "medium_back",
    "medium_front", "screenshot", "screentitle", "video", "system_artwork", "bezel",
    "medium_disc",
}


@dataclass
class ScreenScraperCredentials:
    devid: str
    devpassword: str
    softname: str
    ssid: str = ""
    sspassword: str = ""


class ScreenScraperClient:
    name = "screenscraper"

    def __init__(self, creds: ScreenScraperCredentials, session: requests.Session | None = None):
        self.creds = creds
        self.session = session or requests.Session()

    def _base_params(self) -> dict[str, str]:
        return {
            "devid": self.creds.devid,
            "devpassword": self.creds.devpassword,
            "softname": self.creds.softname,
            "ssid": self.creds.ssid,
            "sspassword": self.creds.sspassword,
            "output": "xml",
        }

    def search_by_hash(self, system_id: str, crc: str = "", md5: str = "", sha1: str = "",
                        filename: str = "", filesize: int = 0) -> GameMatch:
        params = self._base_params()
        params["systemeid"] = system_id
        if crc:
            params["crc"] = crc
        if md5:
            params["md5"] = md5
        if sha1:
            params["sha1"] = sha1
        if filename:
            params["romnom"] = filename
        if filesize:
            params["romtaille"] = str(filesize)

        try:
            resp = self.session.get(f"{API_BASE}/jeuInfos.php", params=params, timeout=20)
        except requests.RequestException:
            return GameMatch(found=False)

        if resp.status_code == 430 or "quota" in resp.text.lower()[:400]:
            detail = resp.text.strip()[:300]
            raise ScreenScraperQuotaError(f"HTTP {resp.status_code} -- {detail}")

        try:
            resp.raise_for_status()
        except requests.RequestException:
            return GameMatch(found=False)

        return self._parse_jeu_infos(resp.text)

    def search_by_name(self, system_id: str, name: str) -> GameMatch:
        # jeuInfos.php accepte romnom seul (sans hash), en dernier recours
        return self.search_by_hash(system_id, filename=name)

    def _parse_jeu_infos(self, xml_text: str) -> GameMatch:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return GameMatch(found=False)

        jeu = root.find("jeu")
        if jeu is None:
            return GameMatch(found=False)

        game_id = jeu.get("id") or (jeu.findtext("id") or None)
        title = None
        noms = jeu.find("noms")
        if noms is not None:
            title = noms.findtext("nom_us") or noms.findtext("nom_eu")

        description = None
        description_lang = None
        synopsis = jeu.find("synopsis")
        if synopsis is not None:
            fr = synopsis.findtext("synopsis_fr")
            en = synopsis.findtext("synopsis_en")
            if fr:
                description, description_lang = fr, "fr"
            elif en:
                description, description_lang = en, "en"

        media_urls: dict[str, str] = {}
        medias = jeu.find("medias")
        if medias is not None:
            for media_el in medias.findall("media"):
                ss_type = media_el.get("type")
                url = media_el.text
                if not ss_type or not url:
                    continue
                for internal_key, mapped_type in SS_MEDIA_MAP.items():
                    if ss_type == mapped_type and internal_key not in media_urls:
                        media_urls[internal_key] = url

        return GameMatch(
            found=True,
            game_id=game_id,
            title=title,
            description=description,
            description_lang=description_lang,
            media_urls=media_urls,
        )

    def download_media(self, url: str, dest_path: str) -> Optional[str]:
        """Telecharge le media vers dest_path. Retourne l'extension de
        fichier detectee (ex: ".png") en cas de succes, None en cas
        d'echec. L'extension est determinee via l'en-tete Content-Type de
        la reponse (voir note en tete de fichier -- l'URL elle-meme n'est
        pas fiable pour ca)."""
        try:
            resp = self.session.get(url, timeout=60, stream=True)
            resp.raise_for_status()
        except requests.RequestException:
            return None
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        return _EXT_FROM_CONTENT_TYPE.get(content_type) or _fallback_ext_from_url(url)

    def fetch_systems_list(self) -> dict[str, str]:
        """Récupère la liste officielle des systèmes ScreenScraper (id -> nom).
        À utiliser une fois pour construire la table de correspondance avec
        les noms de collections RetroFE (mapping manuel, les noms ne
        correspondent jamais exactement)."""
        params = self._base_params()
        try:
            resp = self.session.get(f"{API_BASE}/systemesListe.php", params=params, timeout=20)
            resp.raise_for_status()
        except requests.RequestException:
            return {}
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return {}
        result = {}
        for systeme in root.findall(".//systeme"):
            sid = systeme.get("id") or systeme.findtext("id")
            noms = systeme.find("noms")
            name = noms.findtext("nom_eu") if noms is not None else None
            if sid and name:
                result[sid] = name
        return result
