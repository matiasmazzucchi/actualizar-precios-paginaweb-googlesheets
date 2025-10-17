import requests
import gspread
from google.oauth2.service_account import Credentials
import logging
import re
import os # 👈 AGREGAR ESTA LÍNEA
from dotenv import load_dotenv

# ⚠️ CARGAR VARIABLES DEL ARCHIVO .ENV AL INICIO
load_dotenv()

# En un entorno local, el FileHandler está bien.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("update_prices.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- CONFIGURACIONES ---
WC_URL = "https://motoshondaramonsuarez.com.ar/wp-json/wc/v3/products"

# ⚠️ MODIFICACIÓN CLAVE: Leer desde variables de entorno
CONSUMER_KEY = os.environ.get("WC_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("WC_CONSUMER_SECRET")
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID") # Si no es sensible, podrías dejarlo codificado. Lo movemos para flexibilidad.
SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "MOTOS")

# Verifica que las claves críticas existan (una buena práctica)
if not all([CONSUMER_KEY, CONSUMER_SECRET]):
    logging.error("Las claves de WooCommerce (WC_CONSUMER_KEY o WC_CONSUMER_SECRET) no están configuradas.")
    # Si falta alguna clave, aborta la ejecución
    exit(1)


# --- AUTENTICACIÓN GOOGLE SHEETS ---
logging.info("Autenticando con Google Sheets...")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ⚠️ MODIFICACIÓN CLAVE: Leer la RUTA del archivo JSON desde el entorno
CREDENTIALS_FILE_PATH = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")

if not CREDENTIALS_FILE_PATH:
    logging.error("La ruta del archivo de credenciales (GOOGLE_SHEETS_CREDENTIALS_FILE) no está configurada.")
    exit(1)

try:
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    logging.info("Autenticación con Google Sheets exitosa.")
except Exception as e:
    logging.error(f"Error al autenticar con Google Sheets: {e}")
    exit(1)
    

# --- LEER DATOS DE GOOGLE SHEETS ---
logging.info(f"Leyendo datos de la hoja '{SHEET_NAME}' en Google Sheets...")
data = sheet.get_all_records()
logging.info(f"Total de filas obtenidas (sin encabezados): {len(data)}")

# --- FUNCIÓN PARA LIMPIAR Y CONVERTIR PRECIOS ---
def parse_price(value):
    if not value:
        return None
    try:
        # Eliminar símbolos $, €, comas, puntos de miles
        clean = re.sub(r"[^\d.]", "", str(value))
        # Manejo de miles (si hay más de un punto, dejamos solo el último como decimal)
        if clean.count(".") > 1:
            parts = clean.split(".")
            clean = "".join(parts[:-1]) + "." + parts[-1]
        return float(clean)
    except Exception:
        return None

# --- FUNCIÓN PARA ACTUALIZAR PRECIOS ---
def update_price(sku, price):
    try:
        logging.info(f"Buscando producto con SKU: {sku}...")
        auth = (CONSUMER_KEY, CONSUMER_SECRET)
        response = requests.get(f"{WC_URL}?sku={sku}", auth=auth)
        products = response.json()

        if products:
            product_id = products[0]["id"]
            logging.info(f"Producto encontrado. ID: {product_id}, actualizando precio a {price}...")

            payload = {"regular_price": str(price)}
            update_response = requests.put(
                f"{WC_URL}/{product_id}",
                json=payload,
                auth=auth,
                headers={"Content-Type": "application/json"}
            )

            if update_response.status_code == 200:
                logging.info(f"✅ Precio actualizado para SKU {sku} → {price}")
            else:
                logging.error(f"❌ Error actualizando SKU {sku}: {update_response.text}")
        else:
            logging.warning(f"⚠️ No se encontró producto con SKU {sku}")

    except Exception as e:
        logging.error(f"⚠️ Error procesando SKU {sku}: {e}")

# --- PROCESAR FILAS ---
logging.info("Iniciando actualización de precios...")
for index, row in enumerate(data, start=2):  # +2 porque fila 1 = encabezados
    sku = str(row.get("SKU", "")).strip()
    raw_price = row.get("Regular price")

    price = parse_price(raw_price)

    if sku and price and price > 0:
        logging.info(f"Fila {index}: SKU={sku}, Precio original='{raw_price}' → limpio={price}")
        update_price(sku, price)
    else:
        logging.warning(f"Fila {index}: SKU o precio inválido → SKU='{sku}', Precio='{raw_price}' (omitido)")

logging.info("Proceso finalizado.")