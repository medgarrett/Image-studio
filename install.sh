#!/usr/bin/env bash
# ============================================================
#  install.sh — Instala todas las dependencias (Linux / WSL2 / Mac)
# ============================================================
set -e

VENV_DIR=".venv"

echo "==> Creando entorno virtual en $VENV_DIR ..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> Actualizando pip ..."
pip install --upgrade pip

# Paso 1: PyTorch CPU-only desde el índice oficial de PyTorch
# Esto evita descargar los paquetes CUDA (nvidia_cudnn, etc. > 2 GB)
echo "==> Instalando PyTorch CPU-only ..."
pip install torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu \
    --timeout 300

# Paso 2: Resto de dependencias (torch ya está resuelto, pip no lo toca)
echo "==> Instalando dependencias del proyecto ..."
pip install -r requirements.txt --timeout 120

echo ""
echo "Instalación completada."
echo "Para activar el entorno: source $VENV_DIR/bin/activate"
echo "Para ejecutar:           python main.py --help"
