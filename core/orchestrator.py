"""
Orchestration complète d'un scan : pour chaque collection sélectionnée,
pour chaque rom, cherche le jeu chez le scraper, télécharge les médias
disponibles, écrit la description (traduite si besoin), répare settings.conf,
puis invalide meta.db en fin de run.

C'est le point d'entrée que la CLI et la GUI appelleront.
"""
from __future__ import annotations

import glob
import os
import tempfile
import zlib
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import scan_cache
from .db_cache import invalidate_meta_db
from .media_writer import save_media_file
from .models import Collection, RomFile
from .retrofe_scanner import count_roms
from .scrapers.base import GameMatch, Scraper
from .scrapers.screenscraper import ScreenScraperQuotaError
from .story_writer import write_story
from .translate.manager import TranslationManager


@dataclass
class ScanOptions:
    target_lang: str = "fr"
    system_id_map: dict[str, str] = field(default_factory=dict)   # nom collection -> systemeid scraper
    media_keys: tuple[str, ...] = ("logo", "artwork_front", "video", "screenshot", "screentitle")
    skip_existing: bool = True    # ne retélécharge pas un média déjà présent


@dataclass
class ScanStats:
    games_scanned: int = 0
    games_matched: int = 0
    media_downloaded: int = 0
    stories_written: int = 0
    stories_translated: int = 0
    errors: list[str] = field(default_factory=list)


def _list_roms(collection: Collection) -> list[RomFile]:
    if not collection.roms_path or not os.path.isdir(collection.roms_path):
        return []
    roms = []
    for fname in sorted(os.listdir(collection.roms_path)):
        full = os.path.join(collection.roms_path, fname)
        base, ext = os.path.splitext(fname)
        display = fname if os.path.isdir(full) else base
        roms.append(RomFile(filename=fname, display_name=display, full_path=full, collection=collection.name))
    return roms


# Au-dela de cette taille, on ne calcule pas le CRC32 (trop long pour des
# images CD/DVD volumineuses) : on retombe sur une recherche par nom+taille
# seule, moins fiable mais evite un scan qui bloque des heures sur un seul
# fichier.
MAX_HASH_SIZE_BYTES = 1_500_000_000  # ~1.5 Go
HASH_CHUNK_SIZE = 4 * 1024 * 1024


def _compute_crc32(path: str) -> str:
    """CRC32 du fichier, en hexadecimal majuscule sur 8 caracteres (format
    attendu par l'API ScreenScraper). Necessaire car la recherche par nom
    seul (romnom/romtaille) rate la grande majorite des roms des qu'elles ne
    sont pas nommees a l'identique du set de reference de ScreenScraper --
    la recherche par empreinte (crc/md5/sha1) est nettement plus fiable et
    fonctionne quel que soit le nom de fichier."""
    crc = 0
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                crc = zlib.crc32(chunk, crc)
    except OSError:
        return ""
    return f"{crc & 0xFFFFFFFF:08X}"


