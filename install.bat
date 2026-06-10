@echo off
REM ============================================================
REM  install.bat — Instala todas las dependencias (Windows)
REM ============================================================

echo [1/4] Creando entorno virtual...
python -m venv .venv
call .venv\Scripts\activate.bat

echo [2/4] Actualizando pip...
python -m pip install --upgrade pip

echo [3/4] Instalando PyTorch CPU-only (evita paquetes CUDA de 2 GB)...
pip install torch torchvision ^
    --index-url https://download.pytorch.org/whl/cpu ^
    --timeout 300

echo [4/4] Instalando dependencias del proyecto...
pip install -r requirements.txt --timeout 120

echo.
echo Instalacion completada.
echo Para activar el entorno: .venv\Scripts\activate
echo Para ejecutar:           python main.py --help
pause
