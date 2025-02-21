import time
import random
import csv
import traceback
import pandas as pd
from fake_useragent import UserAgent
from datetime import datetime
import undetected_chromedriver as uc

from agents import agents
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

# Lista de cuentas a extraer
ACCOUNTS = [
 "universalmx"
]

# Año mínimo a filtrar
YEAR_FILTER = 2024
MAX_POSTS = 300  # Número máximo de posts a extraer

# =========================================================================
# CLASE SCRAPER
# =========================================================================
class InstagramScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de Bright Data.
        """
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
        return random.choice(agents)
        


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


    
    def _scroll_human(self):
        """
        Simula scroll humano en la página de perfil.
        """
        body = self.driver.find_element(By.TAG_NAME, "body")
        for _ in range(random.randint(3, 6)):
            body.send_keys(Keys.PAGE_DOWN)
            self._human_delay(1.5, 3.0)

#===========================================================================

#SUPPORT

#===========================================================================
    def scrape_profile(self, username):
        """Extrae posts del perfil de Instagram especificado."""
        print(f"\n🔍 [INFO] Abriendo perfil de {username}...")
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(3, 5)
        self._human_delay(2, 4)

        # Intentar abrir el primer post
        if not self._open_first_post():
            print(f"⚠️ [WARNING] No se pudo abrir el primer post de {username}. Saliendo...")
            return []

        self._human_delay(3, 5)

        posts_data = []
        for i in range(MAX_POSTS):
            try:
                print(f"\n📸 [INFO] Extrayendo post {i+1}/{MAX_POSTS}")
                post_data = self._extract_post_data()

                if post_data:
                    posts_data.append(post_data)
                else:
                    print(f"⚠️ [WARNING] No se pudo extraer datos del post {i+1}. Intentando siguiente...")

                # Intentar ir al siguiente post
                if not self._click_next_post():
                    print("⚠️ [INFO] No hay más posts disponibles o no se pudo hacer clic en 'Next'. Terminando extracción.")
                    break  # Salimos del loop si no hay más posts

            except Exception as e:
                print(f"❌ [ERROR] Ocurrió un problema con el post {i+1}: {e}")
                traceback.print_exc()  # Muestra el error completo para depuración

        print(f"\n✅ [INFO] Extracción completada: {len(posts_data)} posts obtenidos de {username}.")
        return posts_data


    def _open_first_post(self):
        """Abre el primer post en el perfil, asegurando que pertenece a la cuenta deseada."""
        self._human_delay(2, 4)
        try:
            # Esperar a que el primer post con href="/universalmx/..." sea clickeable
            first_post = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@style, 'display: flex; flex-direction: column;')]//a[starts-with(@href, '/universalmx/')][1]")
                )
            )

            # Hacer clic en el post
            self.driver.execute_script("arguments[0].click();", first_post)
            self._human_delay(2, 4)
            print("✅ Primer post abierto con éxito.")
            return True

        except Exception as e:
            print("[ERROR] No se pudo abrir el primer post:", e)
            self.driver.save_screenshot("error_screenshot.png")  # Guardar una captura de pantalla
            print("[INFO] Captura de pantalla guardada como error_screenshot.png")
            return False



    def _extract_post_data(self):
        """Extrae datos del post abierto en el modal."""

        try:
            post_url = self.driver.current_url

            # Extraer número de likes
            try:
                likes_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'liked_by')]/span/span")
                likes = likes_element.text.replace(",", "").strip()  # Eliminar comas y espacios
            except:
                likes = "No disponible"

            # Extraer fecha del post
            try:
                date_element = self.driver.find_element(By.TAG_NAME, "time")
                post_date = date_element.get_attribute("datetime")
            except:
                post_date = "No disponible"

            # Extraer comentarios
            comments = self._extract_comments()

            print(f"✅ Post extraído: {post_url} | Likes: {likes} | Fecha: {post_date}")

            return {
                "url_post": post_url,
                "likes": likes,
                "fecha_post": post_date,
                "comentarios": comments
            }

        except Exception as e:
            print("[ERROR] No se pudo extraer datos del post:", e)
            return None


    def _extract_comments(self):
        """Extrae hasta 10 comentarios del post y maneja imágenes/GIFs."""
        comments_data = []
        
        try:
            # Encontrar todos los comentarios dentro del post (limitado a 10)
            comment_elements = self.driver.find_elements(By.XPATH, "//ul[contains(@class, '_a9z6')]//li[contains(@class, '_a9zj')]")[:10]

            for comment in comment_elements:
                try:
                    # Extraer el nombre de usuario
                    username = comment.find_element(By.XPATH, ".//a").text

                    # Intentar extraer el texto del comentario
                    try:
                        comment_text = comment.find_element(By.XPATH, ".//span[contains(@class, '_ap3a')]").text
                    except:
                        comment_text = None  # Si no se encuentra texto, asumimos que puede ser una imagen/GIF

                    # Verificar si hay imagen en el comentario
                    has_image = comment.find_elements(By.XPATH, ".//img")

                    if comment_text:
                        comments_data.append({username: comment_text})
                    elif has_image:
                        comments_data.append({username: "image"})
                    else:
                        comments_data.append({username: "unknown"})  # En caso de que no detecte ni texto ni imagen

                except Exception as e:
                    print(f"⚠️ Error extrayendo un comentario: {e}")
                    continue  # Saltar al siguiente comentario si hay error

        except Exception as e:
            print(f"⚠️ No se pudieron extraer comentarios: {e}")

        return comments_data




    def _click_next_post(self):
        """Hace clic en el botón 'Next' del modal para avanzar al siguiente post."""
        try:
            # Esperar a que el botón Next esté visible y clickeable
            next_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Next')]"))
            )
            
            # Verificar si el botón está realmente visible
            if next_button.is_displayed():
                print("➡️ Botón Next detectado, intentando hacer clic...")

                # Mover el mouse al botón para simular un comportamiento humano
                self.action.move_to_element(next_button).perform()
                time.sleep(1)

                # Hacer clic en el botón Next
                self.driver.execute_script("arguments[0].click();", next_button)
                self._human_delay(3, 5)

                print("✅ Avanzando al siguiente post...")
                return True
            else:
                print("⚠️ El botón Next está presente pero no visible.")
                return False

        except Exception as e:
            print("⚠️ No hay más posts disponibles o no se pudo hacer clic en 'Next'.", e)
            return False



        
        
    def save_to_csv(self, data, filename):
        """Guarda los datos extraídos en un archivo CSV y muestra el DataFrame antes."""
        if not data:
            print("⚠️ No hay datos para guardar.")
            return
        
        # Convertir los datos en un DataFrame
        df = pd.DataFrame(data)
        
        # Mostrar el DataFrame visualmente antes de guardarlo
        
        print("\n📊 [INFO] DataFrame generado:")
        print(df.head(20))  # Mostrar los primeros 20 registros

        # Guardar en CSV
        df.to_csv(filename, index=False, encoding='utf-8')
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


