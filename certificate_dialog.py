"""
Módulo que define el QDialog para la entrada de datos del certificado de calibración.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QDialogButtonBox, QGroupBox, QLabel)
from PySide6.QtCore import QDate, QTime

class CertificateDialog(QDialog):
    """
    Un diálogo modal para que el usuario ingrese y confirme los datos
    requeridos para el certificado de calibración.
    """
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
        form_layout.addRow("<b>Calibrador:</b>", self.calibrador_input)
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