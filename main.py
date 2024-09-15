import os
import sys
from gui.gui import run_as_admin, create_gui
from gui.utils import setup_logging

# Obtener el directorio de ejecución
if getattr(sys, 'frozen', False):
    # En modo "frozen", cuando está empaquetado por PyInstaller
    current_dir = os.path.dirname(sys.executable)
else:
    # En modo normal (sin empaquetar)
    current_dir = os.path.dirname(os.path.abspath(__file__))

# Configuración del directorio temporal seguro
temp_dir = os.path.abspath(os.path.join(current_dir, 'data'))
print(f"Temporary directory: {temp_dir}")
os.makedirs(temp_dir, exist_ok=True)

if __name__ == "__main__":
    run_as_admin()
    setup_logging()
    create_gui()
