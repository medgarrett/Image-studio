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
import re
import shutil
from typing import Callable, Union

import cv2
import numpy as np
import pandas as pd
from PIL import Image

from src.detector import yolo_detections_to_norfair_detections
from src.spatial_analysis import classify_detections
from src.zone import BboxZone, LineZone, NoZone

TRACEABILITY_FILENAME = 'indice_trazabilidad.json'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

def _draw_detections(pil_image, yolo_detections, confidence_threshold: float):
    """Dibuja bounding boxes y confianza (2 decimales) sobre la imagen para cada detección."""
    img_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    color = (0, 230, 118)  # verde

    for det in yolo_detections.xyxy[0]:
        x1, y1, x2, y2, conf, cls = det.tolist()
        if conf < confidence_threshold or int(cls) != 0:
            continue
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)

        label = f"{conf:.2f}"
        (lw, lh), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(img_bgr, (x1, y1 - lh - bl - 4), (x1 + lw + 4, y1), color, -1)
        cv2.putText(img_bgr, label, (x1 + 2, y1 - bl - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)

    return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))


def _read_overlay(pil_image) -> tuple:
    """
    Lee hora, fecha y temperatura del overlay inferior de una imagen de trampa cámara.
    Recorta el 10% inferior (barra negra con texto blanco), corre OCR y parsea con regex.
    Devuelve (hora, fecha, temperatura). Vacíos si tesseract no está disponible o falla.
    """
    try:
        import pytesseract
        from src.bundle_utils import bundled_path
        # En el bundle el exe está en tesseract/tesseract.exe; en desarrollo usa la instalación del sistema
        candidate = bundled_path('tesseract', 'tesseract.exe')
        if not os.path.isfile(candidate):
            candidate = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = candidate
        # Apuntar tessdata al bundle si existe
        tessdata = bundled_path('tessdata')
        if os.path.isdir(tessdata):
            os.environ.setdefault('TESSDATA_PREFIX', tessdata)

        img = np.array(pil_image)
        h, w = img.shape[:2]

        bar_h = max(int(h * 0.10), 40)
        bar = img[h - bar_h:h, :]

        gray = cv2.cvtColor(bar, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)
        # Escalar 2× para mejorar detección de caracteres pequeños
        big = cv2.resize(thresh, (w * 2, bar_h * 2), interpolation=cv2.INTER_LINEAR)

        text = pytesseract.image_to_string(big, config='--psm 6').strip()

        hora_m  = re.search(r'\d{1,2}:\d{2}', text)
        fecha_m = re.search(r'\d{1,2}/\d{1,2}/\d{4}', text)
        hora  = hora_m.group(0).strip()  if hora_m  else ''
        fecha = fecha_m.group(0).strip() if fecha_m else ''

        # Temperatura: "12 °C", "-5C", "12C", etc.
        tmp = re.search(r'-?\d+\s*[°oO]?\s*C\b', text, re.IGNORECASE)
        temperatura = tmp.group(0).strip() if tmp else ''

        return hora, fecha, temperatura
    except Exception:
        return '', '', ''


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
    show_bbox: bool = False,
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
               else ['Imagen', 'Hora', 'Fecha', 'Temperatura', 'Camara_ID', 'Cant_total']
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
                dest_path = os.path.join(dest, fname)
                if show_bbox:
                    _draw_detections(image, yolo_detections, confidence).save(dest_path)
                else:
                    shutil.copy2(img_path, dest_path)

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
                hora, fecha, temperatura = _read_overlay(image)
                row = [fname, hora, fecha, temperatura, effective_cam_id, counts['total']] + zone_values

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
                row = [fname, '', '', '', camara_id, 0] + ([0, 0] if not is_nozone else [])
            rows.append(row)

        if on_progress:
            on_progress(i + 1, total, fname)

    return pd.DataFrame(rows, columns=columns)


# ── Procesamiento de videos ───────────────────────────────────────────────────

VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mov', '.mkv'}


def parse_frames(frames_str: str) -> list:
    """Convierte '5, 100, 300' en [5, 100, 300] (ordenado, enteros, sin duplicados)."""
    result = set()
    for token in frames_str.split(','):
        token = token.strip()
        if token:
            try:
                result.add(int(float(token)))
            except ValueError:
                pass
    return sorted(result)


