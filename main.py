"""
Punto de entrada principal para la aplicación TVK6 Serial Console.

Este script inicia la aplicación Qt, crea la ventana principal y
ejecuta el bucle de eventos.
"""
import sys
import os
from PySide6.QtWidgets import QApplication

from main_window import MainWindow

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Main ---
if __name__ == '__main__':
    QApplication.setOrganizationName("MiEmpresa")
    QApplication.setApplicationName("TVK6SerialConsole")

    # Nombre del archivo UI
    UI_FILE = resource_path('interfaz_tvk6.ui')
    try:
        open(UI_FILE, 'r').close()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo de interfaz '{UI_FILE}'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(UI_FILE)
    window.show()
    sys.exit(app.exec())