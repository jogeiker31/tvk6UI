"""
Módulo para el SerialConnectionManager.

Encapsula la lógica de creación, gestión y destrucción del QThread y
el SerialWorker para la comunicación serial.
"""
from PySide6.QtCore import QThread

from serial_worker import SerialWorker

class SerialConnectionManager:
    """Gestiona el ciclo de vida del hilo de comunicación serial."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.thread = None
        self.worker = None

    def start_connection(self, port: str):
        """
        Detiene cualquier conexión existente e inicia una nueva en el puerto especificado.
        """
        self.stop_connection() # Asegura que todo esté limpio antes de empezar

        self.thread = QThread()
        self.worker = SerialWorker(port=port)
        self.worker.moveToThread(self.thread)

        # Conectar señales del worker a los slots de la ventana principal
        self.thread.started.connect(self.worker.run)
        self.worker.data_received.connect(self.main_window.display_data)
        self.worker.error.connect(self.main_window.display_error)
        self.worker.connection_status.connect(self.main_window.set_status)
        self.worker.write_result.connect(self.main_window.on_write_result)

        # Conectar la señal de envío de la ventana principal al worker
        self.main_window.send_to_worker.connect(self.worker.write_command)

        self.thread.start()

    def stop_connection(self):
        """Detiene de forma segura el worker y el hilo de comunicación."""
        if self.worker:
            self.worker.stop()
        
        if self.thread:
            self.thread.quit()
            self.thread.wait(2000) # Esperar un máximo de 2 segundos

        self.thread = None
        self.worker = None

    def get_serial_port_status(self):
        """Verifica si el puerto serial del worker está abierto."""
        if self.worker and self.worker.serial_port:
            return self.worker.serial_port.is_open
        return False