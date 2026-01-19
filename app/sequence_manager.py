"""
Módulo para el SequenceManager.

Gestiona la ejecución de una secuencia de comandos con retardos.
"""
from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer

class SequenceManager(QObject):
    """Gestiona la ejecución de una secuencia de comandos con retardos."""
    send_command = Signal(str)
    sequence_finished = Signal(str)

    def __init__(self, delay=500, parent=None):
        super().__init__(parent)
        self.command_queue = deque()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._send_next_command)
        self.delay = delay

    def start_sequence(self, commands):
        self.command_queue = deque(commands)
        self._send_next_command()

    def _send_next_command(self):
        if self.command_queue:
            command = self.command_queue.popleft()
            self.send_command.emit(command)
            if self.command_queue:
                self.timer.start(self.delay)
            else:
                self.sequence_finished.emit("Secuencia de calibración rápida completada.")