import csv
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Configuración de archivos
INPUT_FILE = 'aliexpress.txt'
OUTPUT_FILE = 'gastos_aliexpress.csv'

# Mapeo de meses en español a números para formatear la fecha
MESES = {
    'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
}

def limpiar_precio(texto_precio):
    """
    Convierte el texto sucio del precio (ej: "Total: US $ 15,92") a un número flotante.
    """
    # Eliminar texto "Total:" y espacios
    texto = texto_precio.replace('Total:', '').strip()
    
    # Eliminar símbolos de moneda comunes y espacios extra
    texto = re.sub(r'[€$£USCHFzł\s]', '', texto)
    
    # Reemplazar la coma decimal por punto para que Python lo entienda
    # Nota: Asumimos formato europeo (8,99) -> 8.99
    texto = texto.replace(',', '.')
    
    try:
        return float(texto)
    except ValueError:
        return 0.0

def procesar_fecha(texto_fecha):
    """
    Convierte "Pedido efectuado el: 26 dic, 2025" a "26/12/2025"
    y devuelve también el objeto fecha para ordenar o agrupar.
    """
    # Extraer solo la parte de la fecha (ej: "26 dic, 2025")
    match = re.search(r'(\d+)\s+([a-z]{3}),\s+(\d{4})', texto_fecha.lower())
    if match:
        dia, mes_txt, anio = match.groups()
        mes_num = MESES.get(mes_txt, '01')
        fecha_str = f"{dia}/{mes_num}/{anio}"
        fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
        return fecha_str, f"{mes_num}-{anio}" # Retornamos también Mes-Año para agrupar
    return "Fecha desconocida", "Desconocido"

def main():
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo '{INPUT_FILE}'.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Encontrar todos los bloques de pedido
    items = soup.find_all('div', class_='order-item')
    
    datos_csv = []
    totales_por_mes = {}
    
    print(f"Procesando {len(items)} pedidos...")

    for item in items:
        # 1. Obtener Info de Cabecera (Fecha y Nº Pedido)
        header_info = item.find('div', class_='order-item-header-right-info')
        texto_header = header_info.get_text(" | ", strip=True) if header_info else ""
        
        # Buscar fecha y número de pedido dentro del texto
        # El texto suele ser: "Pedido efectuado el: 26 dic, 2025 | Nº de pedido: 3066..."
        
        parts = texto_header.split('|')
        fecha_bruta = parts[0] if len(parts) > 0 else ""
        pedido_bruto = parts[1] if len(parts) > 1 else ""

        fecha_formateada, mes_anio = procesar_fecha(fecha_bruta)
        
        ref_pedido = pedido_bruto.replace('Nº de pedido:', '').replace('Copiar', '').strip()

        # 2. Obtener Nombre del producto (Concepto)
        nombre_div = item.find('div', class_='order-item-content-info-name')
        if nombre_div and nombre_div.find('span'):
            concepto = f"Pedido: {nombre_div.find('span').get_text(strip=True)}"
            # Acortar concepto si es muy largo para que el CSV se lea bien
            if len(concepto) > 80:
                concepto = concepto[:77] + "..."
        else:
            concepto = "Pedido AliExpress (Sin nombre detectado)"

        # 3. Obtener Precio
        precio_div = item.find('span', class_='order-item-content-opt-price-total')
        if precio_div:
            # get_text une todos los spans internos (números y comas)
            precio_texto = precio_div.get_text(strip=True)
            importe = limpiar_precio(precio_texto)
        else:
            importe = 0.0

        # Acumular total mensual
        if mes_anio not in totales_por_mes:
            totales_por_mes[mes_anio] = 0.0
        totales_por_mes[mes_anio] += importe

        # Guardar fila
        datos_csv.append({
            'Fecha': fecha_formateada,
            'Proveedor': 'AliExpress Europa S.L.',
            'Importe': str(importe).replace('.', ','), # Formato Excel europeo
            'Concepto': concepto,
            'Referencia': ref_pedido,
            'Metodo': 'Tarjeta'
        })

    # Escribir CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['Fecha', 'Proveedor', 'Importe', 'Concepto', 'Referencia', 'Metodo']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')

        writer.writeheader()
        for fila in datos_csv:
            writer.writerow(fila)
        
        # Añadir filas de resumen al final
        writer.writerow({}) # Fila vacía
        writer.writerow({'Fecha': 'RESUMEN MENSUAL', 'Proveedor': '---', 'Importe': '---'})
        
        for mes, total in totales_por_mes.items():
            writer.writerow({
                'Fecha': f"Total {mes}",
                'Proveedor': '',
                'Importe': f"{total:.2f}".replace('.', ','),
                'Concepto': 'Gasto total del mes',
                'Referencia': '',
                'Metodo': ''
            })

    print(f"¡Éxito! Se ha creado el archivo '{OUTPUT_FILE}' con {len(datos_csv)} registros.")
    print("Totales calculados:")
    for mes, total in totales_por_mes.items():
        print(f"  - {mes}: {total:.2f} €")

if __name__ == "__main__":
    main()