## RetroFE-Scraper — le scraper qui manquait à RetroFE

Si tu utilises [RetroFE](https://retrofe.nl/) comme frontend pour ta collection
de jeux rétro, tu as sûrement remarqué qu'aucun scraper existant (Skraper,
Skyscraper, RetroScraper...) ne le connaît. Ils sont tous pensés pour
RetroPie, Recalbox, LaunchBox ou EmulationStation — RetroFE et sa structure
bien à lui (`settings.conf`, `medium_artwork/`, `meta.db`) restaient sur le
carreau.

**RetroFE-Scraper** comble ce manque : il scanne ta collection, va chercher
les jaquettes, logos, vidéos, captures d'écran et descriptions sur
ScreenScraper.fr, range tout au bon endroit, et corrige automatiquement les
`settings.conf` qui ne déclarent pas encore les médias présents.

**Ce qu'il fait en plus des autres :**
- **Traduction automatique dans la langue de ton choix.** Pas seulement le
  français — n'importe quelle langue prise en charge par DeepL ou
  LibreTranslate, configurable dans l'assistant.
- **32 types de médias**, pas juste jaquette + vidéo : logos (normal, HD,
  carbone, acier), cartouche/disque, manuel, figurine, mix Recalbox,
  pictogrammes, fan art, et plus.
- **Auto-réparation de `settings.conf`** : si un média est déjà sur le
  disque mais jamais déclaré, il ajoute la ligne qui va bien tout seul.
- **Interface graphique en assistant**, aucune ligne de commande requise :
  connexion -> détection -> association des systèmes -> options -> scan,
  avec suivi en direct.
- **Gratuit et open source** (licence MIT) — utilisable, modifiable et
  redistribuable librement.

**Pour commencer :** télécharge `RetroFE-Scraper.exe` (aucune installation
Python requise), ou clone le dépôt et lance `python gui_main.py`. Un compte
gratuit sur screenscraper.fr suffit — les identifiants développeur du
logiciel sont déjà intégrés.

Dépôt : [lien GitHub à ajouter]

Projet développé pour et par la communauté CORE TYPE R.
