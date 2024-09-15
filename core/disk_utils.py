import subprocess
import os
import tempfile
from core.cleanup import log_message


def get_defragmentation_report(drive):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            report_path = temp_file.name
            # Ejecuta el comando defrag y guarda la salida en un archivo
            subprocess.run(
                ["defrag", drive, "/O", "/V"],
                stdout=temp_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=True
            )
        # Lee el informe del archivo
        with open(report_path, "r") as f:
            report = f.read()
        os.remove(report_path)  # Eliminar archivo temporal después de su uso
        return report
    except subprocess.CalledProcessError as e:
        return f"Error al obtener el informe de fragmentación: {e}\nSalida: {e.output.decode()}"
    except Exception as e:
        return f"Error inesperado al obtener el informe de fragmentación: {e}"


def is_ssd(drive):
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-PhysicalDisk | Where-Object {{$_.DeviceID -eq (Get-Partition -DriveLetter {drive.strip(':')} | Get-Disk).DeviceID}} | Select MediaType"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return 'SSD' in result.stdout
    except Exception as e:
        return False  # Asumimos que no es un SSD si no podemos determinarlo


def optimize_disk(gui_output=None):
    try:
        if os.name == 'nt':
            drive = os.getenv('SystemDrive')
            if is_ssd(drive):
                log_message(f"El disco {drive} es un SSD; no se requiere desfragmentación.", gui_output)
                return None

            subprocess.run(["defrag", drive, "/O"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            post_report = get_defragmentation_report(drive)
            log_message(f"Optimización del disco {drive} completada.", gui_output)
            return post_report
    except Exception as e:
        log_message(f"Error al optimizar el disco: {e}", gui_output)
        return None
