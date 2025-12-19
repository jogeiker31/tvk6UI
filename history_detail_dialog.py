"""
Módulo para el diálogo de detalles del historial de calibración.
"""
import json
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel, QFrame, QGroupBox, QHBoxLayout, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

# Importaciones de nuestros módulos
from pdf_generator import generate_certificate_pdf
from themes import DARK_THEME, LIGHT_THEME

import sys

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
class HistoryDetailDialog(QDialog):
    """
    Muestra los detalles de un registro de calibración en un formato similar al certificado.
    """
    def __init__(self, calibration_data, theme='dark', parent=None):
        super().__init__(parent)
        self.calibration_data = calibration_data
        self.theme = theme
        
        self.setWindowTitle(f"Detalles de Calibración - ID: {self.calibration_data.get('id', 'N/A')}")
        self.setMinimumSize(800, 700)
        
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        """Configura la interfaz de usuario de la ventana."""
        main_layout = QVBoxLayout(self)

        # 1. Logo
        logo_container = QHBoxLayout()
        logo_container.addStretch()
        logo_label = QLabel()
        logo_path = resource_path('logo.png') # Asumimos que el logo está disponible
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(250, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("TVK6") # Fallback
            logo_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #00008B;")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_container.addWidget(logo_label)
        logo_container.addStretch()
        main_layout.addLayout(logo_container)

        # 2. Datos de cabecera
        header_group = QGroupBox("Datos de la Calibración")
        header_layout = QGridLayout()
        header_layout.setSpacing(15)

        # Fila 1
        header_layout.addWidget(QLabel(f"<b>Fecha:</b><br>{self.calibration_data.get('fecha', 'N/A')}"), 0, 0)
        header_layout.addWidget(QLabel(f"<b>Hora:</b><br>{self.calibration_data.get('hora', 'N/A')}"), 0, 1)
        header_layout.addWidget(QLabel(f"<b>Calibrador:</b><br>{self.calibration_data.get('calibrador', 'N/A')}"), 0, 2)
        
        # Fila 2
        header_layout.addWidget(QLabel(f"<b>Modelo:</b><br>{self.calibration_data.get('modelo', 'N/A')}"), 1, 0)
        header_layout.addWidget(QLabel(f"<b>Constante (X):</b><br>{self.calibration_data.get('constante', 'N/A')}"), 1, 1)
        temp_val = self.calibration_data.get('temperatura')
        temp_str = f"{temp_val} °C" if temp_val and temp_val != 'N/A' else 'N/A'
        header_layout.addWidget(QLabel(f"<b>Temperatura:</b><br>{temp_str}"), 1, 2)

        # Fila 3
        header_layout.addWidget(QLabel(f"<b>Tensión (U1):</b><br>{self.calibration_data.get('tension', 'N/A')}"), 2, 0)
        header_layout.addWidget(QLabel(f"<b>Intensidad (I1):</b><br>{self.calibration_data.get('intensidad', 'N/A')}"), 2, 1)

        # Fila 4
        header_layout.addWidget(QLabel(f"<b>Límite Inferior (di):</b><br>{self.calibration_data.get('di', 'N/A')}"), 3, 0)
        header_layout.addWidget(QLabel(f"<b>Límite Superior (ds):</b><br>{self.calibration_data.get('ds', 'N/A')}"), 3, 1)
        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)

        # 3. Tabla de resultados
        results_group = QGroupBox("Resultados de la Calibración")
        results_layout = QGridLayout()
        results_layout.setSpacing(10)

        # Cabeceras de la tabla
        results_layout.addWidget(QLabel("<b>Medición</b>"), 0, 0, Qt.AlignCenter)
        results_layout.addWidget(QLabel("<b>Valor</b>"), 0, 1, Qt.AlignCenter)
        results_layout.addWidget(QLabel("<b>Medición</b>"), 0, 2, Qt.AlignCenter)
        results_layout.addWidget(QLabel("<b>Valor</b>"), 0, 3, Qt.AlignCenter)
        
        try:
            table_values_json = self.calibration_data.get('tabla_calibracion', '[]')
            table_values = json.loads(table_values_json)
            di_val = float(self.calibration_data.get('di'))
            ds_val = float(self.calibration_data.get('ds'))
        except (ValueError, TypeError, json.JSONDecodeError):
            table_values = []
            di_val, ds_val = None, None

        flat_values = [item for sublist in table_values for item in sublist]
        num_items_per_col = (len(flat_values) + 1) // 2

        for i in range(num_items_per_col):
            # Columna 1 (Medición y Valor)
            val1_str = flat_values[i] if i < len(flat_values) else ''
            if val1_str and val1_str != '---':
                results_layout.addWidget(QLabel(str(i + 1)), i + 1, 0, Qt.AlignCenter)
                results_layout.addWidget(self.create_styled_value_label(val1_str, di_val, ds_val), i + 1, 1)

            # Columna 2 (Medición y Valor)
            idx2 = i + num_items_per_col
            val2_str = flat_values[idx2] if idx2 < len(flat_values) else ''
            if val2_str and val2_str != '---':
                results_layout.addWidget(QLabel(str(idx2 + 1)), i + 1, 2, Qt.AlignCenter)
                results_layout.addWidget(self.create_styled_value_label(val2_str, di_val, ds_val), i + 1, 3)

        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        main_layout.addStretch()

        # 4. Botón para descargar PDF
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.download_button = QPushButton("Descargar Certificado (PDF)")
        self.download_button.setMinimumSize(200, 40)
        # Estilo explícito para que se vea bien en ambos temas
        self.download_button.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; border-radius: 5px;")
        self.download_button.clicked.connect(self.download_pdf)
        button_layout.addWidget(self.download_button)
        main_layout.addLayout(button_layout)

    def create_styled_value_label(self, value_str, di, ds):
        """Crea un QLabel estilizado para un valor de la tabla."""
        label = QLabel(value_str)
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(30)
        
        base_style = "font-weight: bold; border-radius: 4px; padding: 5px;"
        color_style = "background-color: #777; color: white;" # Gris por defecto para no numéricos

        if di is not None and ds is not None:
            try:
                value = float(value_str)
                if di <= value <= ds:
                    color_style = "background-color: #28a745; color: white;" # Verde
                else:
                    color_style = "background-color: #dc3545; color: white;" # Rojo
            except (ValueError, TypeError):
                pass # Mantener estilo por defecto si no es un número
        
        label.setStyleSheet(base_style + color_style)
        return label

    def apply_theme(self):
        """Aplica el tema oscuro o claro a la ventana."""
        if self.theme == 'dark':
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)

    def download_pdf(self):
        """
        Prepara los datos y llama a la función de generación de PDF.
        """
        # Los datos del certificado son los que ya tenemos en self.calibration_data
        certificate_data = self.calibration_data

        # La tabla de valores necesita ser parseada desde el JSON
        try:
            table_values_json = self.calibration_data.get('tabla_calibracion', '[]')
            table_values = json.loads(table_values_json)
        except (json.JSONDecodeError, TypeError):
            table_values = [] # En caso de error, pasamos una tabla vacía

        # Llamamos a la función que genera el PDF, usando 'self' como padre para los diálogos
        generate_certificate_pdf(self, certificate_data, table_values)