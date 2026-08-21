"""
Corrige les fichiers medias mal nommes en ".php" par une version anterieure
de RetroFE-Scraper (bug : l'extension etait devinee depuis l'URL
ScreenScraper, qui pointe toujours vers un endpoint "mediaJeu.php" quel que
soit le vrai type de fichier).

Ce script parcourt un dossier de collections RetroFE, trouve tous les
fichiers se terminant par ".php" dans medium_artwork/*/ et system_artwork/,
detecte le vrai type via la signature binaire du fichier (PNG/JPEG/GIF/WEBP/
BMP/MP4/PDF...), et renomme le fichier avec la bonne extension.

Usage :
    python fix_php_extensions.py "D:\\CORE - TYPE R\\collections"

Sans rien ecrire, pour verifier avant :
    python fix_php_extensions.py "D:\\CORE - TYPE R\\collections" --dry-run
"""
from __future__ import annotations

import os
import sys


def detect_ext(path: str):
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return None

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return ".gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head.startswith(b"BM"):
        return ".bmp"
    if head[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    if head[4:8] == b"ftyp":
        return ".mp4"
    if head.startswith(b"%PDF"):
        return ".pdf"
    return None


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if not args:
        print("Usage: python fix_php_extensions.py \"D:\\CORE - TYPE R\\collections\" [--dry-run]")
        sys.exit(1)

    root = args[0]
    fixed = 0
    unknown = 0
    scanned_dirs = 0

    for collection_name in sorted(os.listdir(root)):
        collection_path = os.path.join(root, collection_name)
        if not os.path.isdir(collection_path):
            continue
        for sub in ("medium_artwork", "system_artwork"):
            base = os.path.join(collection_path, sub)
            if not os.path.isdir(base):
                continue
            for dirpath, _dirnames, filenames in os.walk(base):
                scanned_dirs += 1
                for fname in filenames:
                    if not fname.lower().endswith(".php"):
                        continue
                    full = os.path.join(dirpath, fname)
                    ext = detect_ext(full)
                    if not ext:
                        print(f"  ? extension inconnue, ignore : {full}")
                        unknown += 1
                        continue
                    new_full = full[:-4] + ext  # retire ".php", ajoute la vraie extension
                    if os.path.exists(new_full):
                        print(f"  ! cible existe deja, ignore : {new_full}")
                        continue
                    print(f"  {fname} -> {os.path.basename(new_full)}")
                    if not dry_run:
                        os.rename(full, new_full)
                    fixed += 1

    print()
    print(f"Dossiers parcourus : {scanned_dirs}")
    print(f"Fichiers corriges  : {fixed}{' (simulation, rien ecrit)' if dry_run else ''}")
    print(f"Extensions inconnues (laissees en .php) : {unknown}")


if __name__ == "__main__":
    main()
