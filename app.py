#!/usr/bin/env python3
"""
Image Studio — Clasificador de Trampas Cámara
Interfaz gráfica para análisis de bebedero o alambre.
"""

import tkinter as tk
from ui.main_window import MainWindow


def main():
    root = tk.Tk()
    root.title('Image Studio — Clasificador de Trampas Cámara')
    root.geometry('1000x720')
    root.minsize(800, 600)
    root.configure(bg='#1e1e1e')

    try:
        root.iconbitmap('assets/icon.ico')
    except Exception:
        pass

    app = MainWindow(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == '__main__':
    main()
