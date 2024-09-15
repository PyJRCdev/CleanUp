import threading
import os
import sys
import ctypes
import time
import logging
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from gui.utils import load_png_image, setup_logging, resource_path, setup_backup_directory
from gui.config import load_default_config, load_user_config, save_user_config
from core.cleanup import delete_files_in_directory, backup_and_delete, log_message
from core.browser_utils import clean_browser_cache, close_browser_processes
from core.disk_utils import optimize_disk
from datetime import datetime
from plyer import notification
from PIL import Image

# Variables globales
status_icons = {}
root = None
status_icon_label = None
status_text_label = None
directory_frame = None
directory_vars = {}
browser_frame = None
browser_vars = {}
secure_delete = False
backup = False
exclusions = []
selected_directories = []
selected_browsers = []
operations_log = []
progress_bar = []
gui_output = []


# Funciones Utilitarias
def is_admin():
    """Verifica si el script se está ejecutando como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Reinicia el script con permisos de administrador."""
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(sys.argv[0])}"', None, 1)
        except Exception as e:
            print(f"Error elevando permisos: {e}")
        sys.exit()


def show_instructions():
    instructions = (
        "Bienvenido a la aplicación de Optimización de Windows.\n\n"
        "Instrucciones de uso:\n"
        "1. Haz clic en 'Configuración' > 'Configuración de Limpieza'  \n"
        "2. Selecciona los directorios que deseas limpiar.\n"
        "3. Selecciona los navegadores cuyo caché deseas limpiar.\n"
        "4. Haz clic en 'Guardar Configuración' para guardar tu configuración de limpieza preferida\n"
        "5. Haz clic en 'Iniciar Limpieza' para comenzar el proceso.\n"
        "6. Revisa el estado y los mensajes en el Menú de Reportes para más detalles.\n"
        "7. Puedes programar limpiezas automáticas desde el menú 'Programar Limpieza'.\n\n"
        "Creado por Serra y en fase de desarrollo"
    )
    messagebox.showinfo("Instrucciones de Uso", instructions)


def update_status(status):
    """Actualiza el estado y el icono en la GUI."""
    icon = status_icons.get(status)
    if icon:
        try:
            status_icon_label.configure(image=icon)
            status_icon_label.image = icon
            status_text_label.configure(text=f"Estado: {status.replace('_', ' ').title()}")
        except Exception as e:
            print(f"Error al actualizar el estado con la imagen {status}: {e}")
            status_icon_label.configure(image=None)
            status_text_label.configure(text=f"Estado: {status.replace('_', ' ').title()}")
    else:
        print(f"Icono no encontrado para el estado: {status}")
        status_icon_label.configure(image=None)
        status_text_label.configure(text=f"Estado: {status.replace('_', ' ').title()}")


def update_directory_list(selected_directories):
    """Actualiza la lista de directorios en la GUI."""
    global directory_vars, directory_frame

    if directory_frame:
        for widget in directory_frame.winfo_children():
            widget.destroy()
    directory_frame = ctk.CTkFrame(root)
    directory_frame.pack(pady=10)
    directory_vars = {}
    for item in selected_directories:
        path = expand_environment_variables(item.get("path"))
        description = item.get("description")
        enabled = item.get("enabled", False)
        var = tk.BooleanVar(value=enabled)
        directory_vars[path] = var
        checkbox = ctk.CTkCheckBox(directory_frame, text=f"{description}", variable=var)
        checkbox.pack(anchor=tk.W, pady=2, padx=20)


def update_browser_list(selected_browsers):
    """Actualiza la lista de navegadores en la GUI."""
    global browser_vars, browser_frame
    if browser_frame:
        for widget in browser_frame.winfo_children():
            widget.destroy()
    browser_frame = ctk.CTkFrame(root)
    browser_frame.pack(pady=10)
    browsers = ["Chrome", "Firefox", "Edge", "Safari"]
    browser_vars = {}
    for browser in browsers:
        var = tk.BooleanVar(value=selected_browsers.get(browser, False))
        browser_vars[browser] = var
        browser_check = ctk.CTkCheckBox(browser_frame, text=browser, variable=var)
        browser_check.pack(anchor=tk.W, pady=2, padx=20)


