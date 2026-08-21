"""
Assistant graphique RetroFE-Scraper.

Enchaine : connexion ScreenScraper -> detection de l'installation RetroFE ->
association des systemes -> options -> recapitulatif -> scan avec suivi en
temps reel. Le tout habille en theme sombre "futuriste" (gui/theme.py).

Lancement : python gui_main.py
"""
from __future__ import annotations

import json
import os
import sys
import queue
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk


def resource_path(*parts: str) -> str:
    """Chemin vers un fichier de ressource (icone, etc.), que le script tourne
    normalement ou packagee en .exe via PyInstaller (sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)

from core.orchestrator import ScanOptions, scan_retrofe
from core.retrofe_scanner import find_retrofe_root, scan_collections, count_roms
from core.scrapers.screenscraper import ScreenScraperClient, ScreenScraperCredentials
from core.translate.manager import TranslationManager
from . import theme
from . import system_matcher

# Identifiants developpeur ScreenScraper enregistres pour le logiciel
# "RetroFE-Scraper" -- partages entre tous les utilisateurs de l'outil,
# comme le font Skyscraper/EmulationStation-DE. Chaque utilisateur fournit
# en plus SON PROPRE compte (ssid/sspassword), gratuit, sur screenscraper.fr.
DEFAULT_DEVID = "Thomas77"
DEFAULT_DEVPASSWORD = "7dWk7tGPbt9"
DEFAULT_SOFTNAME = "RetroFE-Scraper"

LANGUAGES = [
    ("fr", "Francais"), ("en", "Anglais"), ("es", "Espagnol"), ("de", "Allemand"),
    ("it", "Italien"), ("pt", "Portugais"), ("nl", "Neerlandais"), ("ja", "Japonais"),
    ("ru", "Russe"), ("pl", "Polonais"),
]

MEDIA_CHOICES = [
    ("logo", "Logo (wheel)"),
    ("logo_hd", "Logo HD"),
    ("logo_carbon", "Logo carbone"),
    ("logo_steel", "Logo acier"),
    ("artwork_front", "Jaquette (recto)"),
    ("artwork_back", "Jaquette (verso)"),
    ("artwork_side", "Jaquette (tranche)"),
    ("artwork_3d", "Jaquette 3D"),
    ("box_texture", "Texture de boite"),
    ("medium_front", "Boite (recto)"),
    ("medium_back", "Boite (verso)"),
    ("cartridge", "Cartouche / disque"),
    ("support_texture", "Texture cartouche"),
    ("video", "Video"),
    ("video_normalise", "Video normalisee"),
    ("screenshot", "Capture d'ecran"),
    ("screentitle", "Ecran titre"),
    ("fanart", "Fan art"),
    ("background", "Fond d'ecran"),
    ("marquee", "Marquee"),
    ("marquee_petit", "Marquee (petit)"),
    ("steamgrid", "SteamGrid"),
    ("manual", "Manuel (PDF)"),
    ("figurine", "Figurine"),
    ("mix_v1", "Mix Recalbox v1"),
    ("mix_v2", "Mix Recalbox v2"),
    ("picto_liste", "Pictogramme (liste)"),
    ("picto_mono", "Pictogramme (mono)"),
    ("picto_couleur", "Pictogramme (couleur)"),
    ("theme_pack", "Pack theme (zip)"),
    ("system_artwork", "Artwork systeme"),
    ("bezel", "Bezel"),
]
DEFAULT_MEDIA_KEYS = {key for key, _ in MEDIA_CHOICES}   # tout coche par defaut


def _mk_font(spec):
    return ctk.CTkFont(family=spec[0], size=spec[1], weight=spec[2] if len(spec) > 2 else "normal")


class GlowFrame(ctk.CTkFrame):
    """Panneau standard : fond legerement plus clair que le fond principal,
    bordure fine cyan, coins arrondis -- l'unite visuelle de base du theme."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.BG_PANEL)
        kwargs.setdefault("corner_radius", theme.CORNER_RADIUS)
        kwargs.setdefault("border_width", theme.BORDER_WIDTH)
        kwargs.setdefault("border_color", theme.CYAN_DIM)
        super().__init__(master, **kwargs)


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(
            master, text=text, font=_mk_font(theme.TITLE_FONT),
            text_color=theme.TEXT_TITLE, anchor="w", **kwargs,
        )


