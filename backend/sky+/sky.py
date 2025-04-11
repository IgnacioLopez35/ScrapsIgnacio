import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from obswebsocket import obsws, requests



# Configuración de Sky+
SKY_URL = "https://www.skymas.mx/webclient/#/live"  # Ajusta la URL real
CHANNEL_XPATH = "//button[contains(text(),'Canal 5')]"  # Ejemplo: XPATH del botón del canal



def setup_browser():
    """Configura Selenium para controlar Chrome"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print("✅ Navegador Chrome listo")
    driver.get(SKY_URL)
    time.sleep(20)
    driver.quit()


setup_browser()