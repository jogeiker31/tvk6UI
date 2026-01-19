"""
Módulo para la generación de certificados de calibración en PDF.
Requiere la librería 'reportlab'. Instalar con: pip install reportlab
"""
import os
import sys
import subprocess
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QStandardPaths

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # En desarrollo, subimos un nivel desde 'app' para llegar a la raíz del proyecto.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, "resources", relative_path)

def generate_certificate_pdf(parent, certificate_data, table_values, serials_data=None):
    """
    Genera un archivo PDF con los datos del certificado y la tabla de calibración.

    :param parent: El widget padre para mostrar diálogos.
    :param certificate_data: Un diccionario con los datos del formulario del certificado.
    :param table_values: Una lista de listas con los valores de la tabla de calibración.
    :param serials_data: Un diccionario opcional con los números de serie {puesto: serial}.
    """
    # 1. Definir la ruta de guardado por defecto en Documentos/certificados_calibracion
    docs_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
    save_dir = os.path.join(docs_path, "certificados_calibracion")
    os.makedirs(save_dir, exist_ok=True) # Crear la carpeta si no existe

    # 2. Construir el nombre de archivo por defecto
    fecha_str = certificate_data.get('fecha', '').replace('/', '-')
    # Limpiamos la hora para que sea un nombre de archivo válido (ej: 04:30 PM -> 0430PM)
    hora_str = certificate_data.get('hora', '').replace(':', '').replace(' ', '')
    modelo_str = certificate_data.get('modelo', 'Medidor')
    default_filename = f"Certificado_{modelo_str}_{fecha_str}_{hora_str}.pdf"
    default_path = os.path.join(save_dir, default_filename)

    # 3. Pedir al usuario dónde guardar el archivo, usando la ruta por defecto
    file_path, _ = QFileDialog.getSaveFileName(parent, "Guardar Certificado PDF", default_path, "PDF Files (*.pdf)")

    if not file_path:
        return # El usuario canceló

    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # --- Estilos personalizados ---
        title_style = ParagraphStyle(
            name='CustomTitle',
            parent=styles['h1'],
            fontSize=28,
            textColor=colors.HexColor('#00008B'), # Azul oscuro
            alignment=TA_CENTER,
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['h2'],
            alignment=TA_CENTER,
            spaceAfter=20
        )
        header_label_style = ParagraphStyle(
            name='HeaderLabel',
            parent=styles['Normal'],
            fontSize=9, # Tamaño de fuente más pequeño para las etiquetas de la cabecera
            leading=10 # Espaciado entre líneas
        )
        table_value_style = ParagraphStyle(
            name='TableValue',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12 # Tamaño más grande para los valores
        )

        # --- Títulos ---
        logo_path = resource_path('logo.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2*inch, height=0.5*inch) # Ajustar tamaño según sea necesario
            logo.hAlign = 'CENTER' # Centrar el logo
            story.append(logo)
        else:
            # Si no se encuentra el logo, se muestra el texto como antes
            story.append(Paragraph("TVK6", title_style))
        story.append(Paragraph("Calibración de Medidores", subtitle_style))
        story.append(Spacer(1, 0.1 * inch)) # Reducir espacio

        # --- Datos del Certificado ---
        data_header = [
            [Paragraph(f"<b>Fecha y Hora:</b><br/>{certificate_data['fecha']} {certificate_data['hora']}", header_label_style),
             Paragraph(f"<b>Calibrador:</b><br/>{certificate_data['calibrador'] or 'N/A'}", header_label_style),
             Paragraph(f"<b>Temperatura:</b><br/>{certificate_data.get('temperatura') or 'N/A'}", header_label_style)
            ],
            [Paragraph(f"<b>Modelo Medidor:</b><br/>{certificate_data['modelo']}", header_label_style), # Fila 2
             Paragraph(f"<b>Constante (X) [R/Kwh]:</b><br/>{certificate_data['constante']}", header_label_style),
             Paragraph(f"<b>Tensión (U1):</b><br/>{certificate_data['tension']}", header_label_style)
            ],
            [Paragraph(f"<b>Intensidad (I1):</b><br/>{certificate_data['intensidad']}", header_label_style), # Fila 3
             Paragraph(f"<b>Límite Inferior (di):</b><br/>{certificate_data.get('di', 'N/A')}", header_label_style),
             Paragraph(f"<b>Límite Superior (ds):</b><br/>{certificate_data.get('ds', 'N/A')}", header_label_style)
            ]
        ]
        header_table = Table(data_header, colWidths=[doc.width/3.0]*3)
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.1 * inch)) # Reducir espacio

        # --- Tabla de Calibración ---
        story.append(Paragraph("Resultados de la Calibración", styles['h3']))
        story.append(Spacer(1, 0.1 * inch)) # Reducir espacio
        
        if serials_data is None:
            serials_data = {}

        # Obtener di y ds para la evaluación de Pass/Fail
        try:
            di_val = float(certificate_data.get('di', 'N/A'))
            ds_val = float(certificate_data.get('ds', 'N/A'))
        except (ValueError, TypeError):
            di_val, ds_val = None, None

        # Crear la tabla de datos
        data_for_table = [
            [Paragraph("<b>Puesto / S/N</b>", styles['Normal']), Paragraph("<b>Valor</b>", styles['Normal']),
             Paragraph("<b>Puesto / S/N</b>", styles['Normal']), Paragraph("<b>Valor</b>", styles['Normal'])]
        ]
        
        flat_values = [item for sublist in table_values for item in sublist]
        num_items_per_col = (len(flat_values) + 1) // 2
        
        for i in range(num_items_per_col):
            # --- Columna 1 ---
            puesto1_num = str(i + 1)
            serial1 = serials_data.get(puesto1_num, '')
            # Ajuste de tamaño de fuente: Puesto más pequeño, S/N más grande y negrita
            puesto1_text = f"<font size='8'>{puesto1_num}</font>" + (f" <b><font size='10'>S/N: {serial1}</font></b>" if serial1 else "")
            val1 = flat_values[i] if i < len(flat_values) else ''
            
            val1_display = val1
            if val1 and val1 != '---' and di_val is not None and ds_val is not None:
                try:
                    value = float(val1)
                    if di_val <= value <= ds_val:
                        val1_display = f"{val1} ✓" # Pasa
                    else:
                        val1_display = f"{val1} ✗" # Falla
                except ValueError:
                    pass # No es un número, no se evalúa

            # --- Columna 2 ---
            idx2 = i + num_items_per_col
            puesto2_num = str(idx2 + 1)
            serial2 = serials_data.get(puesto2_num, '')
            # Ajuste de tamaño de fuente: Puesto más pequeño, S/N más grande y negrita
            puesto2_text = f"<font size='8'>{puesto2_num}</font>" + (f" <b><font size='10'>S/N: {serial2}</font></b>" if serial2 else "")
            val2 = flat_values[idx2] if idx2 < len(flat_values) else ''
            
            val2_display = val2
            if val2 and val2 != '---' and di_val is not None and ds_val is not None:
                try:
                    value = float(val2)
                    if di_val <= value <= ds_val:
                        val2_display = f"{val2} ✓" # Pasa
                    else:
                        val2_display = f"{val2} ✗" # Falla
                except ValueError:
                    pass # No es un número, no se evalúa

            row = [
                Paragraph(puesto1_text, styles['Normal']), # Puesto y Serial
                Paragraph(val1_display, table_value_style), # Valor y Pass/Fail
                Paragraph(puesto2_text if val2 else '', styles['Normal']),
                Paragraph(val2_display, table_value_style)
            ]
            data_for_table.append(row)

        calib_table = Table(data_for_table, colWidths=[doc.width/4.0]*4)
        calib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#555555')), # Fondo oscuro para cabecera
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), # Texto blanco para cabecera
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')) # Líneas más finas y grises
        ]))
        story.append(calib_table)
        story.append(Spacer(1, 0.25 * inch))
        # --- Leyenda ---
        story.append(Paragraph("<b>Leyenda:</b>", styles['h4']))
        story.append(Paragraph("✓: El valor del medidor está dentro de los límites (di/ds).", header_label_style))
        story.append(Paragraph("✗: El valor del medidor está fuera de los límites (di/ds).", header_label_style))
        story.append(Spacer(1, 0.5 * inch)) # Reducir espacio para que la firma quepa en la misma página

        # --- Línea de Firma ---
        story.append(Paragraph("________________________________________", styles['Normal']))
        story.append(Paragraph("Firma del Encargado", styles['Normal']))

        doc.build(story)

        # --- Abrir el PDF automáticamente ---
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.run([opener, file_path], check=True)
        except Exception as open_error:
            print(f"No se pudo abrir el PDF automáticamente: {open_error}")

        QMessageBox.information(parent, "Éxito", f"Certificado generado y abierto:\n{file_path}")

    except Exception as e:
        QMessageBox.critical(parent, "Error", f"No se pudo generar el PDF: {e}")