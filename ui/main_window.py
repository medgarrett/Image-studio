"""
Ventana principal de Image Studio.
Selector de carpeta, modo de zona, controles, barra de progreso y guardado de CSV.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image

from src.bundle_utils import bundled_path, resolve_config_path
from src.detector import YOLO
from src.processor_gui import process_folder, process_videos_folder, parse_frames
from ui.zone_canvas import ZoneCanvas

# ── Paleta oscura ──────────────────────────────────────────────────────────────
_BG      = '#1e1e1e'
_SIDEBAR = '#252526'
_WIDGET  = '#3c3c3c'
_TEXT    = '#cccccc'
_MUTED   = '#888888'
_ACCENT  = '#0e639c'
_ACTIVE  = '#094771'
_SUCCESS = '#4ec9b0'
_ERROR   = '#f44747'
_HINT_BG = '#2d2d2d'

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mov', '.mkv'}


class MainWindow(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_BG, **kwargs)

        self._model = None
        self._folder = None
        self._results_df = None
        self._queue = queue.Queue()
        self._mode = tk.StringVar(value='bbox')
        self._confidence = tk.DoubleVar(value=45)
        self._iou = tk.DoubleVar(value=45)
        self._camara_id = tk.StringVar(value='')
        self._separate_folders = tk.BooleanVar(value=False)
        self._input_mode = tk.StringVar(value='images')
        self._video_seconds = tk.StringVar(value='')

        self._build_ui()
        self._load_model_async()

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build_ui(self):
        sidebar = tk.Frame(self, bg=_SIDEBAR, width=290)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        main = tk.Frame(self, bg=_BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar(sidebar)
        self._build_canvas_area(main)

    def _lbl(self, parent, text, fg=None, **kw):
        return tk.Label(parent, text=text,
                        bg=kw.pop('bg', _SIDEBAR), fg=fg or _TEXT,
                        font=kw.pop('font', ('Segoe UI', 9)), **kw)

    def _btn(self, parent, text, command, **kw):
        opts = dict(bg=_ACCENT, fg='white',
                    activebackground=_ACTIVE, activeforeground='white',
                    relief='flat', font=('Segoe UI', 9),
                    cursor='hand2', padx=8, pady=4)
        opts.update(kw)
        return tk.Button(parent, text=text, command=command, **opts)

    def _sep(self, parent):
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, padx=8, pady=6)

    def _build_sidebar(self, sb):
        pad = dict(padx=12, pady=3)

        # encabezado
        tk.Label(sb, text='Image Studio', bg=_SIDEBAR, fg='white',
                 font=('Segoe UI', 12, 'bold')).pack(pady=(16, 2))
        tk.Label(sb, text='Clasificador de Trampas Cámara', bg=_SIDEBAR,
                 fg=_MUTED, font=('Segoe UI', 8)).pack(pady=(0, 10))
        self._sep(sb)

        # carpeta
        self._lbl(sb, 'Carpeta de imágenes').pack(anchor='w', **pad)
        self._btn(sb, '📁  Seleccionar carpeta', self._select_folder).pack(fill=tk.X, padx=12, pady=2)
        self._folder_lbl = self._lbl(sb, 'Sin selección', fg=_MUTED)
        self._folder_lbl.pack(anchor='w', **pad)
        self._sep(sb)

        # fuente de entrada
        self._lbl(sb, 'Fuente de entrada').pack(anchor='w', **pad)
        tk.Radiobutton(sb, text='Imágenes  (JPG / PNG)',
                       variable=self._input_mode, value='images',
                       bg=_SIDEBAR, fg=_TEXT, selectcolor=_WIDGET,
                       activebackground=_SIDEBAR, activeforeground=_TEXT,
                       font=('Segoe UI', 9),
                       command=self._on_input_mode_change).pack(anchor='w', padx=20, pady=1)
        self._vid_radio = tk.Radiobutton(sb, text='Videos  (AVI / MP4)',
                       variable=self._input_mode, value='videos',
                       bg=_SIDEBAR, fg=_TEXT, selectcolor=_WIDGET,
                       activebackground=_SIDEBAR, activeforeground=_TEXT,
                       font=('Segoe UI', 9),
                       command=self._on_input_mode_change)
        self._vid_radio.pack(anchor='w', padx=20, pady=(1, 4))

        # Panel de segundos — se muestra solo en modo videos
        self._video_opts_frame = tk.Frame(sb, bg=_SIDEBAR)
        self._lbl(self._video_opts_frame, 'Frames a extraer').pack(anchor='w', padx=12, pady=(2, 0))
        self._lbl(self._video_opts_frame, 'Ej: 5, 100, 300  (número de frame)',
                  fg=_MUTED, font=('Segoe UI', 7)).pack(anchor='w', padx=12)
        tk.Entry(
            self._video_opts_frame, textvariable=self._video_seconds,
            bg=_WIDGET, fg=_TEXT, insertbackground=_TEXT,
            relief='flat', font=('Segoe UI', 9),
        ).pack(fill=tk.X, padx=12, pady=(2, 6))

        self._sep(sb)

        # modo
        self._lbl(sb, 'Modo de zona').pack(anchor='w', **pad)
        for text, val in [
            ('Sin zona  (solo con/sin animales)', 'none'),
            ('Bebedero  (rectángulo)', 'bbox'),
            ('Alambre  (línea)', 'line'),
        ]:
            tk.Radiobutton(sb, text=text, variable=self._mode, value=val,
                           bg=_SIDEBAR, fg=_TEXT, selectcolor=_WIDGET,
                           activebackground=_SIDEBAR, activeforeground=_TEXT,
                           font=('Segoe UI', 9),
                           command=self._on_mode_change).pack(anchor='w', padx=20, pady=1)
        self._sep(sb)

        # umbrales
        self._lbl(sb, 'Confianza mínima').pack(anchor='w', **pad)
        row = tk.Frame(sb, bg=_SIDEBAR)
        row.pack(fill=tk.X, padx=12)
        tk.Scale(row, from_=1, to=99, orient=tk.HORIZONTAL, variable=self._confidence,
                 bg=_SIDEBAR, fg=_TEXT, troughcolor=_WIDGET, highlightthickness=0,
                 showvalue=False).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._conf_lbl = self._lbl(row, '45%', width=5, anchor='e', bg=_SIDEBAR)
        self._conf_lbl.pack(side=tk.LEFT)
        self._confidence.trace_add('write',
            lambda *_: self._conf_lbl.config(text=f'{int(self._confidence.get())}%'))

        self._lbl(sb, 'Umbral IOU').pack(anchor='w', **pad)
        row2 = tk.Frame(sb, bg=_SIDEBAR)
        row2.pack(fill=tk.X, padx=12)
        tk.Scale(row2, from_=1, to=99, orient=tk.HORIZONTAL, variable=self._iou,
                 bg=_SIDEBAR, fg=_TEXT, troughcolor=_WIDGET, highlightthickness=0,
                 showvalue=False).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._iou_lbl = self._lbl(row2, '45%', width=5, anchor='e', bg=_SIDEBAR)
        self._iou_lbl.pack(side=tk.LEFT)
        self._iou.trace_add('write',
            lambda *_: self._iou_lbl.config(text=f'{int(self._iou.get())}%'))
        self._sep(sb)

        # ID de cámara
        self._lbl(sb, 'ID de cámara').pack(anchor='w', **pad)
        cam_row = tk.Frame(sb, bg=_SIDEBAR)
        cam_row.pack(fill=tk.X, padx=12, pady=2)
        self._camara_entry = tk.Entry(
            cam_row, textvariable=self._camara_id,
            bg=_WIDGET, fg=_TEXT, insertbackground=_TEXT,
            relief='flat', font=('Segoe UI', 9),
        )
        self._camara_entry.pack(fill=tk.X)
        self._lbl(sb, 'Se auto-completa desde la carpeta o el índice', fg=_MUTED,
                  font=('Segoe UI', 7)).pack(anchor='w', padx=12)
        self._sep(sb)

        # separar imágenes
        tk.Checkbutton(
            sb, text='Separar en con/sin animales',
            variable=self._separate_folders,
            bg=_SIDEBAR, fg=_TEXT, selectcolor=_WIDGET,
            activebackground=_SIDEBAR, activeforeground=_TEXT,
            font=('Segoe UI', 9),
        ).pack(anchor='w', padx=14, pady=2)
        self._sep(sb)

        # zona
        self._btn(sb, 'Limpiar zona', self._clear_zone,
                  bg=_WIDGET, activebackground=_SIDEBAR).pack(fill=tk.X, padx=12, pady=2)
        self._sep(sb)

        # procesar
        self._process_btn = self._btn(sb, '▶  Procesar carpeta', self._start_processing)
        self._process_btn.pack(fill=tk.X, padx=12, pady=2)

        self._progress = ttk.Progressbar(sb, mode='determinate', maximum=100)
        self._progress.pack(fill=tk.X, padx=12, pady=(8, 2))
        self._status_lbl = self._lbl(sb, 'Listo', fg=_MUTED)
        self._status_lbl.pack(anchor='w', **pad)
        self._sep(sb)

        # guardar
        self._save_btn = self._btn(sb, '💾  Guardar CSV', self._save_csv)
        self._save_btn.pack(fill=tk.X, padx=12, pady=2)
        self._save_btn.config(state='disabled')
        self._sep(sb)

        # estado del modelo
        self._model_lbl = self._lbl(sb, '⏳ Cargando modelo...', fg=_MUTED)
        self._model_lbl.pack(anchor='w', **pad)

    def _build_canvas_area(self, parent):
        hint_bar = tk.Frame(parent, bg=_HINT_BG, height=28)
        hint_bar.pack(fill=tk.X)
        hint_bar.pack_propagate(False)
        self._hint_lbl = tk.Label(hint_bar,
                                   text='Seleccioná una carpeta y dibujá la zona sobre la imagen',
                                   bg=_HINT_BG, fg=_MUTED, font=('Segoe UI', 8))
        self._hint_lbl.pack(side=tk.LEFT, padx=10)

        self._zone_canvas = ZoneCanvas(parent, bg=_BG)
        self._zone_canvas.pack(fill=tk.BOTH, expand=True)

    # ── Handlers de UI ────────────────────────────────────────────────────────

    def _on_mode_change(self):
        mode = self._mode.get()
        self._zone_canvas.set_mode(mode)
        if mode == 'none':
            self._hint_lbl.config(text='Modo sin zona — procesá directamente, no es necesario dibujar')
        elif mode == 'bbox':
            self._hint_lbl.config(text='Modo rectángulo: hacé clic y arrastrá sobre la imagen para definir la zona')
        else:
            self._hint_lbl.config(text='Modo línea: hacé clic y arrastrá sobre la imagen para definir la zona')

    def _on_input_mode_change(self):
        if self._input_mode.get() == 'videos':
            self._video_opts_frame.pack(fill=tk.X, after=self._vid_radio)
        else:
            self._video_opts_frame.pack_forget()
        if self._folder:
            if self._input_mode.get() == 'videos':
                self._preview_first_video(self._folder)
            else:
                self._preview_first_image(self._folder)

    def _select_folder(self):
        folder = filedialog.askdirectory(title='Seleccionar carpeta de imágenes')
        if not folder:
            return
        self._folder = folder
        label = folder if len(folder) <= 36 else '…' + folder[-33:]
        self._folder_lbl.config(text=label, fg=_TEXT)

        if not self._camara_id.get():
            self._camara_id.set(os.path.basename(folder))

        if self._input_mode.get() == 'videos':
            self._preview_first_video(folder)
        else:
            self._preview_first_image(folder)

    def _preview_first_image(self, folder):
        for fname in sorted(os.listdir(folder)):
            if os.path.splitext(fname)[1].lower() in IMAGE_EXTENSIONS:
                try:
                    img = Image.open(os.path.join(folder, fname)).convert('RGB')
                    self._zone_canvas.set_image(img)
                    self._zone_canvas.set_mode(self._mode.get())
                    self._hint_lbl.config(text=f'{fname}  —  dibujá la zona sobre la imagen')
                except Exception:
                    pass
                break

    def _preview_first_video(self, folder):
        import cv2
        for fname in sorted(os.listdir(folder)):
            if os.path.splitext(fname)[1].lower() in VIDEO_EXTENSIONS:
                try:
                    cap = cv2.VideoCapture(os.path.join(folder, fname))
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        self._zone_canvas.set_image(img)
                        self._zone_canvas.set_mode(self._mode.get())
                        self._hint_lbl.config(text=f'{fname}  (frame inicial)  —  dibujá la zona sobre la imagen')
                except Exception:
                    pass
                break

    def _clear_zone(self):
        self._zone_canvas.clear_zone()

    # ── Carga del modelo ──────────────────────────────────────────────────────

    def _load_model_async(self):
        def _load():
            try:
                path = bundled_path('model', 'md_v5b.0.0.pt')
                self._model = YOLO(path)
                self.after(0, lambda: self._model_lbl.config(
                    text='✓ Modelo cargado', fg=_SUCCESS))
            except Exception as exc:
                msg = str(exc)
                self.after(0, lambda: self._model_lbl.config(
                    text=f'✗ {msg[:40]}', fg=_ERROR))

        threading.Thread(target=_load, daemon=True).start()

    # ── Procesamiento ─────────────────────────────────────────────────────────

    def _start_processing(self):
        if not self._folder:
            messagebox.showwarning('Sin carpeta', 'Seleccioná una carpeta primero.')
            return
        if self._model is None:
            messagebox.showwarning('Modelo no listo', 'El modelo aún se está cargando. Esperá un momento.')
            return

        zone = self._zone_canvas.get_zone()
        if zone is None:
            messagebox.showwarning('Sin zona', 'Dibujá la zona sobre la imagen antes de procesar.')
            return

        seconds = []
        if self._input_mode.get() == 'videos':
            seconds = parse_frames(self._video_seconds.get())
            if not seconds:
                messagebox.showwarning('Sin frames', 'Ingresá al menos un número de frame válido (ej: 5, 100, 300).')
                return

        self._results_df = None
        self._save_btn.config(state='disabled')
        self._process_btn.config(state='disabled')
        self._progress['value'] = 0
        self._status_lbl.config(text='Procesando...', fg=_TEXT)

        conf     = self._confidence.get() / 100.0
        iou      = self._iou.get() / 100.0
        cam_id   = self._camara_id.get().strip()
        separate = self._separate_folders.get()

        if self._input_mode.get() == 'videos':
            threading.Thread(
                target=self._process_thread_video,
                args=(self._folder, zone, conf, iou, cam_id, separate, seconds),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=self._process_thread,
                args=(self._folder, zone, conf, iou, cam_id, separate),
                daemon=True,
            ).start()
        self.after(100, self._poll_queue)

    def _process_thread(self, folder, zone, conf, iou, cam_id, separate):
        try:
            def on_progress(current, total, fname):
                self._queue.put(('progress', current, total, fname))

            df = process_folder(
                folder, zone, self._model, conf, iou,
                camara_id=cam_id,
                separate_folders=separate,
                on_progress=on_progress,
            )
            self._queue.put(('done', df))
        except Exception as exc:
            self._queue.put(('error', str(exc)))

    def _process_thread_video(self, folder, zone, conf, iou, cam_id, separate, seconds):
        try:
            def on_progress(current, total, fname):
                self._queue.put(('progress', current, total, fname))

            df = process_videos_folder(
                folder, zone, self._model, conf, iou,
                seconds=seconds,
                camara_id=cam_id,
                separate_folders=separate,
                on_progress=on_progress,
            )
            self._queue.put(('done', df))
        except Exception as exc:
            self._queue.put(('error', str(exc)))

    def _poll_queue(self):
        still_running = True
        while True:
            try:
                msg = self._queue.get_nowait()
            except queue.Empty:
                break

            kind = msg[0]
            if kind == 'progress':
                _, current, total, fname = msg
                self._progress['value'] = (current / total) * 100
                self._status_lbl.config(text=f'{current}/{total}  {fname}', fg=_TEXT)
            elif kind == 'done':
                _, df = msg
                self._results_df = df
                self._progress['value'] = 100
                n = len(df)
                if self._input_mode.get() == 'videos':
                    self._status_lbl.config(
                        text=f'✓ {n} frame{"s" if n != 1 else ""} · CSV guardado en carpeta',
                        fg=_SUCCESS)
                else:
                    self._status_lbl.config(
                        text=f'✓ {n} imagen{"es" if n != 1 else ""} procesada{"s" if n != 1 else ""}',
                        fg=_SUCCESS)
                self._process_btn.config(state='normal')
                self._save_btn.config(state='normal')
                still_running = False
            elif kind == 'error':
                _, err = msg
                self._status_lbl.config(text=f'✗ {err[:50]}', fg=_ERROR)
                self._process_btn.config(state='normal')
                still_running = False

        if still_running:
            self.after(100, self._poll_queue)

    # ── Guardado ──────────────────────────────────────────────────────────────

    def _save_csv(self):
        if self._results_df is None or self._results_df.empty:
            messagebox.showinfo('Sin resultados', 'No hay resultados para guardar.')
            return

        default_dir = self._folder or os.path.expanduser('~')
        path = filedialog.asksaveasfilename(
            title='Guardar resultados',
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv'), ('Todos', '*.*')],
            initialdir=default_dir,
            initialfile='resultados.csv',
        )
        if not path:
            return

        self._results_df.to_csv(path, index=False)
        messagebox.showinfo('Guardado', f'CSV guardado en:\n{path}')
