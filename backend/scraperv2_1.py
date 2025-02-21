import time
import random
import csv
import traceback
from fake_useragent import UserAgent
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from seleniumwire import webdriver  # Importar selenium-wire para manejar proxies autenticados



# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================

# Credenciales de Instagram *incrustadas* directamente
INSTA_USER = "redzone_rr"
INSTA_PASS = "provisional2628"

# Lista de cuentas a extraer
# ACCOUNTS = [
#     "disneystudiosla", "paramountmexico", "videocine",
#     "sonypicturesmx", "diamondfilmsmex", "universalmx",
#     "warnerbrosmx", "corazonfilms"
# ]
ACCOUNTS = [
 "universalmx"]


# Año mínimo a filtrar
YEAR_FILTER = 2024

# =========================================================================
# CLASE SCRAPER
# =========================================================================
class InstagramScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de .
        """
        PROXY_HOST = "brd.superproxy.io"
        PROXY_PORT = "33335"
        # PROXY_USER = "brd-customer-hl_5c6b7303-zone-residential_proxy1"
        # PROXY_PASS = "c6y6ev5szcrn"
        PROXY_USER = "sp03mahcda"
        PROXY_PASS = "X3s_awrkk90gNbs0YX"

        # Configuración de Proxy en Chrome
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        proxy_options = {
            "proxy": {
                "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
                "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
            }
        }

        

        # Opciones anti detección Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={self._random_user_agent()}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(seleniumwire_options=proxy_options, options=options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)


        return driver

    def _random_user_agent(self):
        """
        Devuelve un User-Agent aleatorio para evitar detección.
        """
        # ua = UserAgent()
        # random_user_agent = ua.random
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2_1 like Mac OS X)"
            " AppleWebKit/605.1.15 (KHTML, like Gecko)"
            " Version/15.2 Mobile/15E148 Safari/604.1",
        ]
        return random.choice(agents)
        #return random_user_agent


    def _human_delay(self, min_s=1.0, max_s=3.0):
        """
        Pausa aleatoria entre acciones para simular comportamiento humano.
        """
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        time.sleep(total)

    def login(self):
        """
        Inicia sesión en Instagram con espera dinámica.
        """
        self.driver.get("https://www.instagram.com/")
        self._human_delay(3, 5)

        try:
            # Esperar a que el campo de usuario aparezca
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )

            username_input.send_keys(INSTA_USER)
            self._human_delay(0.5, 1.0)
            password_input.send_keys(INSTA_PASS)

            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_btn.click()

            self._human_delay(5, 8)

            if "login" in self.driver.current_url:
                raise Exception("Error de autenticación (quizás CAPTCHA o 2FA).")

            print("[INFO] Login completado.")

        except Exception as e:
            print("[ERROR] en login:", e)
            traceback.print_exc()

    def scrape_profile(self, username):
        """
        Extrae posts del perfil de Instagram especificado.
        """
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(3, 5)

        all_posts = []
        last_date = datetime.now()

        while last_date.year >= YEAR_FILTER:
            self._scroll_human()
            new_posts = self._extract_posts()
            if not new_posts:
                break

            for post in new_posts:
                post_date = datetime.strptime(post['date'], "%Y-%m-%dT%H:%M:%S")
                if post_date.year < YEAR_FILTER:
                    return all_posts
                all_posts.append(post)

            last_date = datetime.strptime(new_posts[-1]['date'], "%Y-%m-%dT%H:%M:%S")

        return all_posts

    def _scroll_human(self):
        """
        Simula scroll humano en la página de perfil.
        """
        body = self.driver.find_element(By.TAG_NAME, "body")
        for _ in range(random.randint(3, 6)):
            body.send_keys(Keys.PAGE_DOWN)
            self._human_delay(1.5, 3.0)

    def _extract_posts(self):
        """
        Extrae los datos de los posts visibles.
        """
        posts_data = []
        articles = self.driver.find_elements(By.TAG_NAME, "article")
        if not articles:
            return posts_data

        for article in articles[-6:]:
            try:
                time_element = article.find_element(By.TAG_NAME, "time")
                date_str = time_element.get_attribute("datetime")
                link_elem = article.find_element(By.TAG_NAME, "a")
                post_url = link_elem.get_attribute("href")

                posts_data.append({
                    "date": date_str,
                    "url": post_url
                })
            except Exception as e:
                print("[ERROR] extrayendo post:", e)
                continue

        return posts_data

    def save_to_csv(self, data, filename):
        """
        Guarda los datos extraídos en un archivo CSV.
        """
        if not data:
            print("No hay datos para guardar en CSV.")
            return
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"[INFO] Se guardaron {len(data)} filas en {filename}.")

# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    scraper = InstagramScraper()
    try:
        # 1) Login
        scraper.login()

        # 2) Recorrer cuentas
        all_posts = []
        for account in ACCOUNTS:
            print(f"\n[INFO] Scrapeando {account}")
            posts = scraper.scrape_profile(account)
            all_posts.extend(posts)
            print(f"[INFO] {account} => {len(posts)} posts extraídos")
            time.sleep(random.randint(5, 15))

        # 3) Guardar en CSV
        scraper.save_to_csv(all_posts, "instagram_posts_2024.csv")
        print("\n[OK] Proceso completado.")

    except Exception as e:
        print("[CRÍTICO] Error en la ejecución:", e)
        traceback.print_exc()
    finally:
        scraper.driver.quit()
        print("[INFO] Selenium cerrado.")