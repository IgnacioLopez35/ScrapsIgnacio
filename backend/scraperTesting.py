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
from selenium.common.exceptions import NoSuchElementException
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
 "warnerbrosmx"
]
ACCOUNT = "warnerbrosmx"

# Año mínimo a filtrar
YEAR_FILTER = 2024
MAX_POSTS = 5 # Número máximo de pocleasts a extraer
NUM_SCROLLS=5

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
        PROXY_PORT = "1005"
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
        # Opciones del navegador Chrome
        options = uc.ChromeOptions()
        
        # 🔒 Evita que los sitios detecten Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")

        # ⚡ Optimiza el rendimiento en servidores sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🖥️ Simula navegación real en una ventana maximizada
        #options.add_argument("--start-maximized")
        # 🚀 Modo headless (sin interfaz gráfica)
        options.add_argument("--headless=new")

        # 🔕 Evita notificaciones emergentes y bloqueos de pop-ups
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # 🔄 Cambia dinámicamente el User-Agent para evitar detección
        options.add_argument(f"--user-agent={self._random_user_agent()}")

        # 🔍 Evita filtración de IP real cuando se usan proxies
        options.add_argument("--disable-webrtc")

        # 🚀 Inicializa el navegador con opciones anti-detección
        driver = uc.Chrome(options=options, use_subprocess=True)


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
            self._human_delay(3.5, 6.7)
    
    def _scroll_n_times(self, times=10, pause_every=30):
        """
        Realiza scroll hacia abajo un número específico de veces en la página de perfil.
        Si `times` es 0, la función simplemente pasa.
        """
        if times <= 0:
            print("🔕 [INFO] Skipping scrolling as times is set to 0.")
            return 
        body = self.driver.find_element(By.TAG_NAME, "body")
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            body.send_keys(Keys.PAGE_DOWN)
            self._human_delay(3.5, 6.7)  # Simular pausa humana

            # Si el número de scrolls alcanza el umbral, hacer una pausa larga
            if i % pause_every == 0:
                pause_time = random.uniform(60, 150)  # Entre 1 min (60s) y 2.5 min (150s)
                print(f"⏸️ [INFO] Pausa larga de {pause_time:.2f} segundos después de {i} scrolls...")
                time.sleep(pause_time)

#===========================================================================

#SUPPORT

