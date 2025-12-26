from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import csv
import re
from datetime import datetime, date

# --- CONFIGURACIÓN ---
LOGIN_URL = "https://cnfans.com/login"
ORDERS_URL = "https://cnfans.com/my-account/orders"

# RANGO DE FECHAS (inclusive)
START_DATE_STR = "09-12-2025"  # dd-mm-YYYY
START_DATE = datetime.strptime(START_DATE_STR, "%d-%m-%Y").date()
END_DATE = date.today()

# Salida
OUTPUT_CSV = "cnfans_pedidos_gastos.csv"
CSV_DELIMITER = ";"  # recomendado para Excel en España

# Constantes contables
SUPPLIER_NAME = "Cnfans"
PAYMENT_METHOD_FORCED = "tarjeta"

load_dotenv()
CNFANS_EMAIL = os.getenv("CNFANS_EMAIL")
CNFANS_PASSWORD = os.getenv("CNFANS_PASSWORD")

if not CNFANS_EMAIL or not CNFANS_PASSWORD:
    raise SystemExit(
        "Faltan credenciales. Asegúrate de tener CNFANS_EMAIL y CNFANS_PASSWORD en tu archivo .env o variables de entorno."
    )


# ----------------- HELPERS -----------------
def parse_create_time_to_date(create_time_raw: str):
    """
    Convierte el texto 'create_time' a date.
    Intenta varios formatos típicos.
    Si no puede, devuelve None.
    """
    if not create_time_raw:
        return None

    s = create_time_raw.strip()
    s = s.replace("Create Time:", "").strip()

    # Si viene con texto extra, nos quedamos con el trozo más "fecha/hora"
    # (no hace milagros, pero ayuda con casos raros)
    s = re.sub(r"\s+", " ", s)

    fmts = [
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        # por si la web usa formato americano (ojo: ambiguo en fechas tipo 12/09/2025)
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
    ]

    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


def parse_money(value: str) -> float:
    """
    Extrae número de un string tipo "€1,234.56" o "1.234,56 €" y lo pasa a float.
    Si no hay valor, 0.0
    """
    if not value:
        return 0.0

    m = re.search(r"[-]?\d[\d.,]*", value)
    if not m:
        return 0.0

    num = m.group(0)

    # Heurística para separar miles/decimales
    has_comma = "," in num
    has_dot = "." in num

    if has_comma and has_dot:
        # El separador decimal suele ser el último que aparece
        if num.rfind(",") > num.rfind("."):
            # decimal=",", miles="."
            num = num.replace(".", "")
            num = num.replace(",", ".")
        else:
            # decimal=".", miles=","
            num = num.replace(",", "")
    elif has_comma and not has_dot:
        # Si hay coma, asumimos decimal si termina en 2 dígitos
        parts = num.split(",")
        if len(parts[-1]) == 2:
            num = num.replace(".", "")
            num = num.replace(",", ".")
        else:
            # coma como miles
            num = num.replace(",", "")
    else:
        # solo puntos o ninguno: asumimos punto decimal / o miles, pero float lo tragará si es coherente
        num = num.replace(",", "")

    try:
        return float(num)
    except ValueError:
        return 0.0


def format_money_es(amount: float) -> str:
    """
    Formato España: 1.234,56 €
    """
    s = f"{amount:,.2f}"           # 1,234.56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,56
    return f"{s} €"


def pick_hoodie_name(products) -> str:
    """
    Devuelve un nombre "representativo" de sudadera.
    Prioriza keywords de sudadera/hoodie; si no, el primer producto con nombre.
    """
    if not products:
        return "sin producto"

    keywords = ("hoodie", "sudadera", "sweatshirt", "pullover", "hood")
    # 1) buscar por keywords
    for p in products:
        name = (p.get("name") or "").strip()
        if name and any(k in name.lower() for k in keywords):
            return name

    # 2) fallback: primero con nombre
    for p in products:
        name = (p.get("name") or "").strip()
        if name:
            return name

    return "sin producto"


