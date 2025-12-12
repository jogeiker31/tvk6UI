"""
Módulo para la vista gráfica personalizada de la tabla de calibración.
"""
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class CalibrationTableView(QWidget):
    """
    Widget que muestra una tabla gráfica de los valores de calibración.
    """
    def __init__(self, rows=2, cols=10, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.cells = []

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(5)
        self.setLayout(self.grid_layout)

        self._create_table()

    def _create_table(self):
        """Crea la rejilla de QLabels que formarán la tabla."""
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                cell = QLabel("---")
                cell.setFrameShape(QFrame.StyledPanel)
                cell.setFrameShadow(QFrame.Sunken)
                cell.setMinimumSize(60, 40)
                cell.setAlignment(Qt.AlignCenter)
                cell.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        font-size: 11pt;
                        border: 1px solid #555;
                        border-radius: 4px;
                        background-color: #333;
                        color: white;
                    }
                """)
                self.grid_layout.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)

    def update_values(self, screen_text, di, ds):
        # Resetear todas las celdas a su estado inicial
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].setText("---")
                self.cells[r][c].setStyleSheet("""
                    QLabel {
                        font-weight: bold; font-size: 11pt; border: 1px solid #555;
                        border-radius: 4px; background-color: #333; color: white;
                    }
                """)

        # Mapeo de la rejilla (fila, columna) a las coordenadas de la pantalla emulada (fila, columna_inicio)
        # Las coordenadas de la pantalla son 0-indexed.
        # Fila 11 -> 10, Fila 13 -> 12, etc. Columna 4 -> 3, Columna 11 -> 10, etc.
        coord_map = {
            (0, 0): (10, 3), (0, 1): (10, 10), (0, 2): (10, 17), (0, 3): (10, 24), (0, 4): (10, 31),
            (0, 5): (12, 3), (0, 6): (12, 10), (0, 7): (12, 17), (0, 8): (12, 24), (0, 9): (12, 31),
            (1, 0): (16, 3), (1, 1): (16, 10), (1, 2): (16, 17), (1, 3): (16, 24), (1, 4): (16, 31),
            (1, 5): (18, 3), (1, 6): (18, 10), (1, 7): (18, 17), (1, 8): (18, 24), (1, 9): (18, 31),
        }

        screen_lines = screen_text.split('\n')

        try:
            di_val = float(di)
            ds_val = float(ds)
        except (ValueError, TypeError):
            di_val, ds_val = None, None

        for grid_pos, screen_coord in coord_map.items():
            grid_row, grid_col = grid_pos
            screen_row, screen_col_start = screen_coord

            if screen_row < len(screen_lines):
                line = screen_lines[screen_row]
                # Extraer el valor de la posición. Asumimos una longitud máxima de 7 caracteres.
                value_str = line[screen_col_start:screen_col_start + 7].strip()

                if not value_str or value_str == "---":
                    continue

                self.cells[grid_row][grid_col].setText(value_str)

                if di_val is not None and ds_val is not None:
                    try:
                        value = float(value_str)
                        if di_val <= value <= ds_val:
                            self.cells[grid_row][grid_col].setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 11pt; border-radius: 4px;")
                        else:
                            self.cells[grid_row][grid_col].setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; font-size: 11pt; border-radius: 4px;")
                    except ValueError:
                        pass