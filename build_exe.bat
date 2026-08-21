@echo off
REM Construit RetroFE-Scraper.exe (fenetre unique, sans console) via PyInstaller.
REM A lancer depuis le dossier du projet, apres avoir installe les dependances :
REM     pip install -r requirements.txt
REM     pip install pyinstaller

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller n'est pas installe. Lance d'abord :
    echo     pip install pyinstaller
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --noconfirm --onefile --windowed ^
    --name "RetroFE-Scraper" ^
    --icon "gui\assets\icon.ico" ^
    --collect-data customtkinter ^
    --add-data "gui\assets;gui\assets" ^
    --add-data "config.example.json;." ^
    --add-data "systems_map.example.json;." ^
    gui_main.py

echo.
echo Termine ! L'executable est dans dist\RetroFE-Scraper.exe
pause