def get_log_file_path():
    """Obtén la ruta del archivo de log en el directorio de la aplicación."""
    return Path(os.getcwd()) / "cleaning_log.txt"


def clean_up_traces():
    """Limpia los rastros y cierra la aplicación de manera segura."""
    log_file_path = get_log_file_path()
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)
    try:
        if log_file_path.exists():
            temp_file_path = log_file_path.with_suffix('.temp')
            log_file_path.rename(temp_file_path)
            time.sleep(1)
            temp_file_path.unlink()
            print("Archivo cleaning_log.txt eliminado exitosamente.")
        else:
            print("Archivo cleaning_log.txt no encontrado.")
    except PermissionError:
        messagebox.showerror("Error", "Archivo cleaning_log.txt en uso, no se pudo eliminar.")
    except Exception as e:
        messagebox.showerror("Error inesperado", f"Error al intentar eliminar cleaning_log.txt: {e}")
    if root:
        root.destroy()


def load_status_icons():
    """Cargar los iconos de estado."""
    global status_icons
    try:
        process_image = Image.open(resource_path("gui/assets/process.png"))
        completed_image = Image.open(resource_path("gui/assets/completed.png"))
        error_image = Image.open(resource_path("gui/assets/error.png"))

        # Convertir imágenes PIL a CTkImage
        status_icons = {
            'En proceso': ctk.CTkImage(light_image=process_image, dark_image=process_image),
            'Completado': ctk.CTkImage(light_image=completed_image, dark_image=completed_image),
            'Error': ctk.CTkImage(light_image=error_image, dark_image=error_image)
        }
        print("Iconos cargados exitosamente.")
    except FileNotFoundError as e:
        print(f"Error al cargar iconos: {e}")


def create_gui():
    global root, status_icon_label, status_text_label, directory_frame, directory_vars, secure_delete, backup, \
        exclusions, selected_directories, selected_browsers, gui_output, progress_bar

    # Cargar configuraciones
    default_config = load_default_config()
    user_config = load_user_config()

    # Configuración predeterminada del usuario
    selected_directories = user_config.get("directories", default_config["directories"])
    selected_browsers = user_config.get("browsers", default_config["browsers"])
    secure_delete = user_config.get("secure_delete", default_config["secure_delete"])
    backup = user_config.get("backup", default_config["backup"])

    ctk.set_appearance_mode("system")
    theme_path = resource_path('gui/theme/blue.json')
    ctk.set_default_color_theme(theme_path)

    root = ctk.CTk()
    root.title("CLEAN UP")
    window_width = 750
    window_height = 650

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    position_x = int((screen_width / 2) - (window_width / 2))
    position_y = int((screen_height / 2) - (window_height / 2))

    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
    root.resizable(False, False)

    title_label = ctk.CTkLabel(root, text="Optimización de Windows", font=ctk.CTkFont(size=22, weight="bold"))
    title_label.pack(pady=20)

    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)
    instructions_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Instrucciones", menu=instructions_menu)
    instructions_menu.add_command(label="Instrucciones de uso", command=show_instructions)

    reports_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Reportes", menu=reports_menu)
    reports_menu.add_command(label="Ver Reporte Detallado", command=show_report)

    settings_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Configuración", menu=settings_menu)
    settings_menu.add_command(label="Configuración de Limpieza", command=show_config_window)

    status_frame = ctk.CTkFrame(root, fg_color='transparent')
    status_frame.pack(pady=10)

    status_icon_label = ctk.CTkLabel(status_frame, text=None)  # Inicializar sin imagen
    status_icon_label.pack(side=tk.LEFT, padx=10)

    status_text_label = ctk.CTkLabel(status_frame, text="Estado: Preparado", font=ctk.CTkFont(size=14))
    status_text_label.pack(side=tk.LEFT)

    gui_output = ctk.CTkTextbox(root, width=700, height=250, wrap="word", border_width=2)
    gui_output.pack(pady=10)

    progress_bar = ctk.CTkProgressBar(root, width=550, mode="determinate")
    progress_bar.set(0)
    progress_bar.pack(pady=15)

    button_frame = ctk.CTkFrame(root, fg_color='transparent')
    button_frame.pack(pady=20)

    start_button = ctk.CTkButton(button_frame, text="Iniciar Limpieza",
                                 command=start_cleanup)
    start_button.grid(row=0, column=0, padx=15)

    schedule_button = ctk.CTkButton(button_frame, text="Programar Limpieza",
                                    command=lambda: schedule_cleanup(7, gui_output))
    schedule_button.grid(row=0, column=1, padx=15)

    quit_button = ctk.CTkButton(button_frame, text="Salir", command=clean_up_traces)
    quit_button.grid(row=0, column=2, padx=15)

    load_status_icons()

    # Mostrar instrucciones al inicio
    root.after(1000, show_instructions)  # Muestra las instrucciones después de 1000 ms (1 segundo)

    root.mainloop()


