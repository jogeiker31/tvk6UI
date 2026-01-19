"""
Módulo que define el QDialog para la entrada de datos del protocolo.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QDialogButtonBox, QGroupBox)
from PySide6.QtCore import QDate, QTime

class ProtocolDialog(QDialog):
    """
    Un diálogo modal para que el usuario ingrese los datos
    requeridos para el protocolo.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entrada de Datos del Protocolo")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_group = QGroupBox("Datos del Protocolo")
        form_layout = QFormLayout()

        # Crear campos de entrada, pre-rellenando fecha y hora
        self.fecha_input = QLineEdit(QDate.currentDate().toString("dd.MM.yy"))
        self.hora_input = QLineEdit(QTime.currentTime().toString("hh:mm"))
        self.temperatura_input = QLineEdit()
        self.protocolo_no_input = QLineEdit()
        self.marca_input = QLineEdit()
        self.tension_nominal_input = QLineEdit()
        self.tipo_input = QLineEdit()
        self.intensidad_nominal_input = QLineEdit()
        self.sistema_input = QLineEdit()
        self.constante_input = QLineEdit()
        self.calibrador_input = QLineEdit()

        # Añadir campos al formulario
        form_layout.addRow("Fecha:", self.fecha_input)
        form_layout.addRow("Hora:", self.hora_input)
        form_layout.addRow("Temperatura [°C]:", self.temperatura_input)
        form_layout.addRow("Protocolo No:", self.protocolo_no_input)
        form_layout.addRow("Marca:", self.marca_input)
        form_layout.addRow("Tensión Nominal [V]:", self.tension_nominal_input)
        form_layout.addRow("Tipo:", self.tipo_input)
        form_layout.addRow("Intensidad Nominal [A]:", self.intensidad_nominal_input)
        form_layout.addRow("Sistema:", self.sistema_input)
        form_layout.addRow("Constante:", self.constante_input)
        form_layout.addRow("Calibrador:", self.calibrador_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Botones de Aceptar y Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self):
        """Devuelve una lista ordenada con los datos del formulario."""
        return [
            self.fecha_input.text(), self.hora_input.text(), self.temperatura_input.text(),
            self.protocolo_no_input.text(), self.marca_input.text(), self.tension_nominal_input.text(),
            self.tipo_input.text(), self.intensidad_nominal_input.text(), self.sistema_input.text(),
            self.constante_input.text(), self.calibrador_input.text()
        ]