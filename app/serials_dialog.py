"""
Módulo que define el QDialog para la entrada de números de serie de los medidores.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QDialogButtonBox, QLabel, QScrollArea, QWidget)
from PySide6.QtCore import Qt

class SerialsDialog(QDialog):
    """
    Un diálogo para que el usuario ingrese los números de serie opcionales
    para cada uno de los 20 puestos de medición.
    """
    def __init__(self, table_values, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingresar Números de Serie (Opcional)")
        self.setMinimumSize(500, 600)

        main_layout = QVBoxLayout(self)

        # Mensaje de instrucción
        info_label = QLabel("Ingrese el número de serie de cada medidor (opcionales).")
        info_label.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        main_layout.addWidget(info_label)

        # ScrollArea para los inputs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)
        form_layout.setSpacing(10)

        self.inputs = {}
        flat_values = [item for sublist in table_values for item in sublist]

        for i in range(20):
            puesto_num = i + 1
            valor_actual = flat_values[i] if i < len(flat_values) and flat_values[i] != '---' else "Sin valor"
            
            label_text = f"Puesto {puesto_num} (Valor: {valor_actual}):"
            serial_input = QLineEdit()
            serial_input.setPlaceholderText(f"Serie para puesto {puesto_num}")
            
            form_layout.addRow(label_text, serial_input)
            self.inputs[str(puesto_num)] = serial_input

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Botones de Aceptar y Cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def get_serials(self):
        """
        Devuelve un diccionario con los números de serie ingresados,
        mapeando el número de puesto al número de serie.
        Solo incluye los que tienen texto.
        """
        serials = {}
        for puesto_num, input_field in self.inputs.items():
            serial_text = input_field.text().strip()
            if serial_text:
                serials[puesto_num] = serial_text
        return serials