"""
Rapport de scan RetroFE - outil en ligne de commande.

Usage:
    python cli_report.py "D:\CORE - TYPE R"

Scanne toutes les collections détectées, affiche pour chacune :
  - le nombre de roms trouvées
  - si le dossier de roms existe bien
  - quelles médias (logo, video, bezel...) sont actifs dans settings.conf
  - une estimation "prêt à scraper" oui/non
"""
from __future__ import annotations

import os
import sys

from core.retrofe_scanner import find_retrofe_root, scan_collections, count_roms


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python cli_report.py <dossier racine RetroFE ou sous-dossier>")
        return 1

    start = argv[1]
    root = find_retrofe_root(start)
    if not root:
        print(f"Impossible de trouver une racine RetroFE depuis: {start}")
        return 1

    print(f"Racine RetroFE détectée : {root}\n")
    collections = scan_collections(root)
    print(f"{len(collections)} collections avec settings.conf trouvées.\n")

    print(f"{'Collection':<38} {'Roms OK':<9} {'Roms#':>7}  {'Médias actifs':<40}")
    print("-" * 100)

    ready, total_roms = 0, 0
    for c in sorted(collections, key=lambda x: x.name):
        roms_ok = bool(c.roms_path and os.path.isdir(c.roms_path))
        n = count_roms(c) if roms_ok else 0
        total_roms += n
        media_keys = ", ".join(k.replace("media.", "") for k in c.media_map) or "(aucun actif)"
        if roms_ok:
            ready += 1
        print(f"{c.name:<38} {'oui' if roms_ok else 'NON':<9} {n:>7}  {media_keys:<40}")

    print("-" * 100)
    print(f"\n{ready}/{len(collections)} collections avec un dossier de roms valide.")
    print(f"Total roms détectées (approx.) : {total_roms}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
