"""
Punto de entrada principal para la aplicación TVK6 Serial Console.

Este script inicia la aplicación Qt, crea la ventana principal y
ejecuta el bucle de eventos.
"""
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow

# --- Main ---
if __name__ == '__main__':
    QApplication.setOrganizationName("MiEmpresa")
    QApplication.setApplicationName("TVK6SerialConsole")

    # Nombre del archivo UI
    UI_FILE = 'interfaz_tvk6.ui'
    try:
        open(UI_FILE, 'r').close()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo de interfaz '{UI_FILE}'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(UI_FILE)
    window.show()
    sys.exit(app.exec())