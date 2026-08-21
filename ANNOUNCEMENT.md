## RetroFE-Scraper — the scraper RetroFE never had

If you use [RetroFE](https://retrofe.nl/) as your retro gaming frontend,
you've probably noticed that none of the existing scrapers (Skraper,
Skyscraper, RetroScraper...) know it exists. They're all built for RetroPie,
Recalbox, LaunchBox, or EmulationStation — RetroFE's own structure
(`settings.conf`, `medium_artwork/`, `meta.db`) was left out in the cold.

**RetroFE-Scraper** fills that gap: it scans your collection, fetches box
art, logos, videos, screenshots and descriptions from ScreenScraper.fr, puts
everything where it belongs, and automatically fixes `settings.conf` entries
that don't yet declare media that's already sitting on disk.

**What it does that others don't:**
- **Automatic translation into any language you want.** Not just French —
  any language supported by DeepL or LibreTranslate, configurable right in
  the wizard.
- **32 media types**, not just box art + video: logos (normal, HD, carbon,
  steel), cartridge/disc art, manuals, figurines, Recalbox mixes,
  pictograms, fan art, and more.
- **Self-healing `settings.conf`**: if a media file is already on disk but
  never declared, it adds the missing line automatically.
- **Graphical wizard**, no command line required: connect -> detect ->
  match systems -> options -> scan, with live progress.
- **Free and open source** (MIT license) — use it, modify it, redistribute
  it freely.

**Getting started:** download `RetroFE-Scraper.exe` (no Python install
needed), or clone the repo and run `python gui_main.py`. A free
screenscraper.fr account is all you need — the software's developer
credentials are already built in.

Repo: https://github.com/E3rek77/RetroFE-Scraper
Direct download (.exe, no Python needed): https://github.com/E3rek77/RetroFE-Scraper/releases/tag/v1.0.0

Built for and by the CORE TYPE R community.