# ----------------- PARSEO HTML -----------------
def extract_order_basic_info(order_html: str):
    """Parsea el HTML de un bloque .order-item individual para info básica."""
    soup = BeautifulSoup(order_html, "lxml")

    header = soup.select_one(".order-date-no")
    create_time = ""
    order_no = ""

    if header:
        date_span = header.select_one(".order-date")
        order_no_span = header.select_one(".order-no")
        if date_span:
            create_time = date_span.get_text(strip=True).replace("Create Time:", "").strip()
        if order_no_span:
            order_no = order_no_span.get_text(strip=True).replace("Order No:", "").strip()

    status_span = soup.select_one(".status-manage-wrapper .status-node-status")
    status = status_span.get_text(strip=True) if status_span else ""

    total_product_amount = ""
    domestic_shipping = ""
    value_added_services = ""
    payment_method = ""

    # extras (si existieran en la web)
    total_amount = ""
    actual_payment = ""

    for price_meta in soup.select(".order-price-info .price-meta"):
        label_el = price_meta.select_one(".meta-label")
        value_el = price_meta.select_one(".meta-value")
        if not label_el or not value_el:
            continue

        label = label_el.get_text(strip=True)
        value = value_el.get_text(strip=True)

        if "Total Product Amount" in label:
            total_product_amount = value
        elif "Domestic Shipping" in label:
            domestic_shipping = value
        elif "Value-added Services" in label:
            value_added_services = value
        elif "Payment Method" in label:
            payment_method = value
        elif ("Actual Payment" in label) or ("Paid Amount" in label):
            actual_payment = value
        elif ("Total Amount" in label) and ("Total Product Amount" not in label):
            total_amount = value

    products = []
    product_blocks = soup.select(".order-product-info .order-product-info-meta.product-detail")
    for pb in product_blocks:
        img_el = pb.select_one(".product-main-img img")
        image_url = img_el["src"] if img_el and img_el.has_attr("src") else ""

        name_span = pb.select_one(".product-name span")
        name = name_span.get_text(strip=True) if name_span else ""

        sku_span = pb.select_one(".product-sku span")
        sku = sku_span.get_text(strip=True) if sku_span else ""

        price_container = pb.select_one(".product-price")
        price = ""
        quantity = ""
        if price_container:
            spans = price_container.select("span")
            if len(spans) >= 1:
                price = spans[0].get_text(strip=True)
            if len(spans) >= 2:
                quantity = spans[1].get_text(strip=True)

        products.append(
            {
                "name": name,
                "sku": sku,
                "price": price,
                "quantity": quantity,
                "image_url": image_url,
            }
        )

    details_link_el = soup.select_one('a[href*="/my-account/order-detail"]')
    details_url = details_link_el["href"] if details_link_el else ""

    return {
        "order_no": order_no,
        "create_time": create_time,
        "status": status,
        "total_product_amount": total_product_amount,
        "domestic_shipping": domestic_shipping,
        "value_added_services": value_added_services,
        "payment_method": payment_method,
        "total_amount": total_amount,
        "actual_payment": actual_payment,
        "details_url": details_url,
        "products": products,
    }


def get_parcel_details(target_page):
    """
    Extrae shipping_cost (precio total logística) y declare_total si aparece.
    """
    try:
        target_page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass

    shipping_cost = ""
    declare_total = ""

    try:
        price_locator = target_page.locator(".logistics-price-total .price-value").first
        price_locator.wait_for(state="attached", timeout=10000)
        if price_locator.count() > 0:
            shipping_cost = price_locator.inner_text().strip()

        declare_locator = target_page.locator(".table-row-item .declare-total").first
        if declare_locator.count() > 0:
            declare_total = declare_locator.inner_text().strip()

    except Exception as e:
        print(f" [Debug: Falló selector en {target_page.url}: {e}] ", end="")
        target_page.screenshot(path="debug_error_parcel.png")

    return shipping_cost, declare_total


