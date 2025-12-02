import serial
import time
import re
import sys

# Importaciones de PySide6 para la UI
from PySide6.QtWidgets import QApplication, QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QObject, Signal, Slot, QThread, QCoreApplication

# --- Configuración Serial ---
PORT = 'COM4'   # IMPORTANTE: AJUSTA ESTO al puerto correcto donde esté conectado el TVK6
BAUDRATE = 4800
TIMEOUT = 2

# Expresión regular para limpiar códigos de escape ANSI/VT100 (crucial para el parsing)
# Esto limpia comandos de posicionamiento, color, etc.
ANSI_ESCAPE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

# --- Worker que vive en un QThread ---
class SerialWorker(QObject):
    """Maneja la comunicación serial en un hilo separado para evitar que la UI se congele."""
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
        """Intenta conectar y entra en el bucle de lectura serial."""
        self.running = True
        try:
            # Configuración del puerto serial según el protocolo del TVK6 (7E2 o 7S2)
            self.serial_port = serial.Serial(
                port=PORT,
                baudrate=BAUDRATE,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_SPACE,  # Paridad 'S' (Space)
                stopbits=serial.STOPBITS_TWO,  # 2 Stop bits
                timeout=TIMEOUT,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            self.connection_status.emit(True, f"CONECTADO: Puerto {PORT} abierto a {BAUDRATE} 7S2.")
        except Exception as e:
            self.serial_port = None
            self.connection_status.emit(False, f"ERROR: No se pudo abrir {PORT}: {e}")
            self.running = False
            return

        while self.running:
            try:
                data = self.serial_port.read_all()
                if data:
                    # Decodificamos la data recibida
                    text = data.decode('ascii', errors='replace').strip()
                    if text:
                        # Emitimos la data RAW para que la UI la procese
                        self.data_received.emit(text)
            except Exception as e:
                self.error.emit(f"Error en comunicación serial: {e}")
                self.connection_status.emit(False, "ERROR: Conexión perdida.")
                self.running = False
                break

            time.sleep(0.05)
            # Permite que el hilo principal procese la señal de escritura
            QCoreApplication.processEvents()

        # Limpieza y cierre del puerto
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.connection_status.emit(False, f"DESCONECTADO: Puerto {PORT} cerrado.")
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
                # El comando RESET se mapea a Ctrl+C (\x03)
                bytes_to_send = b'\x03' 
            else:
                # Otros comandos se envían seguidos de Retorno de Carro (CR)
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


# --- Ventana principal (GUI) ---
class MainWindow(QMainWindow):
    send_to_worker = Signal(str)

    def __init__(self, ui_file):
        super().__init__()

        # Valores internos parseados (Para el panel visual)
        self.parsed_values = {'X': '---', 'K': '---', 'U1': '---'}

        # Cargar UI desde el archivo XML
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setCentralWidget(self.ui)

        # 1. Referencias a Widgets de la UI
        self.monitorSalida = self.ui.findChild(QPlainTextEdit, 'monitorSalida')
        self.campoComando = self.ui.findChild(QLineEdit, 'campoComando')
        self.etiquetaEstado = self.ui.findChild(QLabel, 'etiquetaEstado')
        self.btnReconectar = self.ui.findChild(QPushButton, 'btnReconectar')
        self.btnLimpiarMonitor = self.ui.findChild(QPushButton, 'btnLimpiarMonitor')
        
        # Widgets de Display Visual (Valores Parseados)
        self.valorX = self.ui.findChild(QLabel, 'valorX')
        self.valorK = self.ui.findChild(QLabel, 'valorK')
        self.valorU1 = self.ui.findChild(QLabel, 'valorU1')

        # Widgets de Botones de Menú
        self.btn_reset = self.ui.findChild(QPushButton, 'btn_reset')
        self.btn_menu_1_entradas = self.ui.findChild(QPushButton, 'btn_menu_1_entradas')
        self.btn_menu_2_calibrar = self.ui.findChild(QPushButton, 'btn_menu_2_calibrar')
        self.btn_menu_3_control = self.ui.findChild(QPushButton, 'btn_menu_3_control')

        # Iniciar worker y conectar señales
        self.thread = None
        self.worker = None
        self.start_serial_worker()
        self._connect_signals()
        self.setWindowTitle("TVK6 Serial Console - Python 3.11 / PySide6")

    def _clean_ansi_codes(self, text):
        """Limpia los códigos de escape ANSI/VT100 del texto."""
        return ANSI_ESCAPE.sub('', text)

    def start_serial_worker(self):
        """Inicia o reinicia el QThread y el SerialWorker."""
        # Lógica de detención y limpieza previa
        try:
            if self.worker: self.worker.stop()
            if self.thread: 
                self.thread.quit()
                self.thread.wait() # Esperar a que termine
        except Exception:
            pass
        finally:
             self.thread = None
             self.worker = None

        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        # Conexión de señales del worker
        self.thread.started.connect(self.worker.run)
        self.send_to_worker.connect(self.worker.write_command)   
        self.worker.data_received.connect(self.display_data)
        self.worker.error.connect(self.display_error)
        self.worker.connection_status.connect(self.set_status)
        self.worker.write_result.connect(self.on_write_result)

        self.thread.start()

    def _connect_signals(self):
        # Conexiones de Consola (Enter en el campo de comando)
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        
        # Conexiones de Botones de Control
        self.btnReconectar.clicked.connect(self.start_serial_worker)
        self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)
        
        # Conexiones de Comandos Rápidos
        self.btn_reset.clicked.connect(lambda: self.send_command('reset'))
        self.btn_menu_1_entradas.clicked.connect(lambda: self.send_command('1'))
        self.btn_menu_2_calibrar.clicked.connect(lambda: self.send_command('2'))
        self.btn_menu_3_control.clicked.connect(lambda: self.send_command('3'))
        
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

        if is_connected:
            bg_color = "#28a745" # Verde
            text = "Comando (reset, 1, 2, etc.)"
            enabled = True
        else:
            bg_color = "#dc3545" # Rojo
            text = "ERROR: Conexión serial bloqueada."
            enabled = False
            
        if self.etiquetaEstado:
            self.etiquetaEstado.setStyleSheet(f"color: white; background-color: {bg_color}; padding: 8px; border-radius: 5px; font-weight: bold;")
        
        if self.campoComando:
            self.campoComando.setEnabled(enabled)
            self.campoComando.setPlaceholderText(text)
        
        # Re-habilitar campo si el mensaje es de error crítico pero la app sigue viva
        if "ERROR" in message and self.campoComando:
            self.campoComando.setEnabled(True)

    @Slot(str)
    def send_command(self, command=None):
        """Recupera el texto o usa el comando del botón y lo envía al worker."""
        if command is None and self.campoComando:
            command = self.campoComando.text().strip()
        
        if not command:
            return

        # Chequeo rápido de conexión antes de emitir
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
        
        # 1. Mostrar data RAW en la consola (con la etiqueta del TVK6)
        self.monitorSalida.appendPlainText(f"<- TVK6 RAW: {raw_data}")

        # Limpiar data para intentar el parsing
        cleaned_data = self._clean_ansi_codes(raw_data)
        
        # Si la data RAW contiene la secuencia de menú de datos medidos
        if "X =" in cleaned_data and "U1 =" in cleaned_data:
            
            # 2. Lógica de PARSING de datos Medidos
            # Buscamos todos los números flotantes o enteros
            # La limpieza de ANSI es crucial aquí. El ejemplo:
            # RAW: ... [3;15H1.0 ... [3;67H120.0 ...
            # CLEAN: X = K = M = T = U1 = 1.0 120.0
            
            numbers = re.findall(r'[\d]+\.[\d]+|[\d]+', cleaned_data)
            
            if len(numbers) >= 2:
                # Asignación heurística basada en el patrón conocido del TVK6:
                # El primer valor numérico es la constante de pulsos (X y K)
                self.parsed_values['X'] = numbers[0] 
                self.parsed_values['K'] = numbers[0] 
                
                # El último valor numérico es el voltaje U1
                self.parsed_values['U1'] = numbers[-1]
                
                self.monitorSalida.appendPlainText(f"--- [PARSING OK] X={self.parsed_values['X']}, U1={self.parsed_values['U1']} ---")
            else:
                # Si no hay suficientes números, lo mostramos en la consola
                self.monitorSalida.appendPlainText("--- [PARSING FALLIDO] No se encontraron suficientes valores X/U1. ---")

        # 3. Actualizar la UI visual
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


# --- Main ---
if __name__ == '__main__':
    QApplication.setOrganizationName("MiEmpresa")
    QApplication.setApplicationName("TVK6SerialConsole")

    # Nombre del archivo UI
    UI_FILE = 'interfaz_tvk6.ui'
    try:
        open(UI_FILE, 'r').close()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo de interfaz '{UI_FILE}'.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(UI_FILE)
    window.show()
    sys.exit(app.exec())