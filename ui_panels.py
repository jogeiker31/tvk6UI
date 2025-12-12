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
        self.valorI1 = parent_ui.findChild(QLabel, 'valorI1')
        self.valorDi = parent_ui.findChild(QLabel, 'valorDi')
        self.valorDs = parent_ui.findChild(QLabel, 'valorDs')

    def update_display(self, parsed_values):
        """
        Actualiza los QLabels con los nuevos valores del diccionario.

        :param parsed_values: Un diccionario donde las claves son 'X', 'K', 'U1'
                              y los valores son los datos a mostrar.
        """
        # Usamos f-strings para formatear la salida, lo que puede ser útil
        # si en el futuro necesitas añadir unidades o limitar decimales.
        # Por ejemplo: f"{parsed_values.get('X', '---'):.2f}" para 2 decimales.
        valor_x = parsed_values.get('X', '---')
        valor_k = parsed_values.get('K', '---')
        valor_u1 = parsed_values.get('U1', '---')
        valor_i1 = parsed_values.get('I1', '---')
        valor_di = parsed_values.get('di', '---')
        valor_ds = parsed_values.get('ds', '---')

        self.valorX.setText(f"{valor_x}")
        self.valorK.setText(f"{valor_k}")
        self.valorU1.setText(f"{valor_u1}")
        self.valorI1.setText(f"{valor_i1}")
        self.valorDi.setText(f"{valor_di}")
        self.valorDs.setText(f"{valor_ds}")