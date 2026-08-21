"""
Petit script de test de connexion a l'API ScreenScraper.
A lancer directement chez toi (PC Windows), pas dans le sandbox de Claude
qui n'a pas acces reseau vers cette API.

Utilisation :
    pip install -r requirements.txt
    python test_connexion.py
"""
import json
import sys

import requests

from core.scrapers.screenscraper import ScreenScraperClient, ScreenScraperCredentials

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

ss_conf = config["screenscraper"]

print("=== Test 1 : identifiants (ssuserInfos.php) ===")
params = {
    "devid": ss_conf["devid"],
    "devpassword": ss_conf["devpassword"],
    "softname": ss_conf["softname"],
    "ssid": ss_conf["ssid"],
    "sspassword": ss_conf["sspassword"],
    "output": "json",
}
try:
    resp = requests.get("https://api.screenscraper.fr/api2/ssuserInfos.php", params=params, timeout=20)
    print("Code HTTP :", resp.status_code)
    print(resp.text[:1500])
    if resp.status_code == 200 and "ssuser" in resp.text.lower():
        print("\n--> OK, les identifiants sont acceptes par ScreenScraper.")
    else:
        print("\n--> Reponse inattendue, regarde le texte ci-dessus (identifiants refuses ?).")
except requests.RequestException as e:
    print("ERREUR reseau :", e)
    sys.exit(1)

print("\n=== Test 2 : liste des systemes (via le client du projet) ===")
creds = ScreenScraperCredentials(
    devid=ss_conf["devid"],
    devpassword=ss_conf["devpassword"],
    softname=ss_conf["softname"],
    ssid=ss_conf["ssid"],
    sspassword=ss_conf["sspassword"],
)
client = ScreenScraperClient(creds)
systems = client.fetch_systems_list()
print(f"{len(systems)} systemes recuperes.")
if systems:
    apercu = list(systems.items())[:5]
    for sid, name in apercu:
        print(f"  {sid} -> {name}")
    print("\n--> OK, le client du projet fonctionne correctement.")
else:
    print("\n--> Aucun systeme recupere, quelque chose ne va pas (voir Test 1 ci-dessus).")
