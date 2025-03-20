import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

# Configuración del proxy
PROXY_HOST = "gate.smartproxy.com"
PROXY_PORT = "10009"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "ax4as2g5_S2HHrmIjl"

# Configura el proxy con autenticación
chrome_options = uc.ChromeOptions()
chrome_options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
chrome_options.add_argument(f'--proxy-auth={PROXY_USER}:{PROXY_PASS}')

# Configuraciones adicionales para evitar errores
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Inicia el navegador con las opciones de proxy
driver = uc.Chrome(options=chrome_options)

# Prueba la conexión a YouTube
driver.get("https://www.youtube.com")
time.sleep(5)  # Espera a que la página cargue
print(driver.page_source)  # Deberías ver el contenido de la página de YouTube

# Cierra el navegador
driver.quit()