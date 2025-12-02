"""
Módulo de la ventana principal de la aplicación.

Contiene la clase MainWindow, que gestiona la interfaz de usuario,
las interacciones y la orquestación del SerialWorker.
"""
import re

from PySide6.QtWidgets import QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, Slot, QThread

# Importaciones de nuestros módulos
from serial_worker import SerialWorker
from config import ANSI_ESCAPE

class MainWindow(QMainWindow):
    """Ventana principal que carga la UI y conecta la lógica."""
    send_to_worker = Signal(str)

    def __init__(self, ui_file):
        super().__init__()

        self.parsed_values = {'X': '---', 'K': '---', 'U1': '---'}

        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setCentralWidget(self.ui)

        self._find_widgets()
        self._connect_signals()

        self.thread = None
        self.worker = None
        self.start_serial_worker()
        
        self.setWindowTitle("TVK6 Serial Console - Python 3.11 / PySide6")

    def _find_widgets(self):
        """Encuentra y asigna todos los widgets de la UI a atributos de la clase."""
        self.monitorSalida = self.ui.findChild(QPlainTextEdit, 'monitorSalida')
        self.campoComando = self.ui.findChild(QLineEdit, 'campoComando')
        self.etiquetaEstado = self.ui.findChild(QLabel, 'etiquetaEstado')
        self.btnReconectar = self.ui.findChild(QPushButton, 'btnReconectar')
        self.btnLimpiarMonitor = self.ui.findChild(QPushButton, 'btnLimpiarMonitor')
        
        self.valorX = self.ui.findChild(QLabel, 'valorX')
        self.valorK = self.ui.findChild(QLabel, 'valorK')
        self.valorU1 = self.ui.findChild(QLabel, 'valorU1')

        self.btn_reset = self.ui.findChild(QPushButton, 'btn_reset')
        self.btn_menu_1_entradas = self.ui.findChild(QPushButton, 'btn_menu_1_entradas')
        self.btn_menu_2_calibrar = self.ui.findChild(QPushButton, 'btn_menu_2_calibrar')
        self.btn_menu_3_control = self.ui.findChild(QPushButton, 'btn_menu_3_control')

    def _connect_signals(self):
        """Conecta todas las señales de la UI a sus respectivos slots."""
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        
        self.btnReconectar.clicked.connect(self.start_serial_worker)
        self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)
        
        self.btn_reset.clicked.connect(lambda: self.send_command('reset'))
        self.btn_menu_1_entradas.clicked.connect(lambda: self.send_command('1'))
        self.btn_menu_2_calibrar.clicked.connect(lambda: self.send_command('2'))
        self.btn_menu_3_control.clicked.connect(lambda: self.send_command('3'))

    def _clean_ansi_codes(self, text):
        """Limpia los códigos de escape ANSI/VT100 del texto."""
        return ANSI_ESCAPE.sub('', text)

    def start_serial_worker(self):
        """Inicia o reinicia el QThread y el SerialWorker."""
        try:
            if self.worker: self.worker.stop()
            if self.thread: 
                self.thread.quit()
                self.thread.wait()
        except Exception:
            pass
        finally:
             self.thread = None
             self.worker = None

        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.send_to_worker.connect(self.worker.write_command)   
        self.worker.data_received.connect(self.display_data)
        self.worker.error.connect(self.display_error)
        self.worker.connection_status.connect(self.set_status)
        self.worker.write_result.connect(self.on_write_result)

        self.thread.start()

    @Slot()
    def clear_monitor(self):
        """Limpia el QPlainTextEdit de la consola."""
        if self.monitorSalida:
            self.monitorSalida.clear()
            self.monitorSalida.appendPlainText("[Monitor Limpiado]")
            
    @Slot(bool, str)
    def set_status(self, is_connected, message):
        """Actualiza la barra de estado superior."""
        if self.etiquetaEstado:
            self.etiquetaEstado.setText(message)

        bg_color = "#28a745" if is_connected else "#dc3545"
        text = "Comando (reset, 1, 2, etc.)" if is_connected else "ERROR: Conexión serial bloqueada."
        enabled = is_connected
            
        if self.etiquetaEstado:
            self.etiquetaEstado.setStyleSheet(f"color: white; background-color: {bg_color}; padding: 8px; border-radius: 5px; font-weight: bold;")
        
        if self.campoComando:
            self.campoComando.setEnabled(enabled)
            self.campoComando.setPlaceholderText(text)
        
        if "ERROR" in message and self.campoComando:
            self.campoComando.setEnabled(True)

    @Slot(str)
    def send_command(self, command=None):
        """Recupera el texto o usa el comando del botón y lo envía al worker."""
        if command is None and self.campoComando:
            command = self.campoComando.text().strip()
        
        if not command:
            return

        if not self.thread or not self.thread.isRunning() or not self.worker.serial_port or not self.worker.serial_port.is_open:
            if self.monitorSalida:
                self.monitorSalida.appendPlainText(f"[ERROR LOCAL] No se pudo enviar '{command}': Puerto no conectado.")
            if self.campoComando:
                self.campoComando.clear()
            return

        self.send_to_worker.emit(command)

        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"-> USUARIO: {command} [Enviado]")
        
        if self.campoComando:
             self.campoComando.clear()

    @Slot(object)
    def on_write_result(self, bytes_sent):
        """Señal de confirmación de escritura."""
        if not bytes_sent and self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ADVERTENCIA] Error de escritura. El puerto pudo haberse cerrado.")

    @Slot()
    def update_visual_display(self):
        """Actualiza los QLabel del panel visual con los valores parseados."""
        self.valorX.setText(str(self.parsed_values.get('X', '---')))
        self.valorK.setText(str(self.parsed_values.get('K', '---')))
        self.valorU1.setText(str(self.parsed_values.get('U1', '---')))

    @Slot(str)
    def display_data(self, raw_data):
        """Muestra la data RAW y realiza el parsing de datos Medidos."""
        self.monitorSalida.appendPlainText(f"<- TVK6 RAW: {raw_data}")

        cleaned_data = self._clean_ansi_codes(raw_data)
        
        if "X =" in cleaned_data and "U1 =" in cleaned_data:
            numbers = re.findall(r'[\d]+\.[\d]+|[\d]+', cleaned_data)
            
            if len(numbers) >= 2:
                self.parsed_values['X'] = numbers[0] 
                self.parsed_values['K'] = numbers[0] 
                self.parsed_values['U1'] = numbers[-1]
                self.monitorSalida.appendPlainText(f"--- [PARSING OK] X={self.parsed_values['X']}, U1={self.parsed_values['U1']} ---")
            else:
                self.monitorSalida.appendPlainText("--- [PARSING FALLIDO] No se encontraron suficientes valores X/U1. ---")

        self.update_visual_display()

    @Slot(str)
    def display_error(self, message):
        """Muestra errores internos del hilo worker."""
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ERROR DE HILO] {message}")

    def closeEvent(self, event):
        """Asegura que el worker y el hilo terminen al cerrar la ventana."""
        try:
            if self.worker:
                self.worker.stop()
            if self.thread:
                self.thread.quit()
                self.thread.wait()
        except Exception:
            pass
        super().closeEvent(event)