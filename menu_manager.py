"""
Módulo para gestionar el menú dinámico de la aplicación.

Parsea la salida del TVK6 para encontrar opciones de menú y crea
botones dinámicamente en la interfaz.
"""
import re
from functools import partial
from PySide6.QtWidgets import QPushButton, QSizePolicy, QGroupBox, QVBoxLayout

class MenuManager:
    """Gestiona la creación y actualización del panel de menú dinámico."""

    def __init__(self, parent_ui, main_window):
        """
        Inicializa el gestor de menú.
        :param parent_ui: Referencia a la UI cargada (self.ui).
        :param main_window: Referencia a la instancia de MainWindow para enviar comandos.
        """
        self.main_window = main_window
        self.dynamic_menu_group_box = parent_ui.findChild(QGroupBox, 'groupBoxMenuDinamico')
        self.dynamic_menu_layout = parent_ui.findChild(QVBoxLayout, 'dynamicButtonVBoxLayout')
        if not self.dynamic_menu_group_box or not self.dynamic_menu_layout:
            raise RuntimeError("No se pudieron encontrar 'groupBoxMenuDinamico' o 'dynamicButtonVBoxLayout' en la UI.")
        self.buttons = []
        self.current_config = None
        self.current_menu_options = None

    def reset_history(self):
        """Limpia el historial de líneas, el menú actual y resetea el estado."""
        self.clear_menu()

    def clear_menu(self):
        """Elimina todos los botones actuales del menú dinámico."""
        for button in self.buttons:
            self.dynamic_menu_layout.removeWidget(button)
            button.deleteLater()
        self.buttons = []

    def create_button(self, number, text):
        """Crea y estiliza un nuevo botón para el menú."""
        button = QPushButton(f"{number}. {text.strip()}")
        button.setMinimumHeight(35)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Conectar el clic del botón para enviar el comando numérico
        # Usamos partial para "congelar" el valor de 'number' en el momento de la creación
        button.clicked.connect(partial(self.main_window.send_command, number))
        
        return button

    def update_menu_config(self, config):
        """Recibe la configuración del menú para el estado actual desde el StateManager."""
        self.current_config = config
        self.current_menu_options = None # Forzar redibujado si el menú cambia
        self.clear_menu()
        if self.current_config and 'title' in self.current_config:
            self.dynamic_menu_group_box.setTitle(self.current_config['title'])
        else:
            # Título por defecto si no hay menú o configuración
            self.dynamic_menu_group_box.setTitle("Comandos Rápidos")

    def parse_and_draw(self, screen_text):
        """Parsea el texto de la pantalla usando la configuración actual y dibuja los botones."""
        if not self.current_config:
            self.clear_menu() # Limpiamos si no hay menú que mostrar
            return

        menu_matches = None

        # Usar la lista de botones fijos si existe en la configuración.
        if 'buttons' in self.current_config:
            # Convertimos la lista de dicts a una tupla de tuplas para que coincida con el formato de regex.
            menu_matches = tuple((btn['number'], btn['text']) for btn in self.current_config['buttons'])

        # Si encontramos botones y son diferentes a los que ya mostramos, los redibujamos.
        if menu_matches and menu_matches != self.current_menu_options:
            self.current_menu_options = menu_matches
            self.clear_menu()
            for number, text in menu_matches:
                button = self.create_button(number, text.strip())
                self.dynamic_menu_layout.addWidget(button)
                self.buttons.append(button)