def log_operation(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    operations_log.append(f"{timestamp} - {message}")
    log_message(f"{timestamp} - {message}")


def generate_detailed_report(operations_log, post_report=None):
    report_path = Path("cleaning_report.txt")
    with report_path.open("a") as report_file:
        report_file.write("\n--- INFORMACION DE LA LIMPIEZA ---\n")
        for entry in operations_log:
            report_file.write(f"{entry}\n")

        report_file.write("\nInforme de Desfragmentación:\n")
        if post_report:
            report_file.write("Informe Después de la Desfragmentación:\n")
            report_file.write(post_report + "\n")
        else:
            report_file.write("Informe Después de la Desfragmentación: No disponible\n")


def run_cleanup_with_progress(config, gui_output, progress_bar):
    exclusions = config.get("exclusions", [])
    secure = config.get("secure_delete", False)
    if config.get("backup", False):
        backup_directory = setup_backup_directory() if config.get("backup",
                                                                  False) else None  # Crear el directorio de respaldo
    else:
        backup_directory = None

    total_steps = 6
    step_size = 100 / total_steps

    def update_progress(step):
        progress_bar.set(step * step_size / 100)
        root.update_idletasks()

    def safe_update_status(status):
        root.after(0, update_status, status)

    try:
        gui_output.insert(ctk.END, "Iniciando limpieza...\n")
        root.update_idletasks()
        safe_update_status('En proceso')
        update_progress(1)

        # Realizar la limpieza basada en la configuración del usuario
        directories = config.get("directories", [])
        for directory in directories:
            path = directory.get("path")
            if directory_vars.get(path) and directory_vars[path].get():  # Verificar si el directorio está habilitado
                path = expand_environment_variables(path)
                log_operation(f"Limpieza de {path} iniciada.")
                delete_files_in_directory(path, exclusions, secure, backup_directory, gui_output)
                log_operation(f"Limpieza de {path} completada.")
                gui_output.insert(ctk.END, f"Limpieza de {path} completada.\n")
                root.update_idletasks()
        update_progress(2)

        # Verificar si hay navegadores seleccionados antes de ejecutar cualquier acción de limpieza
        if any(browser_vars[browser].get() for browser in browser_vars):
            for browser in ["Edge", "Chrome", "Firefox", "Safari"]:
                if browser_vars.get(browser, False):
                    close_browser_processes(browser)
            clean_browser_cache(gui_output)
        update_progress(3)

        post_report = optimize_disk(gui_output)
        update_progress(4)

        gui_output.insert(ctk.END, "Optimización de disco completada.\n")
        root.update_idletasks()
        update_progress(5)

        gui_output.insert(ctk.END, "Limpieza finalizada con éxito\n")
        log_operation("Proceso de optimización finalizado.")
        update_progress(6)

        generate_detailed_report(operations_log, post_report)

        messagebox.showinfo("Información", "El proceso de limpieza ha finalizado correctamente.")
        notify_user("Estado: Completado")
        safe_update_status('Completado')

    except Exception as e:
        log_operation(f"Error durante el proceso de limpieza: {e}")
        messagebox.showinfo("Información", "Se ha producido un error durante el proceso de limpieza.")
        notify_user("Estado: Error")
        gui_output.insert(ctk.END, f"Error: {e}\n")
        root.update_idletasks()
        safe_update_status('Error')


def start_cleanup():
    config = load_user_config()
    cleanup_thread = threading.Thread(target=run_cleanup_with_progress,
                                      args=(load_user_config(), gui_output, progress_bar))
    cleanup_thread.start()


def show_report():
    try:
        with open("cleaning_report.txt", "r") as report_file:
            report_text = report_file.read()

        report_window = ctk.CTkToplevel(root)
        report_window.title("Reporte Detallado")
        report_window.geometry("600x500")

        report_textbox = ctk.CTkTextbox(report_window, width=580, height=450, wrap="word", border_width=2)
        report_textbox.pack(pady=20)
        report_textbox.insert(ctk.END, report_text)
    except FileNotFoundError:
        messagebox.showerror("Error", "No se encontró el reporte detallado.")
    except Exception as e:
        messagebox.showerror("Error inesperado", f"Error al intentar mostrar el reporte: {e}")


def show_config_window():
    global directory_vars, browser_vars, secure_delete, backup

    config = load_default_config() or {"directories": []}

    # Crear ventana de configuración
    config_window = ctk.CTkToplevel(root)
    config_window.title("Configuración de Limpieza")
    config_window.geometry("500x600")

    # Frame para directorios
    directory_frame = ctk.CTkFrame(config_window)
    directory_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    directory_label = ctk.CTkLabel(directory_frame, text="Selecciona los Directorios a Limpiar:")
    directory_label.pack(pady=5)

    directory_vars = {}
    for item in config.get("directories", []):
        path = item.get("path")
        description = item.get("description")
        var = tk.BooleanVar(value=item.get("enabled", False))
        directory_vars[path] = var

        checkbox = ctk.CTkCheckBox(directory_frame, text=f"{description}", variable=var)
        checkbox.pack(anchor=tk.W, pady=2, padx=20)

    # Frame para navegadores
    browser_frame = ctk.CTkFrame(config_window)
    browser_frame.pack(pady=8, fill=tk.BOTH, expand=True)

    browser_label = ctk.CTkLabel(browser_frame, text="Selecciona los Navegadores a Limpiar:")
    browser_label.pack(pady=5)

    browsers = ["Chrome", "Firefox", "Edge", "Safari"]
    browser_vars = {}
    for browser in browsers:
        var = tk.BooleanVar(value=config.get("browsers", {}).get(browser, False))
        browser_vars[browser] = var
        browser_check = ctk.CTkCheckBox(browser_frame, text=browser, variable=var)
        browser_check.pack(anchor=tk.W, pady=2, padx=20)

    # Configuración de la opción de respaldo
    backup_var = tk.BooleanVar(value=config.get("backup", False))
    backup_checkbox = ctk.CTkCheckBox(config_window, text="Crear Respaldo", variable=backup_var)
    backup_checkbox.pack(pady=10)

    # Guardar configuración
    def save_changes():
        config["directories"] = [{"path": path, "description": "Descripción", "enabled": var.get()} for path, var in
                                 directory_vars.items()]
        config["browsers"] = {browser: var.get() for browser, var in browser_vars.items()}
        config["secure_delete"] = secure_delete
        config["backup"] = backup_var.get()
        save_user_config(config)
        config_window.destroy()

    save_button = ctk.CTkButton(config_window, text="Guardar Configuración", command=save_changes)
    save_button.pack(pady=20)


def schedule_cleanup(interval_days, gui_output):
    def scheduled_cleanup():
        while True:
            time.sleep(interval_days * 24 * 60 * 60)
            run_cleanup_with_progress(load_user_config(), gui_output, None)

    thread = threading.Thread(target=scheduled_cleanup)
    thread.daemon = True
    thread.start()


def expand_environment_variables(path):
    return os.path.expandvars(path)


def notify_user(message):
    notification.notify(
        title='Optimización de Windows',
        message=message,
        app_icon=str(resource_path("gui/assets/clear.ico")),
        timeout=10,
    )


if __name__ == "__main__":
    run_as_admin()
    setup_logging()
    create_gui()
