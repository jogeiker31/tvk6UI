"""
Módulo para el SerialWorker.

Contiene la clase SerialWorker que maneja la comunicación serial en un hilo
separado para no bloquear la interfaz de usuario.
"""
import serial
import time

from PySide6.QtCore import QObject, Signal, Slot, QCoreApplication

# Importamos la configuración
from config import BAUDRATE, TIMEOUT

class SerialWorker(QObject):
    """Maneja la comunicación serial en un hilo separado para evitar que la UI se congele."""
    data_received = Signal(str)
    error = Signal(str)
    connection_status = Signal(bool, str)       # (is_connected, message)
    write_result = Signal(object)               # bytes enviados o None

    def __init__(self, port):
        super().__init__()
        self.running = False
        self.serial_port = None
        self.port = port

    @Slot()
    def run(self):
        """Intenta conectar y entra en el bucle de lectura serial."""
        self.running = True
        try:
            # Configuración del puerto serial según el protocolo del TVK6 (7S2)
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=BAUDRATE,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_SPACE,  # Paridad 'S' (Space)
                stopbits=serial.STOPBITS_TWO,  # 2 Stop bits
                timeout=TIMEOUT,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            self.connection_status.emit(True, f"CONECTADO: Puerto {self.port} abierto a {BAUDRATE} 7S2.")
        except Exception as e:
            self.serial_port = None
            self.connection_status.emit(False, f"ERROR: No se pudo abrir {self.port}: {e}")
            self.running = False
            return

        while self.running:
            try:
                data = self.serial_port.read_all()
                if data:
                    text = data.decode('ascii', errors='replace').strip()
                    if text:
                        self.data_received.emit(text)
            except Exception as e:
                self.error.emit(f"Error en comunicación serial: {e}")
                self.connection_status.emit(False, "ERROR: Conexión perdida.")
                self.running = False
                break

            time.sleep(0.05)
            QCoreApplication.processEvents()

        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.connection_status.emit(False, f"DESCONECTADO: Puerto {self.port} cerrado.")
        except Exception:
            pass

    @Slot(str)
    def write_command(self, command: str):
        """Escribe un comando al puerto serial."""
        if not self.serial_port or not self.serial_port.is_open:
            self.write_result.emit(None)
            return

        try:
            if command.lower() == 'reset':
                bytes_to_send = b'\x03'  # Ctrl+C
            else:
                bytes_to_send = (command + '\r').encode('ascii')

            self.serial_port.write(bytes_to_send)
            self.write_result.emit(bytes_to_send)
        except Exception as e:
            self.error.emit(f"Error al escribir en serial: {e}")
            self.connection_status.emit(False, f"ERROR DE ESCRITURA: {e}")
            self.write_result.emit(None)

    @Slot()
    def stop(self):
        """Marca el worker para detener la ejecución y salir del bucle."""
        self.running = False