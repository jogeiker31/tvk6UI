"""
Módulo de la ventana principal de la aplicación.

Contiene la clase MainWindow, que gestiona la interfaz de usuario,
las interacciones y la orquestación del SerialWorker.
"""
import re
from collections import deque
from PySide6.QtWidgets import (QDialog, QMainWindow, QLineEdit, QPlainTextEdit, QLabel, QPushButton, QVBoxLayout, QGroupBox, QMenu, QComboBox, QStackedWidget, QCheckBox, QFrame, QMessageBox, QHBoxLayout, QWidget,
                               QGraphicsDropShadowEffect)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, Slot, QThread, Qt, QTimer, QObject
from PySide6.QtCore import Signal, Slot, QThread, Qt, QTimer, QObject, QEvent
from PySide6.QtGui import QKeySequence, QPixmap

# Importaciones de nuestros módulos
from serial.tools import list_ports
from serial_connection_manager import SerialConnectionManager
from config import ANSI_ESCAPE, PORT, BAUDRATE
from ui_panels import MeasurementPanel
from menu_manager import MenuManager
from state_manager import StateManager
from database import DatabaseManager
from ui_model_manager import ModelManagerDialog
from calibrator_manager_dialog import CalibratorManagerDialog
from calibration_view import CalibrationTableView
from ui_input_dialog import InputDialog
from sequence_manager import SequenceManager
from screen_emulator import ScreenEmulator
import json
import os, sys
import datetime
from themes import DARK_THEME, LIGHT_THEME
# --- INICIO DE LA MODIFICACIÓN: Importar lógica de acciones ---
from main_window_actions import (open_settings_dialog, open_model_manager,
                                 open_calibrator_manager, open_history_view,
                                 handle_calibration_data_entry, handle_meter_data_entry,
                                 handle_print_certificate, handle_save_protocol, run_calibration_sequence)