def list_videos(folder: str) -> list:
    files = []
    for fname in sorted(os.listdir(folder)):
        if os.path.splitext(fname)[1].lower() in VIDEO_EXTENSIONS:
            files.append(os.path.join(folder, fname))
    return files


def extract_frame_at_index(video_path: str, frame_index: int):
    """Extrae el frame número frame_index del video. Devuelve PIL Image o None."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(frame_rgb)


def process_videos_folder(
    folder: str,
    zone,
    model,
    confidence: float,
    iou_threshold: float,
    seconds: list,
    camara_id: str = '',
    separate_folders: bool = False,
    show_bbox: bool = False,
    on_progress: Callable[[int, int, str], None] = None,
) -> pd.DataFrame:
    """
    Procesa todos los videos de la carpeta.
    Extrae frames en los segundos indicados, los clasifica y devuelve un DataFrame.
    Los frames se guardan como {video}_{segundo}.jpg en la misma carpeta.
    Siempre crea subcarpetas con_animales/ y sin_animales/ para los frames extraídos.
    El CSV se guarda automáticamente como resultados_video.csv en la misma carpeta.
    """
    video_files = list_videos(folder)
    if not video_files or not seconds:
        return pd.DataFrame()

    is_nozone = isinstance(zone, NoZone)
    is_bbox = isinstance(zone, BboxZone)

    if is_nozone:
        zone_cols = []
    elif is_bbox:
        zone_cols = ['Dentro_zona', 'Fuera_zona']
    else:
        zone_cols = ['Lado_izquierdo', 'Lado_derecho']

    columns = ['Video', 'Frame', 'Imagen', 'Hora', 'Fecha', 'Temperatura', 'Camara_ID', 'Cant_total'] + zone_cols

    # Siempre separar frames en con/sin animales
    carpeta_con = os.path.join(folder, 'con_animales')
    carpeta_sin = os.path.join(folder, 'sin_animales')
    os.makedirs(carpeta_con, exist_ok=True)
    os.makedirs(carpeta_sin, exist_ok=True)

    rows = []
    total = len(video_files) * len(seconds)
    current = 0
    skipped = []

    for video_path in video_files:
        video_fname = os.path.basename(video_path)
        video_stem = os.path.splitext(video_fname)[0]

        for frame_index in seconds:
            current += 1
            frame_name = f"{video_stem}_{frame_index}.jpg"
            frame_path = os.path.join(folder, frame_name)

            try:
                image = extract_frame_at_index(video_path, frame_index)
                if image is None:
                    skipped.append(f"{video_fname} frame {frame_index} (fuera de rango o error de lectura)")
                    if on_progress:
                        on_progress(current, total, f"[omitido] {frame_name}")
                    continue

                yolo_detections = model(
                    image,
                    conf_threshold=confidence,
                    iou_threshold=iou_threshold,
                    image_size=1280,
                    classes=0,
                )
                detections = yolo_detections_to_norfair_detections(yolo_detections, track_points='bbox')
                counts = classify_detections(detections, zone, confidence)

                dest = carpeta_con if counts['total'] > 0 else carpeta_sin
                img_to_save = _draw_detections(image, yolo_detections, confidence) if show_bbox else image
                img_to_save.save(os.path.join(dest, frame_name), 'JPEG')

                if is_nozone:
                    zone_values = []
                elif is_bbox:
                    zone_values = [counts['dentro'], counts['fuera']]
                else:
                    zone_values = [counts['izquierda'], counts['derecha']]

                hora, fecha, temperatura = _read_overlay(image)
                row = [video_fname, frame_index, frame_name, hora, fecha, temperatura, camara_id, counts['total']] + zone_values
                rows.append(row)

            except Exception as e:
                print(f"[processor_gui] Error en {frame_name}: {e}")
                skipped.append(f"{frame_name}: {e}")

            if on_progress:
                on_progress(current, total, frame_name)

    if skipped:
        print(f"[processor_gui] Frames omitidos ({len(skipped)}): {skipped}")

    df = pd.DataFrame(rows, columns=columns)

    # Auto-guardar CSV en la carpeta procesada
    if not df.empty:
        csv_path = os.path.join(folder, 'resultados_video.csv')
        df.to_csv(csv_path, index=False)
        print(f"[processor_gui] CSV guardado en: {csv_path}")

    return df
