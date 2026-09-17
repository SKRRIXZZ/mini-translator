@echo off
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul
if not errorlevel 1 set "PY=py"

%PY% -m PyInstaller --version >nul 2>nul
if errorlevel 1 %PY% -m pip install --upgrade pyinstaller

%PY% -c "import pystray, PIL" >nul 2>nul
if errorlevel 1 %PY% -m pip install --upgrade pystray Pillow

set "ICON="
if exist icon.ico set "ICON=--icon=icon.ico"

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name=MiniTranslator %ICON% --hidden-import=pystray._win32 --hidden-import=PIL._tkinter_finder --collect-all pystray --collect-all PIL mini_translator_multilang.pyw

echo.
echo DONE. See dist\MiniTranslator.exe
pause