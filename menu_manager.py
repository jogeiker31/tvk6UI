"""
Módulo para gestionar el menú dinámico de la aplicación.

Parsea la salida del TVK6 para encontrar opciones de menú y crea
botones dinámicamente en la interfaz.
"""
import re
from functools import partial
from PySide6.QtWidgets import QPushButton, QSizePolicy, QGroupBox

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
        self.dynamic_menu_layout = self.dynamic_menu_group_box.layout()
        self.buttons = []
        self.current_menu_options = None
        self.current_config = None

    def reset(self):
        """Limpia el historial de líneas, el menú actual y resetea el estado."""
        self.current_menu_options = None
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
        """Recibe una nueva configuración de menú desde el StateManager."""
        self.current_config = config
        self.reset()
        if self.current_config and 'title' in self.current_config:
            self.dynamic_menu_group_box.setTitle(self.current_config['title'])
        else:
            self.dynamic_menu_group_box.setTitle("Comandos Rápidos")

    def parse_and_draw(self, screen_text):
        """
        Parsea el texto de la pantalla usando la configuración actual y dibuja los botones.
        """
        if not self.current_config or 'regex_compiled' not in self.current_config:
            return # No hay nada que parsear para este estado

        # Algunos menús están en una sola línea, otros en varias.
        # Para ser robustos, podemos buscar en la última línea o en todo el texto.
        # Por ahora, reemplazamos saltos de línea por espacios para una búsqueda global.
        search_text = screen_text.replace('\n', ' ')
        
        menu_matches = tuple(self.current_config['regex_compiled'].findall(search_text))

        if menu_matches and menu_matches != self.current_menu_options:
            self.current_menu_options = menu_matches
            self.clear_menu()
            
            for number, text in menu_matches:
                clean_text = text.strip()
                button = self.create_button(number, clean_text)
                self.dynamic_menu_layout.addWidget(button)
                self.buttons.append(button)