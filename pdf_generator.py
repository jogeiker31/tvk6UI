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

def generate_certificate_pdf(parent, certificate_data, table_values):
    """
    Genera un archivo PDF con los datos del certificado y la tabla de calibración.

    :param parent: El widget padre para mostrar diálogos.
    :param certificate_data: Un diccionario con los datos del formulario del certificado.
    :param table_values: Una lista de listas con los valores de la tabla de calibración.
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
        table_value_style = ParagraphStyle(
            name='TableValue',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12 # Tamaño más grande para los valores
        )

        # --- Títulos ---
        logo_path = 'logo.png'
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=3*inch, height=0.75*inch) # Ajustar tamaño según sea necesario
            logo.hAlign = 'CENTER'
            story.append(logo)
        else:
            # Si no se encuentra el logo, se muestra el texto como antes
            story.append(Paragraph("TVK6", title_style))
        story.append(Paragraph("Calibración de Medidores", subtitle_style))
        story.append(Spacer(1, 0.25 * inch))

        # --- Datos del Certificado ---
        data_header = [
            [Paragraph(f"<b>Fecha:</b><br/>{certificate_data['fecha']}", styles['Normal']),
             Paragraph(f"<b>Hora:</b><br/>{certificate_data['hora']}", styles['Normal']),
             Paragraph(f"<b>Calibrador:</b><br/>{certificate_data['calibrador'] or 'N/A'}", styles['Normal'])],
            [Paragraph(f"<b>Tensión (U1):</b><br/>{certificate_data['tension']}", styles['Normal']),
             Paragraph(f"<b>Intensidad (I1):</b><br/>{certificate_data['intensidad']}", styles['Normal']),
             Paragraph(f"<b>Temperatura:</b><br/>{certificate_data.get('temperatura') or 'N/A'}", styles['Normal'])],
            [Paragraph(f"<b>Modelo Medidor:</b><br/>{certificate_data['modelo']}", styles['Normal']),
             Paragraph(f"<b>Constante (X):</b><br/>{certificate_data['constante']}", styles['Normal']),
             ''] # Celda vacía para la tercera columna
        ]
        header_table = Table(data_header, colWidths=[2.16*inch, 2.16*inch, 2.16*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('SPAN', (2, 2), (2, 2)) # Unir la celda vacía (no es estrictamente necesario pero es buena práctica)
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.25 * inch))

        # --- Tabla de Calibración ---
        story.append(Paragraph("Resultados de la Calibración", styles['h3']))

        # Crear la tabla de datos
        data_for_table = [
            [Paragraph("<b>Medición</b>", styles['Normal']), Paragraph("<b>Valor</b>", styles['Normal']),
             Paragraph("<b>Medición</b>", styles['Normal']), Paragraph("<b>Valor</b>", styles['Normal'])]
        ]
        
        flat_values = [item for sublist in table_values for item in sublist]
        num_items_per_col = (len(flat_values) + 1) // 2
        
        for i in range(num_items_per_col):
            val1 = flat_values[i] if i < len(flat_values) else ''
            
            idx2 = i + num_items_per_col
            val2 = flat_values[idx2] if idx2 < len(flat_values) else ''
            
            row = [
                Paragraph(str(i + 1), styles['Normal']),
                Paragraph(val1, table_value_style),
                Paragraph(str(idx2 + 1) if val2 else '', styles['Normal']),
                Paragraph(val2, table_value_style)
            ]
            data_for_table.append(row)

        calib_table = Table(data_for_table, colWidths=[doc.width/4.0]*4)
        calib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(calib_table)
        story.append(Spacer(1, 1 * inch))

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