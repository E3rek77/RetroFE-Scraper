"""
Recherche un jeu connu sur ScreenScraper et liste TOUS les types de medias
renvoyes par l'API (attribut type="..." de chaque <media>). Sert a batir la
correspondance complete cote RetroFE-Scraper (SS_MEDIA_MAP).

Usage :
    python test_game_search.py
"""
import json
import xml.etree.ElementTree as ET

import requests

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

ss = config["screenscraper"]
params = {
    "devid": ss["devid"],
    "devpassword": ss["devpassword"],
    "softname": ss["softname"],
    "ssid": ss["ssid"],
    "sspassword": ss["sspassword"],
    "output": "xml",
    "systemeid": "3",       # NES chez ScreenScraper
    "romnom": "Super Mario Bros.zip",
}

resp = requests.get("https://api.screenscraper.fr/api2/jeuInfos.php", params=params, timeout=20)
print("Code HTTP :", resp.status_code)

if resp.status_code != 200:
    print(resp.text[:1000])
    raise SystemExit(1)

root = ET.fromstring(resp.text)
jeu = root.find("jeu")
if jeu is None:
    print("Jeu non trouve. Reponse brute :")
    print(resp.text[:2000])
    raise SystemExit(1)

noms = jeu.find("noms")
titre = noms.findtext("nom_us") if noms is not None else "?"
print(f"\nJeu trouve : {titre}\n")

medias = jeu.find("medias")
if medias is None:
    print("Aucun bloc <medias>.")
    raise SystemExit(0)

print("=== Types de medias disponibles pour ce jeu ===")
seen = set()
for media_el in medias.findall("media"):
    t = media_el.get("type")
    region = media_el.get("region", "")
    fmt = media_el.get("format", "")
    if t and t not in seen:
        seen.add(t)
        print(f"  type={t!r}  region={region!r}  format={fmt!r}")

print(f"\n{len(seen)} types uniques trouves.")
