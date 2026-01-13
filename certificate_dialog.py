"""
Módulo que define el QDialog para la entrada de datos del certificado de calibración.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QDialogButtonBox, QGroupBox, QLabel, QPushButton, 
                               QHBoxLayout, QMessageBox)
from PySide6.QtCore import QDate, QTime, Slot, Signal

# --- INICIO DE LA MODIFICACIÓN: Importar el gestor de calibradores ---
from calibrator_manager_dialog import CalibratorManagerDialog
# --- FIN DE LA MODIFICACIÓN ---


class CertificateDialog(QDialog):
    """
    Un diálogo modal para que el usuario ingrese y confirme los datos
    requeridos para el certificado de calibración.
    """
    # Señal que se emite cuando un calibrador es seleccionado desde este diálogo.
    calibrator_updated = Signal(dict)

    def __init__(self, prefill_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datos para el Certificado de Calibración")
        self.setMinimumWidth(450)

        if prefill_data is None:
            prefill_data = {}

        layout = QVBoxLayout(self)
        form_group = QGroupBox("Confirme los datos del certificado")
        form_layout = QFormLayout()

        # --- Campos de entrada y etiquetas ---

        # Fecha y Hora (no editables)
        self.fecha_label = QLabel(QDate.currentDate().toString("dd/MM/yyyy"))
        self.hora_label = QLabel(QTime.currentTime().toString("hh:mm AP"))

        # Datos a rellenar por el usuario
        self.calibrador_input = QLineEdit()
        self.temperatura_input = QLineEdit()
        self.modelo_input = QLineEdit() # Usamos un QLineEdit para que sea editable

        # --- INICIO DE LA MODIFICACIÓN: Botón para seleccionar calibrador ---
        self.select_calibrator_button = QPushButton("Seleccionar...")
        self.select_calibrator_button.clicked.connect(self.open_calibrator_selector)
        calibrator_layout = QHBoxLayout()
        calibrator_layout.addWidget(self.calibrador_input)
        calibrator_layout.addWidget(self.select_calibrator_button)
        # --- FIN DE LA MODIFICACIÓN ---
        # Pre-rellenar el nombre del calibrador si viene en los datos
        calibrador_name = prefill_data.get('calibrador', '')
        if calibrador_name:
            self.calibrador_input.setText(calibrador_name)

        # Lógica para el campo de modelo:
        # Si el modelo viene pre-rellenado y no es 'N/A', lo mostramos y lo bloqueamos.
        # Si no, dejamos el campo editable para que el usuario lo ingrese.
        model_name = prefill_data.get('modelo', 'N/A')
        if model_name and model_name != 'N/A':
            self.modelo_input.setText(model_name)
            self.modelo_input.setReadOnly(True)
        else:
            self.modelo_input.setPlaceholderText("Ingrese el modelo del medidor")
            self.modelo_input.setReadOnly(False)

        self.constante_label = QLabel(prefill_data.get('constante', '---'))
        self.tension_label = QLabel(prefill_data.get('tension', '---'))
        self.intensidad_label = QLabel(prefill_data.get('intensidad', '---'))

        # Añadir campos al formulario
        form_layout.addRow("Fecha:", self.fecha_label)
        form_layout.addRow("Hora:", self.hora_label)
        form_layout.addRow("<b>Calibrador:</b>", calibrator_layout)
        form_layout.addRow("Temperatura [°C] (Opcional):", self.temperatura_input)
        form_layout.addRow("Modelo Medidor:", self.modelo_input)
        form_layout.addRow("Constante Medidor (X):", self.constante_label)
        form_layout.addRow("Tensión Nominal (U1):", self.tension_label)
        form_layout.addRow("Intensidad Nominal (I1):", self.intensidad_label)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Botones de Aceptar y Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    # --- INICIO DE LA MODIFICACIÓN: Métodos para seleccionar calibrador ---
    @Slot()
    def open_calibrator_selector(self):
        """Abre el gestor de calibradores para seleccionar uno."""
        main_window = self.parent()
        if not main_window or not hasattr(main_window, 'db_manager'):
            QMessageBox.critical(self, "Error", "No se pudo acceder al gestor de base de datos.")
            return

        dialog = CalibratorManagerDialog(main_window.db_manager, self)
        dialog.calibrator_selected.connect(self.update_calibrator_field)
        dialog.exec()

    @Slot(dict)
    def update_calibrator_field(self, calibrator_data):
        """
        Actualiza el campo de texto del calibrador con el nombre seleccionado
        y emite una señal para notificar a la ventana principal.
        """
        if calibrator_data and 'nombre' in calibrator_data:
            self.calibrador_input.setText(calibrator_data['nombre'])
            self.calibrator_updated.emit(calibrator_data)
    # --- FIN DE LA MODIFICACIÓN ---

    def get_data(self):
        """Devuelve un diccionario con todos los datos para el PDF."""
        return {
            "fecha": self.fecha_label.text(),
            "hora": self.hora_label.text(),
            "calibrador": self.calibrador_input.text(),
            "temperatura": self.temperatura_input.text(),
            "modelo": self.modelo_input.text(),
            "constante": self.constante_label.text(),
            "tension": self.tension_label.text(),
            "intensidad": self.intensidad_label.text()
        }