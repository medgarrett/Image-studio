# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec para Image Studio
#
# Generar el .exe desde Windows:
#   pip install pyinstaller
#   pyinstaller image_studio.spec
#
# Resultado: dist/ImageStudio/  (carpeta distribuible con el .exe adentro)

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# ── Recolectar datos e imports ocultos de las dependencias pesadas ────────────

torch_datas, torch_binaries, torch_hidden = collect_all('torch')
yolo_datas,  yolo_binaries,  yolo_hidden  = collect_all('yolov5')

# norfair2 es un paquete local — se incluye como datos
norfair_datas = [('norfair2', 'norfair2')]

# Modelo y configuración — se incluyen dentro del bundle
# El usuario puede reemplazar config.ini junto al .exe después de instalar
bundled_datas = [
    ('config.ini',          '.'),
    ('model/md_v5b.0.0.pt', 'model'),
]

TESSERACT_DIR = r'C:\Program Files\Tesseract-OCR'
tess_binaries = [(os.path.join(TESSERACT_DIR, 'tesseract.exe'), 'tesseract'),
                 (os.path.join(TESSERACT_DIR, 'libtesseract-5.dll'), 'tesseract')]
tess_datas    = [(os.path.join(TESSERACT_DIR, 'tessdata'), 'tessdata')]

all_datas    = (torch_datas + yolo_datas + norfair_datas +
                bundled_datas + tess_datas)
all_binaries = torch_binaries + yolo_binaries + tess_binaries
all_hidden   = (torch_hidden + yolo_hidden +
                collect_submodules('cv2') +
                collect_submodules('PIL') +
                # pandas: no incluir pandas.tests (son cientos de módulos de test
                # que no se usan en producción y multiplican el tiempo de análisis)
                ['pandas', 'pandas.core', 'pandas.io', 'pandas.io.formats',
                 'pandas.io.formats.style', 'pandas._libs'] +
                collect_submodules('pytesseract') +
                collect_submodules('exifread') +
                collect_submodules('ui') +
                collect_submodules('src'))

# ── Análisis ──────────────────────────────────────────────────────────────────

a = Analysis(
    ['app.py'],   # GUI entry point
    pathex=['.'],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['notebook', 'IPython', 'scipy', 'sklearn'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── Excluir DLLs del runtime VC++ del bundle ──────────────────────────────────
# PyInstaller las copia desde la instalación de Python 3.13, pero son una build
# diferente a la que espera torch/c10.dll. Al estar en _internal/ (un directorio
# registrado con AddDllDirectory) se cargan ANTES que las de System32, causando
# ERROR_DLL_INIT_FAILED (1114). Eliminarlas obliga a Windows a usar System32.
_VC_RUNTIME_DLLS = {
    'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll',
}
a.binaries = [
    (name, src, t) for name, src, t in a.binaries
    if os.path.basename(name).lower() not in _VC_RUNTIME_DLLS
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Ejecutable ────────────────────────────────────────────────────────────────

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # False = sin consola negra (app GUI)
    icon=None,              # Reemplazar con 'assets/icon.ico' si tenés ícono
)

# ── Carpeta de distribución (onedir, más rápido que onefile para ML) ──────────
# UPX está desactivado: comprime los .dll nativos de torch/numpy/cv2 y eso
# corrompe su rutina de inicialización (WinError 1114). No vale la pena para
# modelos de ML donde el .pt ya es el 95 % del tamaño total.

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ImageStudio',
)
