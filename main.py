#!/usr/bin/env python3
"""
Image Studio — Wildlife Camera Trap Classifier
Processes AVI files from trail cameras, detects animals with YOLOv5,
and classifies images into 'con_animales' / 'sin_animales' folders.

Usage:
    python main.py
    python main.py --config /path/to/config.ini
    python main.py --config config.ini --mode DEFAULT
    python main.py --entrada /videos --salida /output --modelo ./model/md_v5b.0.0.pt
"""

import argparse
import configparser
import os
import sys

from src.bundle_utils import resolve_config_path, bundled_path
from src.processor import run


def parse_args():
    parser = argparse.ArgumentParser(
        description='Wildlife Camera Trap Classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--config', default='config.ini',
        help='Ruta al archivo de configuración (default: config.ini)',
    )
    parser.add_argument(
        '--mode', default='DEFAULT',
        help='Sección del config a usar (default: DEFAULT)',
    )
    parser.add_argument(
        '--entrada',
        help='Carpeta de entrada con videos AVI (sobreescribe config)',
    )
    parser.add_argument(
        '--salida',
        help='Carpeta de salida (sobreescribe config)',
    )
    parser.add_argument(
        '--modelo',
        help='Ruta al modelo YOLOv5 .pt (sobreescribe config)',
    )
    parser.add_argument(
        '--confianza', type=int,
        help='Confianza mínima 0-100 (sobreescribe config)',
    )
    parser.add_argument(
        '--camara',
        help='Nombre de la cámara/subcarpeta (sobreescribe config)',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    config_path = resolve_config_path(args.config)
    config = configparser.ConfigParser()
    read = config.read(config_path)
    if not read:
        print(f"Error: no se pudo leer el archivo de configuración '{config_path}'")
        sys.exit(1)

    # Si el modelo apunta a una ruta relativa, intentar resolverla desde el bundle
    default_model = config[args.mode].get('WEIGHT_MODEL_PATH', '')
    if default_model and not os.path.isabs(default_model):
        config[args.mode]['WEIGHT_MODEL_PATH'] = bundled_path(default_model)

    # CLI overrides
    if args.entrada:
        config[args.mode]['CARPETA_ENTRADA'] = args.entrada
    if args.salida:
        config[args.mode]['CARPETA_SALIDA'] = args.salida
    if args.modelo:
        config[args.mode]['WEIGHT_MODEL_PATH'] = args.modelo
    if args.confianza is not None:
        config[args.mode]['CONFIDENCE'] = str(args.confianza)
    if args.camara:
        config[args.mode]['CAMARA_NAME'] = args.camara

    run(config, mode=args.mode)


if __name__ == '__main__':
    main()