#===========================================================================
    def scrape_profile(self, username):
        """Extrae posts del perfil de Instagram especificado."""
        print(f"\n🔍 [INFO] Abriendo perfil de {username}...")
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(3.1, 5.9)
        self._human_delay(1.9, 3.9)

        self._scroll_n_times(NUM_SCROLLS,37)

        # Intentar abrir el primer post
        if not self._click_last_post():
            print(f"⚠️ [WARNING] No se pudo abrir el ultimo post de {username}. Saliendo...")
            return []

        self._human_delay(2.9, 4.9)

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
        
    def _click_last_post(self):
        """
        Busca y hace clic en el último post visible con:
        - Un <a> cuyo href contenga 'universalmx/'
        - Un <div> con 'padding-bottom: 133.'
        """
        self._human_delay(2.2, 4.7)
        try:
            # Encuentra todos los elementos <a> que contienen 'universalmx/' en su href
            posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'universalmx/') and descendant::div[contains(@style, 'padding-bottom: 133.')]]")

            if not posts:
                print("⚠️ No se encontraron posts con los criterios especificados después del scroll.")
                return False

            # Seleccionar el último post de la lista
            last_post = posts[-1]

            # Asegurar que el post es visible antes de hacer clic
            self.driver.execute_script("arguments[0].scrollIntoView();", last_post)
            self._human_delay(1, 2)
            self.driver.execute_script("arguments[0].click();", last_post)  # Clic usando JavaScript
            self._human_delay(2.3, 4.8)
            print("✅ Último post del renglón abierto con éxito.")
            return True

        except Exception as e:
            print("[ERROR] No se pudo abrir el último post visible después del scroll:", e)
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

            # Extraer comment del autor
            author_comment = self._author_comment()
            # Extraer comentarios
            comments = self._extract_commentsV2()

            print(f"✅ Post extraído: {post_url} | Likes: {likes} | Fecha: {post_date}")

            return {
                "url_post": post_url,
                "author_comment": author_comment,
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
    
    #===========================================================================================
    def _extract_commentsV2(self):
        """Extrae hasta 20 comentarios del post y maneja imágenes/GIFs."""
        comments_data = {}
        
        try:
            # Encontrar todos los comentarios dentro del post (limitado a 20)
            comment_elements = self.driver.find_elements(By.XPATH, "//ul//li[descendant::time]")[:20]


            for comment in comment_elements:
                try:
                    # Extraer el nombre de usuario buscando el enlace dentro del comentario
                    try:
                        username = comment.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]").get_attribute("alt").replace("'s profile picture", "")
                    except NoSuchElementException:
                        username = "unknown"

                    # Intentar extraer el texto del comentario
                    try:
                        comment_text = comment.find_element(By.XPATH, ".//h3/following-sibling::div//span").text
                    except NoSuchElementException:
                        comment_text = None  # Puede ser una imagen/GIF

                    # Extraer la fecha del comentario buscando el elemento <time>
                    try:
                        date = comment.find_element(By.XPATH, ".//time").get_attribute("datetime")
                    except NoSuchElementException:
                        date = None  # Si no se encuentra la fecha

                    # Extraer número de likes buscando botones con texto "likes"
                    try:
                        likes = comment.find_element(By.XPATH, ".//button/span[contains(text(), 'like')]").text
                    except NoSuchElementException:
                        likes = "0 likes"  # Si no tiene likes visibles

                    # Verificar si el comentario tiene una imagen/GIF en lugar de texto
                    try:
                        image_element = comment.find_elements(By.XPATH, ".//img[not(contains(@alt, ' profile picture'))]")
                        image_url = image_element[0].get_attribute("src") if image_element else None
                    except NoSuchElementException:
                        image_url = None

                    # Guardar los datos correctamente
                    if comment_text:
                        comments_data[username] = (comment_text, date, likes)
                    elif image_url:
                        comments_data[username] = ("image/GIF", image_url, date, likes)
                    else:
                        comments_data[username] = ("unknown", date, likes)  # Si no tiene texto ni imagen

                except Exception as e:
                    print(f"⚠️ Error extrayendo un comentario: {e}")
                    continue  # Saltar al siguiente comentario en caso de error

        except Exception as e:
            print(f"⚠️ No se pudieron extraer comentarios: {e}")

        return comments_data
    



    def _author_comment(self):
        """Extrae el comentario del autor del post en Instagram."""
        try:
            # Buscar el primer comentario dentro del post (usualmente el del autor)
            author_comment_element = self.driver.find_element(By.XPATH, "//ul//li[descendant::h1]")

            # Extraer el nombre del usuario usando la imagen con alt="profile picture"
            try:
                username = author_comment_element.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]").get_attribute("alt").replace("'s profile picture", "")
            except NoSuchElementException:
                username = "unknown"

            # Extraer el texto completo del comentario
            comment_text = author_comment_element.find_element(By.XPATH, ".//h1").text

            # Extraer hashtags (#)
            hashtags = [tag.text for tag in author_comment_element.find_elements(By.XPATH, ".//a[contains(@href, '/explore/tags/')]")]

            # Extraer menciones (@)
            mentions = [mention.text for mention in author_comment_element.find_elements(By.XPATH, ".//a") if '@' in mention.text]

            return {
                "author": username,
                "comment": comment_text,
                "hashtags": hashtags,
                "mentions": mentions
            }

        except NoSuchElementException:
            print("⚠️ No se encontró comentario del autor.")
            return None


    #===========================================================================================




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
        

    def _click_previous_post(self):
        """Hace clic en el botón 'Go back' del modal para avanzar al siguiente post."""
        try:
            # Esperar a que el botón Go back esté visible y clickeable
            go_back_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Go back')]"))
            )
            
            # Verificar si el botón está realmente visible
            if go_back_button.is_displayed():
                print("➡️ Botón Go back detectado, intentando hacer clic...")

                # Mover el mouse al botón para simular un comportamiento humano
                self.action.move_to_element(go_back_button).perform()
                time.sleep(1)

                # Hacer clic en el botón Go back
                self.driver.execute_script("arguments[0].click();", go_back_button)
                self._human_delay(3.2, 5.9)

                print("✅ Avanzando al siguiente post...")
                return True
            else:
                print("⚠️ El botón Go back está presente pero no visible.")
                return False

        except Exception as e:
            print("⚠️ No hay más posts disponibles o no se pudo hacer clic en 'Go back'.", e)
            return False



        
        
    def save_to_csv(self, data, account):
        """Guarda los datos extraídos en un archivo CSV con formato 'instagram_posts_{ACCOUNT}_DD_MM_YYYY.csv'."""
        if not data:
            print("⚠️ No hay datos para guardar.")
            return

        df = pd.DataFrame(data)
        date_str = datetime.now().strftime("%d_%m_%Y")
        filename = f"instagram_posts_{account}_{date_str}.csv"

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

        # 2) RComienza el scraper
        
        print(f"\n[INFO] Scrapeando {ACCOUNT}")
        posts = scraper.scrape_profile(ACCOUNT)

        print(f"[INFO] {ACCOUNT} => {len(posts)} posts extraídos")

        # 3) Guardar en CSV
        scraper.save_to_csv(posts, ACCOUNT)
        print("\n[OK] Proceso completado.")

    except Exception as e:
        print("[CRÍTICO] Error en la ejecución:", e)
        traceback.print_exc()
    finally:
        scraper.driver.quit()
        print("[INFO] Selenium cerrado.")


