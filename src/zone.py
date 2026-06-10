from dataclasses import dataclass


@dataclass
class NoZone:
    """Sin zona. Detecta y cuenta animales en toda la imagen sin clasificar posición."""

    def classify(self, cx: float, cy: float) -> str:
        return 'detectado'

    def is_valid(self) -> bool:
        return True


@dataclass
class BboxZone:
    """Zona rectangular (bebedero). Clasifica animales dentro o fuera."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def left(self):   return min(self.x1, self.x2)
    @property
    def right(self):  return max(self.x1, self.x2)
    @property
    def top(self):    return min(self.y1, self.y2)
    @property
    def bottom(self): return max(self.y1, self.y2)

    def classify(self, cx: float, cy: float) -> str:
        if self.left <= cx <= self.right and self.top <= cy <= self.bottom:
            return 'dentro'
        return 'fuera'

    def is_valid(self) -> bool:
        return abs(self.x2 - self.x1) > 5 and abs(self.y2 - self.y1) > 5


@dataclass
class LineZone:
    """Zona de línea (alambre). Clasifica animales a izquierda o derecha."""
    x1: float
    y1: float
    x2: float
    y2: float

    def classify(self, cx: float, cy: float) -> str:
        # Producto vectorial: signo determina el lado de la línea
        sign = (self.x2 - self.x1) * (cy - self.y1) - (self.y2 - self.y1) * (cx - self.x1)
        if sign == 0:
            return 'izquierda'
        return 'izquierda' if sign > 0 else 'derecha'

    def is_valid(self) -> bool:
        return abs(self.x2 - self.x1) + abs(self.y2 - self.y1) > 10
