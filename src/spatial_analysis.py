from typing import List, Union
from src.zone import BboxZone, LineZone, NoZone


def get_centroid(detection) -> tuple:
    cx = (detection.points[0][0] + detection.points[1][0]) / 2
    cy = (detection.points[0][1] + detection.points[1][1]) / 2
    return cx, cy


def classify_detections(
    detections: list,
    zone: Union[BboxZone, LineZone, NoZone],
    confidence_threshold: float,
) -> dict:
    """
    Clasifica cada detección según la zona y devuelve conteos.

    Para NoZone   devuelve: {total}
    Para BboxZone devuelve: {total, dentro, fuera}
    Para LineZone devuelve: {total, izquierda, derecha}
    """
    if isinstance(zone, NoZone):
        counts = {'total': 0}
    elif isinstance(zone, BboxZone):
        counts = {'total': 0, 'dentro': 0, 'fuera': 0}
    else:
        counts = {'total': 0, 'izquierda': 0, 'derecha': 0}

    for det in detections:
        if det.scores[0] < confidence_threshold:
            continue
        counts['total'] += 1
        if not isinstance(zone, NoZone):
            cx, cy = get_centroid(det)
            label = zone.classify(cx, cy)
            counts[label] += 1

    return counts
