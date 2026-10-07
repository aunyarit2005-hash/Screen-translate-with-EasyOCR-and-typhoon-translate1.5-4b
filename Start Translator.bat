@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -c "import easyocr, mss, PIL, requests" >nul 2>&1
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe setup_models.py
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe game_translator.py
if errorlevel 1 pause
