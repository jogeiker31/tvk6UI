"""
Módulo para desacoplar la lógica de acciones de la MainWindow.

Contiene funciones que manejan la apertura de diálogos, la ejecución de
secuencias y otras lógicas de negocio que antes estaban en main_window.py.
Cada función recibe la instancia de `main_window` como argumento para
acceder a sus widgets, gestores y estado.
"""
import os
import json
import datetime
from PySide6.QtWidgets import QDialog, QMessageBox

# Importaciones de la aplicación
from settings_dialog import SettingsDialog
from ui_model_manager import ModelManagerDialog
from calibrator_manager_dialog import CalibratorManagerDialog
from history_view import HistoryView
from ui_input_dialog import InputDialog
from certificate_dialog import CertificateDialog
from pdf_generator import generate_certificate_pdf

def open_settings_dialog(main_window):
    """Abre el diálogo de configuración."""
    is_console_mode = main_window.viewStackedWidget.currentIndex() == 0
    dialog = SettingsDialog(current_theme=main_window.current_theme, is_console_mode=is_console_mode, parent=main_window)
    dialog.theme_changed.connect(main_window._apply_theme)
    dialog.view_mode_changed.connect(main_window.switch_view)
    dialog.exec()

def open_model_manager(main_window):
    """Abre el diálogo para gestionar los modelos de medidores."""
    dialog = ModelManagerDialog(main_window.db_manager, main_window)
    dialog.start_calibration_requested.connect(lambda params: run_calibration_sequence(main_window, params))
    dialog.exec()

def open_calibrator_manager(main_window):
    """Abre el diálogo para gestionar los calibradores."""
    dialog = CalibratorManagerDialog(main_window.db_manager, main_window)
    dialog.calibrator_selected.connect(main_window._on_calibrator_selected)
    dialog.exec()

def open_history_view(main_window):
    """Abre la ventana del historial de calibraciones."""
    main_window.history_window = HistoryView(main_window.db_manager, theme=main_window.current_theme, parent=main_window)
    main_window.history_window.show()

def run_calibration_sequence(main_window, params):
    """Construye y ejecuta la secuencia de calibración rápida."""
    main_window.show_loader()
    main_window._set_ui_enabled(False)

    if isinstance(params, dict):
        x_value = str(params['constante'])
        k_value = str(params['k'])
        ds_value = str(params['ds'])
        di_value = str(params['di'])
        
        main_window.current_model_data_for_cert = {
            'nombre': params['nombre'],
            'constante': x_value,
            'k': k_value,
            'ds': ds_value,
            'di': di_value,
            'imagen_path': params.get('imagen_path')
        }
        
        main_window.state_manager.parsed_values['modelo'] = params['nombre']
        main_window.state_manager.parsed_values['imagen_path'] = params.get('imagen_path')
        main_window.measurement_panel.update_display(main_window.state_manager.parsed_values)
        main_window._update_active_meter_display()
        
        main_window.etiquetaEstado.setText(f"Cargando calibración con modelo (X={x_value}, K={k_value})...")

    commands = ['reset', '1', '1', '1', x_value, '2', k_value, 'esc', 'esc', '2', '3', "4", " ", " ", " ", di_value, ds_value," "," ", "enter", '1']
    main_window.sequence_manager.start_sequence(commands)

def handle_calibration_data_entry(main_window):
    """Maneja el diálogo para la entrada de datos de la tabla de calibración."""
    labels = ["I [%]:", "L1-2-3:", "cos/sin:", "di:", "ds:", "go:", "r:"]
    defaults = [
        "", "", "",
        main_window.state_manager.parsed_values.get('di', ''),
        main_window.state_manager.parsed_values.get('ds', ''),
        "0.0", ""
    ]
    dialog = InputDialog("Entrar Datos de Calibración", labels, main_window, data_type="multiple", defaults=defaults)

    if dialog.exec() == QDialog.Accepted:
        raw_values = dialog.get_values()
        processed_values = []
        for i, value in enumerate(raw_values):
            if value == " ":
                processed_values.append(value)
                continue
            if i == 1 and value.isdigit() and len(value) == 1:
                processed_values.append(f"{value}-")
            elif value.lstrip('-').isdigit():
                processed_values.append(f"{value}.0")
            else:
                processed_values.append(value)

        commands_to_send = ['4'] + processed_values + ['enter']
        main_window.sequence_manager.start_sequence(commands_to_send)

