"""
Procesador para el modo GUI.
Recibe una carpeta con JPG/PNG, una zona ya definida y un modelo YOLO cargado.
Reporta progreso vía callback y devuelve un DataFrame con resultados.

Si la carpeta contiene un indice_trazabilidad.json generado por el CLI (Módulo 1),
las columnas seq_id, frame_segundo, video_origen, Fecha_hora, Temperatura y Camara_ID
se incorporan automáticamente al resultado.
"""

import json
import os
import shutil
from typing import Callable, Union

import pandas as pd
from PIL import Image

from src.detector import yolo_detections_to_norfair_detections
from src.spatial_analysis import classify_detections
from src.zone import BboxZone, LineZone, NoZone

TRACEABILITY_FILENAME = 'indice_trazabilidad.json'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}


def list_images(folder: str) -> list:
    files = []
    for fname in sorted(os.listdir(folder)):
        if os.path.splitext(fname)[1].lower() in IMAGE_EXTENSIONS:
            files.append(os.path.join(folder, fname))
    return files


def load_traceability_index(folder: str) -> dict:
    """
    Lee indice_trazabilidad.json de la carpeta.
    Devuelve dict keyed por nombre de imagen, o {} si no existe el índice.
    """
    path = os.path.join(folder, TRACEABILITY_FILENAME)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        return {e['imagen']: e for e in entries if 'imagen' in e}
    except Exception as e:
        print(f"[processor_gui] No se pudo leer índice de trazabilidad: {e}")
        return {}


def process_folder(
    folder: str,
    zone: Union[BboxZone, LineZone, NoZone],
    model,
    confidence: float,
    iou_threshold: float,
    camara_id: str = '',
    separate_folders: bool = False,
    on_progress: Callable[[int, int, str], None] = None,
) -> pd.DataFrame:
    """
    Procesa todas las imágenes de la carpeta y devuelve un DataFrame.

    - camara_id: ID de cámara ingresado manualmente (se usa si el índice no lo provee).
    - separate_folders: si True, copia imágenes a subcarpetas con_animales/ y sin_animales/.
    - on_progress(current, total, filename) se llama por cada imagen procesada.
    """
    image_files = list_images(folder)
    total = len(image_files)
    if total == 0:
        return pd.DataFrame()

    traceability = load_traceability_index(folder)
    has_traceability = bool(traceability)

    is_nozone = isinstance(zone, NoZone)
    is_bbox   = isinstance(zone, BboxZone)

    if is_nozone:
        zone_cols = []
    elif is_bbox:
        zone_cols = ['Dentro_zona', 'Fuera_zona']
    else:
        zone_cols = ['Lado_izquierdo', 'Lado_derecho']

    base_cols = ['seq_id', 'frame_segundo', 'video_origen', 'Imagen',
                 'Fecha_hora', 'Temperatura', 'Camara_ID', 'Cant_total'] if has_traceability \
               else ['Imagen', 'Camara_ID', 'Cant_total']
    columns = base_cols + zone_cols

    if separate_folders:
        carpeta_con = os.path.join(folder, 'con_animales')
        carpeta_sin = os.path.join(folder, 'sin_animales')
        os.makedirs(carpeta_con, exist_ok=True)
        os.makedirs(carpeta_sin, exist_ok=True)

    rows = []

    for i, img_path in enumerate(image_files):
        fname = os.path.basename(img_path)
        try:
            image = Image.open(img_path).convert('RGB')

            yolo_detections = model(
                image,
                conf_threshold=confidence,
                iou_threshold=iou_threshold,
                image_size=1280,
                classes=0,
            )
            detections = yolo_detections_to_norfair_detections(
                yolo_detections, track_points='bbox'
            )
            counts = classify_detections(detections, zone, confidence)

            if separate_folders:
                dest = carpeta_con if counts['total'] > 0 else carpeta_sin
                shutil.copy2(img_path, os.path.join(dest, fname))

            tdata = traceability.get(fname, {})
            effective_cam_id = tdata.get('camara_id') or camara_id

            if is_nozone:
                zone_values = []
            elif is_bbox:
                zone_values = [counts['dentro'], counts['fuera']]
            else:
                zone_values = [counts['izquierda'], counts['derecha']]

            if has_traceability:
                row = [
                    tdata.get('seq_id', ''),
                    tdata.get('frame_segundo', ''),
                    tdata.get('video_origen', ''),
                    fname,
                    tdata.get('fecha_hora', ''),
                    tdata.get('temperatura', ''),
                    effective_cam_id,
                    counts['total'],
                ] + zone_values
            else:
                row = [fname, effective_cam_id, counts['total']] + zone_values

            rows.append(row)

        except Exception as e:
            print(f"[processor_gui] Error en {fname}: {e}")
            tdata = traceability.get(fname, {}) if has_traceability else {}
            if has_traceability:
                row = [
                    tdata.get('seq_id', ''), tdata.get('frame_segundo', ''),
                    tdata.get('video_origen', ''), fname,
                    tdata.get('fecha_hora', ''), tdata.get('temperatura', ''),
                    tdata.get('camara_id') or camara_id,
                    0,
                ] + ([0, 0] if not is_nozone else [])
            else:
                row = [fname, camara_id, 0] + ([0, 0] if not is_nozone else [])
            rows.append(row)

        if on_progress:
            on_progress(i + 1, total, fname)

    return pd.DataFrame(rows, columns=columns)
