import os
import subprocess
from pathlib import Path
from core.cleanup import delete_files_in_directory, log_message


def get_firefox_profiles():
    """Obtiene los perfiles de Firefox desde el archivo profiles.ini."""
    profiles_ini_path = Path(os.getenv('APPDATA')) / 'Mozilla' / 'Firefox' / 'profiles.ini'
    profiles = []
    if profiles_ini_path.exists():
        with open(profiles_ini_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith('Path='):
                    profile_path = Path(os.getenv('APPDATA')) / 'Mozilla' / 'Firefox' / line.strip().split('=', 1)[1]
                    profiles.append(profile_path)
    return profiles


def get_chrome_profiles():
    """Obtiene los perfiles de Chrome desde la ruta de usuario."""
    user_data_path = Path(os.getenv('LOCALAPPDATA')) / 'Google' / 'Chrome' / 'User Data'
    if user_data_path.exists():
        profiles = [user_data_path / d for d in os.listdir(user_data_path) if
                    Path(user_data_path / d).is_dir() and d.startswith('Profile ')]
        profiles.append(user_data_path / 'Default')  # Default profile
    else:
        profiles = []
    return profiles


def get_edge_profiles():
    """Obtiene los perfiles de Edge desde la ruta de usuario."""
    user_data_path = Path(os.getenv('LOCALAPPDATA')) / 'Microsoft' / 'Edge' / 'User Data'
    if user_data_path.exists():
        profiles = [user_data_path / d for d in os.listdir(user_data_path) if
                    Path(user_data_path / d).is_dir() and d.startswith('Profile ')]
        profiles.append(user_data_path / 'Default')  # Default profile
    else:
        profiles = []
    return profiles


def close_browser_processes(browser_name):
    """
    Cierra los procesos del navegador especificado.

    :param browser_name: Nombre del navegador cuyo proceso se debe cerrar.
    """
    # Define los nombres de los procesos para diferentes navegadores
    processes = {
        "Edge": "msedge.exe",
        "Chrome": "chrome.exe",
        "Firefox": "firefox.exe",
        "Safari": "safari.exe"
    }

    process_name = processes.get(browser_name)
    if process_name:
        try:
            # Verificar si el proceso está en ejecución antes de intentar cerrarlo
            result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {process_name}"], capture_output=True, text=True)
            if process_name in result.stdout:
                subprocess.run(["taskkill", "/F", "/IM", process_name], check=True)
                print(f"Proceso {process_name} cerrado exitosamente.")
            else:
                print(f"Proceso {process_name} no estaba en ejecución.")
        except subprocess.CalledProcessError as e:
            print(f"No se pudo cerrar el proceso {process_name}: {e}")
    else:
        print(f"Navegador {browser_name} no reconocido.")


def clean_browser_cache(gui_output=None):
    """Limpia la caché de los navegadores compatibles."""
    # Cerrar procesos de navegadores antes de limpiar el caché
    for browser in ["Firefox", "Chrome", "Edge"]:
        close_browser_processes(browser)

    firefox_profiles = get_firefox_profiles()
    for profile in firefox_profiles:
        cache_path = profile / 'cache2'
        if cache_path.exists():
            delete_files_in_directory(cache_path, [], False, None, gui_output)
            log_message(f"Limpieza de caché de Firefox en {cache_path} completada.", gui_output)
        else:
            log_message(f"La caché de Firefox en {cache_path} no existe.", gui_output)

    chrome_profiles = get_chrome_profiles()
    for profile in chrome_profiles:
        cache_path = profile / 'Cache'
        if cache_path.exists():
            delete_files_in_directory(cache_path, [], False, None, gui_output)
            log_message(f"Limpieza de caché de Chrome en {cache_path} completada.", gui_output)
        else:
            log_message(f"La caché de Chrome en {cache_path} no existe.", gui_output)

    edge_profiles = get_edge_profiles()
    for profile in edge_profiles:
        cache_path = profile / 'Cache'
        if cache_path.exists():
            delete_files_in_directory(cache_path, [], False, None, gui_output)
            log_message(f"Limpieza de caché de Edge en {cache_path} completada.", gui_output)
        else:
            log_message(f"La caché de Edge en {cache_path} no existe.", gui_output)
