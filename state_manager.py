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
        self.parsed_values = {'X': '---', 'K': '---', 'M': '---', 'T': '---', 'U1': '---', 'I1': '---', 'di': '---', 'ds': '---'}
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
        # Parseo de X, K, M, T, U1
        # Estos valores pueden aparecer en DATOS_MEDIDOR_MENU, CALIBRAR_MENU y CALIBRAR_TABLE_VIEW
        if self.current_state in ['DATOS_MEDIDOR_MENU', 'CALIBRAR_MENU', 'CALIBRAR_TABLE_VIEW']:
            x_match = re.search(r'X\s*=\s*([0-9.]+)', screen_text)
            k_match = re.search(r'K\s*=\s*([0-9.]+)', screen_text)
            m_match = re.search(r'M\s*=\s*([0-9.]+)', screen_text)
            t_match = re.search(r'T\s*=\s*([0-9.]+)', screen_text)
            u1_match = re.search(r'U1\s*=\s*([0-9.]+)', screen_text)

            if x_match: self.parsed_values['X'] = x_match.group(1)
            if k_match: self.parsed_values['K'] = k_match.group(1)
            if m_match: self.parsed_values['M'] = m_match.group(1)
            if t_match: self.parsed_values['T'] = t_match.group(1)
            if u1_match: self.parsed_values['U1'] = u1_match.group(1)
        
        # Parseo de di, ds e I1
        # Estos valores aparecen en CALIBRAR_MENU y CALIBRAR_TABLE_VIEW
        if self.current_state in ['CALIBRAR_MENU', 'CALIBRAR_TABLE_VIEW']:
            screen_lines = screen_text.split('\n')
            if len(screen_lines) > 5: # Verificar si la línea 6 existe (índice 5)
                line_6 = screen_lines[5]
                # Parseo posicional para di, ds, e I1 en la línea 6
                # di está en las columnas 37-45
                if len(line_6) > 36:
                    di_val = line_6[36:45].strip()
                    if di_val: self.parsed_values['di'] = di_val
                # ds está en las columnas 46-54
                if len(line_6) > 45:
                    ds_val = line_6[45:54].strip()
                    if ds_val: self.parsed_values['ds'] = ds_val
                # I1 [A] está en las columnas 73-80
                if len(line_6) > 72: # Verificar si la columna 73 existe (índice 72)
                    i1_val = line_6[72:80].strip()
                    if i1_val:
                        self.parsed_values['I1'] = i1_val

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

        old_state = self.current_state # Capturar old_state antes de actualizar self.current_state

        if not from_history:
            # Solo añadimos al historial si es una navegación hacia adelante
            self.history.append(old_state) # Usar old_state para el historial
            print(f"Transición de estado: {old_state} -> {new_state}") # Usar old_state para el log
        
        self.current_state = new_state
        
        # Si estamos saliendo de la vista de tabla, reseteamos los valores de di y ds
        # para que se vuelvan a leer la próxima vez que entremos.
        if old_state == 'CALIBRAR_TABLE_VIEW' and self.current_state != 'CALIBRAR_TABLE_VIEW': # Usar self.current_state aquí
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