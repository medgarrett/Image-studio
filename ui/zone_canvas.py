"""
Canvas interactivo para dibujar la zona de análisis sobre una imagen.
Soporta modo bbox (rectángulo) y modo línea (alambre).
"""

import tkinter as tk
from PIL import Image, ImageTk

from src.zone import BboxZone, LineZone, NoZone


class ZoneCanvas(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self._canvas = tk.Canvas(self, bg='#333333', cursor='crosshair', highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._mode = 'bbox'
        self._pil_image = None
        self._photo = None
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0

        # zona en coordenadas de imagen original
        self._zone_img = None   # (x1, y1, x2, y2)

        # estado de dibujo
        self._start_x = None
        self._start_y = None
        self._drag_shape = None

        self._canvas.bind('<ButtonPress-1>', self._on_press)
        self._canvas.bind('<B1-Motion>', self._on_drag)
        self._canvas.bind('<ButtonRelease-1>', self._on_release)
        self._canvas.bind('<Configure>', lambda _e: self._redraw())

    # ── API pública ────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """'bbox', 'line' o 'none'"""
        self._mode = mode
        self.clear_zone()

    def set_image(self, pil_image: Image.Image):
        self._pil_image = pil_image
        self._zone_img = None
        self._redraw()

    def clear_zone(self):
        self._zone_img = None
        self._redraw()

    def get_zone(self):
        """Devuelve NoZone, BboxZone o LineZone en coordenadas de imagen. None si la zona no es válida."""
        if self._mode == 'none':
            return NoZone()
        if self._zone_img is None:
            return None
        x1, y1, x2, y2 = self._zone_img
        if self._mode == 'bbox':
            z = BboxZone(x1, y1, x2, y2)
        else:
            z = LineZone(x1, y1, x2, y2)
        return z if z.is_valid() else None

    # ── Conversión de coordenadas ──────────────────────────────────────────────

    def _canvas_to_image(self, cx, cy):
        ix = (cx - self._offset_x) / self._scale
        iy = (cy - self._offset_y) / self._scale
        return ix, iy

    def _image_to_canvas(self, ix, iy):
        cx = ix * self._scale + self._offset_x
        cy = iy * self._scale + self._offset_y
        return cx, cy

    # ── Dibujo ────────────────────────────────────────────────────────────────

    def _redraw(self):
        self._canvas.delete('all')
        if self._pil_image is None:
            self._canvas.create_text(
                self._canvas.winfo_width() // 2 or 200,
                self._canvas.winfo_height() // 2 or 200,
                text='Seleccioná una carpeta para previsualizar la imagen',
                fill='#666666', font=('Segoe UI', 10),
            )
            return

        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        iw, ih = self._pil_image.size
        self._scale = min(cw / iw, ch / ih)
        new_w = int(iw * self._scale)
        new_h = int(ih * self._scale)
        self._offset_x = (cw - new_w) // 2
        self._offset_y = (ch - new_h) // 2

        img_resized = self._pil_image.resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img_resized)
        self._canvas.create_image(self._offset_x, self._offset_y, anchor='nw', image=self._photo)

        if self._mode == 'none':
            self._draw_no_zone_overlay(cw, ch)
        elif self._zone_img is not None:
            self._draw_zone_overlay()

    def _draw_no_zone_overlay(self, cw, ch):
        self._canvas.create_rectangle(
            self._offset_x + 8, self._offset_y + 8,
            self._offset_x + 8 + 310, self._offset_y + 8 + 24,
            fill='#1e1e1e', outline='', tags='zone',
        )
        self._canvas.create_text(
            self._offset_x + 16, self._offset_y + 20,
            text='Sin zona — se detectan animales en toda la imagen',
            fill='#aaaaaa', font=('Segoe UI', 8), anchor='w', tags='zone',
        )

    def _draw_zone_overlay(self):
        x1, y1, x2, y2 = self._zone_img
        cx1, cy1 = self._image_to_canvas(x1, y1)
        cx2, cy2 = self._image_to_canvas(x2, y2)

        if self._mode == 'bbox':
            self._canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline='#00e676', width=2, tags='zone',
            )
            # esquinas
            r = 5
            for cx, cy in [(cx1, cy1), (cx2, cy1), (cx1, cy2), (cx2, cy2)]:
                self._canvas.create_rectangle(cx - r, cy - r, cx + r, cy + r,
                                               fill='#00e676', outline='', tags='zone')
        else:
            self._canvas.create_line(
                cx1, cy1, cx2, cy2,
                fill='#ff9100', width=2, tags='zone',
            )
            r = 5
            for cx, cy in [(cx1, cy1), (cx2, cy2)]:
                self._canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                          fill='#ff9100', outline='white', tags='zone')

    # ── Eventos de ratón ──────────────────────────────────────────────────────

    def _on_press(self, event):
        if self._mode == 'none':
            return
        self._start_x = event.x
        self._start_y = event.y
        if self._drag_shape:
            self._canvas.delete(self._drag_shape)
            self._drag_shape = None

    def _on_drag(self, event):
        if self._mode == 'none':
            return
        if self._drag_shape:
            self._canvas.delete(self._drag_shape)
        if self._mode == 'bbox':
            self._drag_shape = self._canvas.create_rectangle(
                self._start_x, self._start_y, event.x, event.y,
                outline='#00e676', width=2, dash=(6, 3),
            )
        else:
            self._drag_shape = self._canvas.create_line(
                self._start_x, self._start_y, event.x, event.y,
                fill='#ff9100', width=2, dash=(6, 3),
            )

    def _on_release(self, event):
        if self._mode == 'none':
            return
        if self._drag_shape:
            self._canvas.delete(self._drag_shape)
            self._drag_shape = None

        ix1, iy1 = self._canvas_to_image(self._start_x, self._start_y)
        ix2, iy2 = self._canvas_to_image(event.x, event.y)
        self._zone_img = (ix1, iy1, ix2, iy2)
        self._redraw()
