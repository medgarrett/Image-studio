"""
Resolución de rutas compatibles con ejecución normal y bundle PyInstaller.

Cuando PyInstaller empaqueta la app, los archivos incluidos (modelo, config, etc.)
se extraen a sys._MEIPASS en tiempo de ejecución. Este módulo centraliza esa lógica.
"""

import os
import sys


def bundle_root() -> str:
    """Devuelve la raíz del bundle (sys._MEIPASS) o el directorio del proyecto."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))


def bundled_path(*parts: str) -> str:
    """Construye una ruta relativa a la raíz del bundle."""
    return os.path.join(bundle_root(), *parts)


def resolve_config_path(user_provided: str) -> str:
    """
    Resuelve la ruta del config.ini:
    1. Si el usuario pasó una ruta absoluta/existente, la usa.
    2. Si no, busca config.ini junto al .exe o en el directorio de trabajo.
    """
    if os.path.isabs(user_provided) and os.path.isfile(user_provided):
        return user_provided

    # Junto al ejecutable (útil cuando el usuario edita el config en la carpeta del .exe)
    exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False)
                               else os.path.abspath(__file__))
    candidate = os.path.join(exe_dir, user_provided)
    if os.path.isfile(candidate):
        return candidate

    # Bundleado dentro del paquete
    bundled = bundled_path(user_provided)
    if os.path.isfile(bundled):
        return bundled

    return user_provided  # deja que el llamador maneje el error
