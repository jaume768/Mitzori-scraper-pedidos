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


def procesar_gastos_por_proveedor(csv_files, dividir=False, num_partes=2, metodo='importe'):
    """
    Genera PDFs agrupados por proveedor.
    
    Args:
        csv_files: Lista de archivos CSV (cada uno es un proveedor)
        dividir: Si True, divide cada proveedor en partes
        num_partes: Número de partes por proveedor
        metodo: 'importe' o 'registros'
    """
    from datetime import datetime
    
    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            print(f"Advertencia: No se encuentra '{csv_file}', se omitirá.")
            continue
        
        print(f"\n{'='*60}")
        print(f"Procesando: {csv_file}")
        print(f"{'='*60}\n")
        
        # Leer CSV
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            datos = list(reader)
        
        if not datos or len(datos) <= 1:
            print(f"No hay datos en {csv_file}")
            continue
        
        encabezado = datos[0]
        filas_datos = [fila for fila in datos[1:] 
                       if fila and any(fila) and 'RESUMEN' not in str(fila).upper() 
                       and 'TOTAL' not in str(fila[0]).upper()]
        
        # Ordenar por fecha
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
        
        # Extraer nombre del proveedor del CSV
        nombre_base = csv_file.replace('.csv', '').replace('gastos_', '').replace('_pedidos_gastos', '')
        
        if dividir and num_partes > 1:
            # Dividir este proveedor en partes
            _dividir_y_generar_pdfs(encabezado, filas_datos, num_partes, metodo, f"{nombre_base}_parte")
        else:
            # Generar un solo PDF para este proveedor
            _generar_pdf_unico(encabezado, filas_datos, f"{nombre_base}.pdf")


def _dividir_y_generar_pdfs(encabezado, filas_datos, num_partes, metodo, prefijo_salida):
    """Función auxiliar para dividir y generar PDFs."""
    def extraer_importe(fila):
        try:
            importe_str = fila[2].replace(',', '.').strip()
            return float(importe_str)
        except:
            return 0.0
    
    importe_total = sum(extraer_importe(fila) for fila in filas_datos)
    print(f"Total de registros: {len(filas_datos)}")
    print(f"Importe total: {importe_total:.2f} €")
    
    # Dividir según el método
    if metodo == 'importe':
        print(f"Dividiendo por importe en {num_partes} partes...\n")
        importe_por_parte = importe_total / num_partes
        
        partes = []
        parte_actual = []
        importe_acumulado = 0.0
        
        for fila in filas_datos:
            importe_fila = extraer_importe(fila)
            
            if importe_acumulado + importe_fila > importe_por_parte and parte_actual and len(partes) < num_partes - 1:
                partes.append(parte_actual)
                parte_actual = [fila]
                importe_acumulado = importe_fila
            else:
                parte_actual.append(fila)
                importe_acumulado += importe_fila
        
        if parte_actual:
            partes.append(parte_actual)
    
    else:  # metodo == 'registros'
        print(f"Dividiendo por registros en {num_partes} partes...\n")
        registros_por_parte = len(filas_datos) // num_partes
        
        partes = []
        for i in range(num_partes):
            inicio = i * registros_por_parte
            fin = len(filas_datos) if i == num_partes - 1 else inicio + registros_por_parte
            partes.append(filas_datos[inicio:fin])
    
    # Generar PDFs
    for i, parte in enumerate(partes, 1):
        importe_parte = sum(extraer_importe(fila) for fila in parte)
        pdf_filename = f"{prefijo_salida}_{i}_de_{len(partes)}.pdf"
        _generar_pdf_con_datos(encabezado, parte, pdf_filename, f"TOTAL PARTE {i} de {len(partes)}", importe_parte)
        print(f"✓ {pdf_filename} - {len(parte)} registros - {importe_parte:.2f} €")


def _generar_pdf_unico(encabezado, filas_datos, pdf_filename):
    """Función auxiliar para generar un PDF único."""
    def extraer_importe(fila):
        try:
            importe_str = fila[2].replace(',', '.').strip()
            return float(importe_str)
        except:
            return 0.0
    
    importe_total = sum(extraer_importe(fila) for fila in filas_datos)
    print(f"Total de registros: {len(filas_datos)}")
    print(f"Importe total: {importe_total:.2f} €\n")
    
    _generar_pdf_con_datos(encabezado, filas_datos, pdf_filename, "TOTAL", importe_total)
    print(f"✓ {pdf_filename} - {len(filas_datos)} registros - {importe_total:.2f} €")


