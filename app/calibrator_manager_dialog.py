"""
Módulo que define el QDialog para la gestión (CRUD) de calibradores.
"""
import os
import shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QAbstractItemView,
                               QTableWidgetItem, QPushButton, QLineEdit, QFormLayout, QGroupBox,
                               QHeaderView, QMessageBox, QLabel, QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap, QIcon
from .database import DatabaseManager, get_app_data_path

class CalibratorManagerDialog(QDialog):
    """
    Un diálogo para realizar operaciones CRUD en los calibradores.
    """
    # Señal que se emitirá con los datos del calibrador seleccionado
    calibrator_selected = Signal(dict)

    def __init__(self, db_manager: DatabaseManager, parent=None, initial_selection_mode=False):
        super().__init__(parent)
        self.db = db_manager
        self.current_calibrator_id = None
        self.current_image_path = None # Para guardar la ruta de la imagen seleccionada
        self.initial_selection_mode = initial_selection_mode

        if self.initial_selection_mode:
            self.setWindowTitle("Seleccione un Calibrador para Iniciar")
            self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        else:
            self.setWindowTitle("Gestor de Calibradores")

        # Crear directorio para almacenar las imágenes de los calibradores
        self.images_dir = get_app_data_path() / "calibrator_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.setMinimumSize(1024, 720)
        
        self.setup_ui()
        self.connect_signals()
        self.load_calibrators()
        self.clear_form()

    def setup_ui(self):
        """Configura la interfaz de usuario del diálogo."""
        main_layout = QHBoxLayout(self)

        # Panel izquierdo: Tabla de calibradores
        table_group = QGroupBox("Calibradores Guardados")
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setIconSize(QSize(80, 60))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Identificador", "Ruta Imagen"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(3, True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)

        # Panel derecho: Formulario y botones
        form_group = QGroupBox("Detalles del Calibrador")
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.id_input = QLineEdit()
        
        form_layout.addRow("Nombre:", self.name_input)
        form_layout.addRow("Identificador (Cédula/Código):", self.id_input)
        form_group.setLayout(form_layout)

        # Grupo para la imagen
        image_group = QGroupBox("Imagen del Calibrador")
        image_layout = QVBoxLayout()
        self.image_preview_label = QLabel("No hay imagen seleccionada.")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumSize(200, 150)
        self.image_preview_label.setStyleSheet("border: 1px dashed #6c757d; border-radius: 5px;")
        self.select_image_button = QPushButton("Seleccionar Imagen...")

        image_layout.addWidget(self.image_preview_label)
        image_layout.addWidget(self.select_image_button)
        image_group.setLayout(image_layout)

        # Botones CRUD
        crud_button_layout = QHBoxLayout()
        self.add_button = QPushButton("Añadir Nuevo")
        self.update_button = QPushButton("Actualizar")
        self.delete_button = QPushButton("Eliminar")
        self.clear_button = QPushButton("Limpiar")
        
        crud_button_layout.addWidget(self.add_button)
        crud_button_layout.addWidget(self.update_button)
        crud_button_layout.addWidget(self.delete_button)
        crud_button_layout.addWidget(self.clear_button)

        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(form_group)
        right_panel_layout.addWidget(image_group)
        right_panel_layout.addLayout(crud_button_layout)
        right_panel_layout.addStretch()

        # Panel de Selección
        self.selection_group = QGroupBox("Seleccionar Calibrador")
        selection_layout = QVBoxLayout()
        self.selected_calibrator_label = QLabel("Selecciona un calibrador de la lista.")
        self.selected_calibrator_label.setWordWrap(True)
        self.select_calibrator_button = QPushButton("Seleccionar este Calibrador")
        self.select_calibrator_button.setMinimumHeight(40)
        self.select_calibrator_button.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; font-size: 10pt;")
        
        selection_layout.addWidget(self.selected_calibrator_label)
        selection_layout.addWidget(self.select_calibrator_button)
        self.selection_group.setLayout(selection_layout)
        self.selection_group.setVisible(False)

        right_panel_layout.addWidget(self.selection_group)

        main_layout.addWidget(table_group, 3)
        main_layout.addLayout(right_panel_layout, 1)

    def connect_signals(self):
        """Conecta las señales de los widgets a los slots."""
        self.table.itemSelectionChanged.connect(self.on_calibrator_selected_in_table)
        self.add_button.clicked.connect(self.add_calibrator)
        self.update_button.clicked.connect(self.update_calibrator)
        self.delete_button.clicked.connect(self.delete_calibrator)
        self.clear_button.clicked.connect(self.clear_form)
        self.select_image_button.clicked.connect(self.select_image)
        self.select_calibrator_button.clicked.connect(self.on_select_calibrator)

    def load_calibrators(self):
        """Carga o recarga los calibradores desde la BD y los muestra en la tabla."""
        self.table.setRowCount(0)
        calibrators = self.db.get_all_calibrators()
        for row_num, calibrator in enumerate(calibrators):
            self.table.insertRow(row_num)
            self.table.setRowHeight(row_num, 65)

            nombre_item = QTableWidgetItem(calibrator['nombre'])
            image_path = calibrator['imagen_path']
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                nombre_item.setIcon(QIcon(pixmap))

            self.table.setItem(row_num, 0, QTableWidgetItem(str(calibrator['id'])))
            self.table.setItem(row_num, 1, nombre_item)
            self.table.setItem(row_num, 2, QTableWidgetItem(calibrator['identificador']))
            self.table.setItem(row_num, 3, QTableWidgetItem(calibrator['imagen_path'] or ''))

    def on_calibrator_selected_in_table(self):
        """Rellena el formulario cuando se selecciona un calibrador en la tabla."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.clear_form()
            self.selection_group.setVisible(False)
            return

        selected_row = selected_rows[0].row()
        self.current_calibrator_id = int(self.table.item(selected_row, 0).text())
        
        self.name_input.setText(self.table.item(selected_row, 1).text())
        self.id_input.setText(self.table.item(selected_row, 2).text())

        self.current_image_path = self.table.item(selected_row, 3).text()
        self.display_image(self.current_image_path)

        nombre = self.name_input.text()
        identificador = self.id_input.text()
        self.selected_calibrator_label.setText(f"<b>Nombre:</b> {nombre}<br>"
                                               f"<b>ID:</b> {identificador}")
        self.selection_group.setVisible(True)

    def clear_form(self):
        """Limpia los campos del formulario y la selección."""
        self.current_calibrator_id = None
        self.name_input.clear()
        self.id_input.clear()
        self.current_image_path = None
        self.display_image(None)
        self.table.clearSelection()
        self.selection_group.setVisible(False)

    @Slot()
    def select_image(self):
        """Abre un diálogo para seleccionar un archivo de imagen."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen de Calibrador", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            try:
                file_name = os.path.basename(file_path)
                new_path = self.images_dir / file_name
                shutil.copy(file_path, new_path)
                self.current_image_path = str(new_path)
                self.display_image(self.current_image_path)
            except Exception as e:
                QMessageBox.warning(self, "Error al Copiar Imagen", f"No se pudo guardar la imagen: {e}")

    def display_image(self, image_path):
        """Muestra la imagen en el QLabel de previsualización."""
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.image_preview_label.setPixmap(pixmap.scaled(
                self.image_preview_label.width(), self.image_preview_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            self.image_preview_label.setText("No hay imagen\nseleccionada.")
            self.image_preview_label.setPixmap(QPixmap())

    def get_form_data(self):
        """Recupera y valida los datos del formulario."""
        nombre = self.name_input.text().strip()
        identificador = self.id_input.text().strip()
        if not nombre or not identificador:
            QMessageBox.warning(self, "Datos Requeridos", "El nombre y el identificador no pueden estar vacíos.")
            return None
        
        imagen_path = self.current_image_path
        return nombre, identificador, imagen_path

    def add_calibrator(self):
        """Añade un nuevo calibrador a la base de datos."""
        data = self.get_form_data()
        if data:
            try:
                self.db.add_calibrator(*data)
                self.load_calibrators()
                self.clear_form()
            except self.db.conn.IntegrityError:
                QMessageBox.warning(self, "Error", f"El calibrador con identificador '{data[1]}' ya existe.")

    def update_calibrator(self):
        """Actualiza el calibrador seleccionado."""
        if self.current_calibrator_id is None:
            QMessageBox.information(self, "Información", "Por favor, selecciona un calibrador de la lista para actualizar.")
            return
        
        data = self.get_form_data()
        if data:
            self.db.update_calibrator(self.current_calibrator_id, *data)
            self.load_calibrators()
            self.clear_form()

    def delete_calibrator(self):
        """Elimina el calibrador seleccionado."""
        if self.current_calibrator_id is None:
            QMessageBox.information(self, "Información", "Por favor, selecciona un calibrador de la lista para eliminar.")
            return

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Estás seguro de que quieres eliminar al calibrador '{self.name_input.text()}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            image_to_delete = self.current_image_path
            self.db.delete_calibrator(self.current_calibrator_id)
            self.load_calibrators()
            self.clear_form()

            if image_to_delete and os.path.exists(image_to_delete):
                try:
                    os.remove(image_to_delete)
                except OSError as e:
                    QMessageBox.warning(self, "Error al eliminar imagen", f"No se pudo eliminar el archivo de imagen:\n{e}")

    def on_select_calibrator(self):
        """
        Se activa al pulsar 'Seleccionar este Calibrador'.
        Recopila los datos del calibrador seleccionado y emite la señal.
        """
        if self.current_calibrator_id is None:
            return
        
        form_data = self.get_form_data()
        if form_data:
            nombre, identificador, imagen_path = form_data
            self.calibrator_selected.emit({
                'id': self.current_calibrator_id,
                'nombre': nombre,
                'identificador': identificador,
                'imagen_path': imagen_path
            })
            self.accept() # Cierra el diálogo

    def keyPressEvent(self, event):
        """Sobrescribe para bloquear la tecla Escape en el modo de selección inicial."""
        if self.initial_selection_mode and event.key() == Qt.Key_Escape:
            QMessageBox.warning(self, "Selección Requerida", "Debe seleccionar o crear un calibrador para continuar.")
            event.ignore()
        else:
            super().keyPressEvent(event)