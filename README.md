# Image Studio — Wildlife Camera Trap Classifier

App de escritorio para clasificar imágenes de trampas cámara usando YOLOv5 (MegaDetector).
Detecta animales, los clasifica según una zona dibujada por el usuario (bebedero o alambre)
y genera un CSV resumen.

## Modos de uso

| Modo | Entrada | Análisis | CSV de salida |
|---|---|---|---|
| **GUI — Bebedero** | Carpeta JPG/PNG | Animales dentro / fuera de zona rectangular | `Cant_total, Dentro_zona, Fuera_zona` |
| **GUI — Alambre** | Carpeta JPG/PNG | Animales a izquierda / derecha de una línea | `Cant_total, Lado_izquierdo, Lado_derecho` |
| **CLI** | Carpeta AVI | Detección + OCR (temperatura, ID cámara) | `Fecha, Camara_ID, Temp, Cant_animales` |

---

## Estructura del proyecto

```
Image-studio/
├── app.py                   # Entry point — app GUI
├── main.py                  # Entry point — modo CLI (AVI + OCR)
├── config.ini               # Configuración de cámaras, modelo y rutas
├── requirements.txt
├── install.sh               # Instalador Linux / WSL2
├── install.bat              # Instalador Windows
├── build.bat                # Compila el .exe con PyInstaller (Windows)
├── image_studio.spec        # Spec de PyInstaller
│
├── ui/
│   ├── main_window.py       # Ventana principal tkinter
│   └── zone_canvas.py       # Canvas interactivo para dibujar zona
│
├── src/
│   ├── zone.py              # BboxZone / LineZone — lógica de clasificación espacial
│   ├── spatial_analysis.py  # Centroide de bbox + clasificación por zona
│   ├── processor_gui.py     # Procesador por lotes para modo GUI
│   ├── processor.py         # Procesador para modo CLI (AVI + OCR)
│   ├── detector.py          # Wrapper YOLOv5 + conversión de detecciones
│   ├── bundle_utils.py      # Resolución de rutas dentro del bundle PyInstaller
│   ├── image_utils.py       # Recorte adaptativo de imagen por detección
│   ├── ocr_utils.py         # OCR de temperatura e ID desde overlay de cámara
│   └── video_utils.py       # Extracción de frames y EXIF de archivos AVI
│
├── utils/
│   └── detector_io.py       # Logs JSON y lista de archivos no procesados
│
├── model/                   # ← Poner aquí md_v5b.0.0.pt
└── norfair2/                # ← Copiar desde el Colab original (opcional)
```

---

## Instalación

### Linux / WSL2

```bash
# Dependencias del sistema
sudo apt install python3.12-tk tesseract-ocr

# Instalar todo (crea el venv automáticamente)
./install.sh
```

### Windows

```bat
install.bat
```

### Manual (cualquier plataforma)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# PyTorch CPU-only (evita descargar paquetes CUDA de 2 GB)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
```

### Archivos externos requeridos

```bash
# Modelo MegaDetector v5b
cp /ruta/colab/model/md_v5b.0.0.pt ./model/

# norfair2 personalizado (solo necesario para modo CLI con tracking)
cp -r /ruta/colab/norfair2 ./norfair2
```

> `norfair2` es opcional para la app GUI. Si no está, se usa un fallback interno automáticamente.

---

## Configuración

Editar `config.ini`:

```ini
[DEFAULT]
CAMARA_NAME        = Camara 1
BBDERO_NAME        = BBCORD_camara_1
CARPETA_ENTRADA    = /ruta/a/tus/videos
CARPETA_TEMPORAL   = ./temp
CARPETA_SALIDA     = clasificado
WEIGHT_MODEL_PATH  = ./model/md_v5b.0.0.pt
CONFIDENCE         = 45        # 0-100
IOU_THRESHOLD      = 45        # 0-100
VERBOSE            = True
```

Los bloques `[STEALTH_TEMP]`, `[STEALTH_CAM]`, `[BUSHNELL_TEMP]`, etc. definen las
coordenadas de recorte OCR para cada modelo de cámara.

---

## Uso — App GUI

```bash
python app.py
```

**Flujo:**
1. Seleccioná la carpeta con imágenes JPG/PNG
2. Elegí el modo: **Bebedero** o **Alambre**
3. Dibujá la zona sobre la primera imagen del folder
   - Bebedero: click + drag → rectángulo azul
   - Alambre: click P1 → click P2 → línea naranja
4. Presioná **▶ Procesar carpeta**
5. La barra de progreso muestra el avance imagen por imagen
6. Al finalizar: `resultado_clasificador.csv` guardado en la misma carpeta

---

## Uso — CLI (modo AVI + OCR)

```bash
python main.py                                          # usa config.ini
python main.py --config /ruta/config.ini --mode DEFAULT
python main.py --entrada /videos --confianza 50 --camara "Camara 2"
python main.py --help
```

**Salida:**
```
CARPETA_ENTRADA/clasificado/Camara 1/
├── con_animales/
├── sin_animales/
└── resultado_clasificador.csv
```

---

## Compilar como .exe standalone (Windows)

### Prerrequisitos

```bat
REM Instalar Tesseract OCR:
REM   https://github.com/UB-Mannheim/tesseract/wiki

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Compilar

```bat
build.bat
```

**Resultado:** `dist\ImageStudio\` — carpeta lista para distribuir (zipear y enviar).

```
dist\ImageStudio\
├── ImageStudio.exe     ← doble click para abrir
├── config.ini          ← editable por el usuario final sin recompilar
├── model\md_v5b.0.0.pt
└── ...
```

> Se usa `--onedir` en vez de `--onefile` porque PyTorch es grande (~300 MB)
> y el startup sería muy lento extrayendo a una carpeta temporal en cada ejecución.

### Bundlear Tesseract (distribución 100% standalone)

Descomentá las líneas `TESSERACT_DIR` en `image_studio.spec` apuntando al
directorio de instalación de Tesseract.

---

## Notas

- El modelo `md_v5b.0.0.pt` es [MegaDetector v5b](https://github.com/microsoft/CameraTraps) — detecta animal / persona / vehículo.
- Los archivos ya procesados (modo CLI) quedan en `temp/log_processed.json`; re-ejecutar no reprocesa los mismos videos.
- La zona dibujada en GUI se aplica a todas las imágenes de la carpeta (se asume cámara fija).
- El lado izquierdo/derecho (modo alambre) se calcula con producto vectorial del vector de la línea y el centroide del bbox detectado.
