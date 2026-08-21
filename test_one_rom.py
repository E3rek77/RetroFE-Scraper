"""
Teste la recherche ScreenScraper sur UNE seule rom reelle de ta collection,
avec plusieurs combinaisons de parametres, pour voir laquelle fonctionne.
Beaucoup plus rapide qu'un scan complet pour deboguer.

Usage :
    python test_one_rom.py "D:\\CORE - TYPE R\\collections\\Nintendo Entertainment System\\roms\\NomDuFichier.zip" 3

Le deuxieme argument est le systemeid ScreenScraper (3 = NES).
"""
import json
import sys
import zlib

import requests

if len(sys.argv) < 3:
    print("Usage : python test_one_rom.py <chemin_rom> <systemeid>")
    sys.exit(1)

rom_path = sys.argv[1]
systemeid = sys.argv[2]

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
ss = config["screenscraper"]

import os
filename = os.path.basename(rom_path)
filesize = os.path.getsize(rom_path)

crc = 0
with open(rom_path, "rb") as f:
    while True:
        chunk = f.read(4 * 1024 * 1024)
        if not chunk:
            break
        crc = zlib.crc32(chunk, crc)
crc_hex = f"{crc & 0xFFFFFFFF:08X}"

print(f"Fichier : {filename}")
print(f"Taille  : {filesize} octets")
print(f"CRC32   : {crc_hex}")
print()

base_params = {
    "devid": ss["devid"], "devpassword": ss["devpassword"], "softname": ss["softname"],
    "ssid": ss["ssid"], "sspassword": ss["sspassword"], "output": "xml", "systemeid": systemeid,
}

essais = [
    ("nom seul", {"romnom": filename}),
    ("nom + taille", {"romnom": filename, "romtaille": str(filesize)}),
    ("crc seul", {"crc": crc_hex}),
    ("crc + nom + taille", {"crc": crc_hex, "romnom": filename, "romtaille": str(filesize)}),
]

for label, extra in essais:
    params = dict(base_params)
    params.update(extra)
    resp = requests.get("https://api.screenscraper.fr/api2/jeuInfos.php", params=params, timeout=20)
    found = "<jeu " in resp.text or "<jeu>" in resp.text
    print(f"--- {label} --- HTTP {resp.status_code} -- {'TROUVE' if found else 'PAS TROUVE'}")
    if not found:
        print("   ", resp.text[:300].replace("\n", " "))
    print()