class SubText(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        kwargs.setdefault("text_color", theme.TEXT_DIM)
        super().__init__(master, text=text, font=_mk_font(theme.SUBTITLE_FONT), anchor="w", **kwargs)


class NeonButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", theme.CYAN_DIM)
        kwargs.setdefault("hover_color", theme.CYAN)
        kwargs.setdefault("text_color", theme.BG_MAIN)
        kwargs.setdefault("font", _mk_font(theme.BUTTON_FONT))
        kwargs.setdefault("corner_radius", theme.CORNER_RADIUS)
        kwargs.setdefault("height", 38)
        super().__init__(master, **kwargs)


class GhostButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", theme.BG_PANEL_2)
        kwargs.setdefault("text_color", theme.TEXT_DIM)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.TEXT_DIM)
        kwargs.setdefault("font", _mk_font(theme.BUTTON_FONT))
        kwargs.setdefault("corner_radius", theme.CORNER_RADIUS)
        kwargs.setdefault("height", 38)
        super().__init__(master, **kwargs)


class AppState:
    def __init__(self):
        self.devid = DEFAULT_DEVID
        self.devpassword = DEFAULT_DEVPASSWORD
        self.ssid = ""
        self.sspassword = ""
        self.scraper: Optional[ScreenScraperClient] = None

        self.retrofe_root: Optional[str] = None
        self.collections = []           # list[Collection]
        self.selected_names: set[str] = set()

        self.ss_systems: dict[str, str] = {}
        self.system_map: dict[str, str] = {}   # collection name -> systemeid

        self.target_lang = "fr"
        self.media_keys: set[str] = set(DEFAULT_MEDIA_KEYS)
        self.deepl_api_key = ""

        self.results = {}


class RetroFEScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.state_data = AppState()

        self.title("RetroFE-Scraper")
        self.geometry("1040x700")
        self.minsize(920, 620)
        self.configure(fg_color=theme.BG_MAIN)
        ctk.set_appearance_mode("dark")
        try:
            self.iconbitmap(resource_path("gui", "assets", "icon.ico"))
        except Exception:
            pass

        self._build_shell()
        self.steps = [
            StepConnexion, StepDetection, StepSystems, StepOptions, StepRecap, StepScan,
        ]
        self.current_index = 0
        self.current_frame: Optional[ctk.CTkFrame] = None
        self.goto(0)

    # ---- structure generale : sidebar + zone de contenu ----
    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, fg_color=theme.BG_PANEL, corner_radius=0, width=220)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            sidebar, text="RETROFE\nSCRAPER", font=_mk_font((theme.FONT_FAMILY, 20, "bold")),
            text_color=theme.CYAN, justify="left", anchor="w",
        )
        logo.pack(fill="x", padx=22, pady=(30, 4))
        ctk.CTkLabel(
            sidebar, text="v1.0 -- CORE TYPE R", font=_mk_font(theme.SUBTITLE_FONT),
            text_color=theme.TEXT_DIM, anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 30))

        self.step_labels = []
        for i, name in enumerate(theme.STEP_NAMES):
            row = ctk.CTkFrame(sidebar, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=6)
            dot = ctk.CTkLabel(row, text=f"{i+1:02d}", font=_mk_font((theme.FONT_FAMILY, 12, "bold")),
                                width=28, text_color=theme.TEXT_DIM)
            dot.pack(side="left")
            lbl = ctk.CTkLabel(row, text=name, font=_mk_font(theme.STEP_LABEL_FONT),
                                text_color=theme.TEXT_DIM, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self.step_labels.append((dot, lbl))

        self.content = ctk.CTkFrame(self, fg_color=theme.BG_MAIN, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=30, pady=26)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _refresh_sidebar(self):
        for i, (dot, lbl) in enumerate(self.step_labels):
            if i == self.current_index:
                dot.configure(text_color=theme.CYAN)
                lbl.configure(text_color=theme.CYAN, font=_mk_font((theme.FONT_FAMILY, 11, "bold")))
            elif i < self.current_index:
                dot.configure(text_color=theme.GREEN_OK)
                lbl.configure(text_color=theme.TEXT_MAIN, font=_mk_font(theme.STEP_LABEL_FONT))
            else:
                dot.configure(text_color=theme.TEXT_DIM)
                lbl.configure(text_color=theme.TEXT_DIM, font=_mk_font(theme.STEP_LABEL_FONT))

    def goto(self, index: int):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_index = index
        self._refresh_sidebar()
        cls = self.steps[index]
        self.current_frame = cls(self.content, self)
        self.current_frame.grid(row=0, column=0, sticky="nsew")

    def next_step(self):
        if self.current_index + 1 < len(self.steps):
            self.goto(self.current_index + 1)

    def prev_step(self):
        if self.current_index > 0:
            self.goto(self.current_index - 1)


class WizardStep(ctk.CTkFrame):
    """Base commune : titre, sous-titre, zone de contenu scrollable, barre
    de boutons Precedent/Suivant en bas."""

    TITLE = ""
    SUBTITLE = ""

    def __init__(self, master, app: RetroFEScraperApp):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        SectionTitle(self, self.TITLE).grid(row=0, column=0, sticky="w")
        if self.SUBTITLE:
            SubText(self, self.SUBTITLE).grid(row=1, column=0, sticky="w", pady=(2, 16))
        else:
            ctk.CTkLabel(self, text="", height=8).grid(row=1, column=0)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        self.body.grid_columnconfigure(0, weight=1)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew")
        self.btn_prev = GhostButton(nav, text="< PRECEDENT", width=150, command=self.on_prev)
        self.btn_prev.pack(side="left")
        self.btn_next = NeonButton(nav, text="SUIVANT >", width=150, command=self.on_next)
        self.btn_next.pack(side="right")
        if self.app.current_index == 0:
            self.btn_prev.configure(state="disabled")

        self.build()

    def build(self):
        pass

    def on_prev(self):
        self.app.prev_step()

    def on_next(self):
        self.app.next_step()


# ---------------------------------------------------------------- STEP 1 --
class StepConnexion(WizardStep):
    TITLE = "Connexion ScreenScraper"
    SUBTITLE = "Identifiants developpeur pre-remplis. Renseigne ton propre compte (gratuit sur screenscraper.fr)."

    def build(self):
        panel = GlowFrame(self.body)
        panel.pack(fill="x")
        panel.grid_columnconfigure(1, weight=1)

        st = self.app.state_data

        def row(r, label, var, show=None):
            ctk.CTkLabel(panel, text=label, font=_mk_font(theme.BODY_FONT),
                         text_color=theme.TEXT_MAIN).grid(row=r, column=0, sticky="w", padx=20, pady=10)
            entry = ctk.CTkEntry(panel, textvariable=var, fg_color=theme.BG_INPUT,
                                  border_color=theme.CYAN_DIM, text_color=theme.TEXT_MAIN,
                                  show=show, height=34)
            entry.grid(row=r, column=1, sticky="ew", padx=(0, 20), pady=10)
            return entry

        self.v_devid = tk.StringVar(value=st.devid)
        self.v_devpass = tk.StringVar(value=st.devpassword)
        self.v_ssid = tk.StringVar(value=st.ssid)
        self.v_sspass = tk.StringVar(value=st.sspassword)

        row(0, "Dev ID (logiciel)", self.v_devid)
        row(1, "Dev Password", self.v_devpass, show="*")
        ctk.CTkFrame(panel, fg_color=theme.CYAN_DIM, height=1).grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=6)
        row(3, "Ton pseudo ScreenScraper", self.v_ssid)
        row(4, "Ton mot de passe", self.v_sspass, show="*")

        test_row = ctk.CTkFrame(self.body, fg_color="transparent")
        test_row.pack(fill="x", pady=(16, 0))
        self.btn_test = NeonButton(test_row, text="TESTER LA CONNEXION", width=220, command=self.test_connexion)
        self.btn_test.pack(side="left")
        self.status_label = ctk.CTkLabel(test_row, text="", font=_mk_font(theme.BODY_FONT))
        self.status_label.pack(side="left", padx=16)

        link = ctk.CTkLabel(self.body, text="Pas de compte ? Inscription gratuite sur screenscraper.fr/membreinscription.php",
                             font=_mk_font(theme.SUBTITLE_FONT), text_color=theme.TEXT_DIM)
        link.pack(anchor="w", pady=(20, 0))

    def test_connexion(self):
        self.status_label.configure(text="Connexion en cours...", text_color=theme.AMBER)
        self.btn_test.configure(state="disabled")
        threading.Thread(target=self._do_test, daemon=True).start()

    def _do_test(self):
        creds = ScreenScraperCredentials(
            devid=self.v_devid.get().strip(), devpassword=self.v_devpass.get().strip(),
            softname=DEFAULT_SOFTNAME, ssid=self.v_ssid.get().strip(), sspassword=self.v_sspass.get().strip(),
        )
        client = ScreenScraperClient(creds)
        systems = client.fetch_systems_list()
        ok = len(systems) > 0
        self.after(0, lambda: self._on_test_done(ok, client, systems))

    def _on_test_done(self, ok: bool, client, systems):
        self.btn_test.configure(state="normal")
        if ok:
            self.status_label.configure(text=f"OK -- {len(systems)} systemes ScreenScraper detectes", text_color=theme.GREEN_OK)
            st = self.app.state_data
            st.devid, st.devpassword = self.v_devid.get().strip(), self.v_devpass.get().strip()
            st.ssid, st.sspassword = self.v_ssid.get().strip(), self.v_sspass.get().strip()
            st.scraper = client
            st.ss_systems = systems
        else:
            self.status_label.configure(text="Echec -- verifie tes identifiants", text_color=theme.RED_ERR)

    def on_next(self):
        st = self.app.state_data
        st.devid, st.devpassword = self.v_devid.get().strip(), self.v_devpass.get().strip()
        st.ssid, st.sspassword = self.v_ssid.get().strip(), self.v_sspass.get().strip()
        if st.scraper is None:
            creds = ScreenScraperCredentials(devid=st.devid, devpassword=st.devpassword,
                                              softname=DEFAULT_SOFTNAME, ssid=st.ssid, sspassword=st.sspassword)
            st.scraper = ScreenScraperClient(creds)
        super().on_next()


