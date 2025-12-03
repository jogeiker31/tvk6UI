"""
Módulo del StateManager.

Gestiona el estado actual de la aplicación, las transiciones entre estados
y la configuración de los menús.
"""
import json
import re

class StateManager:
    """Gestiona la máquina de estados de la aplicación."""

    def __init__(self, menu_manager, config_file='menu_config.json'):
        self.menu_manager = menu_manager
        self.current_state = 'INIT'
        self._load_config(config_file)
        self.menu_manager.update_menu_config(None) # Iniciar sin menú

    def _load_config(self, config_file):
        """Carga la configuración de estados y menús desde un archivo JSON."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                # Precompilar todas las regex para eficiencia
                for state_data in self.config['states'].values():
                    if 'regex' in state_data:
                        state_data['regex_compiled'] = re.compile(state_data['regex'], re.UNICODE)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error cargando la configuración de estados: {e}")
            self.config = {'states': {}}

    def get_current_state_name(self):
        return self.current_state

    def process_screen_text(self, screen_text):
        """Analiza el texto de la pantalla para detectar cambios de estado automáticos."""
        if self.current_state == 'INIT':
            init_config = self.config['states'].get('INIT', {})
            keywords = init_config.get('detection_keywords', [])
            if all(keyword in screen_text for keyword in keywords):
                self.set_state(init_config.get('transition_to', 'MAIN_MENU'))
                return

        # Detección para otros menús que pueden aparecer sin un comando explícito
        state_config = self.config['states'].get(self.current_state, {})
        keywords = state_config.get('detection_keywords', [])
        if keywords and all(keyword in screen_text for keyword in keywords):
            # El menú coincide con el estado actual, pasamos la config al MenuManager
            self.menu_manager.update_menu_config(state_config)
            self.menu_manager.parse_and_draw(screen_text)

    def process_command(self, command):
        """Procesa un comando del usuario y realiza la transición de estado si corresponde."""
        command = command.lower()
        
        # Lógica de retorno genérica
        if command in ['esc', 'reset']:
            # Reglas de retorno específicas
            if self.current_state in ['DATOS_MEDIDOR_MENU', 'ENTRADAS_MENU']:
                self.set_state('MAIN_MENU')
            elif self.current_state in ['CALIBRAR_DATA_ENTRY', 'CALIBRAR_MENU']:
                 self.set_state('MAIN_MENU')
            else:
                self.set_state('INIT')
            return

        # Transiciones basadas en el estado actual
        state_config = self.config['states'].get(self.current_state, {})
        transitions = state_config.get('transitions', {})
        
        if command in transitions:
            self.set_state(transitions[command])

    def set_state(self, new_state):
        """Establece un nuevo estado y notifica al MenuManager."""
        print(f"Transición de estado: {self.current_state} -> {new_state}")
        self.current_state = new_state
        new_state_config = self.config['states'].get(new_state)
        self.menu_manager.update_menu_config(new_state_config)