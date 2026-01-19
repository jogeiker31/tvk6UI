"""
Módulo para el ProtocolSequenceManager.

Gestiona la ejecución de una secuencia de comandos de protocolo, enviando
cada comando carácter por carácter con retardos configurables.
"""
from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer

class ProtocolSequenceManager(QObject):
    """
    Gestiona el envío de datos de protocolo carácter por carácter.
    """
    send_char = Signal(str)
    send_enter = Signal()
    sequence_finished = Signal(str)

    def __init__(self, char_delay=100, field_delay=500, parent=None):
        super().__init__(parent)
        self.field_queue = deque()
        self.char_queue = deque()
        
        self.char_timer = QTimer(self)
        self.char_timer.setSingleShot(True)
        self.char_timer.timeout.connect(self._send_next_char)
        self.char_delay = char_delay

        self.field_timer = QTimer(self)
        self.field_timer.setSingleShot(True)
        self.field_timer.timeout.connect(self._send_next_field)
        self.field_delay = field_delay

    def start_sequence(self, fields):
        self.field_queue = deque(fields)
        self._send_next_field()

    def _send_next_field(self):
        if self.field_queue:
            field_text = self.field_queue.popleft()
            self.char_queue = deque(field_text)
            self._send_next_char()
        else:
            self.sequence_finished.emit("Secuencia de protocolo completada.")

    def _send_next_char(self):
        if self.char_queue:
            char = self.char_queue.popleft()
            self.send_char.emit(char)
            self.char_timer.start(self.char_delay)
        else: # Terminamos de enviar los caracteres de un campo
            self.send_enter.emit() # Enviamos el 'Enter'
            if self.field_queue:
                self.field_timer.start(self.field_delay) # Esperamos antes del siguiente campo
            else:
                self.sequence_finished.emit("Secuencia de protocolo completada.")