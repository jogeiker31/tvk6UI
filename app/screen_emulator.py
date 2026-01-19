"""
Módulo para el ScreenEmulator.

Emulador simple de terminal VT100 para reconstruir la pantalla del TVK6.
"""
import re

class ScreenEmulator:
    """Emulador simple de terminal VT100 para reconstruir la pantalla del TVK6."""
    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.screen = [[' ' for _ in range(cols)] for _ in range(rows)]
        self.cursor_pos = [0, 0]
        self.ansi_pattern = re.compile(r'\x1b\[([0-9;?]*)([A-Za-z])')
        self.incomplete_data_buffer = ""

    def reset(self):
        """Limpia la pantalla y resetea la posición del cursor."""
        self.screen = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_pos = [0, 0]
        self.incomplete_data_buffer = "" # También reseteamos el buffer

    def process_data(self, data: str):
        """Procesa un fragmento de datos, actualizando el estado de la pantalla."""
        data = self.incomplete_data_buffer + data
        self.incomplete_data_buffer = "" # Limpiamos el buffer una vez usado
        i = 0
        while i < len(data):
            char = data[i] 

            if char == '\x1b':
                i += 1 # Consumimos '\x1b'
                if i >= len(data): # Secuencia incompleta, guardamos y salimos
                    self.incomplete_data_buffer = "\x1b"
                    break

                if data[i] == '[': # Secuencia CSI (Control Sequence Introducer)
                    i += 1 # Consumimos '['
                    params_str = ""
                    while i < len(data) and data[i] in '0123456789;?':
                        params_str += data[i]
                        i += 1
                    
                    if i >= len(data): # Secuencia CSI incompleta
                        self.incomplete_data_buffer = "\x1b[" + params_str
                        break
                    else: # Secuencia CSI completa
                        command = data[i]
                        params = params_str.split(';')

                        if command == 'H': # Mover cursor
                            row = int(params[0]) - 1 if params and params[0] else 0
                            col = int(params[1]) - 1 if len(params) > 1 and params[1] else 0
                            self.cursor_pos = [max(0, min(row, self.rows - 1)), max(0, min(col, self.cols - 1))]
                        elif command == 'C': # Cursor Forward (CUF)
                            num_cols = int(params[0]) if params and params[0] else 1
                            self.cursor_pos[1] = min(self.cols - 1, self.cursor_pos[1] + num_cols)
                        elif command == 'D': # Cursor Backward (CUB)
                            num_cols = int(params[0]) if params and params[0] else 1
                            self.cursor_pos[1] = max(0, self.cursor_pos[1] - num_cols)
                        elif command == 'K': # Erase in Line (EL)
                            if not params_str or params_str == '0': # Por defecto: borrar desde el cursor hasta el final de la línea
                                row, col = self.cursor_pos
                                for c in range(col, self.cols):
                                    self.screen[row][c] = ' '
                        i += 1 
                elif data[i] in '#()': # Secuencias como ESC #6, ESC )0, ESC (B
                    i += 1 # Consumimos '#' o '(' o ')'
                    if i >= len(data): # Secuencia incompleta
                        self.incomplete_data_buffer = f"\x1b{data[i-1]}"
                        break
                    else: # Consumimos el siguiente carácter (ej. '6', '0', 'B')
                        i += 1
                else: # Otras secuencias de escape de un solo carácter (ej. ESC E)
                    i += 1
            else: # No es una secuencia de escape, es un carácter normal
                if char == '\n':
                    self.cursor_pos[0] += 1 # Mover a la siguiente línea
                elif char not in '\x0e\x0f\r':
                    row, col = self.cursor_pos
                    if row < self.rows and col < self.cols:
                        self.screen[row][col] = char
                        self.cursor_pos[1] += 1
                i += 1 # Avanzamos al siguiente carácter

    def get_screen_text(self) -> str:
        """Devuelve el contenido de la pantalla como un string multilinea."""
        return "\n".join("".join(row) for row in self.screen)