# ---------------------------------------------------------------- STEP 2 --
class StepDetection(WizardStep):
    TITLE = "Detection de l'installation RetroFE"
    SUBTITLE = "Choisis le dossier racine (celui qui contient collections/) puis coche les systemes a traiter."

    def build(self):
        st = self.app.state_data
        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.pack(fill="x")
        default_path = st.retrofe_root or (r"D:\CORE - TYPE R" if os.path.isdir(r"D:\CORE - TYPE R") else "")
        self.v_path = tk.StringVar(value=default_path)
        entry = ctk.CTkEntry(top, textvariable=self.v_path, fg_color=theme.BG_INPUT,
                              border_color=theme.CYAN_DIM, text_color=theme.TEXT_MAIN, height=36)
        entry.pack(side="left", fill="x", expand=True)
        GhostButton(top, text="PARCOURIR", width=120, command=self.browse).pack(side="left", padx=(10, 0))
        NeonButton(top, text="DETECTER", width=140, command=self.detect).pack(side="left", padx=(10, 0))

        status_row = ctk.CTkFrame(self.body, fg_color="transparent")
        status_row.pack(fill="x", pady=(10, 6))
        self.status_label = ctk.CTkLabel(status_row, text="", font=_mk_font(theme.BODY_FONT), text_color=theme.TEXT_DIM)
        self.status_label.pack(side="left")
        GhostButton(status_row, text="TOUT COCHER", width=110, height=26,
                    command=lambda: self._set_all(True)).pack(side="right", padx=(6, 0))
        GhostButton(status_row, text="TOUT DECOCHER", width=120, height=26,
                    command=lambda: self._set_all(False)).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(self.body, fg_color=theme.BG_PANEL,
                                                   corner_radius=theme.CORNER_RADIUS,
                                                   border_width=theme.BORDER_WIDTH, border_color=theme.CYAN_DIM)
        self.list_frame.pack(fill="both", expand=True)
        self.checks: dict[str, tk.BooleanVar] = {}

        if st.collections:
            self._populate(st.collections)

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.v_path.set(d)

    def detect(self):
        self.status_label.configure(text="Recherche en cours...", text_color=theme.AMBER)
        threading.Thread(target=self._do_detect, daemon=True).start()

    def _do_detect(self):
        path = self.v_path.get().strip()
        root = find_retrofe_root(path) if path else None
        if not root:
            self.after(0, lambda: self.status_label.configure(
                text="Racine RetroFE introuvable depuis ce chemin.", text_color=theme.RED_ERR))
            return
        collections = scan_collections(root)
        self.after(0, lambda: self._on_detected(root, collections))

    def _on_detected(self, root, collections):
        st = self.app.state_data
        st.retrofe_root = root
        st.collections = collections
        st.selected_names = {c.name for c in collections}
        self.status_label.configure(
            text=f"Racine trouvee : {root} -- {len(collections)} collections", text_color=theme.GREEN_OK)
        self._populate(collections)

    def _populate(self, collections):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.checks.clear()
        st = self.app.state_data
        for c in collections:
            n = count_roms(c)
            var = tk.BooleanVar(value=c.name in st.selected_names)
            self.checks[c.name] = var
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=3)
            cb = ctk.CTkCheckBox(row, text=f"{c.name}", variable=var, text_color=theme.TEXT_MAIN,
                                  fg_color=theme.CYAN_DIM, hover_color=theme.CYAN,
                                  font=_mk_font(theme.BODY_FONT))
            cb.pack(side="left")
            ctk.CTkLabel(row, text=f"{n} roms", text_color=theme.TEXT_DIM,
                         font=_mk_font(theme.SUBTITLE_FONT)).pack(side="right", padx=10)

    def _set_all(self, value: bool):
        for var in self.checks.values():
            var.set(value)

    def on_next(self):
        st = self.app.state_data
        st.selected_names = {name for name, var in self.checks.items() if var.get()}
        if not st.retrofe_root or not st.selected_names:
            self.status_label.configure(text="Detecte une racine et coche au moins un systeme.", text_color=theme.RED_ERR)
            return
        super().on_next()


