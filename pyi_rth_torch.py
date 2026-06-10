# Runtime hook: pre-carga las DLLs de torch en orden de dependencia antes de que
# torch/__init__.py las cargue con LoadLibraryExW y flags restringidos.
#
# Problema raíz: torch usa LoadLibraryExW con LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
# pero llama a os.add_dll_directory() sin guardar el handle, que Python GC-ea
# de inmediato. La pre-carga con LoadLibraryW (que respeta PATH) las mete en el
# módulo del proceso antes de que corra el loop de torch.
import ctypes
import os
import sys

_dll_dir_handles = []  # evitar GC de los handles de AddDllDirectory

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _meipass = sys._MEIPASS
    _torch_lib = os.path.join(_meipass, 'torch', 'lib')

    if os.path.isdir(_torch_lib):
        # PATH para que LoadLibraryW encuentre dependencias transitivas (python313.dll, etc.)
        os.environ['PATH'] = (
            _torch_lib + os.pathsep
            + _meipass + os.pathsep
            + os.environ.get('PATH', '')
        )

        # AddDllDirectory con handles guardados para que LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
        # los encuentre si torch intenta cargarlo después de que corramos
        for _dir in (_meipass, _torch_lib):
            try:
                _dll_dir_handles.append(os.add_dll_directory(_dir))
            except OSError:
                pass

        # Pre-carga en orden de dependencia con LoadLibraryW (usa PATH → funciona)
        _kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        _kernel32.LoadLibraryW.restype = ctypes.c_void_p

        _LOAD_ORDER = [
            'uv.dll',
            'libiomp5md.dll',
            'libiompstubs5md.dll',
            'shm.dll',
            'c10.dll',
            'torch.dll',
            'torch_cpu.dll',
            'torch_global_deps.dll',
            'torch_python.dll',
        ]
        for _name in _LOAD_ORDER:
            _dll_path = os.path.join(_torch_lib, _name)
            if os.path.isfile(_dll_path):
                _kernel32.LoadLibraryW(_dll_path)
