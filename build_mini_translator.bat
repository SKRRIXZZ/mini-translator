@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon=icon.ico --name=MiniTranslator "mini_translator_multilang.pyw"
echo.
echo Done: dist\MiniTranslator.exe
pause
