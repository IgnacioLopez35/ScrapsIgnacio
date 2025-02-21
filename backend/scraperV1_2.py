import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class GoogleSearchBot:
    def __init__(self):
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """ Configura el navegador con opciones anti-detección. """
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        #options.add_argument("--headless")  # Opcional: Ejecuta en segundo plano (sin GUI)

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        return driver

    def type_slowly(self, element, text):
        """ Teclea cada letra con un retraso aleatorio de 1 segundo """
        for letter in text:
            element.send_keys(letter)
            time.sleep(random.uniform(0.3, 1)) 

    def search_instagram(self):
        """ Abre Google, busca Instagram y muestra los resultados """
        self.driver.get("https://www.google.com/")
        time.sleep(random.uniform(1, 2))  # Espera para que cargue la página

        try:
            search_box = self.driver.find_element(By.NAME, "q")
            print("✅ Campo de búsqueda encontrado. Escribiendo 'Instagram'...")

            # Escribe "Instagram" con un retraso de 1 segundo por letra
            self.type_slowly(search_box, "Instagram")

            # Presiona Enter para buscar
            search_box.send_keys(Keys.ENTER)
            print("🔍 Búsqueda enviada. Esperando resultados...")

            time.sleep(3)  # Espera para ver los resultados
            print("✅ Resultados de búsqueda mostrados.")
        except Exception as e:
            print(f"❌ Error durante la búsqueda: {e}")

    def close(self):
        """ Cierra el navegador """
        self.driver.quit()
        print("🚪 Navegador cerrado.")

# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    bot = GoogleSearchBot()
    try:
        bot.search_instagram()
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        bot.close()
