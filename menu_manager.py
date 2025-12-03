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
    MAIN_MENU_REGEX = re.compile(r'(\d)\s+([A-ZÁÉÍÓÚ\s\.]+?)(?=\s+\d|$)', re.UNICODE)

    # Regex específica para el MENÚ DE ENTRADAS.
    # Busca patrones como "1 DAT.MEDID.", "2 DAT.SYST.", etc., que están más juntos.
    # El \s* permite cero o más espacios. El lookahead (?=\d|$) se detiene justo antes del siguiente dígito.
    ENTRADAS_MENU_REGEX = re.compile(r'(\d)\s*([A-ZÁÉÍÓÚ\s\.]+?)(?=\d|$)', re.UNICODE)

    # Regex específica para el MENÚ "DATOS MEDIDOR".
    # Busca patrones como "1 X [r/kWh]", "2 K", etc., incluyendo corchetes y barras.
    # Esta regex es más robusta: busca un dígito seguido de un espacio, al principio de la línea de menú.
    # (^|\s{2,}) asegura que estamos al inicio de la línea o después de varios espacios.
    DATOS_MEDIDOR_MENU_REGEX = re.compile(r'(?:^|\s{2,})(\d)\s+([A-Z0-9\[\]./].*?)(?=\s+\d\s+|$)', re.UNICODE)

    # Regex específica para el MENÚ "CALIBRACION".
    # Busca patrones como "1 COMIENZO", "2 x.x   x.xx", etc.
    # El lookahead (?=\s+\d\s|$) busca el inicio del siguiente botón o el final de la línea.
    # Es no codicioso (non-greedy) para capturar solo hasta el siguiente botón.
    CALIBRAR_MENU_REGEX = re.compile(r'(\d)\s+([A-Za-z0-9./\s]+?)(?=\s+\d\s|$)', re.UNICODE)

    def __init__(self, parent_ui, main_window, history_size=5): # history_size ya no se usa pero lo dejamos por compatibilidad
        """
        Inicializa el gestor de menú.
        :param parent_ui: Referencia a la UI cargada (self.ui).
        :param main_window: Referencia a la instancia de MainWindow para enviar comandos.
        """
        self.main_window = main_window
        self.dynamic_menu_group_box = parent_ui.findChild(QGroupBox, 'groupBoxMenuDinamico')
        self.dynamic_menu_layout = self.dynamic_menu_group_box.layout()
        self.buttons = []

        # --- INICIO DE LA MODIFICACIÓN: MÁQUINA DE ESTADOS ---
        self.current_state = 'INIT' # Estado inicial
        self.current_menu_options = None
        # --- FIN DE LA MODIFICACIÓN ---


    def reset_history(self):
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

    def update_menu(self, cleaned_data):
        """
        Parsea los datos limpios, busca opciones de menú y actualiza la UI.
        
        :param cleaned_data: String de datos recibidos del serial, ya sin códigos ANSI.
        """
        # Usamos el texto de la pantalla directamente. El emulador ya nos da la vista completa.
        full_screen_text_for_parsing = cleaned_data

        # Si el estado es INIT, asumimos que estamos esperando el menú principal.
        if self.current_state == 'INIT':
            # Buscamos la palabra clave que nos confirma que es el menú principal.
            if "ENTRADAS" in full_screen_text_for_parsing and "CALIBRAR" in full_screen_text_for_parsing:
                self.current_state = 'MAIN_MENU'

        # Lógica de parsing específica para cada estado
        if self.current_state == 'MAIN_MENU':
            menu_matches = tuple(self.MAIN_MENU_REGEX.findall(full_screen_text_for_parsing.replace('\n', ' ')))

            # Si encontramos los botones y son diferentes a los que ya mostramos
            if menu_matches and menu_matches != self.current_menu_options:
                self.current_menu_options = menu_matches
                self.clear_menu()
                self.dynamic_menu_group_box.setTitle("Menú Principal")
                
                for number, text in menu_matches:
                    # Limpiamos el texto para quedarnos solo con la parte relevante del menú
                    # Simplemente limpiamos espacios al inicio/final. La regex ya hace el trabajo pesado.
                    clean_text = text.strip()
                    button = self.create_button(number, clean_text)
                    self.dynamic_menu_layout.addWidget(button)
                    self.buttons.append(button)
        
        elif self.current_state == 'ENTRADAS_MENU':
            # La palabra clave para este menú es "DAT.MEDID."
            if "DAT.MEDID." in full_screen_text_for_parsing:
                # Debugging: Imprimimos el texto que se está usando para el regex
                print(f"text for parsing (ENTRADAS): {full_screen_text_for_parsing.replace(chr(10), ' ')}")
                menu_matches = tuple(self.ENTRADAS_MENU_REGEX.findall(full_screen_text_for_parsing.replace('\n', ' ')))
                print(f"MENU MATCHES (ENTRADAS): {menu_matches!r}")
                if menu_matches and menu_matches != self.current_menu_options:
                    self.current_menu_options = menu_matches
                    self.clear_menu()
                    self.dynamic_menu_group_box.setTitle("Entradas")

                    for number, text in menu_matches:
                        # Limpiamos el texto para quedarnos solo con la parte relevante del menú
                        # Simplemente limpiamos espacios al inicio/final.
                        clean_text = text.strip()
                        button = self.create_button(number, clean_text)
                        self.dynamic_menu_layout.addWidget(button)
                        self.buttons.append(button)
        
        elif self.current_state == 'DATOS_MEDIDOR_MENU':
            # La palabra clave para este menú es "DATOS MEDIDOR" o "X ="
            if "DATOS MEDIDOR" in full_screen_text_for_parsing or "X =" in full_screen_text_for_parsing:
                # Debugging: Imprimimos el texto que se está usando para el regex
                print(f"text for parsing (DATOS MEDIDOR): {full_screen_text_for_parsing.replace(chr(10), ' ')}")
                # --- INICIO DE LA MODIFICACIÓN: Aplicar regex solo a la última línea ---
                # Dividimos la pantalla en líneas y tomamos la última que no esté vacía.
                last_line = next((line for line in reversed(full_screen_text_for_parsing.split('\n')) if line.strip()), "")
                menu_matches = tuple(self.DATOS_MEDIDOR_MENU_REGEX.findall(last_line))
                # --- FIN DE LA MODIFICACIÓN ---
                print(f"MENU MATCHES (DATOS MEDIDOR): {menu_matches}")
                
                # Si encontramos botones, los redibujamos.
                # Simplificamos la lógica: si encontramos botones y son diferentes a los que ya mostramos, actualizamos.
                if menu_matches and tuple(sorted(menu_matches)) != self.current_menu_options:
                    self.current_menu_options = tuple(sorted(menu_matches)) # Guardamos el nuevo estado
                    self.clear_menu()
                    # --- INICIO DE LA MODIFICACIÓN: Título dinámico ---
                    # Si el título de la pantalla está presente, lo usamos.
                    title_match = re.search(r'DATOS\s+MEDIDOR', full_screen_text_for_parsing)
                    title = title_match.group(0).strip() if title_match else "Datos Medidor"
                    # --- FIN DE LA MODIFICACIÓN ---
                    self.dynamic_menu_group_box.setTitle("Datos Medidor")

                    for number, text in menu_matches:
                        clean_text = text.strip()
                        button = self.create_button(number, clean_text)
                        self.dynamic_menu_layout.addWidget(button)
                        self.buttons.append(button)
        
        elif self.current_state == 'CALIBRAR_MENU':
            # La palabra clave para este menú es "CALIBRACION"
            if "CALIBRACION" in full_screen_text_for_parsing:
                # Debugging
                last_line = next((line for line in reversed(full_screen_text_for_parsing.split('\n')) if line.strip()), "")
                print(f"text for parsing (CALIBRAR): {last_line!r}")
                menu_matches = tuple(self.CALIBRAR_MENU_REGEX.findall(last_line))
                print(f"MENU MATCHES (CALIBRAR): {menu_matches}")

                if menu_matches and tuple(sorted(menu_matches)) != self.current_menu_options:
                    self.current_menu_options = tuple(sorted(menu_matches))
                    self.clear_menu()
                    self.dynamic_menu_group_box.setTitle("Calibración") # Título del menú

                    for number, text in menu_matches:
                        clean_text = text.strip()
                        button = self.create_button(number, clean_text)
                        self.dynamic_menu_layout.addWidget(button)
                        self.buttons.append(button)

        # --- INICIO DE LA MODIFICACIÓN: Lógica de título simplificada ---
        # Si los botones del menú de calibración están visibles, pero el estado no es CALIBRAR_MENU,
        # significa que estamos en modo de edición.
        if self.current_state == 'CALIBRAR_DATA_ENTRY' and self.current_menu_options:
            self.dynamic_menu_group_box.setTitle("Calibración (Editando)")
        # --- FIN DE LA MODIFICACIÓN ---

    def set_state(self, new_state):
        """Permite a la ventana principal cambiar el estado del menú."""
        self.current_state = new_state
        self.current_menu_options = None
        self.clear_menu()