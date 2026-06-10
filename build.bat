@echo off
REM ============================================================
REM  build.bat — Compila Image Studio como .exe en Windows
REM ============================================================
REM Requisitos previos (ejecutar una vez):
REM   pip install pyinstaller
REM   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
REM   pip install -r requirements.txt
REM
REM Tesseract OCR (descargar e instalar antes de compilar):
REM   https://github.com/UB-Mannheim/tesseract/wiki
REM ============================================================

echo [1/3] Limpiando builds anteriores...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [2/3] Compilando con PyInstaller...
pyinstaller image_studio.spec

echo [3/3] Listo!
echo.
echo Distribuible en: dist\ImageStudio\
echo Ejecutar con:    dist\ImageStudio\ImageStudio.exe --help
pause