# ---------------------------------------------------------------- STEP 3 --
class StepSystems(WizardStep):
    TITLE = "Association des systemes"
    SUBTITLE = "Correspondance automatique collection RetroFE <-> systeme ScreenScraper. Verifie/corrige si besoin."

    def build(self):
        self.rows: dict[str, dict] = {}
        self.list_frame = ctk.CTkScrollableFrame(self.body, fg_color=theme.BG_PANEL,
                                                   corner_radius=theme.CORNER_RADIUS,
                                                   border_width=theme.BORDER_WIDTH, border_color=theme.CYAN_DIM)
        self.list_frame.pack(fill="both", expand=True)
        self.status_label = ctk.CTkLabel(self.body, text="", font=_mk_font(theme.BODY_FONT), text_color=theme.TEXT_DIM)
        self.status_label.pack(anchor="w", pady=(8, 0))

        st = self.app.state_data
        if not st.ss_systems:
            self.status_label.configure(text="Recuperation de la liste des systemes ScreenScraper...", text_color=theme.AMBER)
            threading.Thread(target=self._fetch_systems, daemon=True).start()
        else:
            self._populate()

    def _fetch_systems(self):
        st = self.app.state_data
        systems = st.scraper.fetch_systems_list() if st.scraper else {}
        st.ss_systems = systems
        self.after(0, self._populate)

    def _populate(self):
        st = self.app.state_data
        if not st.ss_systems:
            self.status_label.configure(text="Impossible de recuperer la liste des systemes (verifie la connexion, etape 1).",
                                         text_color=theme.RED_ERR)
            return
        self.status_label.configure(text=f"{len(st.ss_systems)} systemes ScreenScraper disponibles.", text_color=theme.TEXT_DIM)

        names_by_id = st.ss_systems
        # ScreenScraper peut avoir plusieurs systemeid partageant le meme nom
        # affiche -- un simple dict {nom: id} ecraserait silencieusement les
        # doublons et ferait chercher sur le mauvais systeme. On distingue
        # chaque doublon en suffixant l'id ScreenScraper entre crochets.
        name_counts: dict[str, int] = {}
        for name in names_by_id.values():
            name_counts[name] = name_counts.get(name, 0) + 1

        display_by_id: dict[str, str] = {}
        for sid, name in names_by_id.items():
            display_by_id[sid] = name if name_counts[name] == 1 else f"{name} [{sid}]"
        id_by_display = {v: k for k, v in display_by_id.items()}
        display_values = ["(ignorer)"] + sorted(display_by_id.values())

        selected = [c for c in st.collections if c.name in st.selected_names]
        suggestions = system_matcher.build_system_map([c.name for c in selected], st.ss_systems)

        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows.clear()

        for c in selected:
            sug = suggestions.get(c.name, {"systemeid": "", "ss_name": "", "score": 0.0})
            existing_id = st.system_map.get(c.name, sug["systemeid"])
            existing_name = display_by_id.get(existing_id, "(ignorer)") if existing_id else "(ignorer)"

            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=4)
            row.grid_columnconfigure(0, weight=1)

            color = theme.GREEN_OK if sug["score"] >= 0.85 else (theme.AMBER if sug["score"] > 0 else theme.TEXT_DIM)
            ctk.CTkLabel(row, text=c.name, text_color=color, font=_mk_font(theme.BODY_FONT), anchor="w",
                         width=280).grid(row=0, column=0, sticky="w")

            var = tk.StringVar(value=existing_name)
            menu = ctk.CTkOptionMenu(row, values=display_values, variable=var, width=340,
                                      fg_color=theme.BG_INPUT, button_color=theme.CYAN_DIM,
                                      button_hover_color=theme.CYAN, text_color=theme.TEXT_MAIN,
                                      dropdown_fg_color=theme.BG_PANEL_2)
            menu.grid(row=0, column=1, sticky="e", padx=(10, 0))
            self.rows[c.name] = {"var": var, "id_by_display": id_by_display}

    def on_next(self):
        st = self.app.state_data
        mapping = {}
        for name, info in self.rows.items():
            chosen = info["var"].get()
            if chosen and chosen != "(ignorer)":
                mapping[name] = info["id_by_display"].get(chosen, "")
        st.system_map = mapping
        if not mapping:
            self.status_label.configure(text="Associe au moins un systeme avant de continuer.", text_color=theme.RED_ERR)
            return
        super().on_next()


