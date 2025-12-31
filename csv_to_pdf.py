import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
import os


def calcular_tamaño_fuente(num_columnas, num_filas, ancho_disponible):
    """
    Calcula el tamaño de fuente óptimo basándose en el número de columnas.
    """
    if num_columnas <= 4:
        return 10
    elif num_columnas <= 6:
        return 8
    else:
        return 7


def csv_to_pdf(csv_file, pdf_file=None, orientacion='landscape'):
    """
    Convierte un archivo CSV a PDF.
    
    Args:
        csv_file: Ruta del archivo CSV de entrada
        pdf_file: Ruta del archivo PDF de salida (opcional, se genera automáticamente si no se especifica)
        orientacion: 'landscape' (horizontal) o 'portrait' (vertical)
    """
    if not os.path.exists(csv_file):
        print(f"Error: No se encuentra el archivo '{csv_file}'")
        return
    
    if pdf_file is None:
        pdf_file = csv_file.replace('.csv', '.pdf')
    
    # Leer el CSV
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        datos = list(reader)
    
    if not datos:
        print(f"Error: El archivo '{csv_file}' está vacío")
        return
    
    # Configurar el tamaño de página
    pagesize = landscape(A4) if orientacion == 'landscape' else A4
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=pagesize,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )
    
    # Dimensiones disponibles
    ancho_disponible = pagesize[0] - 20*mm
    alto_disponible = pagesize[1] - 20*mm
    
    num_columnas = len(datos[0]) if datos else 0
    num_filas = len(datos)
    
    # Calcular tamaño de fuente
    font_size = calcular_tamaño_fuente(num_columnas, num_filas, ancho_disponible)
    
    # Calcular anchos de columna proporcionales
    ancho_columna = ancho_disponible / num_columnas if num_columnas > 0 else 50*mm
    col_widths = [ancho_columna] * num_columnas
    
    # Crear la tabla
    tabla = Table(datos, colWidths=col_widths, repeatRows=1)
    
    # Estilo de la tabla
    estilo = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), font_size),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), font_size),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
        
        # Padding para que el texto respire
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        
        # Word wrap automático
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ])
    
    # Aplicar estilo especial a filas de TOTAL o RESUMEN
    for i, fila in enumerate(datos):
        if any('TOTAL' in str(celda).upper() or 'RESUMEN' in str(celda).upper() for celda in fila):
            estilo.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFE699'))
            estilo.add('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')
    
    tabla.setStyle(estilo)
    
    # Construir el PDF
    elementos = [tabla]
    
    try:
        doc.build(elementos)
        print(f"✓ PDF generado exitosamente: {pdf_file}")
        print(f"  - {num_filas} filas, {num_columnas} columnas")
        print(f"  - Tamaño de fuente: {font_size}")
    except Exception as e:
        print(f"Error al generar el PDF: {e}")


def combinar_csv_en_pdf(csv_files, pdf_output, titulo_pdf="Gastos Combinados"):
    """
    Combina múltiples archivos CSV en un solo PDF.
    
    Args:
        csv_files: Lista de rutas de archivos CSV a combinar
        pdf_output: Nombre del archivo PDF de salida
        titulo_pdf: Título para el PDF combinado
    """
    from datetime import datetime
    
    datos_combinados = []
    
    # Leer todos los CSV
    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            print(f"Advertencia: No se encuentra '{csv_file}', se omitirá.")
            continue
        
        print(f"Leyendo: {csv_file}")
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            datos = list(reader)
            
            if not datos:
                continue
            
            # Añadir encabezado solo la primera vez
            if not datos_combinados:
                datos_combinados.append(datos[0])
            
            # Añadir datos (sin encabezado, sin filas vacías, sin resúmenes)
            for fila in datos[1:]:
                # Filtrar filas vacías o de resumen
                if fila and any(fila) and 'RESUMEN' not in str(fila).upper() and 'TOTAL' not in fila[0]:
                    datos_combinados.append(fila)
    
    if len(datos_combinados) <= 1:
        print("No hay datos suficientes para combinar.")
        return
    
    # Ordenar por fecha (asumiendo que la fecha está en la primera columna)
    encabezado = datos_combinados[0]
    filas_datos = datos_combinados[1:]
    
    def parse_fecha(fila):
        try:
            fecha_str = fila[0]
            if '/' in fecha_str:
                return datetime.strptime(fecha_str, "%d/%m/%Y")
            elif '-' in fecha_str:
                return datetime.strptime(fecha_str, "%d-%m-%Y")
        except:
            pass
        return datetime.min
    
    filas_datos.sort(key=parse_fecha, reverse=True)
    
    # Reconstruir datos ordenados
    datos_ordenados = [encabezado] + filas_datos
    
    # Configurar el PDF
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(
        pdf_output,
        pagesize=pagesize,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )
    
    ancho_disponible = pagesize[0] - 20*mm
    num_columnas = len(encabezado)
    font_size = calcular_tamaño_fuente(num_columnas, len(datos_ordenados), ancho_disponible)
    
    ancho_columna = ancho_disponible / num_columnas
    col_widths = [ancho_columna] * num_columnas
    
    tabla = Table(datos_ordenados, colWidths=col_widths, repeatRows=1)
    
    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), font_size),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), font_size),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ])
    
    tabla.setStyle(estilo)
    
    try:
        doc.build([tabla])
        print(f"✓ PDF combinado generado exitosamente: {pdf_output}")
        print(f"  - {len(datos_ordenados)} filas totales (incluyendo encabezado)")
        print(f"  - {num_columnas} columnas")
        print(f"  - Tamaño de fuente: {font_size}")
    except Exception as e:
        print(f"Error al generar el PDF combinado: {e}")


def convertir_todos_los_csv():
    """
    Busca y convierte todos los archivos CSV en el directorio actual.
    """
    archivos_csv = [f for f in os.listdir('.') if f.endswith('.csv')]
    
    if not archivos_csv:
        print("No se encontraron archivos CSV en el directorio actual.")
        return
    
    print(f"Se encontraron {len(archivos_csv)} archivo(s) CSV:\n")
    
    for csv_file in archivos_csv:
        print(f"Procesando: {csv_file}")
        csv_to_pdf(csv_file)
        print()


if __name__ == "__main__":
    print("=== Conversor de CSV a PDF ===\n")
    
    # Opción 1: Combinar ambos CSV en un solo PDF
    print("Generando PDF combinado...")
    combinar_csv_en_pdf(
        ['gastos_aliexpress.csv', 'cnfans_pedidos_gastos.csv'],
        'gastos_combinados.pdf',
        'Gastos Totales'
    )
    print()
    
    # Opción 2: Convertir cada CSV individualmente (descomenta si prefieres esto)
    # convertir_todos_los_csv()
    
    # Opción 3: Convertir archivos específicos (descomenta si prefieres esto)
    # csv_to_pdf('gastos_aliexpress.csv')
    # csv_to_pdf('cnfans_pedidos_gastos.csv')
