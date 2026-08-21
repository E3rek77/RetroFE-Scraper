"""
Palette et constantes visuelles pour l'interface "futuriste" de RetroFE-Scraper.
Fond très sombre presque noir, accents neon cyan/magenta, coins arrondis,
bordures lumineuses. Utilisé par toutes les vues de gui/app.py.
"""

# Fond
BG_MAIN = "#05070d"
BG_PANEL = "#0b1020"
BG_PANEL_2 = "#0f152b"
BG_INPUT = "#0d1224"

# Accents
CYAN = "#00e5ff"
CYAN_DIM = "#0a7f96"
MAGENTA = "#ff2fd6"
MAGENTA_DIM = "#7a1a6b"
GREEN_OK = "#39ff8f"
RED_ERR = "#ff3b5c"
AMBER = "#ffb84d"

# Texte
TEXT_MAIN = "#e6f7ff"
TEXT_DIM = "#6f88a8"
TEXT_TITLE = "#ffffff"

FONT_FAMILY = "Consolas"
FONT_FAMILY_UI = "Segoe UI"

TITLE_FONT = (FONT_FAMILY, 26, "bold")
SUBTITLE_FONT = (FONT_FAMILY_UI, 13)
STEP_LABEL_FONT = (FONT_FAMILY, 11, "bold")
BODY_FONT = (FONT_FAMILY_UI, 13)
MONO_FONT = (FONT_FAMILY, 11)
BUTTON_FONT = (FONT_FAMILY, 13, "bold")

CORNER_RADIUS = 10
BORDER_WIDTH = 1

STEP_NAMES = [
    "CONNEXION",
    "DETECTION",
    "SYSTEMES",
    "OPTIONS",
    "RECAP",
    "SCAN",
]
