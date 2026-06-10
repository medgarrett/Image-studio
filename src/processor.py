import json
import os
import pathlib
import cv2
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw

from src.detector import YOLO, yolo_detections_to_norfair_detections
from src.image_utils import (
    definir_puntos_recorte,
    crear_lista_booleanos,
    actualizar_lista_booleanos,
)
from src.ocr_utils import read_stealth_cam_metadata, read_bushnell_metadata, read_stealth_cam_datetime
from src.video_utils import extract_frames_at_times, get_video_duration
from utils.detector_io import (
    check_log_file,
    check_file_empty,
    read_log_file,
    create_log_file,
    update_log_file,
    check_processed_raw_files_v2,
)

TRACEABILITY_FILENAME = 'indice_trazabilidad.json'
CSV_COLUMNS = [
    'seq_id', 'frame_segundo', 'video_origen', 'Imagen',
    'Fecha_hora', 'Temperatura', 'Camara_ID', 'Marca_Camara',
    'Nombre_carpeta', 'Cant_animales',
]


def _ensure_dirs(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _init_log(filepath, verbose):
    try:
        if check_log_file(filepath):
            if check_file_empty(filepath):
                return []
            data = read_log_file(filepath)
            if verbose:
                print(f"Log existente: {filepath} ({len(data)} entradas)")
            return data
        else:
            create_log_file(filepath, [])
            return []
    except Exception as e:
        print(f"[processor] Error inicializando log {filepath}: {e}")
        return []


def _build_extraction_times(config, mode, duration_seconds):
    """
    Devuelve lista de segundos a extraer según config.
    EXTRACTION_TIMESTAMPS tiene prioridad. Si está vacío, usa EXTRACTION_INTERVAL_SECONDS.
    """
    timestamps_str = config[mode].get('EXTRACTION_TIMESTAMPS', '').strip()
    if timestamps_str:
        return sorted(float(t.strip()) for t in timestamps_str.split(',') if t.strip())

    interval = float(config[mode].get('EXTRACTION_INTERVAL_SECONDS', '5'))
    times = []
    t = 0.0
    while t <= duration_seconds:
        times.append(t)
        t += interval
    return times


def _load_traceability(path):
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_traceability(path, entries):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def run(config, mode: str = 'DEFAULT'):
    now = datetime.now()
    verbose = config[mode].getboolean('VERBOSE', fallback=True)

    camara_name   = config[mode]['CAMARA_NAME']
    dir_entrada   = config[mode]['CARPETA_ENTRADA']
    dir_temp      = pathlib.Path(config[mode]['CARPETA_TEMPORAL'])
    carpeta_sal   = config[mode]['CARPETA_SALIDA']
    model_path    = config[mode]['WEIGHT_MODEL_PATH']
    confidence    = int(config[mode]['CONFIDENCE']) / 100.0
    iou_threshold = int(config[mode]['IOU_THRESHOLD']) / 100.0

    dir_salida   = os.path.join(dir_entrada, carpeta_sal, camara_name)
    dir_entrada  = os.path.join(dir_entrada, camara_name)
    dir_temp_str = str(dir_temp)

    carpeta_con   = os.path.join(dir_salida, 'con_animales')
    carpeta_sin   = os.path.join(dir_salida, 'sin_animales')
    log_proc_path = os.path.join(dir_temp_str, 'log_processed.json')
    traceability_path = os.path.join(dir_salida, TRACEABILITY_FILENAME)

    _ensure_dirs(dir_salida, dir_temp_str, carpeta_con, carpeta_sin)

    if not os.path.isdir(dir_entrada):
        print(f"[processor] Carpeta de entrada no encontrada: {dir_entrada}")
        return

    existing_log = _init_log(log_proc_path, verbose)
    # seq_id continúa desde el último video ya procesado
    next_seq_id = len(existing_log) + 1

    model = YOLO(model_path, device='cpu')

    new_files = check_processed_raw_files_v2(log_proc_path, dir_entrada)
    if not new_files:
        print("[processor] No hay archivos nuevos para procesar.")
        return

    print(f"[processor] {len(new_files)} archivo(s) nuevo(s) encontrado(s).")

    traceability = _load_traceability(traceability_path)
    lista_csv = []

    for (avi_path, file_size) in new_files:
        video_basename = os.path.basename(avi_path)
        video_stem = os.path.splitext(video_basename)[0]

        duration = get_video_duration(avi_path)
        times_to_extract = _build_extraction_times(config, mode, duration)

        if verbose:
            print(f"\nProcesando: {video_basename} ({duration:.1f}s)")
            print(f"  Extrayendo en segundos: {times_to_extract}")

        frames = extract_frames_at_times(avi_path, times_to_extract)

        if not frames:
            print(f"[processor] No se pudo extraer ningún frame de {avi_path}")
            update_log_file(log_proc_path, [(str(pathlib.PureWindowsPath(avi_path)), file_size)])
            next_seq_id += 1
            continue

        seq_id = next_seq_id
        next_seq_id += 1

        # OCR del primer frame para metadatos del video
        tag_marca_cam = 'Stealth Cam'
        tag_temp = ''
        tag_cam_id = ''
        tag_fecha_hora = ''

        first_frame_bgr = frames[0][0]
        try:
            tag_temp, tag_cam_id = read_stealth_cam_metadata(first_frame_bgr, config)
            tag_fecha_hora = read_stealth_cam_datetime(first_frame_bgr, config)
        except Exception as ocr_err:
            print(f"[processor] OCR fallido: {ocr_err}")

        if verbose:
            print(f"  Temperatura: {tag_temp} | Camara ID: {tag_cam_id} | Fecha: {tag_fecha_hora}")

        # Procesar cada frame extraído
        for frame_bgr, t_seconds in frames:
            out_name = f"{seq_id:04d}_{int(t_seconds):03d}s_{video_stem}.png"

            image = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

            yolo_detections = model(
                image,
                conf_threshold=confidence,
                iou_threshold=iou_threshold,
                image_size=1280,
                classes=0,
            )
            detections = yolo_detections_to_norfair_detections(yolo_detections, track_points='bbox')

            cant_animales = 0
            detect_animal = False

            if detections:
                lista_booleanos = crear_lista_booleanos(detections)
                width, height = image.size
                draw = ImageDraw.Draw(image)

                for i, det in enumerate(detections):
                    if lista_booleanos[i]:
                        continue
                    if det.scores[0] > confidence:
                        cant_animales += 1
                        lx = int(det.points[0][0])
                        ly = int(det.points[0][1])

                        if width >= 1280 and height >= 1280:
                            pts = definir_puntos_recorte(lx, ly, width, height, 1280)
                            lista_booleanos = actualizar_lista_booleanos(
                                pts, detections, lista_booleanos, i
                            )

                        rect = [det.points[0][0], det.points[0][1],
                                det.points[1][0], det.points[1][1]]
                        draw.rectangle(rect, outline='red', width=4)
                        detect_animal = True

            dest_folder = carpeta_con if detect_animal else carpeta_sin
            image.save(os.path.join(dest_folder, out_name), optimize=True, quality=80)

            traceability.append({
                'seq_id': seq_id,
                'frame_segundo': t_seconds,
                'video_origen': video_basename,
                'imagen': out_name,
                'fecha_hora': tag_fecha_hora,
                'temperatura': tag_temp,
                'camara_id': tag_cam_id,
                'marca_camara': tag_marca_cam,
            })

            lista_csv.append([
                seq_id, t_seconds, video_basename, out_name,
                tag_fecha_hora, tag_temp, tag_cam_id, tag_marca_cam,
                camara_name, cant_animales,
            ])

            if verbose:
                status = f"{cant_animales} animal(es)" if detect_animal else "sin animales"
                print(f"  t={t_seconds}s → {out_name} [{status}]")

        # Guardar después de cada video para no perder progreso
        _save_traceability(traceability_path, traceability)
        df = pd.DataFrame(lista_csv, columns=CSV_COLUMNS)
        df.to_csv(os.path.join(dir_salida, 'resultado_clasificador.csv'), index=False)

        update_log_file(log_proc_path, [(str(pathlib.PureWindowsPath(avi_path)), file_size)])

    print(f"\n[processor] Proceso completado. {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Con animales : {carpeta_con}")
    print(f"  Sin animales : {carpeta_sin}")
    print(f"  Trazabilidad : {traceability_path}")
