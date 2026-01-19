"""
Punto de entrada principal para la aplicación TVK6 Serial Console.

Este script inicia la aplicación Qt, crea la ventana principal y
ejecuta el bucle de eventos.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        # La carpeta 'resources' debe estar al mismo nivel que el ejecutable.
        base_path = sys._MEIPASS
    except Exception:
        # En desarrollo, la ruta base es el directorio del proyecto.
        base_path = os.path.abspath(".")
    
    # Construimos la ruta hacia la carpeta 'resources'
    return os.path.join(base_path, "resources", relative_path)

# --- Main ---
if __name__ == '__main__':
    QApplication.setOrganizationName("MiEmpresa")
    QApplication.setApplicationName("TVK6Nexo")

    # Nombre del archivo UI
    UI_FILE = resource_path('interfaz_tvk6.ui') # Ahora buscará en la carpeta 'resources'
    try:
        open(UI_FILE, 'r').close()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo de interfaz '{UI_FILE}'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(UI_FILE)
    window.show()
    sys.exit(app.exec())