# ----------------- SCRAPING POR PÁGINA -----------------
def process_page_orders(page):
    """
    Recorre pedidos de la página actual.
    - Filtra por rango de fecha.
    - Si detecta un pedido anterior al START_DATE, activa stop_early (asumiendo orden descendente).
    Devuelve: (orders_in_range, stop_early)
    """
    processed_orders = []
    stop_early = False

    page.wait_for_selector("div.orders div.order-list div.order-item", timeout=15000)
    items_count = page.locator("div.orders div.order-list div.order-item").count()
    print(f"   -> Encontrados {items_count} pedidos en esta página.")

    for i in range(items_count):
        order_locator = page.locator("div.orders div.order-list div.order-item").nth(i)
        order_html = order_locator.inner_html()
        order_data = extract_order_basic_info(order_html)

        order_date = parse_create_time_to_date(order_data.get("create_time", ""))
        if order_date is None:
            print(f"      [{i+1}/{items_count}] Pedido {order_data.get('order_no','')} sin fecha parseable -> SKIP")
            continue

        # Corte por rango
        if order_date < START_DATE:
            print(f"      [{i+1}/{items_count}] Pedido {order_data.get('order_no','')} ({order_date}) < {START_DATE} -> STOP")
            stop_early = True
            break

        if order_date > END_DATE:
            # raro, pero por si acaso
            print(f"      [{i+1}/{items_count}] Pedido {order_data.get('order_no','')} ({order_date}) > {END_DATE} -> SKIP")
            continue

        print(f"      [{i+1}/{items_count}] Pedido: {order_data['order_no']} ({order_date})...", end="", flush=True)

        # Solo si entra en rango, intentamos sacar shipping_cost (View Parcel)
        view_parcel_btn = order_locator.locator("button", has_text="View Parcel")
        shipping_cost = ""
        declare_total = ""

        if view_parcel_btn.count() > 0:
            try:
                # Importante: timeout bajo para no perder 30s si NO abre popup
                with page.context.expect_page(timeout=1500) as new_page_info:
                    view_parcel_btn.first.click()

                # Caso A: popup
                new_page = new_page_info.value
                new_page.wait_for_load_state()
                shipping_cost, declare_total = get_parcel_details(new_page)
                new_page.close()
                print(f" [Popup OK: Envío={shipping_cost}]", end="")

            except:
                # Caso B: misma pestaña
                try:
                    page.wait_for_url("*parcel-detail*", timeout=10000)
                    shipping_cost, declare_total = get_parcel_details(page)
                    print(f" [Nav OK: Envío={shipping_cost}]", end="")

                    page.go_back()
                    page.wait_for_selector("div.orders div.order-list div.order-item", timeout=15000)
                except Exception as e:
                    print(f" [No cargó parcel info: {e}]", end="")
                    if "orders" not in page.url:
                        page.go_back()
                        page.wait_for_selector("div.orders div.order-list div.order-item", timeout=15000)
        else:
            print(" [Sin botón Parcel]", end="")

        print(" Done.")

        order_data["shipping_cost"] = shipping_cost
        order_data["declare_total"] = declare_total
        processed_orders.append(order_data)

    return processed_orders, stop_early


def go_to_next_page(page) -> bool:
    active = page.locator(".n-pagination-item.n-pagination-item--active")
    if active.count() == 0:
        return False

    current_page_text = active.first.inner_text().strip()
    try:
        current_page = int(current_page_text)
    except ValueError:
        return False

    next_page_str = str(current_page + 1)
    next_page_item = page.locator(
        ".n-pagination-item.n-pagination-item--clickable", has_text=next_page_str
    )

    if next_page_item.count() == 0:
        return False

    print(f"--- Navegando a página {next_page_str} ---")
    next_page_item.first.click()
    page.wait_for_timeout(3000)
    return True


# ----------------- TRANSFORMACIÓN A CSV CONTABLE -----------------
def compute_paid_amount(order: dict) -> float:
    """
    Importe pagado:
    - Si existe actual_payment -> usarlo
    - else si existe total_amount -> usarlo
    - else sumar total_product_amount + domestic_shipping + value_added_services + shipping_cost
    """
    if order.get("actual_payment"):
        return parse_money(order["actual_payment"])
    if order.get("total_amount"):
        return parse_money(order["total_amount"])

    return (
        parse_money(order.get("total_product_amount", ""))
        + parse_money(order.get("domestic_shipping", ""))
        + parse_money(order.get("value_added_services", ""))
        + parse_money(order.get("shipping_cost", ""))
    )


