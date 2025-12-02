import serial
import time
import re
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QObject, Signal, Slot, QThread

# --- Configuración Serial ---
PORT = 'COM4'   # AJUSTA ESTO
BAUDRATE = 4800
TIMEOUT = 0.1


# --- Worker que vive en un QThread ---
class SerialWorker(QObject):
    data_received = Signal(str)
    error = Signal(str)
    connection_status = Signal(bool, str)       # (is_connected, message)
    write_result = Signal(object)               # bytes enviados o None

    def __init__(self):
        super().__init__()
        self.running = False
        self.serial_port = None

    @Slot()
    def run(self):
        """Método que ejecuta el loop del thread."""
        self.running = True
        try:
            # Intentar abrir puerto
            self.serial_port = serial.Serial(
                port=PORT,
                baudrate=BAUDRATE,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_SPACE,
                stopbits=serial.STOPBITS_TWO,
                timeout=TIMEOUT,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            self.connection_status.emit(True, f"CONECTADO: Puerto {PORT} abierto.")
        except Exception as e:
            self.serial_port = None
            self.connection_status.emit(False, f"ERROR: No se pudo abrir {PORT}: {e}")
            # No salimos inmediatamente, dejamos running = False para terminar
            self.running = False
            return

        # Loop de lectura
        while self.running:
            try:
                data = self.serial_port.read_all()
                if data:
                    text = data.decode('ascii', errors='replace').strip()
                    # Limpieza de control chars
                    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
                    if cleaned:
                        self.data_received.emit(f"<- TVK6: {cleaned}")
            except Exception as e:
                # Error de lectura/puerto -> avisar y terminar loop
                self.error.emit(f"Error en comunicación serial: {e}")
                self.connection_status.emit(False, "ERROR: Conexión perdida.")
                self.running = False
                break

            # pequeña pausa para no saturar CPU
            time.sleep(0.02)

        # Cerrar puerto si está abierto
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.connection_status.emit(False, f"DESCONECTADO: Puerto {PORT} cerrado.")
        except Exception:
            pass

    @Slot(str)
    def write_command(self, command: str):
        """
        Escribe comando en el puerto serial. Esta función es llamada desde la GUI
        mediante una señal (queued connection), por lo que se ejecuta en el hilo del worker.
        Emite write_result con los bytes enviados o None si falló.
        """
        if not self.serial_port or not self.serial_port.is_open:
            self.write_result.emit(None)
            self.connection_status.emit(False, f"DESCONECTADO: Puerto {PORT} no disponible.")
            return

        try:
            if command.lower() == 'reset':
                bytes_to_send = b'\x03'
            else:
                bytes_to_send = (command + '\r').encode('ascii')

            self.serial_port.write(bytes_to_send)
            # Emitir resultado (se puede conectar desde la GUI)
            self.write_result.emit(bytes_to_send)
        except Exception as e:
            self.error.emit(f"Error al escribir en serial: {e}")
            self.connection_status.emit(False, f"ERROR DE ESCRITURA: {e}")
            self.write_result.emit(None)

    @Slot()
    def stop(self):
        """Pone flag para terminar el loop; el run cerrará el puerto."""
        self.running = False


# --- Ventana principal (GUI) ---
class MainWindow(QMainWindow):
    # Señal para enviar texto al worker (se conecta a SerialWorker.write_command)
    send_to_worker = Signal(str)

    def __init__(self, ui_file):
        super().__init__()

        # Estado interno
        self.current_k_value = 0.0
        self.current_menu = "PRINCIPAL"

        # Cargar UI
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setCentralWidget(self.ui)

        # Widgets
        self.monitorSalida = self.ui.findChild(QPlainTextEdit, 'monitorSalida')
        self.campoComando = self.ui.findChild(QLineEdit, 'campoComando')
        self.etiquetaEstado = self.ui.findChild(QLabel, 'etiquetaEstado')
        self.btnReconectar = self.ui.findChild(QPushButton, 'btnReconectar')
        self.btnLimpiarMonitor = self.ui.findChild(QPushButton, 'btnLimpiarMonitor')

        # Thread & worker placeholders
        self.thread = None
        self.worker = None

        # Iniciar worker
        self.start_serial_worker()

        # Conectar señales UI
        self._connect_signals()

    def start_serial_worker(self):
        """Crea un QThread nuevo con su worker y lo inicia."""
        # Si hay un hilo anterior, pedir que termine (no bloquear la GUI)
        try:
            if self.worker:
                # Pedir al worker que termine
                self.worker.stop()
            if self.thread:
                # Solicitar finalización del thread
                self.thread.quit()
                # esperamos un tiempo muy corto para limpieza; no bloqueamos mucho
                self.thread.wait(100)
        except Exception:
            pass

        # Crear nuevo thread y worker
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        # Conectar señales entre thread/worker y GUI
        self.thread.started.connect(self.worker.run)
        self.send_to_worker.connect(self.worker.write_command)   # GUI -> worker(write)
        self.worker.data_received.connect(self.display_data)
        self.worker.error.connect(self.display_error)
        self.worker.connection_status.connect(self.set_status)
        self.worker.write_result.connect(self.on_write_result)

        # Iniciar thread (esto lanza worker.run() en ese hilo)
        self.thread.start()

    def _connect_signals(self):
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        if self.btnReconectar:
            self.btnReconectar.clicked.connect(self.start_serial_worker)
        if self.btnLimpiarMonitor:
            self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)

    @Slot()
    def clear_monitor(self):
        if self.monitorSalida:
            self.monitorSalida.clear()
            self.monitorSalida.appendPlainText("[Monitor Limpiado]")

    @Slot(bool, str)
    def set_status(self, is_connected, message):
        """Actualizar barra de estado y habilitar/deshabilitar input según conexión."""
        if self.etiquetaEstado:
            self.etiquetaEstado.setText(message)

        if self.campoComando:
            if is_connected:
                if self.etiquetaEstado:
                    self.etiquetaEstado.setStyleSheet(
                        "color: white; background-color: #28a745; padding: 8px; border-radius: 5px;")
                self.campoComando.setEnabled(True)
                self.campoComando.setPlaceholderText("Comando (reset, 1, 2, etc.)")
                if self.btnReconectar:
                    self.btnReconectar.setText("Desconectar")
            else:
                if self.etiquetaEstado:
                    self.etiquetaEstado.setStyleSheet(
                        "color: white; background-color: #dc3545; padding: 8px; border-radius: 5px;")
                # Deshabilitamos para evitar envíos inútiles
                self.campoComando.setEnabled(False)
                self.campoComando.setPlaceholderText("ERROR: Conexión serial bloqueada. Presiona Reconectar.")
                if self.btnReconectar:
                    self.btnReconectar.setText("Reconectar")

                if "ERROR" in message and self.monitorSalida:
                    self.monitorSalida.appendPlainText(f"\n[CRÍTICO] {message}")

    @Slot()
    def send_command(self):
        """Recupera el texto y lo envía al worker de manera segura mediante señales."""
        if not self.campoComando:
            return

        command = self.campoComando.text().strip()
        # no limpiar el campo hasta saber si se envió (mejor experiencia)
        if not command:
            return

        # Desactivar temporal el botón Enter para evitar doble envío inmediato
        if self.campoComando:
            self.campoComando.setEnabled(False)

        # Emitir señal hacia el worker (se manejará en su hilo)
        self.send_to_worker.emit(command)

        # Se volverá a habilitar o no dependiendo de on_write_result()
        # Mostrar registro provisional
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"-> USUARIO: {command} [Enviando...]")

    @Slot(object)
    def on_write_result(self, bytes_sent):
        """Recibimos el resultado del intento de escritura desde el worker."""
        if bytes_sent:
            # Éxito: mostrar log y limpiar input
            if self.monitorSalida:
                self.monitorSalida.appendPlainText(f"[OK] Envío: {repr(bytes_sent)}")
            if self.campoComando:
                self.campoComando.clear()
                self.campoComando.setEnabled(True)
        else:
            # Falla: mostrar advertencia y mantener habilitado para reintentar (o reconectar)
            if self.monitorSalida:
                self.monitorSalida.appendPlainText(f"[ADVERTENCIA] No se envió el comando. Puerto cerrado o error.")
            # Actualizar estado global a desconectado (esto también establece campo disabled)
            self.set_status(False, f"DESCONECTADO: Puerto {PORT} cerrado o no disponible.")
            # Permitir al usuario intentar escribir (si desea) para reintentar localmente:
            if self.campoComando:
                self.campoComando.setEnabled(True)

    @Slot(str)
    def display_data(self, data):
        """Muestra y parsea la data recibida."""
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(data)
        # Rehabilitar input si vino respuesta
        if self.campoComando:
            self.campoComando.setEnabled(True)

        # Parsing básico (igual que antes)
        if "Menu Principal:" in data:
            self.current_menu = "PRINCIPAL"
            self.setWindowTitle(f"TVK6 - Menú: {self.current_menu}")
        elif "Menu Datos:" in data:
            self.current_menu = "DATOS"
            self.setWindowTitle(f"TVK6 - Menú: {self.current_menu}")
        elif "Enter new K value:" in data:
            self.current_menu = "INGRESO_K"
            self.setWindowTitle(f"TVK6 - Modo: Ingresando valor K")

        match_k = re.search(r'K:\s*([\d\.]+)', data)
        if match_k:
            try:
                self.current_k_value = float(match_k.group(1))
                if self.monitorSalida:
                    self.monitorSalida.appendPlainText(f"--- [PARSING] Valor K detectado: {self.current_k_value} ---")
            except ValueError:
                if self.monitorSalida:
                    self.monitorSalida.appendPlainText("--- [PARSING ERROR] No se pudo convertir K a número. ---")

    @Slot(str)
    def display_error(self, message):
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ERROR DE HILO] {message}")

    def closeEvent(self, event):
        """Cerrar el worker de forma ordenada al salir."""
        try:
            if self.worker:
                self.worker.stop()
            if self.thread:
                self.thread.quit()
                self.thread.wait(200)  # espera corta para terminar
        except Exception:
            pass
        super().closeEvent(event)


# --- Main ---
if __name__ == '__main__':
    UI_FILE = 'interfaz_tvk6.ui'
    try:
        open(UI_FILE, 'r').close()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo de interfaz '{UI_FILE}'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(UI_FILE)
    window.setWindowTitle("TVK6 Serial Console - Python 3.11 / PySide6")
    window.show()
    sys.exit(app.exec())
