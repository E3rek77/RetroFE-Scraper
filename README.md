# RetroFE-Scraper

Outil de scraping de médias et métadonnées pour [RetroFE](https://retrofe.nl/),
avec un accent particulier sur la traduction automatique dans la langue de
ton choix (pas seulement le français).

## Pourquoi ce projet ?

Les scrapers existants (Skraper, Skyscraper, RetroScraper...) supportent
Recalbox, RetroPie, LaunchBox, EmulationStation — mais aucun ne connaît la
structure de collections de RetroFE (`settings.conf`, `media.*`,
`medium_artwork/`, `meta.db`). Ce projet comble ce manque, et ajoute une
fonctionnalité que les autres outils n'ont pas : la **traduction automatique
configurable** des descriptions de jeux quand la langue voulue n'existe pas
côté scraper (français par défaut, mais n'importe quelle langue supportée
par DeepL/LibreTranslate).

## État actuel

- [x] Détection automatique d'une installation RetroFE
- [x] Lecture de toutes les collections + parsing de `settings.conf` —
      validé sur une installation réelle de 67 collections / ~76 000 roms
- [x] Invalidation automatique de `meta.db` après un scan
- [x] Auto-réparation de `settings.conf` : ajoute/décommente les lignes
      `media.*` manquantes dès qu'un dossier de médias existe réellement —
      validé et appliqué sur 63 collections réelles (le bug le plus courant :
      des médias déjà présents sur le disque mais jamais déclarés)
- [x] Téléchargement des médias vers la bonne arborescence par collection
- [x] Écriture des descriptions (`story.txt`) avec traduction automatique
      vers une langue cible configurable
- [x] Client API ScreenScraper.fr (recherche par CRC/nom, médias, description)
      — **écrit mais pas encore testé en conditions réelles**, en attente des
      identifiants développeur (demande postée sur le forum ScreenScraper)
- [x] Pipeline complet testé de bout en bout avec un scraper et un traducteur
      factices (aucun appel réseau requis pour valider la logique)
- [x] Identifiants développeur ScreenScraper obtenus et validés en conditions
      réelles (connexion + récupération de la liste des systèmes)
- [x] Reprise sur quota : progression mémorisée par collection
      (`.retrofe_scraper_cache.json`), un scan interrompu par le quota
      journalier ScreenScraper reprend exactement où il s'était arrêté sans
      reconsommer de quota pour ce qui est déjà traité
- [x] Interface graphique façon assistant, thème sombre/néon
      (`gui/`, lancée via `gui_main.py`)
- [x] Script de packaging en `.exe` Windows (`build_exe.bat`, PyInstaller)

## Interface graphique (recommandé)

```
pip install -r requirements.txt
python gui_main.py
```

L'assistant enchaîne : connexion ScreenScraper (identifiants développeur déjà
intégrés, il suffit de renseigner ton propre compte gratuit) -> détection de
l'installation RetroFE -> association automatique des systèmes -> choix de la
langue et des médias -> récapitulatif -> scan avec suivi en direct.

Pour construire un `.exe` autonome (Windows, aucune installation Python
requise pour l'utilisateur final) :

```
pip install pyinstaller
build_exe.bat
```

L'exécutable est généré dans `dist\RetroFE-Scraper.exe`.

## Ligne de commande

Rapport de scan (aucune dépendance, fonctionne tout de suite) :

```
python cli_report.py "D:\CORE - TYPE R"
```

Scan complet avec scraping (nécessite `pip install -r requirements.txt` et
des identifiants ScreenScraper dans `config.json`, voir `config.example.json`) :

```
python cli_scrape.py "D:\CORE - TYPE R" --config config.json --collection "Nintendo 64"
```

Il faut aussi remplir `systems_map.json` (copie de `systems_map.example.json`)
avec les identifiants de système ScreenScraper correspondant à chaque
collection RetroFE — `ScreenScraperClient.fetch_systems_list()` permet de
récupérer la liste officielle une fois les identifiants obtenus.

## Structure du projet

```
core/
  models.py                 modèles de données (Collection, RomFile)
  retrofe_scanner.py        détection racine RetroFE + parsing settings.conf
  media_writer.py           écriture médias + auto-réparation settings.conf
  story_writer.py           écriture story.txt + traduction
  db_cache.py                invalidation meta.db
  orchestrator.py           pipeline complet (scan -> scrape -> écrit -> traduit)
  scrapers/
    base.py                  interface commune
    screenscraper.py          client ScreenScraper.fr
  translate/
    base.py, manager.py, deepl_translator.py, libretranslate_translator.py
gui/
  app.py                     assistant graphique (customtkinter, thème néon)
  theme.py                    couleurs/polices du thème
  system_matcher.py           association auto collection <-> système ScreenScraper
  assets/icon.ico               icône de l'application
gui_main.py                  point d'entrée de l'interface graphique
build_exe.bat                packaging en .exe Windows (PyInstaller)
test_connexion.py            script de test rapide des identifiants ScreenScraper
cli_report.py                rapport de scan en ligne de commande
cli_scrape.py                 scan complet avec scraping
config.example.json           config à copier en config.json
systems_map.example.json      table collection -> systemeid ScreenScraper
```

## Licence

MIT — libre d'utilisation, modification et redistribution pour la
communauté RetroFE.