def build_expense_rows(orders: list[dict]) -> list[dict]:
    """
    Devuelve filas con SOLO las columnas pedidas:
    - Fecha del gasto
    - Proveedor
    - Importe pagado
    - Concepto: "pedido + nombre de sudadera"
    - Nº de pedido
    - Método de pago
    Además, se añadirán filas de TOTAL por mes al final.
    """
    rows = []
    for o in orders:
        order_date = parse_create_time_to_date(o.get("create_time", ""))
        if order_date is None:
            continue

        hoodie_name = pick_hoodie_name(o.get("products", []))
        concepto = f"pedido {hoodie_name}"

        paid = compute_paid_amount(o)

        rows.append(
            {
                "Fecha del gasto": order_date,
                "Proveedor": SUPPLIER_NAME,
                "Importe pagado": paid,
                "Concepto": concepto,
                "Nº de pedido": o.get("order_no", ""),
                "Método de pago": PAYMENT_METHOD_FORCED,
            }
        )

    # Ordenar por fecha ascendente
    rows.sort(key=lambda r: r["Fecha del gasto"])

    # Insertar total mensual al final de cada mes
    final_rows = []
    current_month = None
    month_sum = 0.0

    for r in rows:
        ym = (r["Fecha del gasto"].year, r["Fecha del gasto"].month)
        if current_month is None:
            current_month = ym

        if ym != current_month:
            y, m = current_month
            final_rows.append(
                {
                    "Fecha del gasto": "",
                    "Proveedor": "",
                    "Importe pagado": month_sum,
                    "Concepto": f"TOTAL MES {y}-{m:02d}",
                    "Nº de pedido": "",
                    "Método de pago": "",
                }
            )
            month_sum = 0.0
            current_month = ym

        month_sum += float(r["Importe pagado"])
        final_rows.append(r)

    # último mes
    if current_month is not None:
        y, m = current_month
        final_rows.append(
            {
                "Fecha del gasto": "",
                "Proveedor": "",
                "Importe pagado": month_sum,
                "Concepto": f"TOTAL MES {y}-{m:02d}",
                "Nº de pedido": "",
                "Método de pago": "",
            }
        )

    return final_rows


def save_expenses_to_csv(expense_rows: list[dict], filename: str = OUTPUT_CSV):
    fieldnames = [
        "Fecha del gasto",
        "Proveedor",
        "Importe pagado",
        "Concepto",
        "Nº de pedido",
        "Método de pago",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for r in expense_rows:
            fecha = r["Fecha del gasto"]
            fecha_str = fecha.strftime("%d-%m-%Y") if isinstance(fecha, date) else ""

            importe = r["Importe pagado"]
            importe_str = format_money_es(float(importe)) if importe != "" else ""

            writer.writerow(
                {
                    "Fecha del gasto": fecha_str,
                    "Proveedor": r["Proveedor"],
                    "Importe pagado": importe_str,
                    "Concepto": r["Concepto"],
                    "Nº de pedido": r["Nº de pedido"],
                    "Método de pago": r["Método de pago"],
                }
            )


# ----------------- SCRAPER PRINCIPAL -----------------
def scrape_cnfans_orders():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("Iniciando sesión...")
        page.goto(LOGIN_URL, wait_until="networkidle")
        page.fill('input[placeholder="Username or email address"]', CNFANS_EMAIL)
        page.fill('input[placeholder="Enter password"]', CNFANS_PASSWORD)
        page.click('button:has-text("login")')
        page.wait_for_timeout(4000)

        print("Yendo a lista de pedidos...")
        page.goto(ORDERS_URL, wait_until="networkidle")

        all_orders = []
        seen_order_nos = set()

        while True:
            orders_on_page, stop_early = process_page_orders(page)

            for o in orders_on_page:
                order_no = o.get("order_no")
                if not order_no:
                    continue
                if order_no in seen_order_nos:
                    continue
                seen_order_nos.add(order_no)
                all_orders.append(o)

            if stop_early:
                break

            if not go_to_next_page(page):
                break

        browser.close()
        return all_orders


if __name__ == "__main__":
    print("Iniciando Scraper CNFans...")
    print(f"Rango: {START_DATE.strftime('%d-%m-%Y')} -> {END_DATE.strftime('%d-%m-%Y')}")

    orders = scrape_cnfans_orders()
    print(f"\nPedidos en rango (únicos): {len(orders)}")

    expense_rows = build_expense_rows(orders)
    save_expenses_to_csv(expense_rows, OUTPUT_CSV)

    print(f"Archivo guardado: {OUTPUT_CSV}")
