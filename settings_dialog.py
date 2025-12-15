"""
Módulo que define el QDialog para la configuración de la aplicación.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QCheckBox)
from PySide6.QtCore import Signal, Slot

class SettingsDialog(QDialog):
    """
    Un diálogo modal para ajustar la configuración de la aplicación,
    como el tema visual.
    """
    # Señal que emite el nombre del tema ('dark' o 'light')
    theme_changed = Signal(str)

    def __init__(self, current_theme='dark', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        group_box = QGroupBox("Apariencia")
        group_layout = QVBoxLayout()

        self.theme_switch = QCheckBox("Modo Oscuro")
        self.theme_switch.setChecked(current_theme == 'dark')
        self.theme_switch.toggled.connect(self.on_theme_toggled)

        group_layout.addWidget(self.theme_switch)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    @Slot(bool)
    def on_theme_toggled(self, checked):
        self.theme_changed.emit('dark' if checked else 'light')