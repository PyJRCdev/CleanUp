import logging
import os
import sys
from PIL import Image
from pathlib import Path


def setup_backup_directory():
    """Crea el directorio de respaldo en la misma carpeta que el script de la aplicación."""
    # Obtener el directorio donde se ejecuta el programa
    main_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    # Define la ruta completa para la carpeta de respaldo
    backup_directory = os.path.join(main_directory, "backup")

    # Crear el directorio de respaldo si no existe
    if not os.path.exists(backup_directory):
        os.makedirs(backup_directory)
        print(f"Directorio de respaldo creado en: {backup_directory}")
    else:
        print(f"Directorio de respaldo ya existe en: {backup_directory}")

    return backup_directory


def setup_logging():
    """Configura el logging de la aplicación."""
    logging.basicConfig(filename="app.log", level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")


def load_png_image(image_path):
    """Carga una imagen PNG y la convierte en un objeto CTkImage."""
    try:
        image = Image.open(image_path)
        return image
    except FileNotFoundError as e:
        print(f"Error al cargar imagen {image_path}: {e}")
        return None


def resource_path(relative_path):
    """Obtiene la ruta del recurso en un entorno empaquetado."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
