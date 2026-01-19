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
    # Señales para notificar cambios
    theme_changed = Signal(str)
    view_mode_changed = Signal(bool)

    def __init__(self, current_theme='dark', is_console_mode=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        group_box = QGroupBox("Apariencia")
        group_layout = QVBoxLayout(group_box)

        # Checkbox para el tema
        self.theme_switch = QCheckBox("Modo Oscuro")
        self.theme_switch.setChecked(current_theme == 'dark')
        self.theme_switch.toggled.connect(self.on_theme_toggled)
        group_layout.addWidget(self.theme_switch)

        # --- INICIO DE LA MODIFICACIÓN: Añadir checkbox de modo consola ---
        self.view_mode_switch = QCheckBox("Modo Consola")
        self.view_mode_switch.setChecked(is_console_mode)
        self.view_mode_switch.toggled.connect(self.on_view_mode_toggled)
        group_layout.addWidget(self.view_mode_switch)
        # --- FIN DE LA MODIFICACIÓN ---

        layout.addWidget(group_box)

    @Slot(bool)
    def on_theme_toggled(self, checked):
        self.theme_changed.emit('dark' if checked else 'light')

    @Slot(bool)
    def on_view_mode_toggled(self, checked):
        """Emite una señal cuando el modo de vista cambia."""
        self.view_mode_changed.emit(checked)