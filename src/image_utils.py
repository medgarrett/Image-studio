import os
from PIL import Image


def definir_puntos_recorte(left_x, left_y, width, height, tamanio_recorte):
    if left_x + tamanio_recorte * 0.8 > width:
        right = width
        left = width - tamanio_recorte
    elif left_x - tamanio_recorte * 0.2 < 0:
        left = 0
        right = tamanio_recorte
    else:
        right = left_x + tamanio_recorte * 0.8
        left = left_x - tamanio_recorte * 0.2

    if left_y + tamanio_recorte * 0.8 > height:
        bottom = height
        top = height - tamanio_recorte
    elif left_y - tamanio_recorte * 0.2 < 0:
        top = 0
        bottom = tamanio_recorte
    else:
        bottom = left_y + tamanio_recorte * 0.8
        top = left_y - tamanio_recorte * 0.2

    return (left, top, right, bottom)


def recorte_imagen(image, dir_salida, input_path, puntos_recorte, indice):
    image_recortada = image.crop(puntos_recorte)
    image_recortada.save(
        os.path.join(dir_salida, f"{indice}-{os.path.basename(input_path)}"),
        optimize=True,
        quality=100,
    )


def crear_lista_booleanos(detections):
    return [False] * len(detections)


def esta_dentro_del_recorte(puntos, deteccion):
    left_x = int(deteccion.points[0][0])
    left_y = int(deteccion.points[0][1])
    return (
        puntos[0] <= left_x <= puntos[2]
        and puntos[1] <= left_y <= puntos[3]
    )


def actualizar_lista_booleanos(puntos, detecciones, lista_bool, indice):
    for i in range(indice, len(detecciones)):
        lista_bool[i] = esta_dentro_del_recorte(puntos, detecciones[i])
    return lista_bool
