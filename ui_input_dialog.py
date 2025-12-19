"""
Módulo que define un QDialog modal para la entrada de datos del usuario.
"""
from typing import List
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QFormLayout)
from PySide6.QtCore import Qt

class InputDialog(QDialog):
    """
    Un diálogo modal para la entrada de datos.
    Puede manejar un solo campo o múltiples campos de formulario.
    """
    def __init__(self, title: str, labels, parent=None, data_type: str = "single", defaults: List[str] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        # No permitimos cerrar con el botón 'X' de la ventana para forzar OK/Cancel
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        self.inputs: List[QLineEdit] = []
        layout = QVBoxLayout(self)

        if data_type == "multiple" and isinstance(labels, list):
            form_layout = QFormLayout()
            for i, label_text in enumerate(labels):
                input_field = QLineEdit()
                # --- INICIO DE LA MODIFICACIÓN: Rellenar valores por defecto ---
                if defaults and i < len(defaults) and defaults[i] and defaults[i] != '---':
                    input_field.setText(defaults[i])
                # --- FIN DE LA MODIFICACIÓN ---
                form_layout.addRow(label_text, input_field)
                self.inputs.append(input_field)
            layout.addLayout(form_layout)
        else: # single input
            label_text = labels if isinstance(labels, str) else "Valor:"
            self.input_field = QLineEdit()
            form_layout = QFormLayout()
            form_layout.addRow(label_text, self.input_field)
            self.inputs.append(self.input_field)
            layout.addLayout(form_layout)

        # Botones de Aceptar y Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

    def get_value(self):
        """Devuelve el texto del primer campo de entrada."""
        if self.inputs:
            return self.inputs[0].text()
        return ""

    def get_values(self) -> List[str]:
        """
        Devuelve una lista con los valores de todos los campos de entrada.
        Si un campo está vacío, devuelve un solo espacio " ".
        """
        return [field.text() if field.text() else " " for field in self.inputs]

    def keyPressEvent(self, event):
        """
        Sobrescribimos el evento de pulsación de tecla para ignorar 'Escape'.
        """
        if event.key() == Qt.Key_Escape:
            # Al presionar Escape, se rechaza el diálogo (equivale a Cancelar)
            self.reject()
        else:
            super().keyPressEvent(event)