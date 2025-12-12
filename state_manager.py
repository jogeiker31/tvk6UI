"""
Módulo del StateManager.

Gestiona el estado actual de la aplicación, las transiciones entre estados
y la configuración de los menús.
"""
import json
import re
from PySide6.QtCore import QObject, Signal # Import QObject and Signal

class StateManager(QObject): # Inherit from QObject
    """Gestiona la máquina de estados de la aplicación."""
    clear_screen_requested = Signal() # Nueva señal para solicitar limpieza de pantalla

    def __init__(self, menu_manager, config_file='menu_config.json'):
        super().__init__() # ¡Llamada crucial al constructor de QObject!
        self.menu_manager = menu_manager
        self.current_state = 'INIT'
        self._load_config(config_file)
        self.history = [] # Pila para el historial de navegación
        self.parsed_values = {'X': '---', 'K': '---', 'U1': '---', 'I1': '---', 'di': '---', 'ds': '---'}
        self.menu_manager.update_menu_config(None) # Iniciar sin menú

    def _load_config(self, config_file):
        """Carga la configuración de estados y menús desde un archivo JSON."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error cargando la configuración de estados: {e}")
            self.config = {'states': {}}

    def get_current_state_name(self):
        return self.current_state

    def process_screen_text(self, screen_text, measurement_panel=None):
        """Analiza el texto de la pantalla para detectar cambios de estado automáticos."""
        # Parseo de datos de medición
        x_match = re.search(r'X\s*=\s*([0-9.]+)', screen_text)
        k_match = re.search(r'K\s*=\s*([0-9.]+)', screen_text)
        u1_match = re.search(r'U1\s*=\s*([0-9.]+)', screen_text)

        # --- INICIO DE LA MODIFICACIÓN: Parseo robusto de di y ds ---
        # Buscamos la línea que contiene "di" y "ds" y la línea siguiente que contiene los valores.
        # Esto es más robusto que buscar el texto y el número juntos.
        # La regex busca la línea de cabecera y luego, en la línea de datos, captura los valores
        # que están aproximadamente bajo 'di' y 'ds'. Solo lo hacemos si aún no los tenemos.
        if self.current_state == 'CALIBRAR_MENU':
            di_ds_match = re.search(r'di\s+ds.*\n.*?\s+(-?[0-9.]+)\s+(-?[0-9.]+)', screen_text, re.DOTALL)
            if di_ds_match:
                di_val, ds_val = di_ds_match.groups()
                self.parsed_values['di'] = di_val
                self.parsed_values['ds'] = ds_val

        # El valor de I1 [A] se encuentra al final de la línea que empieza con "1 ".
        # La salida del TVK6 es posicional, por lo que esta es una forma más robusta
        # de encontrar el valor, incluso si los espacios varían.
        # La regex busca una línea que empiece con "1" (y espacios), y captura el último
        # número flotante/entero en esa línea.
        # Buscamos la línea que contiene los valores de 'di' y 'ds' (-100.0, 100.0)
        # y capturamos el último número flotante en esa línea, que corresponde a I1.
        calib_data_line_match = re.search(r'^\s*.*-100\.0\s+100\.0\s+.*?\s+([0-9.-]+)\s*$', screen_text, re.MULTILINE)
        if calib_data_line_match:
            # El último grupo capturado en esa línea es el valor de I1
            self.parsed_values['I1'] = calib_data_line_match.group(1).strip()

        if x_match:
            self.parsed_values['X'] = x_match.group(1)
        if k_match:
            self.parsed_values['K'] = k_match.group(1)
        if u1_match:
            self.parsed_values['U1'] = u1_match.group(1)

        if measurement_panel:
            measurement_panel.update_display(self.parsed_values)

        # --- INICIO DE LA MODIFICACIÓN: Bloquear detección en modos de entrada de datos ---
        # Si estamos en un estado de entrada de datos, no intentamos detectar un nuevo
        # estado a partir de la pantalla, ya que esta se redibuja constantemente.
        # El estado solo cambiará por una acción explícita del usuario (comando 'esc', 'reset', etc.).
        if self.current_state in ['CALIBRAR_DATA_ENTRY', 'CALIBRAR_TABLE_VIEW']:
            # --- INICIO DE LA MODIFICACIÓN: Salida de CALIBRAR_DATA_ENTRY ---
            # Excepción: si estamos en CALIBRAR_DATA_ENTRY y recibimos la pantalla del menú de calibración,
            # forzamos la transición de vuelta. Esto es crucial para la secuencia de automatización.
            if self.current_state == 'CALIBRAR_DATA_ENTRY' and all(keyword in screen_text for keyword in self.config['states']['CALIBRAR_MENU']['detection_keywords']):
                self.set_state('CALIBRAR_MENU')
                return # Salimos después de hacer la transición
            # --- FIN DE LA MODIFICACIÓN ---
            # --- INICIO DE LA MODIFICACIÓN: Forzar redibujado si es necesario ---
            # Si estamos en la vista de tabla, nos aseguramos de que el menú se mantenga
            # correctamente configurado, incluso si no hay cambio de estado.
            current_config = self.config['states'].get(self.current_state, {})
            self.menu_manager.update_menu_config(current_config)
            # --- FIN DE LA MODIFICACIÓN ---
            return

        # Detección de estado/menú
        # Primero, intentamos detectar si la pantalla corresponde a un nuevo estado.
        for state_name, state_data in self.config['states'].items():
            keywords = state_data.get('detection_keywords', [])
            if keywords and all(keyword in screen_text for keyword in keywords):
                # Si se detecta un nuevo estado y es diferente al actual, realizamos la transición.
                if state_name != self.current_state:
                    self.set_state(state_name) # La lógica de historial se maneja dentro de set_state
                break # Dejamos de buscar una vez que encontramos una coincidencia

        # Una vez que el estado es el correcto, dibujamos el menú si es necesario.
        current_config = self.config['states'].get(self.current_state, {})
        if 'buttons' in current_config:
            self.menu_manager.parse_and_draw(screen_text)

    def process_command(self, command):
        """Procesa un comando del usuario y realiza la transición de estado si corresponde."""
        command = command.lower()
        current_config = self.config['states'].get(self.current_state, {})
        
        # --- INICIO DE LA MODIFICACIÓN: Sistema de navegación basado en historial ---
        if command == 'reset':
            self.history = [] # Limpiamos el historial
            self.clear_screen_requested.emit() # Siempre limpiar pantalla en reset
            self.set_state('MAIN_MENU')
            return
        
        if command == 'esc':
            # Ver si hay una regla de escape específica en el JSON
            # Si estamos en cualquier estado que no sea el menú principal, volvemos a él.
            if self.current_state != 'MAIN_MENU':
                self.clear_screen_requested.emit() # Limpiar pantalla al retornar al MAIN_MENU
                self.set_state('MAIN_MENU')
            # Si ya estamos en el menú principal, 'esc' no hace nada.
            return
        # --- FIN DE LA MODIFICACIÓN ---

        # Transiciones basadas en el estado actual
        transitions = current_config.get('transitions', {})
        
        if command in transitions:
            transition_data = transitions[command]
            
            # Comprobar si la transición está en el nuevo formato de diccionario
            if isinstance(transition_data, dict):
                new_state = transition_data.get('target')
                clear_screen = transition_data.get('clear_screen', False)

                if clear_screen:
                    self.clear_screen_requested.emit()
                
                if new_state:
                    self.set_state(new_state)
            else: # Mantener compatibilidad con el formato antiguo (string)
                self.set_state(transition_data)

    def set_state(self, new_state, from_history=False):
        """Establece un nuevo estado y notifica al MenuManager."""
        if self.current_state == new_state:
            return # No hacer nada si el estado ya es el actual

        if not from_history:
            # Solo añadimos al historial si es una navegación hacia adelante
            self.history.append(self.current_state)
            print(f"Transición de estado: {self.current_state} -> {new_state}")
        
        self.current_state = new_state
        
        # Si estamos saliendo de la vista de tabla, reseteamos los valores de di y ds
        # para que se vuelvan a leer la próxima vez que entremos.
        if old_state == 'CALIBRAR_TABLE_VIEW' and new_state != 'CALIBRAR_TABLE_VIEW':
            self.parsed_values['di'] = '---'
            self.parsed_values['ds'] = '---'
        # --- INICIO DE LA MODIFICACIÓN: Limpiar botones en modo de entrada de datos ---
        # Si el nuevo estado es un modo de entrada de datos, no mostramos botones dinámicos.
        if new_state in ['CALIBRAR_DATA_ENTRY']:
            new_state_config = self.config['states'].get(new_state, {})
        else:
            new_state_config = self.config['states'].get(new_state)
        # --- FIN DE LA MODIFICACIÓN ---
        self.menu_manager.update_menu_config(new_state_config)