import time
import random
import csv
import traceback
from dateutil import parser
import pandas as pd
from move_mouse import MoveMouse
from fake_useragent import UserAgent
from datetime import datetime
#from selenium import webdriver
#from seleniumwire import webdriver 
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================

# Credenciales de Instagram *incrustadas* directamente
INSTA_USER = "redzone_rr"
INSTA_PASS = "provisional2628"
#https://www.instagram.com/universalmx/
# Lista de cuentas a extraer
ACCOUNTS = [
    "universalmx"
]
# Año mínimo a filtrar
YEAR_FILTER = 2024

# =========================================================================
# CLASE SCRAPER
# =========================================================================
class GoogleSearchBot(MoveMouse):
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de Bright Data.
        """
        # Configuración de Proxy Smartproxy
        PROXY_HOST = "gate.smartproxy.com"
        PROXY_PORT = "1008"
        PROXY_USER = "sp03mahcda"
        PROXY_PASS = "X3s_awrkk90gNbs0YX"

        proxy_options = {
            "proxy": {
                "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
                "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
                "no_proxy": "localhost,127.0.0.1",
            }
        }
        # Configuración del navegador
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")

        # Opciones anti detección Selenium
        options.add_argument(f"--user-agent={self._random_user_agent()}")
        #options.add_experimental_option("excludeSwitches", ["enable-automation"])
        #options.add_experimental_option("useAutomationExtension", False)

        # Iniciar Chrome con `undetected_chromedriver`
        driver = uc.Chrome(options=options)


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

    # Navegadores Chrome en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",

    # Navegadores Chrome en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",

    # Navegadores Firefox en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/108.0",

    # Navegadores Firefox en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/108.0",

    # Navegadores Safari en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",

    # Navegadores Chrome en Android
    "Mozilla/5.0 (Linux; Android 12; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36",

    # Navegadores Safari en iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",

    # Navegadores Edge en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.46",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.55",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.46",

    # Navegadores Opera en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 OPR/96.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 OPR/95.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 OPR/94.0.0.0",

        ]
        return random.choice(agents)
        # return random_user_agent


    

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
            self._human_delay(3, 5)  # Esperar resultados

            # Seleccionar el primer resultado con el mouse
            first_result = self.driver.find_element(By.XPATH, "//h3")  # Primer título de resultado
            print("🖱️ Primer resultado encontrado. Haciendo clic con el mouse...")

            # Mover el mouse sobre el primer resultado y hacer clic
            # Simular movimiento del mouse con curva Bézier
            self.smooth_mouse_move(self.driver, first_result)

            # # Hacer clic en el primer resultado
            first_result.click()
            self._human_delay(3, 5) # Esperar para la carga de Instagram



            # self.smooth_mouse_move(first_result)
            # self.action.click(first_result).perform()
            # self._human_delay(3, 5)

            print("✅ ¡Instagram abierto con éxito!")
            try:
                # Aceptar cookies
                allow_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Permitir')]")
                allow_btn.click()
                self._human_delay(1, 2)
            except:
                pass

            time.sleep(3)  # Espera para ver los resultados
            print("✅ Resultados de búsqueda mostrados.")
        except Exception as e:
            print(f"❌ Error durante la búsqueda: {e}")




    def login_insta(self):
        """ Inicia sesión en Instagram si ya está en la página de login. """
        self._human_delay(2, 3)

        # Esperar a que cargue la página y verificar si estamos en Instagram
        if "https://www.instagram.com/" not in self.driver.current_url:
            print("⚠️ No estamos en la página de login de Instagram. Verifica la navegación.")
            return

        print("✅ Página de Instagram detectada. Procediendo con el login...")

        try:
            # Mover el mouse y escribir en el campo de usuario
            username_input = self.driver.find_element(By.NAME, "username")
            print("🖱️ Moviendo mouse al campo de usuario...")
            self.smooth_mouse_move(self.driver, username_input)
            #self.smooth_mouse_move(username_input)
            username_input.click()  # Asegurar que está activo antes de escribir
            self.type_slowly(username_input, INSTA_USER)
            self._human_delay(0.5, 1.0)
            # Mover el mouse y escribir en el campo de contraseña
            password_input = self.driver.find_element(By.NAME, "password")
            print("🖱️ Moviendo mouse al campo de contraseña...")
            self.smooth_mouse_move(self.driver, password_input)
            password_input.click()  # Asegurar que está activo antes de escribir
            self.type_slowly(password_input, INSTA_PASS)
            self._human_delay(0.5, 1.0)
            # Mover el mouse al botón de login y hacer clic
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            print("🖱️ Moviendo mouse al botón de login...")
            self.smooth_mouse_move(self.driver, login_btn)
            self.action.click(login_btn).perform()

            self._human_delay(6, 6)


            # Verificar si la autenticación fue exitosa
            if "login" in self.driver.current_url:
                raise Exception("Error de autenticación (quizás CAPTCHA o 2FA).")

            print("✅ Login completado con éxito.")

        except Exception as e:
            print("[ERROR] en login:", e)
            traceback.print_exc()



    def login(self):
        """
        Inicia sesión en Instagram con las credenciales.
        """
        self.driver.get("https://www.instagram.com/")
        self._human_delay(3, 5)

        try:
            # Aceptar cookies
            allow_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Permitir')]")
            allow_btn.click()
            self._human_delay(1, 2)
        except:
            pass

        try:
            username_input = self.driver.find_element(By.NAME, "username")
            password_input = self.driver.find_element(By.NAME, "password")

            # Escribir usuario y contraseña
            username_input.send_keys(INSTA_USER)
            self._human_delay(0.5, 1.0)
            password_input.send_keys(INSTA_PASS)

            # Click en "Iniciar sesión"
            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()

            self._human_delay(5, 8)

            if "login" in self.driver.current_url:
                raise Exception("Error de autenticación (quizás 2FA o captcha).")
            else:
                print("[INFO] Login completado.")
        except Exception as e:
            print("[ERROR] en login:", e)
            traceback.print_exc()

    def _extract_postsV2(self):
        """
        Extrae los datos de los posts visibles.
        """
        posts_data = []
        posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")  # Encontrar posts por enlace

        for post in posts[:6]:  # Extraer los últimos 6 posts
            try:
                post_url = post.get_attribute("href")
                post.click()
                self._human_delay(3, 5)

                # Esperar que se cargue el post antes de extraer información
                try:
                    date_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "time"))
                    )
                    date_str = date_element.get_attribute("datetime") if date_element else "No disponible"
                except Exception:
                    print("⚠️ No se encontró la fecha, puede ser un video o un post especial.")
                    date_str = "No disponible"

                # Extraer información del post
                title = self._extract_text("//div[@role='dialog']//h1")  # Título del post
                likes = self._extract_text("//section//span[contains(text(), 'Me gusta')]/preceding-sibling::span")  # Likes
                comments = self._extract_text("//ul[contains(@class, 'XQXOT')]//span")  # Comentarios

                posts_data.append({
                    "title": title,
                    "date": date_str,
                    "url": post_url,
                    "likes": likes,
                    "comments": comments
                })

                print(f"✅ Post extraído: {post_url}")

                # Cerrar el post para continuar con el siguiente
                self._close_post()

            except Exception as e:
                print(f"❌ Error extrayendo post: {e}")

        return posts_data



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
            new_posts = self._extract_postsV2()
            if not new_posts:
                break

            for post in new_posts:
                try:
                    # Parsear fecha automáticamente
                    post_date = parser.parse(post['date'])  

                    if post_date.year < YEAR_FILTER:
                        return all_posts

                    post['date'] = post_date.strftime("%Y-%m-%d %H:%M:%S")  # Convertir a formato estándar
                    all_posts.append(post)

                except Exception as e:
                    print(f"⚠️ Error al convertir fecha: {post['date']} -> {e}")

            last_date = parser.parse(new_posts[-1]['date'])

        return all_posts

    

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
    
    def _extract_postsV2(self):
        """
        Extrae los datos de los posts visibles con manejo de clics bloqueados.
        """
        posts_data = []
        posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")  # Encontrar posts por enlace

        for post in posts[:6]:  # Extraer los últimos 6 posts
            try:
                post_url = post.get_attribute("href")

                # **Cerrar Popups antes de hacer clic**
                self._close_popups()

                # **Intentar hacer clic con scroll**
                if not self._click_with_scroll(post):
                    print(f"⚠️ No se pudo hacer clic en el post: {post_url}")
                    continue  # Pasar al siguiente post

                # **Esperar carga del post**
                self._human_delay(3, 5)

                # **Extraer información del post**
                date_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
                date_str = date_element.get_attribute("datetime") if date_element else "No disponible"

                title = self._extract_text("//div[@role='dialog']//h1")  # Título del post
                likes = self._extract_text("//section//span[contains(text(), 'Me gusta')]/preceding-sibling::span")  # Likes
                comments = self._extract_text("//ul[contains(@class, 'XQXOT')]//span")  # Comentarios

                posts_data.append({
                    "title": title,
                    "date": date_str,
                    "url": post_url,
                    "likes": likes,
                    "comments": comments
                })

                print(f"✅ Post extraído: {post_url}")

                # **Cerrar el post**
                self._close_post()

            except Exception as e:
                print(f"❌ Error extrayendo post: {e}")

        return posts_data


    
    

    
    
    # def save_to_dataframe(self, data):
    #     """ Guarda los datos en un DataFrame y muestra `.head()`. """
    #     if not data:
    #         print("⚠️ No hay datos extraídos.")
    #         return None

    #     df = pd.DataFrame(data)
    #     print("\n📊 **Vista previa de los datos extraídos:**")
    #     print(df.head())  # Mostrar primeras filas
    #     return df
    

    




# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    scraper = GoogleSearchBot()
    try:
        scraper.search_instagram()
        scraper.login_insta()
        for account in ACCOUNTS:
            print(f"\n[INFO] Scrapeando {account}")
            posts = scraper.scrape_profile(account)
            df = scraper.save_to_dataframe(posts)  # Guardar en DataFrame
            df = scraper.save_to_dataframe(posts, "instagram.csv")
    except Exception as e:
        print("[CRÍTICO] Error en la ejecución:", e)
        traceback.print_exc()
    finally:
        scraper.driver.quit()
        print("[INFO] Selenium cerrado.")
        # # 1) Login
        # scraper.login()

        # # 2) Recorrer cuentas
        # all_posts = []
        # for account in ACCOUNTS:
        #     print(f"\n[INFO] Scrapeando {account}")
        #     posts = scraper.scrape_profile(account)
        #     all_posts.extend(posts)
        #     print(f"[INFO] {account} => {len(posts)} posts extraídos")
        #     time.sleep(random.randint(5, 15))

        # # 3) Guardar en CSV
        # scraper.save_to_csv(all_posts, "instagram_posts_2024.csv")
        # print("\n[OK] Proceso completado.")

    # except Exception as e:
    #     print("[CRÍTICO] Error en la ejecución:", e)
    #     traceback.print_exc()
    # finally:
    #     scraper.driver.quit()
    #     print("[INFO] Selenium cerrado.")