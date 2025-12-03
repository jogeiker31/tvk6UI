"""
Módulo de la ventana principal de la aplicación.

Contiene la clase MainWindow, que gestiona la interfaz de usuario,
las interacciones y la orquestación del SerialWorker.
"""
import re

from PySide6.QtWidgets import QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, Slot, QThread, Qt
from PySide6.QtGui import QKeySequence

# Importaciones de nuestros módulos
from serial_worker import SerialWorker
from config import ANSI_ESCAPE, PORT, BAUDRATE
from ui_panels import MeasurementPanel
from menu_manager import MenuManager

class ScreenEmulator:
    """Emulador simple de terminal VT100 para reconstruir la pantalla del TVK6."""
    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.screen = [[' ' for _ in range(cols)] for _ in range(rows)]
        self.cursor_pos = [0, 0]
        self.ansi_pattern = re.compile(r'\x1b\[([0-9;?]*)([A-Za-z])')
        # --- INICIO DE LA MODIFICACIÓN: Buffer para datos incompletos ---
        self.incomplete_data_buffer = ""
        # --- FIN DE LA MODIFICACIÓN ---

    def reset(self):
        """Limpia la pantalla y resetea la posición del cursor."""
        self.screen = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_pos = [0, 0]
        self.incomplete_data_buffer = "" # También reseteamos el buffer

    def process_data(self, data: str):
        """Procesa un fragmento de datos, actualizando el estado de la pantalla."""
        # --- INICIO DE LA MODIFICACIÓN: Unir buffer con nuevos datos ---
        data = self.incomplete_data_buffer + data
        self.incomplete_data_buffer = "" # Limpiamos el buffer una vez usado
        # Procesamos el flujo de datos carácter por carácter para un manejo robusto de ANSI.
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
                        elif command == 'K': # Erase in Line (EL)
                            if not params_str or params_str == '0': # Por defecto: borrar desde el cursor hasta el final de la línea
                                row, col = self.cursor_pos
                                for c in range(col, self.cols):
                                    self.screen[row][c] = ' '
                        # Consumimos el carácter de comando CSI
                        i += 1 
                elif data[i] in '#()': # Secuencias como ESC #6, ESC )0, ESC (B
                    i += 1 # Consumimos '#' o '(' o ')'
                    if i >= len(data): # Secuencia incompleta
                        self.incomplete_data_buffer = f"\x1b{data[i-1]}"
                        break
                    else: # Consumimos el siguiente carácter (ej. '6', '0', 'B')
                        i += 1
                else: # Otras secuencias de escape de un solo carácter (ej. ESC E)
                    # No hay nada que guardar si se corta aquí, ya que es un solo carácter
                    # después de ESC, así que simplemente avanzamos.
                    i += 1
                # --- FIN DE LA MODIFICACIÓN ---
            else: # No es una secuencia de escape, es un carácter normal
                # Ignoramos caracteres de control no imprimibles como SO/SI (0x0e, 0x0f)
                if char not in '\x0e\x0f\r\n':
                    row, col = self.cursor_pos
                    if row < self.rows and col < self.cols:
                        self.screen[row][col] = char
                        self.cursor_pos[1] += 1
                i += 1 # Avanzamos al siguiente carácter

    def get_screen_text(self) -> str:
        """Devuelve el contenido de la pantalla como un string multilinea."""
        return "\n".join("".join(row) for row in self.screen)

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
        # Crear instancias de nuestros gestores de paneles
        self.measurement_panel = MeasurementPanel(self.ui)
        self.menu_manager = MenuManager(self.ui, self, history_size=5)
        self.screen_emulator = ScreenEmulator()

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
        
        # Botones de la barra de herramientas de la consola
        self.btnReconectar = self.ui.findChild(QPushButton, 'btnReconectar')
        self.btnRetornar = self.ui.findChild(QPushButton, 'btnRetornar')
        self.btn_reset = self.ui.findChild(QPushButton, 'btn_reset')
        self.btnLimpiarMonitor = self.ui.findChild(QPushButton, 'btnLimpiarMonitor')

    def _connect_signals(self):
        """Conecta todas las señales de la UI a sus respectivos slots."""
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        
        # Conectar botones fijos
        self.btnReconectar.clicked.connect(self.start_serial_worker)
        self.btnRetornar.clicked.connect(lambda: self.send_command('esc'))
        self.btn_reset.clicked.connect(lambda: self.send_command('reset'))
        self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)
        
        # Atajos de teclado
        self.btnRetornar.setShortcut(QKeySequence(Qt.Key.Key_Return))
        self.btn_reset.setShortcut(QKeySequence("Ctrl+R")) # Ctrl+C es para copiar


    def _clean_ansi_codes(self, text):
        """Limpia los códigos de escape ANSI/VT100 del texto."""
        return ANSI_ESCAPE.sub('', text)

    def start_serial_worker(self):
        """Inicia o reinicia el QThread y el SerialWorker."""
        # Limpiar la consola al iniciar o reconectar.
        self.clear_monitor()
        
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
        self.worker = SerialWorker(port=PORT) # Pasamos el puerto al worker
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
            # --- INICIO DE LA MODIFICACIÓN ---
            # También reiniciamos el historial del gestor de menú.
            # Y reseteamos el emulador de pantalla para una transición limpia.
            self.screen_emulator.reset()
            self.menu_manager.reset_history()
            # --- FIN DE LA MODIFICACIÓN ---
            
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

        # --- INICIO DE LA MODIFICACIÓN ---
        # Si el comando implica un cambio de pantalla (navegación, reset, retorno),
        # limpiamos la consola ANTES de enviar el comando para una transición limpia.
        if command.isdigit() or command.lower() in ['reset', 'esc']:
            self.clear_monitor()
            if command.lower() == 'reset':
                self.menu_manager.set_state('INIT')

            # --- INICIO DE LA MODIFICACIÓN: Transición de Estado ---
            # Si estamos en el menú principal y se presiona '1', cambiamos al estado del menú de entradas.
            if self.menu_manager.current_state == 'MAIN_MENU' and command == '1':
                self.menu_manager.set_state('ENTRADAS_MENU')
            # Aquí añadiremos más transiciones para otros botones y menús.
            # elif self.menu_manager.current_state == 'MAIN_MENU' and command == '2':
            #     self.menu_manager.set_state('CALIBRAR_MENU')
            # --- FIN DE LA MODIFICACIÓN ---
        # --- FIN DE LA MODIFICACIÓN ---

        if not self.thread or not self.thread.isRunning() or not self.worker.serial_port or not self.worker.serial_port.is_open:
            if self.monitorSalida:
                self.monitorSalida.appendPlainText(f"[ERROR LOCAL] No se pudo enviar '{command}': Puerto no conectado.")
            if self.campoComando:
                self.campoComando.clear()
            return

        self.send_to_worker.emit(command)

        if self.campoComando:
             self.campoComando.clear()

    @Slot(object)
    def on_write_result(self, bytes_sent):
        """Señal de confirmación de escritura."""
        if not bytes_sent and self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ADVERTENCIA] Error de escritura. El puerto pudo haberse cerrado.")

    @Slot(str)
    def display_data(self, raw_data):
        """Muestra la data RAW y realiza el parsing de datos Medidos."""
        # No mostramos el raw_data directamente para evitar basura visual.
        # En su lugar, lo procesamos con el emulador de pantalla.
        self.screen_emulator.process_data(raw_data)
        screen_text = self.screen_emulator.get_screen_text() # Obtener el texto reconstruido de la pantalla
        
        self.monitorSalida.setPlainText(screen_text) # Mostrar el texto emulado en la consola
        
        # Ahora usamos el texto reconstruido de la pantalla para el parsing
        if "X =" in screen_text and "U1 =" in screen_text:
            numbers = re.findall(r'[\d]+\.[\d]+|[\d]+', screen_text) # Corregido: usar screen_text
            
            if len(numbers) >= 2:
                self.parsed_values['X'] = numbers[0] 
                self.parsed_values['K'] = numbers[0] 
                self.parsed_values['U1'] = numbers[-1]

        # Delegamos la actualización visual al panel correspondiente
        self.measurement_panel.update_display(self.parsed_values)
        
        # Delegamos la actualización del menú dinámico
        self.menu_manager.update_menu(screen_text)

    @Slot(str)
    def display_error(self, message):
        """Muestra errores internos del hilo worker."""
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ERROR DE HILO] {message}")

    def keyPressEvent(self, event):
        """Captura eventos de teclado para atajos numéricos."""
        key = event.key()
        # Si se presiona una tecla numérica (0-9)
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            command = str(key - Qt.Key.Key_0)
            self.send_command(command)
        else:
            super().keyPressEvent(event)

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