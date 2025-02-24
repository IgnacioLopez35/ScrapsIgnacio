import time
import random
import csv
import json
import os
from pathlib import Path
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
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.folder_path = Path(datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))
        self.folder_path.mkdir(parents=True, exist_ok=True)

        # Lista para almacenar datos extraídos
        self.data = []

    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de Bright Data.
        """
        # Configuración de Proxy Smartproxy
        PROXY_HOST = "gate.smartproxy.com"
        PROXY_PORT = "1009"
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
            print("⚠️ No estamos en la página de login de Instagram. Verifica la navegación, utilizando otro metodo.")
            self.login()
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
            allow_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Allow')]")
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

    def _human_delay(self, min_s=1.0, max_s=3.0):
        """
        Pausa aleatoria entre acciones para simular comportamiento humano.
        """
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        time.sleep(total)

   

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

    def scrape_posts(self, profile_url, max_posts=20):
        self.driver.get(profile_url)
        self._human_delay(3, 5)

        posts = self.driver.find_elements(By.XPATH, "//article//a[contains(@href, '/p/')]")
        if not posts:
            print("No se encontraron posts.")
            return

        for i, post in enumerate(posts[:max_posts], start=1):
            try:
                # Capturar pantalla del post antes de hacer clic
                img_path = str(self.folder_path / f"{i}.png")
                post.screenshot(img_path)
                print(f"📸 Captura guardada: {img_path}")

                # Obtener URL del post
                post_url = post.get_attribute("href")
                self._human_delay(1, 4)

                # Hacer clic en el post
                self.driver.execute_script("arguments[0].click();", post)
                self._human_delay(1, 4)

                # Extraer datos del post
                post_data = self._extract_post_data(post_url, f"{i}.png")
                if post_data:
                    self.data.append(post_data)

                # Cerrar modal
                self._close_post()

            except Exception as e:
                print(f"❌ Error extrayendo post {i}: {e}")


    def _extract_post_data(self, post_url, image_name):
        try:
            # Extraer fecha del post
            date_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "time"))
            )
            post_date = date_element.get_attribute("datetime")

            # Extraer número de likes
            try:
                likes_element = self.driver.find_element(By.XPATH, "//section//span[contains(text(), 'Like')]/preceding-sibling::span")
                likes = likes_element.text.replace(",", "")
            except:
                likes = "No disponible"

            # Extraer comentarios
            comments = self._extract_comments()

            # Guardar datos en formato de diccionario
            return {
                "url_post": post_url,
                "fecha_ejecucion": self.timestamp,
                "nombre_imagen": image_name,
                "likes": likes,
                "fecha_post": post_date,
                "comentarios": json.dumps(comments, ensure_ascii=False)
            }
        except Exception as e:
            print(f"❌ Error extrayendo datos del post: {e}")
            return None
        
    def _extract_comments(self):
        """ Extrae hasta 10 comentarios en formato JSON """
        comments_data = {}
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//ul[contains(@class, 'XQXOT')]//li")[:10]
            for comment in comment_elements:
                try:
                    username = comment.find_element(By.XPATH, ".//h3").text
                    comment_text = comment.find_element(By.XPATH, ".//span").text
                    comments_data[username] = comment_text
                except:
                    comments_data[username] = "image"
        except:
            pass
        return comments_data
    
    def _close_post(self):
        """ Cierra el modal del post """
        try:
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE).perform()
            self._human_delay(3, 5)
        except:
            print("⚠️ No se pudo cerrar el post.")

    def save_to_dataframe(self):
        """ Guarda los datos en un DataFrame y en CSV """
        if not self.data:
            print("⚠️ No hay datos extraídos.")
            return None

        df = pd.DataFrame(self.data)
        df.to_csv(str(self.folder_path / "instagram.csv"), index=False, encoding="utf-8")
        print(f"📊 Datos guardados en {self.folder_path}/instagram.csv")
        return df
    

    




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
            profile_url = f"https://www.instagram.com/{account}/"
            scraper.scrape_posts(profile_url, max_posts=20)
        
        # Guardar datos en DataFrame y CSV
        df = scraper.save_to_dataframe()
    
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