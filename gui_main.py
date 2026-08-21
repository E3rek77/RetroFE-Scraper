"""Point d'entree de l'interface graphique RetroFE-Scraper.

Usage :
    python gui_main.py

C'est aussi le fichier cible pour PyInstaller (voir build_exe.bat).
"""
from gui.app import run

if __name__ == "__main__":
    run()
