from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QWidget, QAbstractItemView, QSizePolicy
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt
from database import DatabaseManager
from pathlib import Path

class HistoryDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        # Load the .ui file using QUiLoader
        loader = QUiLoader()
        ui_file_path = Path(__file__).resolve().parent / "historial_dialog.ui"
        self.setMinimumSize(800, 600)

        self.ui = loader.load(str(ui_file_path), self)


        self.tabla_historial = self.findChild(QTableWidget, 'tablaHistorial')
        self.tabla_historial.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.db_manager = db_manager
        self.cargar_datos()

    def cargar_datos(self):
        """Loads the calibration history data from the database."""

        datos = self.db_manager.get_all_calibration_data()

        # Configure the table
        self.tabla_historial.setColumnCount(10)  # Adjust based on the number of columns in your table
        self.tabla_historial.setHorizontalHeaderLabels(["ID", "Fecha", "Hora", "Calibrador", "Constante", "Modelo", "Tension", "Intensidad", "Di", "Ds"])
        self.tabla_historial.setRowCount(len(datos))

        # Insert the data into the table

        for row_num, row_data in enumerate(datos):
            self.tabla_historial.setItem(row_num, 0, QTableWidgetItem(str(row_data['id'])))
            self.tabla_historial.setItem(row_num, 1, QTableWidgetItem(row_data['fecha']))
            self.tabla_historial.setItem(row_num, 2, QTableWidgetItem(row_data['hora']))
            self.tabla_historial.setItem(row_num, 3, QTableWidgetItem(row_data['calibrador']))
            self.tabla_historial.setItem(row_num, 4, QTableWidgetItem(row_data['constante']))
            self.tabla_historial.setItem(row_num, 5, QTableWidgetItem(row_data['modelo']))
            self.tabla_historial.setItem(row_num, 6, QTableWidgetItem(row_data['tension']))
            self.tabla_historial.setItem(row_num, 7, QTableWidgetItem(row_data['intensidad']))
            self.tabla_historial.setItem(row_num, 8, QTableWidgetItem(row_data['di']))
            self.tabla_historial.setItem(row_num, 9, QTableWidgetItem(row_data['ds']))

        self.setWindowTitle("Calibration History")

    def closeEvent(self, event):
        """Override closeEvent to ensure proper database closure."""
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    # Replace with your actual database initialization
    db_manager = DatabaseManager()
    dialog = HistoryDialog(db_manager)
    dialog.show()
    sys.exit(app.exec())