def scan_collection(
    collection: Collection,
    scraper: Scraper,
    options: ScanOptions,
    translator: Optional[TranslationManager] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> ScanStats:
    """Scanne une collection entière. progress_cb(nom_jeu, index, total) est
    appelé avant chaque jeu si fourni (pour brancher une barre de progression).

    Reprise sur quota : la progression (jeu trouvé/pas trouvé, médias déjà
    téléchargés, story déjà écrite) est mémorisée dans un fichier de cache
    par collection (voir scan_cache.py), mis à jour après CHAQUE rom. Si le
    quota ScreenScraper du compte est atteint en cours de route, le scan
    s'arrête proprement (au lieu de continuer à interroger l'API pour rien)
    et un prochain run reprendra exactement où il s'était arrêté, sans
    reconsommer de quota pour ce qui a déjà été traité avec succès."""
    stats = ScanStats()
    system_id = options.system_id_map.get(collection.name)
    if not system_id:
        stats.errors.append(f"{collection.name}: pas de systemeid connu, ignoré")
        return stats

    roms = _list_roms(collection)
    total = len(roms)
    requested_keys = set(options.media_keys)
    cache = scan_cache.load_cache(collection.path)

    for i, rom in enumerate(roms):
        if progress_cb:
            progress_cb(rom.display_name, i + 1, total)
        stats.games_scanned += 1

        cached_entry = cache.get(rom.filename)
        if scan_cache.is_fully_done(cached_entry, requested_keys, needs_story=True):
            if cached_entry.matched:
                stats.games_matched += 1
            continue

        size = 0
        is_file = False
        try:
            is_file = os.path.isfile(rom.full_path)
            if is_file:
                size = os.path.getsize(rom.full_path)
        except OSError:
            pass

        crc = ""
        if is_file and 0 < size <= MAX_HASH_SIZE_BYTES:
            crc = _compute_crc32(rom.full_path)

        try:
            match = GameMatch(found=False)
            if crc:
                match = scraper.search_by_hash(system_id, crc=crc)
            if not match.found:
                # repli : recherche par nom seul, SANS la taille -- envoyer
                # romtaille en meme temps que romnom fait echouer la
                # recherche cote API des que la taille ne correspond pas au
                # pixel pres (entete iNES, trainer, dump different...), ce
                # qui est tres frequent. Le nom seul est nettement plus
                # tolerant.
                match = scraper.search_by_hash(system_id, filename=rom.filename)
        except ScreenScraperQuotaError as e:
            stats.errors.append(
                f"{collection.name}: quota/limite ScreenScraper atteint ({e}), "
                f"scan interrompu à {i}/{total} -- relance plus tard pour continuer "
                f"(la progression est sauvegardée)."
            )
            scan_cache.save_cache(collection.path, cache)
            return stats

        entry = cached_entry or scan_cache.RomCacheEntry(matched=False)
        entry.matched = match.found

        if not match.found:
            cache[rom.filename] = entry
            scan_cache.save_cache(collection.path, cache)
            continue
        stats.games_matched += 1

        for key in options.media_keys:
            if key in entry.media_keys_done:
                continue
            url = match.media_urls.get(key)
            if not url:
                # ScreenScraper n'a pas ce type de media pour ce jeu -- fait
                # constant, pas la peine de reverifier a chaque scan
                entry.media_keys_done.append(key)
                continue
            target_dir = os.path.join(collection.path, "medium_artwork", key) \
                if key != "system_artwork" else os.path.join(collection.path, "system_artwork")
            # ne devine plus l'extension pour verifier l'existant : on
            # regarde s'il existe deja un fichier "<nom du jeu>.*" quelle
            # que soit son extension (l'URL ScreenScraper ne donne aucune
            # extension fiable, voir screenscraper.download_media)
            existing_matches = glob.glob(os.path.join(target_dir, glob.escape(rom.display_name) + ".*"))
            if options.skip_existing and existing_matches:
                entry.media_keys_done.append(key)
                continue

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            ext = scraper.download_media(url, tmp_path)
            if ext:
                try:
                    save_media_file(collection, key, rom.display_name, tmp_path, ext)
                    stats.media_downloaded += 1
                    entry.media_keys_done.append(key)
                except Exception as e:
                    stats.errors.append(f"{rom.display_name}: écriture média {key} échouée ({e})")
            os.unlink(tmp_path)

        if match.description:
            try:
                _, translated = write_story(
                    collection, rom.display_name, match.description,
                    match.description_lang or "en", options.target_lang, translator,
                )
                stats.stories_written += 1
                if translated:
                    stats.stories_translated += 1
                entry.story_done = True
            except Exception as e:
                stats.errors.append(f"{rom.display_name}: écriture story échouée ({e})")
        else:
            entry.story_done = True  # rien a ecrire, pas la peine de reessayer

        cache[rom.filename] = entry
        scan_cache.save_cache(collection.path, cache)

    return stats


def scan_retrofe(
    retrofe_root: str,
    collections: list[Collection],
    scraper: Scraper,
    options: ScanOptions,
    translator: Optional[TranslationManager] = None,
    progress_cb: Optional[Callable[[str, str, int, int], None]] = None,
) -> dict[str, ScanStats]:
    """Scanne plusieurs collections puis invalide meta.db une seule fois à la fin.

    Si le quota ScreenScraper est atteint en cours de route, les collections
    restantes sont marquées comme non traitées (au lieu de les interroger
    inutilement) -- elles reprendront normalement au prochain run grâce au
    cache de progression par collection."""
    results: dict[str, ScanStats] = {}
    quota_hit = False
    for collection in collections:
        if quota_hit:
            skipped = ScanStats()
            skipped.errors.append(f"{collection.name}: non traité (quota ScreenScraper déjà dépassé sur ce run)")
            results[collection.name] = skipped
            continue

        def cb(name, i, total, _coll=collection.name):
            if progress_cb:
                progress_cb(_coll, name, i, total)
        stats = scan_collection(collection, scraper, options, translator, cb)
        results[collection.name] = stats
        if any("quota/limite ScreenScraper atteint" in e for e in stats.errors):
            quota_hit = True

    invalidate_meta_db(retrofe_root)
    return results