def _generar_pdf_con_datos(encabezado, filas_datos, pdf_filename, texto_total, importe_total):
    """Función auxiliar que genera el PDF con los datos proporcionados."""
    # Construir datos con encabezado, registros y total
    datos_parte = [encabezado] + filas_datos
    
    # Añadir fila de TOTAL
    fila_total = [''] * len(encabezado)
    fila_total[2] = f"{importe_total:.2f}"
    fila_total[3] = texto_total
    datos_parte.append(fila_total)
    
    # Generar PDF
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=pagesize,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )
    
    ancho_disponible = pagesize[0] - 20*mm
    num_columnas = len(encabezado)
    font_size = calcular_tamaño_fuente(num_columnas, len(datos_parte), ancho_disponible)
    
    ancho_columna = ancho_disponible / num_columnas
    col_widths = [ancho_columna] * num_columnas
    
    tabla = Table(datos_parte, colWidths=col_widths, repeatRows=1)
    
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
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFE699')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), font_size + 1),
    ])
    
    tabla.setStyle(estilo)
    doc.build([tabla])


def dividir_gastos_en_pdfs(csv_files, num_partes=2, metodo='importe', prefijo_salida='gastos_parte'):
    """
    Divide los gastos en múltiples PDFs.
    
    Args:
        csv_files: Lista de archivos CSV a combinar y dividir
        num_partes: Número de partes en las que dividir (default: 2)
        metodo: 'importe' para dividir por valor acumulado, 'registros' para dividir por cantidad
        prefijo_salida: Prefijo para los nombres de archivos PDF
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
            
            # Guardar encabezado
            if not datos_combinados:
                encabezado = datos[0]
                datos_combinados.append(encabezado)
            
            # Añadir datos (sin encabezado, sin filas vacías, sin resúmenes)
            for fila in datos[1:]:
                if fila and any(fila) and 'RESUMEN' not in str(fila).upper() and 'TOTAL' not in str(fila[0]).upper():
                    datos_combinados.append(fila)
    
    if len(datos_combinados) <= 1:
        print("No hay datos suficientes para dividir.")
        return
    
    encabezado = datos_combinados[0]
    filas_datos = datos_combinados[1:]
    
    # Ordenar por fecha descendente
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
    
    # Calcular el total de gastos
    def extraer_importe(fila):
        try:
            # El importe está en la columna 2 (índice 2)
            importe_str = fila[2].replace(',', '.').strip()
            return float(importe_str)
        except:
            return 0.0
    
    importe_total = sum(extraer_importe(fila) for fila in filas_datos)
    print(f"\nTotal de registros: {len(filas_datos)}")
    print(f"Importe total: {importe_total:.2f} €")
    
    # Dividir según el método seleccionado
    if metodo == 'importe':
        print(f"\nDividiendo por importe en {num_partes} partes...")
        importe_por_parte = importe_total / num_partes
        
        partes = []
        parte_actual = []
        importe_acumulado = 0.0
        
        for fila in filas_datos:
            importe_fila = extraer_importe(fila)
            
            # Si añadir esta fila supera el límite y ya tenemos algo en la parte actual
            if importe_acumulado + importe_fila > importe_por_parte and parte_actual and len(partes) < num_partes - 1:
                partes.append(parte_actual)
                parte_actual = [fila]
                importe_acumulado = importe_fila
            else:
                parte_actual.append(fila)
                importe_acumulado += importe_fila
        
        # Añadir la última parte
        if parte_actual:
            partes.append(parte_actual)
    
    else:  # metodo == 'registros'
        print(f"\nDividiendo por registros en {num_partes} partes...")
        registros_por_parte = len(filas_datos) // num_partes
        
        partes = []
        for i in range(num_partes):
            inicio = i * registros_por_parte
            if i == num_partes - 1:
                # Última parte toma todo lo que queda
                fin = len(filas_datos)
            else:
                fin = inicio + registros_por_parte
            
            partes.append(filas_datos[inicio:fin])
    
    # Generar un PDF por cada parte
    print(f"\nGenerando {len(partes)} PDFs...\n")
    
    for i, parte in enumerate(partes, 1):
        # Calcular importe de esta parte
        importe_parte = sum(extraer_importe(fila) for fila in parte)
        
        # Construir datos con encabezado, registros y total
        datos_parte = [encabezado] + parte
        
        # Añadir fila de TOTAL al final
        fila_total = [''] * len(encabezado)
        fila_total[0] = ''  # Fecha vacía
        fila_total[1] = ''  # Proveedor vacío
        fila_total[2] = f"{importe_parte:.2f}"  # Importe total
        fila_total[3] = f"TOTAL"  # Concepto
        datos_parte.append(fila_total)
        
        # Nombre del archivo
        pdf_filename = f"{prefijo_salida}_{i}_de_{len(partes)}.pdf"
        
        # Generar PDF
        pagesize = landscape(A4)
        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=pagesize,
            leftMargin=10*mm,
            rightMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        
        ancho_disponible = pagesize[0] - 20*mm
        num_columnas = len(encabezado)
        font_size = calcular_tamaño_fuente(num_columnas, len(datos_parte), ancho_disponible)
        
        ancho_columna = ancho_disponible / num_columnas
        col_widths = [ancho_columna] * num_columnas
        
        tabla = Table(datos_parte, colWidths=col_widths, repeatRows=1)
        
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
            # Estilo para la fila de TOTAL (última fila)
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFE699')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), font_size + 1),
        ])
        
        tabla.setStyle(estilo)
        
        try:
            doc.build([tabla])
            print(f"✓ Parte {i}: {pdf_filename}")
            print(f"  - {len(parte)} registros")
            print(f"  - Importe: {importe_parte:.2f} €")
        except Exception as e:
            print(f"Error generando parte {i}: {e}")


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
    
    # ==================== CONFIGURACIÓN ====================
    # Cambia estas variables según tus necesidades
    
    AGRUPAR_POR_PROVEEDOR = True  # True: PDF por proveedor | False: Todo junto
    DIVIDIR_GASTOS = True         # True: Dividir en partes | False: PDF único
    NUM_PARTES = 2                 # Número de partes (solo si DIVIDIR_GASTOS=True)
    METODO_DIVISION = 'importe'    # 'importe' o 'registros'
    
    archivos_csv = ['gastos_aliexpress.csv', 'cnfans_pedidos_gastos.csv']
    # =======================================================
    
    if AGRUPAR_POR_PROVEEDOR:
        # Opción 1: PDFs separados por proveedor (con o sin división)
        if DIVIDIR_GASTOS:
            print(f"Generando PDFs por proveedor, divididos en {NUM_PARTES} partes cada uno\n")
        else:
            print("Generando un PDF por cada proveedor\n")
        
        procesar_gastos_por_proveedor(
            archivos_csv,
            dividir=DIVIDIR_GASTOS,
            num_partes=NUM_PARTES,
            metodo=METODO_DIVISION
        )
    
    elif DIVIDIR_GASTOS:
        # Opción 2: Todo junto pero dividido en partes
        print(f"Dividiendo todos los gastos en {NUM_PARTES} partes por {METODO_DIVISION}...\n")
        dividir_gastos_en_pdfs(
            archivos_csv,
            num_partes=NUM_PARTES,
            metodo=METODO_DIVISION,
            prefijo_salida='gastos_parte'
        )
    
    else:
        # Opción 3: Todo junto en un solo PDF
        print("Generando PDF combinado...\n")
        combinar_csv_en_pdf(
            archivos_csv,
            'gastos_combinados.pdf',
            'Gastos Totales'
        )
    
    print()
    
    # Opción 4: Convertir cada CSV individualmente (descomenta si prefieres esto)
    # convertir_todos_los_csv()
    
    # Opción 5: Convertir archivos específicos (descomenta si prefieres esto)
    # csv_to_pdf('gastos_aliexpress.csv')
    # csv_to_pdf('cnfans_pedidos_gastos.csv')