# --- FIN DE LA MODIFICACIÓN ---

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    """Ventana principal que carga la UI y conecta la lógica."""
    send_to_worker = Signal(str)
    # Señal para enviar comandos desde la UI al StateManager
    command_to_statemanager = Signal(str)

    def __init__(self, ui_file):
        super().__init__()

        self.parsed_values = {'X': '---', 'K': '---', 'U1': '---', 'I1': '---', 'di': '---', 'ds': '---'}

        # Almacenar datos del modelo y calibrador para el certificado y estado general
        self.current_model_data_for_cert = {}
        self.current_calibrator_data = {}

        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setCentralWidget(self.ui)

        self.current_theme = 'dark' # Tema por defecto
        self._find_widgets()
        self._update_active_calibrator_display() # Actualizar estado inicial del panel de calibrador

        logo_container = QHBoxLayout()
        logo_container.addStretch()
        logo_label = QLabel()
        logo_path = resource_path('logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Ajustamos el tamaño para que no sea demasiado grande en la UI principal
            logo_label.setPixmap(pixmap.scaled(200, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("TVK6") # Fallback si no se encuentra el logo
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00008B;")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_container.addWidget(logo_label)
        logo_container.addStretch()

        if self.ui.layout():
            self.ui.layout().insertLayout(0, logo_container)

        self.measurement_panel = MeasurementPanel(self.ui)
        self.menu_manager = MenuManager(self.ui, self)
        self.screen_emulator = ScreenEmulator()
        self.state_manager = StateManager(self.menu_manager)
        self.sequence_manager = SequenceManager(delay=2000, parent=self)
        
        # 1. Inicializar el gestor de la base de datos
        self.db_manager = DatabaseManager()

        self._connect_signals()

        self.processing_timer = QTimer(self)
        self.processing_timer.setInterval(1000)  # ms de espera antes de procesar (2 segundos)
        self.processing_timer.setSingleShot(True)
        self.processing_timer.timeout.connect(self._process_screen_snapshot)
        self._setup_visual_effects()

        # Llenar la lista de puertos COM
        self.refresh_com_ports()

        self.connection_manager = SerialConnectionManager(self)
        self.start_connection()
        
        # Aplicar el tema inicial
        self._apply_theme(self.current_theme)

        self.setWindowTitle("TVK6 Serial Console - Python 3.11 / PySide6")

        self.showMaximized()

        # Establecer la vista inicial (gráfica) y la visibilidad de los botones
        self.switch_view(is_console_mode=False)

        # Forzar la selección de un calibrador al inicio
        self.select_initial_calibrator()

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

        # Widgets del panel Medidor Activo
        self.valorModelo = self.ui.findChild(QLabel, 'valorModelo')
        self.imagenMedidor = self.ui.findChild(QLabel, 'imagenMedidor')

        # Widgets del panel Calibrador Activo (ahora definidos en el .ui)
        self.calibradorActivoGroupBox = self.ui.findChild(QGroupBox, 'calibradorActivoGroupBox')
        self.details_widget = self.ui.findChild(QWidget, 'calibratorDetailsWidget')
        self.imagenCalibrador = self.ui.findChild(QLabel, 'imagenCalibrador')
        self.valorNombreCalibrador = self.ui.findChild(QLabel, 'valorNombreCalibrador')
        self.valorIdCalibrador = self.ui.findChild(QLabel, 'valorIdCalibrador')
        self.btnSeleccionarCalibrador = self.ui.findChild(QPushButton, 'btnSeleccionarCalibrador')

        # Derivar la referencia al GroupBox del medidor activo
        if self.valorModelo:
            parent = self.valorModelo.parentWidget()
            while parent and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            self.medidorActivoGroupBox = parent # Será el QGroupBox o None si no se encuentra
        else:
            self.medidorActivoGroupBox = self.ui.findChild(QGroupBox, 'medidorActivoGroupBox')

        # Widgets para el cambio de vista
        self.viewSwitcher = self.ui.findChild(QCheckBox, 'viewSwitcher')
        if self.viewSwitcher:
            self.viewSwitcher.setVisible(False)
        self.graphicViewTitle = self.ui.findChild(QLabel, 'graphicViewTitle')
        self.viewStackedWidget = self.ui.findChild(QStackedWidget, 'viewStackedWidget')

        self.customGraphicLayout = self.ui.findChild(QVBoxLayout, 'customGraphicLayout')
        self.calibration_table_view = CalibrationTableView(rows=2, cols=10)
        self.customGraphicLayout.insertWidget(0, self.calibration_table_view) # Añadirlo al layout
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
        self.calibration_table_view.setVisible(False) # Oculto por defecto

        self.loadingOverlay = self.ui.findChild(QFrame, 'loadingOverlay')
        self.loadingLabel = self.ui.findChild(QLabel, 'loadingLabel')
        self.hide_loader() # Asegurarse de que esté oculto al inicio

    def _connect_signals(self):
        """Conecta todas las señales de la UI a sus respectivos slots."""
        if self.campoComando:
            self.campoComando.returnPressed.connect(self.send_command)
        
        # Conectar botones fijos
        self.command_to_statemanager.connect(self.state_manager.process_command)
        self.btnRefrescarPuertos.clicked.connect(self.refresh_com_ports) 
        self.btnReconectar.clicked.connect(self.start_connection)
        self.btnRetornar.clicked.connect(lambda: self.send_command('esc'))
        self.btn_reset.clicked.connect(lambda: self.send_command('reset'))
        self.state_manager.state_changed.connect(self.on_state_changed)
        self.btnLimpiarMonitor.clicked.connect(self.clear_monitor)
        self.btnConfiguracion.clicked.connect(lambda: open_settings_dialog(self))
        self.btnGestionarModelos.clicked.connect(lambda: open_model_manager(self))
        if hasattr(self, 'btnSeleccionarCalibrador'):
            self.btnSeleccionarCalibrador.clicked.connect(lambda: open_calibrator_manager(self)) # La conexión ahora es más simple
        self.state_manager.clear_screen_requested.connect(self.clear_monitor) # Conectar la nueva señal
        self.ui.btnHistorial.clicked.connect(lambda: open_history_view(self)) # Mantenemos el historial
        # El interruptor de vista ahora se gestiona desde el diálogo de configuración.

        # Conectar el gestor de secuencias
        self.sequence_manager.send_command.connect(self.send_command)
        self.sequence_manager.sequence_finished.connect(self._on_sequence_finished)
        
        self.btn_reset.setShortcut(QKeySequence("Ctrl+R")) # Ctrl+R para reset

        # Instalar filtros de eventos para hacer que los paneles de estado sean clickables.
        # El manejo real del clic se hace en el método eventFilter.
        if self.valorModelo:
            self.valorModelo.setCursor(Qt.PointingHandCursor)
            self.valorModelo.setToolTip("Click para abrir el gestor de modelos")
            self.valorModelo.installEventFilter(self)
        if self.imagenMedidor:
            self.imagenMedidor.setCursor(Qt.PointingHandCursor)
            self.imagenMedidor.setToolTip("Click para abrir el gestor de modelos")
            self.imagenMedidor.installEventFilter(self)

        if hasattr(self, 'imagenCalibrador'):
            self.imagenCalibrador.setCursor(Qt.PointingHandCursor)
            self.imagenCalibrador.setToolTip("Click para abrir el gestor de calibradores")
            self.imagenCalibrador.installEventFilter(self)
        if hasattr(self, 'valorNombreCalibrador'):
            self.valorNombreCalibrador.setCursor(Qt.PointingHandCursor)
            self.valorNombreCalibrador.setToolTip("Click para abrir el gestor de calibradores")
            self.valorNombreCalibrador.installEventFilter(self)
        if hasattr(self, 'valorIdCalibrador'):
            self.valorIdCalibrador.setCursor(Qt.PointingHandCursor)
            self.valorIdCalibrador.setToolTip("Click para abrir el gestor de calibradores")
            self.valorIdCalibrador.installEventFilter(self)
    
    @Slot(dict)
    def _on_calibrator_selected(self, data):
        """Se activa cuando un calibrador es seleccionado en el diálogo."""
        self.current_calibrator_data = data
        self._update_active_calibrator_display()

    @Slot()
    def _update_active_calibrator_display(self):
        """Actualiza el panel del calibrador activo con nombre, ID e imagen."""
        if not self.current_calibrator_data:
            # Estado "no seleccionado"
            self.details_widget.setVisible(False)
            self.btnSeleccionarCalibrador.setText("Seleccionar Calibrador")
        else:
            self.btnSeleccionarCalibrador.setStyleSheet("background-color: #007bff; color: white;")
            # Estado "seleccionado"
            self.valorNombreCalibrador.setText(self.current_calibrator_data.get('nombre', 'N/A'))
            self.valorIdCalibrador.setText(f"ID: {self.current_calibrator_data.get('identificador', '---')}")
            
            imagen_path = self.current_calibrator_data.get('imagen_path')
            if imagen_path and os.path.exists(imagen_path):
                pixmap = QPixmap(imagen_path)
                self.imagenCalibrador.setPixmap(pixmap.scaled(
                    self.imagenCalibrador.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                self.imagenCalibrador.clear()

            self.details_widget.setVisible(True)
            self.btnSeleccionarCalibrador.setText("Cambiar Calibrador")

    @Slot(str)
    def _apply_theme(self, theme_name):
        """Aplica la hoja de estilos correspondiente al tema seleccionado."""
        self.current_theme = theme_name
        if theme_name == 'dark':
            self.ui.setStyleSheet(DARK_THEME)
        else:
            self.ui.setStyleSheet(LIGHT_THEME)
        # Podríamos necesitar reaplicar estilos específicos si se pierden

    def select_initial_calibrator(self):
        """
        Fuerza al usuario a seleccionar un calibrador al iniciar la aplicación.
        El diálogo no se puede cerrar hasta que se seleccione uno.
        """
        if not self.current_calibrator_data:
            QMessageBox.information(self, "Bienvenido", "Para comenzar, por favor seleccione el calibrador que realizará el trabajo.")
            
            dialog = CalibratorManagerDialog(self.db_manager, self, initial_selection_mode=True)
            dialog.calibrator_selected.connect(self._on_calibrator_selected)
            dialog.exec()
            
            # Si por alguna razón el diálogo se cierra sin seleccionar, cerramos la app.
            if not self.current_calibrator_data:
                self.close()

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
            self.viewStackedWidget.setCurrentIndex(0)  # Ir a la página de consola
        else:
            self.viewStackedWidget.setCurrentIndex(1)  # Ir a la página de gráficos

        # Ocultar el botón "Limpiar Consola" si no estamos en modo consola
        if self.btnLimpiarMonitor:
            self.btnLimpiarMonitor.setVisible(is_console_mode)

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

    def start_connection(self):
        """Inicia o reinicia el QThread y el SerialWorker."""
        # Limpiar la consola al iniciar o reconectar.
        self.clear_monitor()
        
        # Obtener el puerto seleccionado del ComboBox
        selected_port = self.comboPuerto.currentText()
        if "No hay puertos" in selected_port:
            self.set_status(False, "Error: No se ha seleccionado un puerto COM válido.")
            return
        
        # Delegamos toda la gestión al connection_manager
        self.connection_manager.start_connection(selected_port)

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
            
    @Slot(str)
    def on_state_changed(self, new_state):
        """Se activa cuando el StateManager cambia de estado."""
        # Actualiza la barra de estado y las vistas dinámicas según el nuevo estado.
        if new_state == 'MAIN_MENU' and self.connection_manager and self.connection_manager.get_serial_port_status():
            self.set_status(True, "CONECTADO - TVK6 LISTO")
        
        # Centralizamos la actualización de la UI aquí
        self._update_dynamic_views(new_state)

    @Slot(bool, str)
    def set_status(self, is_connected, message):
        """Actualiza la barra de estado superior."""
        current_app_state = self.state_manager.get_current_state_name()

        if self.etiquetaEstado:
            self.etiquetaEstado.setText(message)

        if not is_connected:
            bg_color = "#dc3545"  # Rojo
        elif current_app_state == 'INIT':
            bg_color = "#fd7e14"  # Naranja
            self.etiquetaEstado.setText("ESPERANDO DATOS DEL TVK6")
        else:
            bg_color = "#28a745"  # Verde

        text = "Comando (reset, 1, 2, etc.)" if is_connected else "ERROR: Conexión serial bloqueada."
        enabled = is_connected
            
        if self.etiquetaEstado:
            self.etiquetaEstado.setStyleSheet(f"color: white; background-color: {bg_color}; padding: 8px; border-radius: 5px; font-weight: bold;")

        if self.campoComando:
            self.campoComando.setEnabled(enabled)
            self.campoComando.setPlaceholderText(text)

        if "ERROR" in message and self.campoComando:
            self.campoComando.setEnabled(True)

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
        
        if current_state in ['CALIBRAR_MENU', 'CALIBRAR_TABLE_VIEW'] and command == '4' and not self.sequence_manager.command_queue:
            handle_calibration_data_entry(self)
            return

        elif current_state == 'DATOS_MEDIDOR_MENU' and command in ['1', '2', '3', '4'] and not self.sequence_manager.command_queue:
            handle_meter_data_entry(self, command)
            return

        elif current_state == 'CALIBRAR_TABLE_VIEW' and command == '5':
            handle_print_certificate(self)
            return
        
        elif current_state == 'CALIBRAR_TABLE_VIEW' and command == '6':
            handle_save_protocol(self)
            return
        
        else:
            # Lógica de envío normal para todos los demás comandos y estados
            self.monitorSalida.appendPlainText(f"-> CMD: '{command}'")
            self.command_to_statemanager.emit(command) # Notificar al StateManager
            self.send_to_worker.emit(command) # Enviar al SerialWorker
        
        if not self.connection_manager.get_serial_port_status():
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
        self._update_active_meter_display()

        current_state = self.state_manager.get_current_state_name()
        self._update_dynamic_views(current_state, screen_text)

        if current_state != 'CALIBRAR_TABLE_VIEW':
            self.hide_loader() # Ocultar el loader después de procesar todo

    def _update_dynamic_views(self, current_state, screen_text=None):
        """
        Actualiza la visibilidad y el contenido de los paneles dinámicos
        (título, cabeceras, tabla de calibración) según el estado actual.
        """
        # Actualizar título principal de la vista gráfica
        state_config = self.state_manager.config['states'].get(current_state, {})
        title_for_state = state_config.get('title')
        self.graphicViewTitle.setText(title_for_state or "")
        self.graphicViewTitle.setVisible(bool(title_for_state))

        # Visibilidad y datos de las cabeceras
        is_datos_medidor_visible = (current_state == 'DATOS_MEDIDOR_MENU')
        self.datosMedidorHeader.setVisible(is_datos_medidor_visible)
        if is_datos_medidor_visible:
            self._update_header_data('datos_medidor')

        is_calib_header_visible = current_state in ['CALIBRAR_MENU', 'CALIBRAR_TABLE_VIEW']
        self.calibrationHeader.setVisible(is_calib_header_visible)
        if is_calib_header_visible:
            self._update_header_data('calibracion')

        # Visibilidad y datos de la tabla de calibración
        is_calib_table_visible = (current_state == 'CALIBRAR_TABLE_VIEW')
        self.calibration_table_view.setVisible(is_calib_table_visible)
        if is_calib_table_visible and screen_text:
            di = self.state_manager.parsed_values.get('di', '---')
            ds = self.state_manager.parsed_values.get('ds', '---')
            self.calibration_table_view.update_values(screen_text, di, ds)
            self.menu_manager.parse_and_draw(screen_text)

    def _update_header_data(self, header_type):
        """Rellena los QLabels de una cabecera específica con datos del StateManager."""
        vals = self.state_manager.parsed_values
        if header_type == 'datos_medidor':
            self.valorDatosX.setText(vals.get('X', '---'))
            self.valorDatosK.setText(vals.get('K', '---'))
            self.valorDatosM.setText(vals.get('M', '---'))
            self.valorDatosT.setText(vals.get('T', '---'))
            self.valorDatosU1.setText(vals.get('U1', '---'))
        elif header_type == 'calibracion':
            self.valorCalibPercent.setText(vals.get('calib_percent', '---'))
            self.valorCalibIndicac.setText(f"INDICAC.: {vals.get('calib_indicac', '---')}")
            self.valorCalibX.setText(vals.get('X', '---'))
            self.valorCalibK.setText(vals.get('K', '---'))
            self.valorCalibM.setText(vals.get('M', '---'))
            self.valorCalibT.setText(vals.get('T', '---'))
            self.valorCalibU1.setText(vals.get('U1', '---'))
            self.valorCalibI.setText(vals.get('calib_i_percent', '---'))
            self.valorCalibL123.setText(vals.get('calib_l123', '---'))
            self.valorCalibCos.setText(vals.get('calib_cos', '---'))
            self.valorCalibDi.setText(vals.get('di', '---'))
            self.valorCalibDs.setText(vals.get('ds', '---'))
            self.valorCalibGo.setText(vals.get('calib_go', '---'))
            self.valorCalibR.setText(vals.get('calib_r', '---'))
            self.valorCalibI1A.setText(vals.get('I1', '---'))

    def show_loader(self):
        """Muestra el panel de carga superpuesto."""
        self.loadingLabel.setText("Cargando...")
        self.loadingOverlay.setVisible(True)
        self.loadingOverlay.raise_()

    def _update_active_meter_display(self):
        """Actualiza el panel del medidor activo con el nombre y la imagen."""
        valor_modelo = self.state_manager.parsed_values.get('modelo', 'Sin especificar')
        imagen_path = self.state_manager.parsed_values.get('imagen_path')

        if self.valorModelo:
            self.valorModelo.setText(valor_modelo)
            # Cambiar el color del texto si hay un modelo especificado para mayor visibilidad
            if valor_modelo != 'Sin especificar':
                self.valorModelo.setStyleSheet("color: #ffffff;") # Blanco brillante
            else:
                self.valorModelo.setStyleSheet("color: #adb5bd;") # Gris por defecto

        if self.imagenMedidor:
            if imagen_path and os.path.exists(imagen_path):
                pixmap = QPixmap(imagen_path)
                # Escalar el pixmap para que quepa en el QLabel manteniendo la relación de aspecto.
                self.imagenMedidor.setPixmap(pixmap.scaled(
                    self.imagenMedidor.width(), 
                    self.imagenMedidor.height(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
                self.imagenMedidor.setToolTip(f"Imagen para {valor_modelo}\nClick para cambiar de modelo.")
            else:
                self.imagenMedidor.clear()
                self.imagenMedidor.setPixmap(QPixmap()) # Limpiar pixmap
                self.imagenMedidor.setToolTip("")


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
            # --- INICIO DE LA MODIFICACIÓN: Validar comando antes de enviar ---
            # Consultamos al StateManager si el comando es válido para el estado actual.
            current_config = self.state_manager.config['states'].get(current_state, {})            
            # Un comando es válido si tiene una transición O si existe un botón habilitado con ese número.
            has_transition = command in current_config.get('transitions', {})
            is_enabled_button = any(
                btn.get('number') == command and btn.get('enabled', True) for btn in current_config.get('buttons', [])
            )
            if has_transition or is_enabled_button:
                # Solo enviamos el comando si existe una transición válida para él.
                self.send_command(command)
            # --- FIN DE LA MODIFICACIÓN ---
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

    def eventFilter(self, watched, event):
        """
        Filtra eventos para hacer clickables los paneles de estado (medidor y calibrador).
        """
        # Si se hace clic izquierdo en uno de los widgets observados, abrimos el gestor correspondiente.
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            # Panel del Medidor
            if watched in [self.valorModelo, self.imagenMedidor]:
                open_model_manager(self)
                return True  # Evento manejado
            # Panel del Calibrador
            if hasattr(self, 'imagenCalibrador') and watched in [self.imagenCalibrador, self.valorNombreCalibrador, self.valorIdCalibrador]:
                open_calibrator_manager(self)
                return True # Evento manejado
        
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        """Asegura que el worker y el hilo terminen al cerrar la ventana."""
        # Cerrar la conexión de la base de datos
        if self.anim_timer:
            self.anim_timer.stop()
        self.db_manager.close()
        self.connection_manager.stop_connection()

    def open_history_view(self):
        """Abre la ventana del historial de calibraciones."""
        open_history_view(self)