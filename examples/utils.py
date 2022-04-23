"""Utilities for examples"""

def select_model() -> str:
    from tkinter import filedialog, Tk
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(True)
    except:
        pass
    Tk().withdraw()
    file_path = filedialog.askopenfilenames(
        filetypes=[
            ('STLファイル', '*.stl'), ('UFPファイル', '*.ufp')])
    if len(file_path) != 1:
        raise Exception('File Selection Error: Select exactly ONE file.')
    return file_path[0]
