import json
import os
from pathlib import Path
import sys


def resource_path(relative_path):
    """Obtiene la ruta del recurso en un entorno empaquetado."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_default_config():
    """Carga la configuración predeterminada desde el archivo."""
    try:
        with open(resource_path("gui/config/config.json"), "r") as file:
            config = json.load(file)
            return {
                "directories": config.get("directories", []),
                "browsers": config.get("browsers", {}),
                "exclusions": config.get("exclusions", []),
                "secure_delete": config.get("secure_delete", False),
                "backup": config.get("backup", False)
            }
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error al cargar la configuración predeterminada: {e}")
        return {"directories": [], "browsers": {}, "exclusions": [], "secure_delete": False, "backup": False}


def load_user_config():
    """Carga la configuración del usuario desde el archivo."""
    try:
        if not os.path.exists(resource_path("user_config.json")):
            return load_default_config()
        with open(resource_path("user_config.json"), "r") as file:
            config = json.load(file)
            return {
                "directories": config.get("directories", []),
                "browsers": config.get("browsers", {}),
                "exclusions": config.get("exclusions", []),
                "secure_delete": config.get("secure_delete", False),
                "backup": config.get("backup", False)
            }
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error al cargar la configuración del usuario: {e}")
        return load_default_config()


def save_user_config(config):
    """Guarda la configuración del usuario en el archivo."""
    try:
        with open(resource_path("user_config.json"), "w") as file:
            json.dump(config, file, indent=4)
    except IOError as e:
        print(f"Error al guardar la configuración del usuario: {e}")