def handle_meter_data_entry(main_window, command):
    """Maneja el diálogo para la entrada de datos del medidor (X, K, M, T)."""
    dialog_map = {
        '1': ("Entrar Valor X", "Nuevo valor para X [r/kWh]:"),
        '2': ("Entrar Valor K", "Nuevo valor para K:"),
        '3': ("Entrar Valor M", "Nuevo valor para M:"),
        '4': ("Entrar Valor T", "Nuevo valor para T [min]:")
    }
    title, label = dialog_map[command]

    main_window.monitorSalida.appendPlainText(f"-> CMD: '{command}' (Abriendo diálogo)")
    main_window.send_to_worker.emit(command)

    dialog = InputDialog(title, label, main_window)
    if dialog.exec() == QDialog.Accepted:
        value = dialog.get_value()
        if value:
            processed_value = f"{value}.0" if value.lstrip('-').isdigit() else value
            main_window.monitorSalida.appendPlainText(f"-> DATO: Enviando '{processed_value}'")
            main_window.send_to_worker.emit(processed_value)
        else:
            main_window.send_to_worker.emit('esc')
            main_window.monitorSalida.appendPlainText("-> CMD: 'esc' (Entrada vacía, cancelando)")
    else:
        main_window.send_to_worker.emit('esc')
        main_window.monitorSalida.appendPlainText("-> CMD: 'esc' (Diálogo cancelado)")

def handle_print_certificate(main_window):
    """Recopila datos y genera el certificado PDF."""
    prefill_data = {
        'modelo': main_window.current_model_data_for_cert.get('nombre', 'N/A'),
        'constante': main_window.state_manager.parsed_values.get('X', '---'),
        'tension': main_window.state_manager.parsed_values.get('U1', '---'),
        'intensidad': main_window.state_manager.parsed_values.get('I1', '---'),
        'calibrador': main_window.current_calibrator_data.get('nombre', '')
    }
    
    dialog = CertificateDialog(prefill_data, main_window)
    if dialog.exec() == CertificateDialog.Accepted:
        certificate_data = dialog.get_data()
        table_values = main_window.calibration_table_view.get_all_values()
        generate_certificate_pdf(main_window, certificate_data, table_values)

def handle_save_protocol(main_window):
    """Recopila datos y los guarda en el historial de la base de datos."""
    prefill_data = {
        'modelo': main_window.current_model_data_for_cert.get('nombre', 'N/A'),
        'constante': main_window.state_manager.parsed_values.get('X', '---'),
        'tension': main_window.state_manager.parsed_values.get('U1', '---'),
        'intensidad': main_window.state_manager.parsed_values.get('I1', '---'),
        'calibrador': main_window.current_calibrator_data.get('nombre', '')
    }
    
    dialog = CertificateDialog(prefill_data, main_window)
    dialog.setWindowTitle("Finalizar y Guardar Protocolo")
    
    if dialog.exec() == CertificateDialog.Accepted:
        cert_data = dialog.get_data()
        
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")
        hora = datetime.datetime.now().strftime("%H:%M:%S")
        calibrador = cert_data.get('calibrador', 'N/A')
        modelo = cert_data.get('modelo', 'N/A')
        constante = cert_data.get('constante', '---')
        tension = cert_data.get('tension', '---')
        intensidad = cert_data.get('intensidad', '---')
        temperatura = cert_data.get('temperatura') or 'N/A'
        di = main_window.state_manager.parsed_values.get('di', '---')
        ds = main_window.state_manager.parsed_values.get('ds', '---')
        
        table_values = main_window.calibration_table_view.get_all_values()
        table_json = json.dumps(table_values)

        main_window.db_manager.save_calibration_data(
            fecha, hora, calibrador, constante, modelo, tension, 
            intensidad, di, ds, table_json, temperatura
        )

        QMessageBox.information(
            main_window,
            "Protocolo Finalizado",
            "Los datos de calibración han sido guardados en el historial."
        )