# ---------------------------------------------------------------- STEP 4 --
class StepOptions(WizardStep):
    TITLE = "Options du scan"
    SUBTITLE = "Langue cible des descriptions, medias a telecharger, traduction."

    def build(self):
        st = self.app.state_data
        panel = GlowFrame(self.body)
        panel.pack(fill="x", pady=(0, 16))
        panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(panel, text="Langue cible des descriptions", font=_mk_font(theme.BODY_FONT),
                     text_color=theme.TEXT_MAIN).grid(row=0, column=0, sticky="w", padx=20, pady=16)
        lang_values = [f"{code} - {name}" for code, name in LANGUAGES]
        current = next((f"{c} - {n}" for c, n in LANGUAGES if c == st.target_lang), lang_values[0])
        self.v_lang = tk.StringVar(value=current)
        ctk.CTkOptionMenu(panel, values=lang_values, variable=self.v_lang, width=260,
                          fg_color=theme.BG_INPUT, button_color=theme.CYAN_DIM,
                          button_hover_color=theme.CYAN, dropdown_fg_color=theme.BG_PANEL_2
                          ).grid(row=0, column=1, sticky="w", padx=(0, 20))

        ctk.CTkLabel(panel, text="Cle API DeepL (optionnel)", font=_mk_font(theme.BODY_FONT),
                     text_color=theme.TEXT_MAIN).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        self.v_deepl = tk.StringVar(value=st.deepl_api_key)
        ctk.CTkEntry(panel, textvariable=self.v_deepl, fg_color=theme.BG_INPUT,
                    border_color=theme.CYAN_DIM, text_color=theme.TEXT_MAIN, width=260, height=32
                    ).grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(0, 20))

        media_header = ctk.CTkFrame(self.body, fg_color="transparent")
        media_header.pack(fill="x")
        ctk.CTkLabel(media_header, text=f"Medias a recuperer ({len(MEDIA_CHOICES)} types disponibles)",
                     font=_mk_font(theme.BODY_FONT), text_color=theme.TEXT_MAIN).pack(side="left")
        GhostButton(media_header, text="TOUT COCHER", width=110, height=26,
                    command=lambda: self._set_all(True)).pack(side="right", padx=(6, 0))
        GhostButton(media_header, text="TOUT DECOCHER", width=120, height=26,
                    command=lambda: self._set_all(False)).pack(side="right")

        media_panel = ctk.CTkScrollableFrame(self.body, fg_color=theme.BG_PANEL,
                                              corner_radius=theme.CORNER_RADIUS,
                                              border_width=theme.BORDER_WIDTH, border_color=theme.CYAN_DIM)
        media_panel.pack(fill="both", expand=True, pady=(8, 0))

        self.media_vars: dict[str, tk.BooleanVar] = {}
        for i, (key, label) in enumerate(MEDIA_CHOICES):
            var = tk.BooleanVar(value=key in st.media_keys)
            self.media_vars[key] = var
            cb = ctk.CTkCheckBox(media_panel, text=label, variable=var, text_color=theme.TEXT_MAIN,
                                  fg_color=theme.CYAN_DIM, hover_color=theme.CYAN,
                                  font=_mk_font(theme.BODY_FONT))
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=14, pady=8)

    def _set_all(self, value: bool):
        for var in self.media_vars.values():
            var.set(value)

    def on_next(self):
        st = self.app.state_data
        st.target_lang = self.v_lang.get().split(" - ")[0]
        st.deepl_api_key = self.v_deepl.get().strip()
        st.media_keys = {k for k, v in self.media_vars.items() if v.get()}
        super().on_next()


