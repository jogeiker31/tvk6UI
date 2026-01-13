"""
Módulo que define el QDialog para la gestión (CRUD) de modelos de medidores.
"""
import os
import shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QAbstractItemView,
                               QTableWidgetItem, QPushButton, QLineEdit, QFormLayout, QGroupBox,
                               QHeaderView, QMessageBox, QLabel, QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap, QIcon
from database import DatabaseManager, get_app_data_path

class ModelManagerDialog(QDialog):
    """
    Un diálogo para realizar operaciones CRUD en los modelos de medidores.
    """
    # Señal que se emitirá con los datos del modelo para iniciar la calibración
    start_calibration_requested = Signal(dict)

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_model_id = None
        self.current_image_path = None # Para guardar la ruta de la imagen seleccionada

        # Crear directorio para almacenar las imágenes de los modelos
        self.images_dir = get_app_data_path() / "model_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("Gestor de Modelos de Medidor")
        self.setMinimumSize(1024, 720)
        
        self.setup_ui()
        self.connect_signals()
        self.load_models()
        self.clear_form() # Rellenar formulario con valores por defecto al inicio

    def setup_ui(self):
        """Configura la interfaz de usuario del diálogo."""
        main_layout = QHBoxLayout(self)

        # Panel izquierdo: Tabla de modelos
        table_group = QGroupBox("Modelos Guardados")
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setIconSize(QSize(80, 60)) # Tamaño para las miniaturas
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre (Modelo)", "Constante (X)", "K", "di", "ds", "Ruta Imagen"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnHidden(0, True) # Ocultar columna ID
        self.table.setColumnHidden(6, True) # Ocultar columna de ruta de imagen

        # Ajustar el tamaño de las columnas para dar prioridad a Nombre y Constante
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Nombre (Modelo)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Constante (X)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # K
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # ds
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # di

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)

        # Panel derecho: Formulario y botones
        form_group = QGroupBox("Detalles del Modelo")
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.constante_input = QLineEdit()
        self.k_input = QLineEdit()
        self.ds_input = QLineEdit()
        self.di_input = QLineEdit()
        
        form_layout.addRow("Nombre:", self.name_input)
        form_layout.addRow("Constante (X):", self.constante_input)
        form_layout.addRow("K:", self.k_input)
        form_layout.addRow("di:", self.di_input)
        form_layout.addRow("ds:", self.ds_input)
        form_group.setLayout(form_layout)

        # Grupo para la imagen
        image_group = QGroupBox("Imagen del Medidor")
        image_layout = QVBoxLayout()
        self.image_preview_label = QLabel("No hay imagen seleccionada.")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumSize(200, 150)
        self.image_preview_label.setStyleSheet("border: 1px dashed #6c757d; border-radius: 5px;")
        self.select_image_button = QPushButton("Seleccionar Imagen...")

        image_layout.addWidget(self.image_preview_label)
        image_layout.addWidget(self.select_image_button)
        image_group.setLayout(image_layout)

        # Botones
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Añadir Nuevo")
        self.update_button = QPushButton("Actualizar")
        self.delete_button = QPushButton("Eliminar")
        self.clear_button = QPushButton("Limpiar")
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)

        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(form_group)
        right_panel_layout.addWidget(image_group)
        right_panel_layout.addLayout(button_layout)
        right_panel_layout.addStretch()

        # Panel de Calibración (inicialmente oculto)
        self.calibration_group = QGroupBox("Calibración Rápida")
        calibration_layout = QVBoxLayout()
        self.selected_model_label = QLabel("Selecciona un modelo para calibrar.")
        self.selected_model_label.setWordWrap(True)
        self.start_calibration_button = QPushButton("Iniciar Calibración")
        self.start_calibration_button.setMinimumHeight(40)
        self.start_calibration_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 10pt;")
        
        calibration_hint_label = QLabel("Iniciar calibración con este modelo")
        calibration_hint_label.setAlignment(Qt.AlignCenter)
        calibration_hint_label.setStyleSheet("font-size: 8pt; color: #6c757d;")
        
        calibration_layout.addWidget(self.selected_model_label)
        calibration_layout.addWidget(self.start_calibration_button)
        calibration_layout.addWidget(calibration_hint_label)
        self.calibration_group.setLayout(calibration_layout)
        self.calibration_group.setVisible(False) # Oculto por defecto

        right_panel_layout.addWidget(self.calibration_group)

        main_layout.addWidget(table_group, 3) # 3/4 del espacio
        main_layout.addLayout(right_panel_layout, 1) # 1/4 del espacio

    def connect_signals(self):
        """Conecta las señales de los widgets a los slots."""
        self.table.itemSelectionChanged.connect(self.on_model_selected)
        self.add_button.clicked.connect(self.add_model)
        self.update_button.clicked.connect(self.update_model)
        self.delete_button.clicked.connect(self.delete_model)
        self.clear_button.clicked.connect(self.clear_form)
        self.select_image_button.clicked.connect(self.select_image)
        self.start_calibration_button.clicked.connect(self.on_start_calibration)

    def load_models(self):
        """Carga o recarga los modelos desde la BD y los muestra en la tabla."""
        self.table.setRowCount(0)
        models = self.db.get_all_models()
        for row_num, model in enumerate(models):
            self.table.insertRow(row_num)
            self.table.setRowHeight(row_num, 65) # Altura de fila para la imagen

            # Celda para el nombre del modelo
            nombre_item = QTableWidgetItem(model['nombre'])

            # Cargar la imagen y establecerla como icono en la celda del nombre
            image_path = model['imagen_path']
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                nombre_item.setIcon(QIcon(pixmap))

            self.table.setItem(row_num, 0, QTableWidgetItem(str(model['id'])))
            self.table.setItem(row_num, 1, nombre_item)
            self.table.setItem(row_num, 2, QTableWidgetItem(str(model['constante'])))
            self.table.setItem(row_num, 3, QTableWidgetItem(str(model['k'])))
            self.table.setItem(row_num, 4, QTableWidgetItem(str(model['di'])))
            self.table.setItem(row_num, 5, QTableWidgetItem(str(model['ds'])))
            self.table.setItem(row_num, 6, QTableWidgetItem(model['imagen_path'] or ''))

    def on_model_selected(self):
        """Rellena el formulario cuando se selecciona un modelo en la tabla."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.clear_form()
            self.calibration_group.setVisible(False)
            return

        selected_row = selected_rows[0].row()
        self.current_model_id = int(self.table.item(selected_row, 0).text())
        
        self.name_input.setText(self.table.item(selected_row, 1).text())
        self.constante_input.setText(self.table.item(selected_row, 2).text())
        self.k_input.setText(self.table.item(selected_row, 3).text())
        self.di_input.setText(self.table.item(selected_row, 4).text())
        self.ds_input.setText(self.table.item(selected_row, 5).text())

        # Cargar y mostrar la imagen
        self.current_image_path = self.table.item(selected_row, 6).text()
        self.display_image(self.current_image_path)

        # Actualizar y mostrar el panel de calibración
        nombre = self.name_input.text()
        constante = self.constante_input.text()
        k = self.k_input.text()
        ds = self.ds_input.text()
        di = self.di_input.text()
        self.selected_model_label.setText(f"<b>Modelo:</b> {nombre}<br>"
                                          f"<b>X:</b> {constante}, <b>K:</b> {k}, <b>ds:</b> {ds}, <b>di:</b> {di}")
        self.calibration_group.setVisible(True)

    def clear_form(self):
        """Limpia los campos del formulario y la selección."""
        self.current_model_id = None
        self.name_input.clear()
        self.constante_input.clear()
        self.k_input.setText("1.0")
        self.di_input.setText("-0.2")
        self.ds_input.setText("0.5")
        self.current_image_path = None
        self.display_image(None)
        self.table.clearSelection()
        self.calibration_group.setVisible(False)

    @Slot()
    def select_image(self):
        """Abre un diálogo para seleccionar un archivo de imagen."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen de Medidor", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
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
            self.image_preview_label.setPixmap(QPixmap()) # Limpiar pixmap

    def get_form_data(self):
        """Recupera y valida los datos del formulario."""
        nombre = self.name_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Dato Requerido", "El nombre del modelo no puede estar vacío.")
            return None
        try:
            constante = float(self.constante_input.text())
            k = float(self.k_input.text())
            ds = float(self.ds_input.text())
            di = float(self.di_input.text())
            imagen_path = self.current_image_path
            return nombre, constante, k, ds, di, imagen_path
        except ValueError:
            QMessageBox.warning(self, "Error de Formato", "Los campos numéricos deben contener valores válidos.")
            return None

    def add_model(self):
        """Añade un nuevo modelo a la base de datos."""
        data = self.get_form_data()
        if data:
            try:
                self.db.add_model(*data)
                self.load_models()
                self.clear_form()
            except self.db.conn.IntegrityError:
                QMessageBox.warning(self, "Error", f"El modelo con nombre '{data[0]}' ya existe.")

    def update_model(self):
        """Actualiza el modelo seleccionado."""
        if self.current_model_id is None:
            QMessageBox.information(self, "Información", "Por favor, selecciona un modelo de la lista para actualizar.")
            return
        
        data = self.get_form_data()
        if data:
            self.db.update_model(self.current_model_id, *data)
            self.load_models()
            self.clear_form()

    def delete_model(self):
        """Elimina el modelo seleccionado."""
        if self.current_model_id is None:
            QMessageBox.information(self, "Información", "Por favor, selecciona un modelo de la lista para eliminar.")
            return

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Estás seguro de que quieres eliminar el modelo '{self.name_input.text()}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            image_to_delete = self.current_image_path

            self.db.delete_model(self.current_model_id)
            self.load_models()
            self.clear_form()

            # Eliminar el archivo de imagen asociado, si existe
            if image_to_delete and os.path.exists(image_to_delete):
                try:
                    os.remove(image_to_delete)
                except OSError as e:
                    QMessageBox.warning(self, "Error al eliminar imagen", f"No se pudo eliminar el archivo de imagen:\n{e}")

    def on_start_calibration(self):
        """
        Se activa al pulsar 'Iniciar Calibración'.
        Recopila los datos del modelo seleccionado y emite la señal.
        """
        if self.current_model_id is None:
            return
        
        model_data = self.get_form_data()
        if model_data:
            nombre, constante, k, ds, di, imagen_path = model_data
            # Primero cerramos el diálogo para que la ventana principal sea visible
            self.accept()
            # Luego emitimos la señal para que comience la secuencia (y el loader)
            self.start_calibration_requested.emit({'nombre': nombre, 'constante': constante, 'k': k, 'ds': ds, 'di': di, 'imagen_path': imagen_path})