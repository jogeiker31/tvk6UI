import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox, QAbstractItemView
)
from PySide6.QtCore import Qt

# Importamos el nuevo diálogo de detalles
from history_detail_dialog import HistoryDetailDialog
# Importamos los temas
from themes import DARK_THEME, LIGHT_THEME

class HistoryView(QDialog):
    """
    Ventana para mostrar y filtrar el historial de calibraciones.
    """
    def __init__(self, db_manager, theme='dark', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.theme = theme
        self.setWindowTitle("Historial de Calibraciones")
        self.setMinimumSize(1000, 600)

        self.setup_ui()
        self.load_history()
        self.apply_theme()

    def setup_ui(self):
        """Configura la interfaz de usuario de la ventana."""
        layout = QVBoxLayout(self)

        # Título
        title_label = QLabel("Historial de Calibraciones")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Grupo de filtros
        filter_group = QGroupBox("Filtros de Búsqueda")
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Fecha (YYYY-MM-DD):"))
        self.fecha_filter = QLineEdit()
        self.fecha_filter.setPlaceholderText("Ej: 2025-12-19")
        filter_layout.addWidget(self.fecha_filter)

        filter_layout.addWidget(QLabel("Calibrador:"))
        self.calibrador_filter = QLineEdit()
        self.calibrador_filter.setPlaceholderText("Buscar por nombre...")
        filter_layout.addWidget(self.calibrador_filter)

        filter_layout.addWidget(QLabel("Modelo:"))
        self.modelo_filter = QLineEdit()
        self.modelo_filter.setPlaceholderText("Buscar por modelo...")
        filter_layout.addWidget(self.modelo_filter)

        filter_layout.addStretch()

        self.filter_button = QPushButton("Buscar")
        self.filter_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.filter_button)

        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_button)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla de resultados
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha", "Hora", "Calibrador", "Modelo", "Constante (X)", "Tensión (U1)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection) # Seleccionar solo una fila a la vez
        self.table.setSortingEnabled(False)

        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addWidget(self.table)

        # Botón para ver detalles
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.details_button = QPushButton("Ver Detalles")
        self.details_button.setMinimumSize(150, 40)
        self.details_button.setEnabled(False) # Deshabilitado por defecto
        self.details_button.clicked.connect(self.open_detail_view)
        button_layout.addWidget(self.details_button)
        layout.addLayout(button_layout)

    def load_history(self, fecha=None, calibrador=None, modelo=None):
        """Carga los datos del historial en la tabla, aplicando filtros si se proporcionan."""
        try:
            history_data = self.db_manager.get_all_calibration_data(fecha=fecha, calibrador=calibrador, modelo=modelo)
            self.table.setRowCount(len(history_data))

            for row_idx, record in enumerate(history_data):
                id_item = QTableWidgetItem(str(record['id']))
                id_item.setData(Qt.UserRole, record)
                
                self.table.setItem(row_idx, 0, id_item)
                self.table.setItem(row_idx, 1, QTableWidgetItem(record['fecha']))
                self.table.setItem(row_idx, 2, QTableWidgetItem(record['hora']))
                self.table.setItem(row_idx, 3, QTableWidgetItem(record['calibrador']))
                self.table.setItem(row_idx, 4, QTableWidgetItem(record['modelo']))
                self.table.setItem(row_idx, 5, QTableWidgetItem(str(record['constante'])))
                self.table.setItem(row_idx, 6, QTableWidgetItem(str(record['tension'])))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el historial: {e}")

    def apply_filters(self):
        """Aplica los filtros introducidos por el usuario y recarga la tabla."""
        fecha = self.fecha_filter.text().strip() or None
        calibrador = self.calibrador_filter.text().strip() or None
        modelo = self.modelo_filter.text().strip() or None
        self.load_history(fecha=fecha, calibrador=calibrador, modelo=modelo)

    def clear_filters(self):
        """Limpia los campos de filtro y recarga la tabla completa."""
        self.fecha_filter.clear()
        self.calibrador_filter.clear()
        self.modelo_filter.clear()
        self.load_history()

    def on_selection_changed(self):
        """Habilita o deshabilita el botón de detalles basado en la selección."""
        self.details_button.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def open_detail_view(self):
        """Abre la ventana de detalles para el registro seleccionado."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        selected_item = self.table.item(selected_rows[0].row(), 0)
        if not selected_item: return
        
        full_data = selected_item.data(Qt.UserRole)
        if not full_data: return

        detail_dialog = HistoryDetailDialog(full_data, theme=self.theme, parent=self)
        detail_dialog.exec()

    def apply_theme(self):
        """Aplica el tema oscuro o claro a la ventana."""
        if self.theme == 'dark':
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)