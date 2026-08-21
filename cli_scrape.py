"""
Lance un scan complet (scraping + médias + traduction) sur une ou plusieurs
collections RetroFE.

Usage:
    python cli_scrape.py "D:\CORE - TYPE R" --config config.json --collection "Nintendo 64"

Nécessite un config.json rempli (voir config.example.json) avec des
identifiants ScreenScraper valides.
"""
from __future__ import annotations

import argparse
import json
import sys

from core.orchestrator import ScanOptions, scan_retrofe
from core.retrofe_scanner import find_retrofe_root, scan_collections
from core.scrapers.screenscraper import ScreenScraperClient, ScreenScraperCredentials
from core.translate.manager import TranslationManager


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("retrofe_path")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--collection", action="append", help="Nom de collection à scanner (répétable). Sans cet argument : toutes.")
    args = parser.parse_args()

    config = load_json(args.config)
    ss_conf = config["screenscraper"]
    if not ss_conf.get("devid") or not ss_conf.get("ssid"):
        print("Identifiants ScreenScraper manquants dans le config.json (devid/ssid).")
        return 1

    system_map = load_json(config.get("system_id_map_file", "systems_map.json"))
    system_map = {k: v for k, v in system_map.items() if k != "_comment" and v}

    root = find_retrofe_root(args.retrofe_path)
    if not root:
        print(f"Racine RetroFE introuvable depuis {args.retrofe_path}")
        return 1

    all_collections = scan_collections(root)
    if args.collection:
        wanted = set(args.collection)
        all_collections = [c for c in all_collections if c.name in wanted]

    if not all_collections:
        print("Aucune collection à scanner.")
        return 1

    creds = ScreenScraperCredentials(**ss_conf)
    scraper = ScreenScraperClient(creds)
    translator = TranslationManager(
        deepl_api_key=config.get("deepl_api_key", ""),
        libretranslate_url=config.get("libretranslate_url", "https://libretranslate.com"),
        libretranslate_api_key=config.get("libretranslate_api_key", ""),
    )
    options = ScanOptions(target_lang=config.get("target_lang", "fr"), system_id_map=system_map)

    def progress(coll, game, i, total):
        print(f"[{coll}] {i}/{total} {game}", end="\r")

    results = scan_retrofe(root, all_collections, scraper, options, translator, progress)

    print()
    for name, stats in results.items():
        print(f"{name}: {stats.games_matched}/{stats.games_scanned} trouvés, "
              f"{stats.media_downloaded} médias, {stats.stories_written} descriptions "
              f"({stats.stories_translated} traduites)")
        for err in stats.errors[:5]:
            print("  !", err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