# ---------------------------------------------------------------- STEP 5 --
class StepRecap(WizardStep):
    TITLE = "Recapitulatif"
    SUBTITLE = "Verifie les parametres avant de lancer le scan."

    def build(self):
        st = self.app.state_data
        panel = GlowFrame(self.body)
        panel.pack(fill="both", expand=True)

        lines = [
            ("Racine RetroFE", st.retrofe_root or "-"),
            ("Systemes selectionnes", str(len(st.system_map))),
            ("Langue cible", st.target_lang),
            ("Medias", ", ".join(sorted(st.media_keys)) or "aucun"),
            ("Traduction", "DeepL + LibreTranslate (repli)" if st.deepl_api_key else "LibreTranslate uniquement"),
            ("Compte ScreenScraper", st.ssid or "-"),
        ]
        for i, (label, value) in enumerate(lines):
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(row, text=label, font=_mk_font(theme.BODY_FONT), text_color=theme.TEXT_DIM,
                         width=220, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, font=_mk_font(theme.BODY_FONT), text_color=theme.TEXT_MAIN,
                         anchor="w").pack(side="left", fill="x", expand=True)

        warn = ctk.CTkLabel(
            self.body, text="Le scan peut prendre longtemps selon le nombre de roms. "
                             "Les medias deja presents ne sont pas re-telecharges.",
            font=_mk_font(theme.SUBTITLE_FONT), text_color=theme.AMBER, wraplength=600, justify="left")
        warn.pack(anchor="w", pady=(16, 0))

    def on_next(self):
        self.app.next_step()
        # le lancement effectif se fait dans StepScan.build() (appele par goto)


