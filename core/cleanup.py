import os
import sys
import shutil
import logging
from pathlib import Path
from gui.utils import setup_backup_directory


def resource_path(relative_path):
    """Obtiene la ruta absoluta de un recurso dentro del paquete."""
    try:
        # PyInstaller crea una carpeta temporal para los archivos empaquetados
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # En desarrollo, simplemente usa el directorio actual
        base_path = Path(__file__).parent
    return base_path / relative_path


# Configuración del log
def configure_logging(log_file="cleaning_log.txt", level=logging.DEBUG):
    logging.basicConfig(
        filename=log_file,
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="a"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)


configure_logging()


def log_message(message, level="INFO", gui_output=None):
    if not isinstance(level, str):
        level = "INFO"

    levels = {
        "DEBUG": logging.debug,
        "INFO": logging.info,
        "WARNING": logging.warning,
        "ERROR": logging.error,
        "CRITICAL": logging.critical
    }

    log_func = levels.get(level.upper(), logging.info)
    log_func(message)

    if gui_output:
        gui_output.insert("end", f"{level}: {message}\n")
        gui_output.see("end")


def expand_environment_variables(path):
    """Expande variables de entorno en la ruta especificada."""
    return os.path.expandvars(path)


def secure_delete(file_path, passes=3, gui_output=None):
    """Realiza una eliminación segura del archivo sobrescribiéndolo varias veces."""
    try:
        if not os.path.exists(file_path):
            log_message(f"El archivo {file_path} no existe para eliminación segura.", "WARNING", gui_output)
            return

        with open(file_path, "ba+") as f:
            length = f.tell()

        with open(file_path, "br+") as f:
            for _ in range(passes):
                f.seek(0)
                f.write(os.urandom(length))

        os.remove(file_path)
        log_message(f"Eliminación segura: {file_path}", "INFO", gui_output)
    except PermissionError:
        log_message(f"Acceso denegado al archivo {file_path}. Intenta ejecutar como administrador.", "ERROR", gui_output)
    except Exception as e:
        log_message(f"Error en la eliminación segura de {file_path}: {e}", "ERROR", gui_output)


def backup_and_delete(file_path, backup_directory, gui_output=None):
    """Copia el archivo al directorio de respaldo y luego lo elimina."""
    try:
        backup_path = Path(backup_directory) / file_path.relative_to(file_path.anchor)
        backup_path.parent.mkdir(parents=True, exist_ok=True)  # Crear directorios necesarios
        shutil.copy2(file_path, backup_path)  # Copia el archivo al directorio de respaldo
        log_message(f"Respaldo creado: {backup_path}", "INFO", gui_output)

        file_path.unlink()  # Luego de copiar, eliminar el archivo original
        log_message(f"Eliminado: {file_path}", "INFO", gui_output)
    except Exception as e:
        log_message(f"No se pudo respaldar o eliminar {file_path}: {e}", "ERROR", gui_output)


def delete_files_in_directory(directory, exclusions=None, secure=False, backup_directory=None, gui_output=None):
    """Elimina archivos y directorios en la ruta especificada, con opciones para exclusión, copia de seguridad y eliminación segura."""
    directory = expand_environment_variables(directory)
    exclusions = exclusions or []

    if not os.path.exists(directory):
        log_message(f"El directorio {directory} no existe.", "WARNING", gui_output)
        return

    exclusions = [os.path.normpath(expand_environment_variables(excl)) for excl in exclusions]

    for root, subdirs, files in os.walk(directory):
        files = [f for f in files if Path(root) / f not in exclusions]
        subdirs[:] = [d for d in subdirs if Path(root) / d not in exclusions]

        for file in files:
            file_path = Path(root) / file
            try:
                if backup_directory:
                    backup_and_delete(file_path, backup_directory, gui_output)
                elif secure:
                    secure_delete(file_path, gui_output=gui_output)
                else:
                    file_path.unlink()  # Eliminar sin respaldo
                    log_message(f"Eliminado: {file_path}", "INFO", gui_output)
            except FileNotFoundError:
                log_message(f"El archivo {file_path} no se encontró.", "WARNING", gui_output)
            except Exception as e:
                log_message(f"No se pudo eliminar {file_path}: {e}", "ERROR", gui_output)

        for subdir in subdirs:
            subdir_path = Path(root) / subdir
            try:
                if subdir_path not in exclusions:
                    shutil.rmtree(subdir_path)
                    log_message(f"Eliminado: {subdir_path}", "INFO", gui_output)
                else:
                    log_message(f"Directorio {subdir_path} excluido de la eliminación.", "INFO", gui_output)
            except FileNotFoundError:
                log_message(f"El directorio {subdir_path} no se encontró.", "WARNING", gui_output)
            except Exception as e:
                log_message(f"No se pudo eliminar {subdir_path}: {e}", "ERROR", gui_output)