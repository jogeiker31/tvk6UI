"""
Módulo de la ventana principal de la aplicación.

Contiene la clase MainWindow, que gestiona la interfaz de usuario,
las interacciones y la orquestación del SerialWorker.
"""
import re
from collections import deque
from PySide6.QtWidgets import (QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton, QVBoxLayout, QGroupBox, QMenu, QComboBox, QStackedWidget, QCheckBox, QFrame, QMessageBox,
                               QGraphicsDropShadowEffect)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, Slot, QThread, Qt, QTimer, QObject
from PySide6.QtGui import QKeySequence

# Importaciones de nuestros módulos
from serial.tools import list_ports
from serial_worker import SerialWorker
from config import ANSI_ESCAPE, PORT, BAUDRATE
from ui_panels import MeasurementPanel
from menu_manager import MenuManager
from state_manager import StateManager
from database import DatabaseManager
from ui_model_manager import ModelManagerDialog
from calibration_view import CalibrationTableView
from ui_input_dialog import InputDialog
from sequence_manager import SequenceManager
from screen_emulator import ScreenEmulator
from settings_dialog import SettingsDialog
from themes import DARK_THEME, LIGHT_THEME

class MainWindow(QMainWindow):
    """Ventana principal que carga la UI y conecta la lógica."""
    send_to_worker = Signal(str)
    # Señal para enviar comandos desde la UI al StateManager
    command_to_statemanager = Signal(str)

    def __init__(self, ui_file):
        super().__init__()

        self.parsed_values = {'X': '---', 'K': '---', 'U1': '---', 'I1': '---', 'di': '---', 'ds': '---'}

        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setCentralWidget(self.ui)

        self.current_theme = 'dark' # Tema por defecto
        self._find_widgets()
        # Crear instancias de nuestros gestores de paneles
        self.measurement_panel = MeasurementPanel(self.ui)
        self.menu_manager = MenuManager(self.ui, self)
        self.screen_emulator = ScreenEmulator()
        self.state_manager = StateManager(self.menu_manager)
        self.sequence_manager = SequenceManager(delay=2000, parent=self)
        
        # 1. Inicializar el gestor de la base de datos
        self.db_manager = DatabaseManager()

        self._connect_signals()

        # --- INICIO DE LA MODIFICACIÓN: Temporizador para procesar snapshots ---
        self.processing_timer = QTimer(self)
        self.processing_timer.setInterval(1000)  # ms de espera antes de procesar (2 segundos)
        self.processing_timer.setSingleShot(True)
        self.processing_timer.timeout.connect(self._process_screen_snapshot)
        
        # Configurar animaciones y efectos visuales
        self._setup_visual_effects()

        # Llenar la lista de puertos COM
        self.refresh_com_ports()

        self.thread = None
        self.worker = None
        self.start_serial_worker()
        
        # Aplicar el tema inicial
        self._apply_theme(self.current_theme)

        self.setWindowTitle("TVK6 Serial Console - Python 3.11 / PySide6")

    def _find_widgets(self):
        """Encuentra y asigna todos los widgets de la UI a atributos de la clase."""
        self.monitorSalida = self.ui.findChild(QPlainTextEdit, 'monitorSalida')
        self.campoComando = self.ui.findChild(QLineEdit, 'campoComando')
        self.etiquetaEstado = self.ui.findChild(QLabel, 'etiquetaEstado')
        
        # Botones de la barra de herramientas de la consola
        self.comboPuerto = self.ui.findChild(QComboBox, 'comboPuerto')
        self.btnRefrescarPuertos = self.ui.findChild(QPushButton, 'btnRefrescarPuertos')
        self.btnReconectar = self.ui.findChild(QPushButton, 'btnReconectar')
        self.btnRetornar = self.ui.findChild(QPushButton, 'btnRetornar')
        self.btn_reset = self.ui.findChild(QPushButton, 'btn_reset')
        self.btnConfiguracion = self.ui.findChild(QPushButton, 'btnConfiguracion')
        self.btnLimpiarMonitor = self.ui.findChild(QPushButton, 'btnLimpiarMonitor')
        self.btnGestionarModelos = self.ui.findChild(QPushButton, 'btnGestionarModelos')

        # Widgets para el cambio de vista
        self.viewSwitcher = self.ui.findChild(QCheckBox, 'viewSwitcher')
        self.graphicViewTitle = self.ui.findChild(QLabel, 'graphicViewTitle')
        self.viewStackedWidget = self.ui.findChild(QStackedWidget, 'viewStackedWidget')
        # --- INICIO DE LA MODIFICACIÓN: Widget para la vista de calibración ---
        # Referencia al label genérico para poder ocultarlo
        self.customGraphicLayout = self.ui.findChild(QVBoxLayout, 'customGraphicLayout')
        self.calibration_table_view = CalibrationTableView(rows=2, cols=10)
        self.customGraphicLayout.insertWidget(0, self.calibration_table_view) # Añadirlo al layout
        # --- INICIO DE LA MODIFICACIÓN: Cabecera de Datos Medidor ---
        self.datosMedidorHeader = self.ui.findChild(QFrame, 'datosMedidorHeader')
        self.valorDatosX = self.ui.findChild(QLabel, 'valorDatosX')
        self.valorDatosK = self.ui.findChild(QLabel, 'valorDatosK')
        self.valorDatosM = self.ui.findChild(QLabel, 'valorDatosM')
        self.valorDatosT = self.ui.findChild(QLabel, 'valorDatosT')
        self.valorDatosU1 = self.ui.findChild(QLabel, 'valorDatosU1')
        self.calibrationHeader = self.ui.findChild(QFrame, 'calibrationHeader')
        self.valorCalibPercent = self.ui.findChild(QLabel, 'valorCalibPercent')
        self.valorCalibIndicac = self.ui.findChild(QLabel, 'valorCalibIndicac')
        self.valorCalibX = self.ui.findChild(QLabel, 'valorCalibX')
        self.valorCalibK = self.ui.findChild(QLabel, 'valorCalibK')
        self.valorCalibM = self.ui.findChild(QLabel, 'valorCalibM')
        self.valorCalibT = self.ui.findChild(QLabel, 'valorCalibT')
        self.valorCalibU1 = self.ui.findChild(QLabel, 'valorCalibU1')
        # Fila 4 de la cabecera de calibración
        self.valorCalibNo = self.ui.findChild(QLabel, 'valorCalibNo')
        self.valorCalibI = self.ui.findChild(QLabel, 'valorCalibI')
        self.valorCalibL123 = self.ui.findChild(QLabel, 'valorCalibL123')
        self.valorCalibCos = self.ui.findChild(QLabel, 'valorCalibCos')
        self.valorCalibDi = self.ui.findChild(QLabel, 'valorCalibDi')
        self.valorCalibDs = self.ui.findChild(QLabel, 'valorCalibDs')
        self.valorCalibGo = self.ui.findChild(QLabel, 'valorCalibGo')
        self.valorCalibR = self.ui.findChild(QLabel, 'valorCalibR')
        self.valorCalibI1A = self.ui.findChild(QLabel, 'valorCalibI1A')
        self.calibrationHeader.setVisible(False) # Oculto por defecto
        self.datosMedidorHeader.setVisible(False) # Oculto por defecto
        # --- FIN DE LA MODIFICACIÓN ---
        self.calibration_table_view.setVisible(False) # Oculto por defecto
        # --- FIN DE LA MODIFICACIÓN ---
        # --- INICIO DE LA MODIFICACIÓN: Loader Overlay ---
        self.loadingOverlay = self.ui.findChild(QFrame, 'loadingOverlay')
        self.loadingLabel = self.ui.findChild(QLabel, 'loadingLabel')
        self.hide_loader() # Asegurarse de que esté oculto al inicio
        # --- FIN DE LA MODIFICACIÓN ---

    def _connect_signals(self):
        """Conecta todas las señales de la UI a sus respectivos slots."""
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        
        # Conectar botones fijos
        self.command_to_statemanager.connect(self.state_manager.process_command)
        self.btnRefrescarPuertos.clicked.connect(self.refresh_com_ports)
        self.btnReconectar.clicked.connect(self.start_serial_worker)
        self.btnRetornar.clicked.connect(lambda: self.send_command('esc'))
        self.btn_reset.clicked.connect(lambda: self.send_command('reset'))
        self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)
        self.btnConfiguracion.clicked.connect(self._open_settings_dialog)
        self.btnGestionarModelos.clicked.connect(self.open_model_manager)
        self.state_manager.clear_screen_requested.connect(self.clear_monitor) # Conectar la nueva señal

        # Conectar el interruptor de vista
        self.viewSwitcher.toggled.connect(self.switch_view)

        # Conectar el gestor de secuencias
        self.sequence_manager.send_command.connect(self.send_command)
        self.sequence_manager.sequence_finished.connect(self._on_sequence_finished)
        
        # --- INICIO DE LA MODIFICACIÓN: Corrección de doble comando ---
        # Se elimina el atajo global para la tecla Enter (Return).
        # El envío al presionar Enter en el campo de texto ya se maneja con la señal `returnPressed`.
        # Mantener este atajo causaba que se enviara el comando del campo Y el comando 'esc' del botón.
        self.btn_reset.setShortcut(QKeySequence("Ctrl+R")) # Ctrl+R para reset

    @Slot()
    def _open_settings_dialog(self):
        """Abre el diálogo de configuración para el cambio de tema."""
        dialog = SettingsDialog(current_theme=self.current_theme, parent=self)
        dialog.theme_changed.connect(self._apply_theme)
        dialog.exec()

    @Slot(str)
    def _apply_theme(self, theme_name):
        """Aplica la hoja de estilos correspondiente al tema seleccionado."""
        self.current_theme = theme_name
        if theme_name == 'dark':
            self.ui.setStyleSheet(DARK_THEME)
        else:
            self.ui.setStyleSheet(LIGHT_THEME)
        # Podríamos necesitar reaplicar estilos específicos si se pierden

    def open_model_manager(self):
        """
        Crea y muestra el diálogo para gestionar los modelos de medidores.
        """
        dialog = ModelManagerDialog(self.db_manager, self)
        dialog.start_calibration_requested.connect(self._run_calibration_sequence)
        dialog.exec() # Usamos exec() para que sea una ventana modal (bloqueante)

    def _setup_visual_effects(self):
        """Configura animaciones y otros efectos para los widgets."""
        if not self.btnGestionarModelos:
            return

        # Crear un efecto de sombra que usaremos para la animación de "latido"
        self.shadow_effect = QGraphicsDropShadowEffect(self.btnGestionarModelos)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(Qt.GlobalColor.green)
        self.shadow_effect.setOffset(0, 0)
        self.btnGestionarModelos.setGraphicsEffect(self.shadow_effect)

        # Usar un QTimer para crear un ciclo de animación suave
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_pulse)
        self.anim_timer.start(20) # Actualizar 50 veces por segundo

    def _clean_ansi_codes(self, text):
        """Limpia los códigos de escape ANSI/VT100 del texto."""
        cleaned_text = ANSI_ESCAPE.sub('', text)
        return cleaned_text.replace('\x0e', '').replace('\x0f', '')

    @Slot(bool)
    def switch_view(self, is_console_mode):
        """Cambia entre la vista de consola y la vista gráfica."""
        if is_console_mode:
            self.viewStackedWidget.setCurrentIndex(0) # Ir a la página de consola
        else:
            self.viewStackedWidget.setCurrentIndex(1) # Ir a la página de gráficos

    @Slot()
    def refresh_com_ports(self):
        """Escanea los puertos COM disponibles y actualiza el QComboBox."""
        if not self.comboPuerto:
            return
        
        self.comboPuerto.clear()
        ports = list_ports.comports()
        if not ports:
            self.comboPuerto.addItem("No hay puertos disponibles")
            self.comboPuerto.setEnabled(False)
        else:
            for port in sorted(ports):
                self.comboPuerto.addItem(port.device, port.description)
            self.comboPuerto.setEnabled(True)

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
        
        # Obtener el puerto seleccionado del ComboBox
        selected_port = self.comboPuerto.currentText()
        if "No hay puertos" in selected_port:
            self.set_status(False, "Error: No se ha seleccionado un puerto COM válido.")
            return

        self.worker = SerialWorker(port=selected_port) # Pasamos el puerto seleccionado al worker
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
        # El StateManager se encarga ahora del historial.
            self.screen_emulator.reset() # Resetear el emulador de pantalla
            self.state_manager.set_state('INIT') # Resetear el estado de la máquina de estados
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
        
        # El botón de gestionar modelos debe estar SIEMPRE habilitado.
        if self.btnGestionarModelos:
            self.btnGestionarModelos.setEnabled(True)

    @Slot(str)
    def send_command(self, command=None, from_button=False):
        """Recupera el texto o usa el comando del botón y lo envía al worker."""
        is_from_input_field = command is None
        if command is None and self.campoComando:
            command = self.campoComando.text().strip()
        
        if not command:
            return

        # --- INICIO DE LA MODIFICACIÓN: Lógica de diálogo modal para DATOS_MEDIDOR ---
        current_state = self.state_manager.get_current_state_name()
        if current_state == 'DATOS_MEDIDOR_MENU' and command in ['1', '2', '3', '4'] and not self.sequence_manager.command_queue:
            # Mapeo de comandos a títulos y etiquetas para el diálogo
            dialog_map = {
                '1': ("Entrar Valor X", "Nuevo valor para X [r/kWh]:"),
                '2': ("Entrar Valor K", "Nuevo valor para K:"),
                '3': ("Entrar Valor M", "Nuevo valor para M:"),
                '4': ("Entrar Valor T", "Nuevo valor para T [min]:")
            }
            title, label = dialog_map[command]

            # Primero, enviamos el comando numérico para entrar al modo de edición en el TVK6
            self.monitorSalida.appendPlainText(f"-> CMD: '{command}' (Abriendo diálogo)")
            self.send_to_worker.emit(command)

            # Abrimos el diálogo modal
            dialog = InputDialog(title, label, self)
            if dialog.exec() == InputDialog.Accepted:
                value = dialog.get_value()
                self.monitorSalida.appendPlainText(f"-> DATO: Enviando '{value}'")
                # Enviamos el valor introducido por el usuario
                self.send_to_worker.emit(value)
                # El SerialWorker ya añade un 'enter' (\r) al final de un envío de múltiples caracteres,
                # por lo que no necesitamos enviar 'enter' explícitamente aquí.
        else:
            # Lógica de envío normal para todos los demás comandos y estados
            self.monitorSalida.appendPlainText(f"-> CMD: '{command}'")
            self.command_to_statemanager.emit(command) # Notificar al StateManager
            self.send_to_worker.emit(command) # Enviar al SerialWorker
        
        if not self.thread or not self.thread.isRunning() or not self.worker.serial_port or not self.worker.serial_port.is_open:
            if self.monitorSalida:
                self.monitorSalida.appendPlainText(f"[ERROR LOCAL] No se pudo enviar '{command}': Puerto no conectado.")
            if self.campoComando:
                self.campoComando.clear()
            return
        # --- FIN DE LA MODIFICACIÓN ---

        if self.campoComando:
            self.campoComando.clear()

    def _set_ui_enabled(self, enabled):
        """Habilita o deshabilita los controles principales de la UI durante una secuencia."""
        self.btnReconectar.setEnabled(enabled)
        self.btnRetornar.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)
        self.campoComando.setEnabled(enabled)
        self.btnGestionarModelos.setEnabled(enabled)

    @Slot()
    def _run_calibration_sequence(self, params):
        """
        Construye y ejecuta la secuencia de calibración.
        :param params: Puede ser un string (valor de X) o un dict con {constante, k, ds, di}.
        """
        self.show_loader()
        self._set_ui_enabled(False)

        if isinstance(params, dict): # Calibración desde el gestor de modelos
            x_value = str(params['constante'])
            k_value = str(params['k'])
            ds_value = str(params['ds'])
            di_value = str(params['di'])
            self.etiquetaEstado.setText(f"Cargando calibración con modelo (X={x_value}, K={k_value})...")

        # Secuencia de calibración actualizada
        # Se eliminan los 'enter' explícitos después de x_value y k_value.
        # El SerialWorker ya envía un \r después de transmitir un valor de múltiples caracteres.
        commands = ['reset', '1', '1', '1', x_value, '2', k_value, 'esc', 'esc', '2', '3', "4", " ", " ", " ", ds_value, di_value, "enter", '1']
        self.sequence_manager.start_sequence(commands)

    @Slot(object)
    def on_write_result(self, bytes_sent):
        """Señal de confirmación de escritura."""
        if not bytes_sent and self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ADVERTENCIA] Error de escritura. El puerto pudo haberse cerrado.")

    @Slot(str)
    def _on_sequence_finished(self, message):
        """Se ejecuta cuando el SequenceManager ha terminado todos sus comandos."""
        self.hide_loader()
        self._set_ui_enabled(True)
        self.etiquetaEstado.setText(message)

    def _animate_pulse(self):
        """Función llamada por el QTimer para actualizar la animación."""
        import math
        # Usamos una función seno para crear un ciclo suave de crecimiento y decrecimiento
        current_time = self.anim_timer.interval() * self.anim_timer.timerId() / 1000.0
        pulse = (math.sin(current_time * 2) + 1) / 2 # Normalizado entre 0 y 1
        blur_radius = 10 + pulse * 15 # Animar entre 10 y 25
        self.shadow_effect.setBlurRadius(blur_radius)

    @Slot(str)
    def display_data(self, raw_data):
        """Muestra la data RAW y realiza el parsing de datos Medidos."""
        # 1. Mostramos el loader solo si no estamos en la vista de calibración.
        if self.state_manager.get_current_state_name() != 'CALIBRAR_TABLE_VIEW':
            self.show_loader()
        self.screen_emulator.process_data(raw_data)
        # 2. Reiniciamos el temporizador. La lógica de procesamiento solo se ejecutará
        #    cuando los datos dejen de llegar por un breve momento.
        self.processing_timer.start()

    def _process_screen_snapshot(self):
        """
        Se ejecuta cuando el temporizador termina, procesando la pantalla "estable".
        Este es el núcleo de la nueva lógica de snapshots.
        """
        screen_text = self.screen_emulator.get_screen_text()

        # Actualizar la consola de texto con la pantalla completa y estable
        # --- INICIO DE LA MODIFICACIÓN: Minimizar líneas en blanco ---
        minimized_screen_text_lines = []
        last_line_was_blank = False
        for line in screen_text.splitlines():
            if line.strip() == "":
                if not last_line_was_blank:
                    minimized_screen_text_lines.append(line)
                last_line_was_blank = True
            else:
                minimized_screen_text_lines.append(line)
                last_line_was_blank = False
        minimized_screen_text = "\n".join(minimized_screen_text_lines)
        print("\n--- SNAPSHOT DE PANTALLA (2s) ---\n" + minimized_screen_text + "\n-----------------------------------\n")
        # --- FIN DE LA MODIFICACIÓN ---
        self.monitorSalida.setPlainText(screen_text) # Mostrar el texto emulado en la consola
        
        # El StateManager se encarga de todo:
        # 1. Parsear datos de medición (X, K, U1) y actualizar el panel.
        # 2. Detectar cambios de estado (ej. INIT -> MAIN_MENU).
        # 3. Dibujar los botones del menú actual.
        self.state_manager.process_screen_text(screen_text, self.measurement_panel)
        # --- INICIO DE LA MODIFICACIÓN: Actualizar vista gráfica de calibración ---
        # --- INICIO DE LA MODIFICACIÓN: Lógica de visibilidad de widgets personalizados ---
        current_state = self.state_manager.get_current_state_name()

        # Visibilidad del título principal en el modo gráfico
        state_config = self.state_manager.config['states'].get(current_state, {})
        title_for_state = state_config.get('title')

        if title_for_state:
            self.graphicViewTitle.setText(title_for_state)
            self.graphicViewTitle.setVisible(True)
        else:
            self.graphicViewTitle.setVisible(False)

        # Visibilidad de la cabecera de Datos Medidor
        if current_state == 'DATOS_MEDIDOR_MENU':
            self.datosMedidorHeader.setVisible(True)
            # Actualizar valores en la cabecera
            self.valorDatosX.setText(self.state_manager.parsed_values.get('X', '---'))
            self.valorDatosK.setText(self.state_manager.parsed_values.get('K', '---'))
            self.valorDatosM.setText(self.state_manager.parsed_values.get('M', '---'))
            self.valorDatosT.setText(self.state_manager.parsed_values.get('T', '---'))
            self.valorDatosU1.setText(self.state_manager.parsed_values.get('U1', '---'))
        else:
            self.datosMedidorHeader.setVisible(False)

        # Visibilidad de la cabecera de Calibración
        if current_state in ['CALIBRAR_MENU', 'CALIBRAR_TABLE_VIEW']:
            self.calibrationHeader.setVisible(True)
            # Actualizar valores en la cabecera de calibración
            self.valorCalibPercent.setText(self.state_manager.parsed_values.get('calib_percent', '---'))
            indicac_text = self.state_manager.parsed_values.get('calib_indicac', '---')
            self.valorCalibIndicac.setText(f"INDICAC.: {indicac_text}")
            # Actualizar la segunda fila de la cabecera de calibración
            self.valorCalibX.setText(self.state_manager.parsed_values.get('X', '---'))
            self.valorCalibK.setText(self.state_manager.parsed_values.get('K', '---'))
            self.valorCalibM.setText(self.state_manager.parsed_values.get('M', '---'))
            self.valorCalibT.setText(self.state_manager.parsed_values.get('T', '---'))
            self.valorCalibU1.setText(self.state_manager.parsed_values.get('U1', '---'))
            # Actualizar la cuarta fila (datos de la tabla)
            self.valorCalibDi.setText(self.state_manager.parsed_values.get('di', '---'))
            self.valorCalibDs.setText(self.state_manager.parsed_values.get('ds', '---'))
            self.valorCalibI1A.setText(self.state_manager.parsed_values.get('I1', '---'))
            # Los otros valores (No, I, L123, etc.) no se parsean actualmente. Se mostrarán como '---'.
        else:
            self.calibrationHeader.setVisible(False)

        # Visibilidad de la tabla de calibración
        if current_state == 'CALIBRAR_TABLE_VIEW':
            self.calibration_table_view.setVisible(True)
            # Obtener di y ds del state_manager
            di = self.state_manager.parsed_values.get('di', '---')
            ds = self.state_manager.parsed_values.get('ds', '---')
            self.calibration_table_view.update_values(screen_text, di, ds)
            # --- INICIO DE LA MODIFICACIÓN: Dibujar botones del menú de calibración ---
            # Forzamos que se dibujen los botones del menú de calibración debajo de la tabla.
            self.menu_manager.parse_and_draw(screen_text, force_config_name='CALIBRAR_MENU')
            # --- FIN DE LA MODIFICACIÓN ---
        else:
            # Si no estamos en esa vista, nos aseguramos de que esté oculta
            self.calibration_table_view.setVisible(False)
            # Restaurar el título si es necesario (esto podría necesitar más lógica)
        # --- FIN DE LA MODIFICACIÓN ---
        # --- FIN DE LA MODIFICACIÓN ---
        if current_state != 'CALIBRAR_TABLE_VIEW':
            self.hide_loader() # Ocultar el loader después de procesar todo

    def show_loader(self):
        """Muestra el panel de carga superpuesto."""
        self.loadingLabel.setText("Cargando...")
        self.loadingOverlay.setVisible(True)
        self.loadingOverlay.raise_()

    def hide_loader(self):
        """Oculta el panel de carga."""
        self.loadingOverlay.setVisible(False)


    @Slot(str)
    def display_error(self, message):
        """Muestra errores internos del hilo worker."""
        if self.monitorSalida:
            self.monitorSalida.appendPlainText(f"[ERROR DE HILO] {message}")

    def keyPressEvent(self, event):
        """Captura eventos de teclado para atajos numéricos."""
        key = event.key()
        current_state = self.state_manager.get_current_state_name()

        # Si se presiona una tecla numérica (0-9) y el campo de texto no tiene el foco
        # Y NO estamos en un modo de entrada de datos.
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9 and self.campoComando and not self.campoComando.hasFocus() and current_state not in ['CALIBRAR_DATA_ENTRY']:
            command = str(key - Qt.Key.Key_0)
            # Centralizamos el envío de comandos a través de un único método
            self.send_command(command)
        # --- INICIO DE LA MODIFICACIÓN: Atajo global para Enter/Return ---
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter] and self.campoComando and not self.campoComando.hasFocus():
            # Si se presiona Enter y no estamos en un campo de texto, enviamos el comando de retorno ('esc' se mapea a \r)
            self.send_command('esc')
        # --- FIN DE LA MODIFICACIÓN ---
        # --- INICIO DE LA MODIFICACIÓN: Navegación por campos ---
        # Si estamos en modo de entrada de datos de calibración, las flechas y Enter tienen funciones especiales.
        elif current_state in ['CALIBRAR_DATA_ENTRY']:
            # En el modo de entrada de datos, solo las flechas y el borrado son atajos globales. El "Enter"
            # es manejado exclusivamente por el QLineEdit para evitar dobles envíos.
            # La flecha derecha puede actuar como "Enter" para avanzar al siguiente campo.
            if key == Qt.Key.Key_Right:
                self.send_command('enter') # 'enter' se traduce a \r en el worker
                event.accept() # Marcamos el evento como manejado
            elif key == Qt.Key.Key_Left:
                # Flecha Izquierda envía un escape para retroceder.
                self.send_command('esc_key')
                event.accept()
            elif key in [Qt.Key.Key_Backspace, Qt.Key.Key_Delete]:
                # La tecla de borrar envía un backspace para borrar en el TVK6
                self.send_command('del')
                event.accept()
            else:
                super().keyPressEvent(event)
        # --- FIN DE LA MODIFICACIÓN ---
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Se llama cada vez que la ventana cambia de tamaño."""
        super().resizeEvent(event)
        # Centrar el overlay de carga
        overlay_size = self.loadingOverlay.size()
        center_point = self.rect().center()
        self.loadingOverlay.move(center_point.x() - overlay_size.width() / 2, center_point.y() - overlay_size.height() / 2)

    def closeEvent(self, event):
        """Asegura que el worker y el hilo terminen al cerrar la ventana."""
        # Cerrar la conexión de la base de datos
        if self.anim_timer:
            self.anim_timer.stop()
        self.db_manager.close()
        try:
            if self.worker:
                self.worker.stop()
            if self.thread:
                self.thread.quit()
                self.thread.wait()
        except Exception:
            pass
        super().closeEvent(event)