# ---------------------------------------------------------------- STEP 6 --
class StepScan(WizardStep):
    TITLE = "Scan en cours"
    SUBTITLE = "Ne ferme pas cette fenetre pendant le scan."

    def build(self):
        self.btn_prev.configure(state="disabled")
        self.btn_next.configure(text="FERMER", command=self.app.destroy, state="disabled")

        self.overall_label = ctk.CTkLabel(self.body, text="Preparation...", font=_mk_font(theme.BODY_FONT),
                                           text_color=theme.CYAN)
        self.overall_label.pack(anchor="w")
        self.progress = ctk.CTkProgressBar(self.body, progress_color=theme.CYAN, fg_color=theme.BG_INPUT)
        self.progress.pack(fill="x", pady=(6, 16))
        self.progress.set(0)

        self.log = ctk.CTkTextbox(self.body, fg_color=theme.BG_PANEL, text_color=theme.TEXT_MAIN,
                                   font=_mk_font(theme.MONO_FONT), border_width=theme.BORDER_WIDTH,
                                   border_color=theme.CYAN_DIM, corner_radius=theme.CORNER_RADIUS)
        self.log.pack(fill="both", expand=True)
        self.log.insert("end", "Demarrage du scan...\n")

        self.msg_queue: "queue.Queue" = queue.Queue()
        threading.Thread(target=self._run_scan, daemon=True).start()
        self.after(150, self._poll_queue)

    def _run_scan(self):
        st = self.app.state_data
        translator = TranslationManager(
            deepl_api_key=st.deepl_api_key,
            libretranslate_url="https://libretranslate.com",
        )
        options = ScanOptions(target_lang=st.target_lang, system_id_map=st.system_map,
                               media_keys=tuple(st.media_keys))
        selected = [c for c in st.collections if c.name in st.system_map]

        def progress_cb(coll, game, i, total):
            self.msg_queue.put(("progress", coll, game, i, total))

        try:
            results = scan_retrofe(st.retrofe_root, selected, st.scraper, options, translator, progress_cb)
            st.results = results
            self.msg_queue.put(("done", results))
        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, coll, game, i, total = item
                    self.overall_label.configure(text=f"[{coll}] {i}/{max(total,1)} -- {game}")
                    if total:
                        self.progress.set(i / total)
                    if i == 1:
                        self.log.insert("end", f"\n--- {coll} ({total} roms) ---\n")
                        self.log.see("end")
                elif kind == "done":
                    self._on_done(item[1])
                    return
                elif kind == "error":
                    self.log.insert("end", f"\nERREUR FATALE : {item[1]}\n")
                    self.overall_label.configure(text="Erreur", text_color=theme.RED_ERR)
                    self.btn_next.configure(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _on_done(self, results):
        self.progress.set(1)
        self.overall_label.configure(text="Scan termine.", text_color=theme.GREEN_OK)
        self.log.insert("end", "\n=== RESUME ===\n")
        for name, stats in results.items():
            self.log.insert(
                "end",
                f"{name} : {stats.games_matched}/{stats.games_scanned} trouves, "
                f"{stats.media_downloaded} medias, {stats.stories_written} descriptions "
                f"({stats.stories_translated} traduites)\n",
            )
            for err in stats.errors[:5]:
                self.log.insert("end", f"  ! {err}\n")
        self.log.see("end")
        self.btn_next.configure(state="normal")


def run():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = RetroFEScraperApp()
    app.mainloop()
