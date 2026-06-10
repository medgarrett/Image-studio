# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

App de escritorio para clasificar imágenes de **trampas cámara de fauna silvestre**.
Detecta animales con YOLOv5 (MegaDetector v5b) y los clasifica según una zona definida
por el usuario. Originado como migración de un notebook Google Colab.

## Comandos de desarrollo

```bash
# Primera instalación (Windows) — crea .venv y descarga torch CPU-only
install.bat

# Activar el entorno virtual
.venv\Scripts\activate

# Ejecutar la GUI directamente
python app.py

# Ejecutar el CLI (AVI → frames → OCR → YOLO → CSV)
python main.py --help
python main.py --config config.ini --entrada /ruta/videos --camara "Camara 1"

# Compilar el .exe (limpia builds anteriores y llama a pyinstaller)
build.bat
# O directamente:
pyinstaller image_studio.spec --noconfirm
```

`torch` y `torchvision` deben instalarse **antes** que el resto con:
```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
Si se instala desde PyPI sin ese flag, pip descarga paquetes CUDA (~2 GB).
`requirements.txt` excluye torch a propósito.

## Dos modos de uso

| Entry point | Modo | Entrada | Salida |
|---|---|---|---|
| `app.py` | GUI tkinter | JPG / PNG en carpeta | CSV con conteos por zona |
| `main.py` | CLI | AVI (extrae frames + OCR) | CSV + carpetas `con_animales` / `sin_animales` |

## Stack

- **Detección**: YOLOv5 via `yolov5` pip package, clase `0` = animal
- **Tracking** (CLI): `norfair2/` — copia local modificada de Norfair, carpeta no incluida en repo
- **OCR** (CLI): `pytesseract` + `cv_algorithms.zhang_suen` para leer overlay de temperatura/ID
- **GUI**: `tkinter` + `Pillow/ImageTk`
- **Modelo**: `model/md_v5b.0.0.pt` — MegaDetector, no incluido en repo
- **Python**: 3.13, venv en `.venv/`

## Archivos clave

| Archivo | Propósito |
|---|---|
| `ui/main_window.py` | Ventana principal: selector de carpeta, modos, barra de progreso |
| `ui/zone_canvas.py` | Canvas interactivo: dibuja bbox (bebedero) o línea (alambre) |
| `src/zone.py` | `BboxZone` y `LineZone` con método `classify(cx, cy)` |
| `src/spatial_analysis.py` | `classify_detections()` — centroide de cada bbox vs zona |
| `src/processor_gui.py` | Procesador por lotes para GUI, callback de progreso |
| `src/processor.py` | Pipeline CLI: AVI → frame → OCR → YOLO → CSV |
| `src/detector.py` | Wrapper `YOLO` + `yolo_detections_to_norfair_detections()` |
| `src/bundle_utils.py` | `bundled_path()` — resuelve rutas dentro del bundle PyInstaller |
| `config.ini` | Configuración de rutas, modelo, coordenadas OCR por modelo de cámara |
| `utils/detector_io.py` | Logs JSON de archivos ya procesados |

## Convenciones importantes

### norfair2 es opcional
`src/detector.py` intenta `from norfair2 import Detection` y si falla usa un
dataclass fallback interno con la misma interfaz (`.points`, `.scores`).
No romper esa lógica.

### Coordenadas de zona en imagen original
`ZoneCanvas` trabaja en coordenadas de pantalla (canvas escalado) pero siempre
convierte a coordenadas de la imagen original antes de guardar la zona.
La conversión es: `img_x = (canvas_x - offset_x) / scale`.

### Procesamiento en thread separado
`MainWindow._process_thread()` corre en un `threading.Thread` y comunica con la UI
via `queue.Queue` + `self.after(100, self._poll_queue)`.
**Nunca tocar widgets tkinter desde el thread de procesamiento.**

### torch.load con weights_only=False
PyTorch >= 2.6 cambió el default de `weights_only` a `True`, bloqueando las clases
custom de YOLOv5. `src/detector.py` parchea `torch.load` para forzar `False`.
No revertir ese parche.

## Lógica de clasificación espacial

**BboxZone (bebedero):**
El centroide del bbox detectado cae dentro del rectángulo dibujado → `'dentro'`, sino → `'fuera'`.

**LineZone (alambre):**
Producto vectorial del vector de la línea y el vector al centroide:
```python
sign = (x2 - x1) * (cy - y1) - (y2 - y1) * (cx - x1)
# sign > 0 → 'izquierda' | sign < 0 → 'derecha'
```

## CSV de salida

GUI Bebedero: `Imagen, Cant_total, Dentro_zona, Fuera_zona`
GUI Alambre:  `Imagen, Cant_total, Lado_izquierdo, Lado_derecho`
CLI:          `Fecha, Marca Camara, Camara ID, Temperatura, Nombre_carpeta, Subcarpeta, Imagen, Cant_animales`

## Compilación .exe (PyInstaller)

`image_studio.spec` + `build.bat` — PyInstaller `--onedir` desde Windows.
Entry point del bundle: `app.py` (GUI), `console=False`.
El modelo y `config.ini` se incluyen en el bundle como `datas`.

### Restricciones críticas del spec

**UPX desactivado** (`upx=False` en EXE y COLLECT): UPX corrompe los DLL nativos de
torch/numpy/cv2 causando `ERROR_DLL_INIT_FAILED (1114)`.

**VC++ runtime DLLs excluidos del bundle**: PyInstaller copia `msvcp140.dll`,
`vcruntime140.dll` y `vcruntime140_1.dll` desde la instalación de Python. Al estar
en `_internal/` (registrado con `AddDllDirectory`), se cargan antes que los de
`System32` causando un mismatch de versión con `c10.dll`. Se filtran de `a.binaries`
después del Analysis en el spec.

**matplotlib no se puede excluir**: `yolov5/utils/metrics.py` lo importa a nivel de
módulo. Si está en `excludes`, el bundle falla al iniciar.

**`collect_submodules('pandas')` incluye todos los tests de pandas** (~1500 módulos
extra). En el spec se enumeran solo los subpaquetes necesarios para producción.

## Lo que NO está implementado todavía

- Recorte individual por animal detectado (`recorte_imagen` existe pero está comentado)
- OCR de timestamp (columna `Fecha` siempre vacía en el CLI)
- Soporte de subcarpetas en GUI
- Detección de especie (MegaDetector solo clasifica animal/persona/vehículo)
