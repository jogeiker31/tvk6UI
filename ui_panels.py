"""
Módulo para gestionar paneles o componentes específicos de la UI.

Cada clase en este módulo encapsula la lógica de una parte de la interfaz,
haciendo que MainWindow sea más limpio y actúe como un orquestador.
"""
from PySide6.QtWidgets import QLabel

class MeasurementPanel:
    """
    Gestiona la lógica y los widgets del panel 'Valores de Medición'.
    """
    def __init__(self, parent_ui):
        """
        Busca y almacena las referencias a los widgets de este panel.
        
        :param parent_ui: La referencia al widget de la UI cargado (self.ui en MainWindow).
        """
        self.valorX = parent_ui.findChild(QLabel, 'valorX')
        self.valorK = parent_ui.findChild(QLabel, 'valorK')
        self.valorU1 = parent_ui.findChild(QLabel, 'valorU1')

    def update_display(self, parsed_values):
        """
        Actualiza los QLabels con los nuevos valores del diccionario.
        """
        self.valorX.setText(str(parsed_values.get('X', '---')))
        self.valorK.setText(str(parsed_values.get('K', '---')))
        self.valorU1.setText(str(parsed_values.get('U1', '---')))