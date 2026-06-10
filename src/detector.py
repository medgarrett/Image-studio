from dataclasses import dataclass
from typing import List, Optional, Union

import numpy as np
import torch
import yolov5
from PIL import Image

# PyTorch >= 2.6 cambió weights_only=True por defecto, bloqueando clases custom
# de YOLOv5. Como el modelo MegaDetector es de fuente confiable, forzamos False.
_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load

try:
    # norfair2 es una copia local personalizada — copiá la carpeta al root del proyecto.
    from norfair2 import Detection
except ModuleNotFoundError:
    @dataclass
    class Detection:
        """Fallback minimal cuando norfair2 no está disponible."""
        points: np.ndarray
        scores: np.ndarray
        data: np.ndarray = None


class YOLO:
    def __init__(self, model_path: str, device: Optional[str] = None):
        if device is not None and "cuda" in device and not torch.cuda.is_available():
            raise RuntimeError("device='cuda' requested but CUDA is not available.")
        if device is None:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"

        self.model = yolov5.load(model_path, device=device)

    def __call__(
        self,
        img: Union[str, np.ndarray, Image.Image],
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 720,
        classes: Optional[int] = None,
    ) -> torch.Tensor:
        self.model.conf = conf_threshold
        self.model.iou = iou_threshold
        if classes is not None:
            self.model.classes = classes
        return self.model(img, size=image_size)


def euclidean_distance(detection, tracked_object):
    return np.linalg.norm(detection.points - tracked_object.estimate)


def yolo_detections_to_norfair_detections(
    yolo_detections: torch.Tensor,
    track_points: str = 'bbox',
) -> List[Detection]:
    norfair_detections: List[Detection] = []

    if track_points == 'centroid':
        for det in yolo_detections.xywh[0]:
            centroid = np.array([det[0].item(), det[1].item()])
            scores = np.array([det[4].item()])
            data = np.array([det[5].item()])
            norfair_detections.append(Detection(points=centroid, scores=scores, data=data))

    elif track_points == 'bbox':
        for det in yolo_detections.xyxy[0]:
            bbox = np.array([
                [det[0].item(), det[1].item()],
                [det[2].item(), det[3].item()],
            ])
            scores = np.array([det[4].item(), det[4].item()])
            norfair_detections.append(Detection(points=bbox, scores=scores))

    return norfair_detections
