"""
Módulo que define un QDialog modal para la entrada de datos del usuario.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QDialogButtonBox)
from PySide6.QtCore import Qt

class InputDialog(QDialog):
    """
    Un diálogo modal simple que solicita un valor al usuario.

    Este diálogo no puede ser cerrado con la tecla 'Escape' o el botón de cerrar
    de la ventana. La única forma de cerrarlo es a través del botón 'Aceptar'.
    """
    def __init__(self, title, label_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        # --- INICIO DE LA MODIFICACIÓN: Evitar cierre accidental ---
        # Deshabilitamos el botón de cerrar de la ventana
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        # --- FIN DE LA MODIFICACIÓN ---

        layout = QVBoxLayout(self)

        self.label = QLabel(label_text)
        self.input_field = QLineEdit()
        
        # Botón de Aceptar
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)

        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.button_box)

    def get_value(self):
        """Devuelve el texto introducido por el usuario."""
        return self.input_field.text()

    def keyPressEvent(self, event):
        """
        Sobrescribimos el evento de pulsación de tecla para ignorar 'Escape'.
        """
        if event.key() == Qt.Key_Escape:
            event.ignore() # Ignoramos la tecla Escape
        else:
            super().keyPressEvent(event)