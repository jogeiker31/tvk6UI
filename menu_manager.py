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

    # Regex específica para el MENÚ PRINCIPAL.
    # Busca patrones como "1 ENTRADAS", "2 CALIBRAR", etc.
    MAIN_MENU_REGEX = re.compile(r'(\d)\s+([A-ZÁÉÍÓÚ\s\.]+?)(?=\s*\d|\s*$)', re.UNICODE)

    # Regex específica para el MENÚ DE ENTRADAS.
    # Busca patrones como "1 DAT.MEDID.", "2 DAT.SYST.", etc., que están más juntos.
    # El \s* permite cero o más espacios. El lookahead (?=\d|$) se detiene justo antes del siguiente dígito.
    ENTRADAS_MENU_REGEX = re.compile(r'(\d)\s*([A-ZÁÉÍÓÚ\s\.]+?)(?=\d|$)', re.UNICODE)

    def __init__(self, parent_ui, main_window, history_size=5):
        """
        Inicializa el gestor de menú.
        :param parent_ui: Referencia a la UI cargada (self.ui).
        :param main_window: Referencia a la instancia de MainWindow para enviar comandos.
        """
        self.main_window = main_window
        self.dynamic_menu_group_box = parent_ui.findChild(QGroupBox, 'groupBoxMenuDinamico')
        self.dynamic_menu_layout = self.dynamic_menu_group_box.layout()
        self.buttons = []
        self.line_history = []
        self.history_size = history_size

        # --- INICIO DE LA MODIFICACIÓN: MÁQUINA DE ESTADOS ---
        self.current_state = 'INIT' # Estado inicial
        self.current_menu_options = None
        # --- FIN DE LA MODIFICACIÓN ---


    def reset_history(self):
        """Limpia el historial de líneas, el menú actual y resetea el estado."""
        self.line_history = []
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

    def update_menu(self, cleaned_data):
        """
        Parsea los datos limpios, busca opciones de menú y actualiza la UI.
        
        :param cleaned_data: String de datos recibidos del serial, ya sin códigos ANSI.
        """
        # Añadimos las nuevas líneas limpias al historial.
        # Esto es crucial para reconstruir la pantalla si los datos llegan fragmentados.
        new_lines = cleaned_data.strip().splitlines()
        self.line_history.extend(new_lines)
        # Mantenemos el historial a un tamaño razonable para evitar acumulación excesiva.
        if len(self.line_history) > self.history_size:
            self.line_history = self.line_history[-self.history_size:]

        # Unimos todo el historial en una sola línea para aplicar el regex.
        # Esto maneja los casos donde el menú se fragmenta en múltiples recepciones.
        full_screen_text_for_parsing = " ".join(self.line_history).replace('\n', ' ')

        # Si el estado es INIT, asumimos que estamos esperando el menú principal.
        if self.current_state == 'INIT':
            # Buscamos la palabra clave que nos confirma que es el menú principal.
            if "ENTRADAS" in full_screen_text_for_parsing and "CALIBRAR" in full_screen_text_for_parsing:
                self.current_state = 'MAIN_MENU'

        # Lógica de parsing específica para cada estado
        if self.current_state == 'MAIN_MENU':
            menu_matches = tuple(self.MAIN_MENU_REGEX.findall(full_screen_text_for_parsing))

            # Si encontramos los botones y son diferentes a los que ya mostramos
            if menu_matches and menu_matches != self.current_menu_options:
                self.current_menu_options = menu_matches
                self.clear_menu()
                self.dynamic_menu_group_box.setTitle("Menú Principal")
                
                for number, text in menu_matches:
                    button = self.create_button(number, text)
                    self.dynamic_menu_layout.addWidget(button)
                    self.buttons.append(button)
        
        elif self.current_state == 'ENTRADAS_MENU':
            # La palabra clave para este menú es "DAT.MEDID."
            if "DAT.MEDID." in full_screen_text_for_parsing:
                menu_matches = tuple(self.ENTRADAS_MENU_REGEX.findall(full_screen_text_for_parsing))

                if menu_matches and menu_matches != self.current_menu_options:
                    self.current_menu_options = menu_matches
                    self.clear_menu()
                    self.dynamic_menu_group_box.setTitle("Entradas")

                    for number, text in menu_matches:
                        button = self.create_button(number, text)
                        self.dynamic_menu_layout.addWidget(button)
                        self.buttons.append(button)

    def set_state(self, new_state):
        """Permite a la ventana principal cambiar el estado del menú."""
        self.current_state = new_state
        # Al cambiar de estado, forzamos la limpieza del menú anterior.
        self.current_menu_options = None
        self.clear_menu()