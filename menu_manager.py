"""
Módulo para gestionar el menú dinámico de la aplicación.

Parsea la salida del TVK6 para encontrar opciones de menú y crea
botones dinámicamente en la interfaz.
"""
import re
from functools import partial
from PySide6.QtWidgets import QPushButton, QSizePolicy, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel

class MenuManager:
    """Gestiona la creación y actualización del panel de menú dinámico."""

    def __init__(self, parent_ui, main_window):
        """
        Inicializa el gestor de menú.
        :param parent_ui: Referencia a la UI cargada (self.ui).
        :param main_window: Referencia a la instancia de MainWindow para enviar comandos.
        """
        self.main_window = main_window
        # Layout para la vista gráfica (horizontal)
        self.graphic_menu_layout = parent_ui.findChild(QHBoxLayout, 'graphicsHorizontalButtonLayout')

        # El graphicViewTitle fue eliminado, así que lo quitamos de la comprobación.
        if not self.graphic_menu_layout:
            raise RuntimeError("No se pudieron encontrar todos los widgets de menú en la UI.")
        
        self.graphic_buttons = []
        # Añadimos espaciadores al layout horizontal para centrar los botones
        self.graphic_menu_layout.addStretch(1)
        self.current_config = None
        self.current_menu_options = None

    def reset_history(self):
        """Limpia el historial de líneas, el menú actual y resetea el estado."""
        self.clear_menu()

    def clear_menu(self):
        """Elimina todos los botones actuales del menú dinámico."""
        for button in self.graphic_buttons:
            self.graphic_menu_layout.removeWidget(button)
            button.deleteLater()
        self.graphic_buttons = []

    def create_button(self, number, text, is_graphic_mode=False):
        """Crea y estiliza un nuevo botón para el menú."""
        button = QPushButton(f"{number}. {text.strip()}")
        button.setMinimumSize(120, 50)
        button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Conectar el clic del botón para enviar el comando numérico
        # Usamos partial para "congelar" el valor de 'number' y el flag 'from_button=True'
        # para indicar que la llamada viene de un clic de botón.
        button.clicked.connect(partial(self.main_window.send_command, number, from_button=True))
        
        return button

    def update_menu_config(self, config):
        """Recibe la configuración del menú para el estado actual desde el StateManager."""
        self.current_config = config
        self.current_menu_options = None # Forzar redibujado si el menú cambia
        self.clear_menu()

    def parse_and_draw(self, screen_text, force_config_name=None):
        """Parsea el texto de la pantalla usando la configuración actual y dibuja los botones."""
        config_to_use = self.current_config

        # Si se fuerza un nombre de configuración, lo usamos en su lugar.
        if force_config_name:
            config_to_use = self.main_window.state_manager.config['states'].get(force_config_name)

        if not config_to_use:
            self.clear_menu() # Limpiamos si no hay menú que mostrar
            return

        menu_matches = None

        if 'buttons' in config_to_use:
            menu_matches = tuple((btn['number'], btn['text']) for btn in config_to_use['buttons'])

        # Si encontramos botones y son diferentes a los que ya mostramos, los redibujamos.
        if menu_matches and menu_matches != self.current_menu_options:
            self.current_menu_options = menu_matches
            self.clear_menu()
            for number, text in menu_matches:
                # Crear botón para la vista gráfica
                graphic_button = self.create_button(number, text.strip(), is_graphic_mode=True)
                # Insertamos antes del espaciador final para mantener los botones centrados
                self.graphic_menu_layout.insertWidget(self.graphic_menu_layout.count() - 1, graphic_button)
                self.graphic_buttons.append(graphic_button)
        elif not menu_matches:
            self.clear_menu()