"""
Módulo que contiene las hojas de estilo (QSS) para los temas de la aplicación.
"""

DARK_THEME = """
QWidget, QDialog {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-family: Segoe UI;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
}

QLabel#etiquetaEstado {
    font-weight: bold;
    padding: 8px;
    border-radius: 5px;
    background-color: #555555;
    color: white;
}

QPlainTextEdit#monitorSalida {
    background-color: #1e1e1e;
    color: #00ff00;
    border: 1px solid #333;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 9pt;
    padding: 5px;
    border-radius: 3px;
}

QLineEdit, QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 5px;
}

QPushButton {
    background-color: #555;
    color: white;
    border: 1px solid #666;
    border-radius: 5px;
    padding: 8px;
}

QPushButton:hover {
    background-color: #666;
}

QPushButton:pressed {
    background-color: #444;
}

/* Estilos específicos de botones */
QPushButton#btnGestionarModelos { background-color: #28a745; }
QPushButton#btnConfiguracion { background-color: #6c757d; }
QPushButton#btn_reset { background-color: #ffc107; color: black; }
QPushButton#btnRetornar { background-color: #28a745; }
QPushButton#btnLimpiarMonitor { background-color: #007bff; }

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
"""

LIGHT_THEME = """
QWidget, QDialog {
    background-color: #f0f0f0;
    color: #000000;
    font-family: Segoe UI;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    margin-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
}

QPlainTextEdit#monitorSalida {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 9pt;
}

QLineEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 5px;
}
"""