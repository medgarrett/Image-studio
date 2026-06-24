"""
Detección de movimiento por sustracción de fondo.

Compara un frame de referencia (primer frame extraído de cada video)
contra frames posteriores dentro de una ROI configurable.
"""

import cv2
import numpy as np
from PIL import Image


class MotionDetector:
    """
    Detector de movimiento basado en diferencia absoluta de frames.

    Parámetros
    ----------
    reference   : PIL Image usado como fondo (primer frame del video).
    pixel_threshold : diferencia mínima por pixel (0-255) para considerarlo cambiado.
    area_threshold  : % mínimo de pixels de la ROI que deben cambiar para marcar movimiento.
    blur            : radio del kernel gaussiano (siempre impar).
    """

    def __init__(
        self,
        reference: Image.Image,
        pixel_threshold: int = 30,
        area_threshold: float = 2.0,
        blur: int = 3,
    ):
        self._pixel_threshold = pixel_threshold
        self._area_threshold = area_threshold
        k = blur if blur % 2 == 1 else blur + 1
        self._k = k
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        ref_gray = cv2.cvtColor(np.array(reference), cv2.COLOR_RGB2GRAY)
        self._ref = cv2.GaussianBlur(ref_gray, (k, k), 0)

    def compare(self, image: Image.Image, zone=None) -> dict:
        """
        Compara image contra la referencia dentro de la zona indicada.

        Si zone es BboxZone (tiene atributo .left), se usa ese rectángulo como ROI.
        En cualquier otro caso (LineZone, NoZone o None) se usa la imagen completa.

        Retorna
        -------
        dict con:
            delta_score  : float  — % de pixels de la ROI que cambiaron (0-100).
            movimiento   : bool   — True si delta_score >= area_threshold.
        """
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (self._k, self._k), 0)

        h, w = gray.shape
        if zone is not None and hasattr(zone, 'left'):
            x1 = max(0, int(zone.left))
            y1 = max(0, int(zone.top))
            x2 = min(w, int(zone.right))
            y2 = min(h, int(zone.bottom))
        else:
            x1, y1, x2, y2 = 0, 0, w, h

        ref_roi = self._ref[y1:y2, x1:x2]
        cur_roi = blurred[y1:y2, x1:x2]

        diff = cv2.absdiff(ref_roi, cur_roi)
        _, mask = cv2.threshold(diff, self._pixel_threshold, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)

        total = (x2 - x1) * (y2 - y1)
        changed = int(np.sum(mask > 0))
        delta = round(changed / total * 100, 2) if total > 0 else 0.0

        return {
            'delta_score': delta,
            'movimiento': delta >= self._area_threshold,
        }
