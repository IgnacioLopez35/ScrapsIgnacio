import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

# Add the project root to the Python path so Python can find the modules directory
sys.path.append(project_root)

# Now you can import from modules
from agents import agents
import time
import random
import csv
import traceback
import pandas as pd
from fake_useragent import UserAgent
from datetime import datetime
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================

# Credenciales de Instagram *incrustadas* directamente
INSTA_USER = "ignacio.lopez@wivboost.com"
INSTA_PASS = "buenosdiasAlegria777"

# Lista de cuentas a extraer
ACCOUNTS = [
 "platacard"
]
ACCOUNT = "platacard"

# Año mínimo a filtrar
YEAR_FILTER = 2025
MAX_POSTS = 11 # Número máximo de pocleasts a extraer
NUM_SCROLLS = 10  # Aumentado el número de scrolls

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
        
        # Configuración del navegador Chrome
        options = uc.ChromeOptions()
        
        # 🔒 Evita que los sitios detecten Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")

        # ⚡ Optimiza el rendimiento en servidores sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🖥️ Simula navegación real en una ventana maximizada
        options.add_argument("--start-maximized")
        
        # NO USAR HEADLESS MODE - Esta era la línea problemática
        #options.add_argument("--headless=new")

        # 🔕 Evita notificaciones emergentes y bloqueos de pop-ups
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # 🔄 Cambia dinámicamente el User-Agent para evitar detección
        options.add_argument(f"--user-agent={self._random_user_agent()}")

        # 🔍 Evita filtración de IP real cuando se usan proxies
        options.add_argument("--disable-webrtc")
        
        # Añadir opciones para mejorar la carga de imágenes
        options.add_argument('--blink-settings=imagesEnabled=true')
        options.add_argument('--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies')

        # 🚀 Inicializa el navegador con opciones anti-detección
        # Solución: usar una versión más simple de inicialización que no use subprocess
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
        print("[INFO] Iniciando proceso de login...")
        self.driver.get("https://www.instagram.com/")
        self._human_delay(5, 8)  # Aumentado tiempo de espera inicial

        try:
            # Aceptar cookies (múltiples intentos con diferentes textos)
            cookie_buttons = [
                "//button[contains(., 'Permitir')]", 
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Allow')]",
                "//button[contains(., 'Aceptar')]"
            ]
            
            for btn_xpath in cookie_buttons:
                try:
                    allow_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, btn_xpath))
                    )
                    allow_btn.click()
                    self._human_delay(1, 2)
                    print("[INFO] Cookies aceptadas.")
                    break
                except:
                    continue
                    
        except:
            print("[INFO] No se detectó diálogo de cookies o ya fueron aceptadas.")

        # Tomar captura de pantalla de la página de login
        print("[INFO] Tomando captura de la página de login...")
        self.driver.save_screenshot("login_page.png")

        try:
            # Esperar a que los campos de login estén disponibles
            print("[INFO] Buscando campos de login...")
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_input = self.driver.find_element(By.NAME, "password")

            print("[INFO] Campos de login encontrados, ingresando credenciales...")
            # Escribir usuario y contraseña simulando entrada humana
            for char in INSTA_USER:
                username_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            self._human_delay(0.5, 1.0)
            
            for char in INSTA_PASS:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            # Click en "Iniciar sesión"
            print("[INFO] Buscando botón de login...")
            login_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            print("[INFO] Haciendo clic en botón de login...")
            login_btn.click()

            # Esperar más tiempo para el login
            print("[INFO] Esperando el proceso de login...")
            self._human_delay(8, 12)
            
            # Tomar captura después del clic en login
            self.driver.save_screenshot("after_login_click.png")
            
            # Verificar si hay diálogos adicionales post-login y manejarlos
            try:
                # Botón "Not Now" para guardar información
                print("[INFO] Buscando diálogos post-login...")
                not_now_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                print("[INFO] Encontrado diálogo 'Not Now', haciendo clic...")
                not_now_btn.click()
                self._human_delay(2, 3)
            except:
                print("[INFO] No se encontró diálogo 'Not Now' para guardar info.")
                
            try:
                # Botón "Not Now" para notificaciones
                not_now_notif = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                print("[INFO] Encontrado diálogo de notificaciones, haciendo clic en 'Not Now'...")
                not_now_notif.click()
                self._human_delay(2, 3)
            except:
                print("[INFO] No se encontró diálogo de notificaciones.")

            # Verificar si el login fue exitoso
            if "login" in self.driver.current_url:
                print("[ERROR] La URL sigue conteniendo 'login', posible error de autenticación.")
                self.driver.save_screenshot("login_error.png")
                raise Exception("Error de autenticación (quizás 2FA o captcha).")
            else:
                print("[INFO] Login completado correctamente.")
                self.driver.save_screenshot("login_successful.png")
        except Exception as e:
            print("[ERROR] en login:", e)
            self.driver.save_screenshot("login_error.png")
            traceback.print_exc()
            raise  # Relanzamos la excepción para que se maneje en el bloque principal

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
            
        # Esperamos a que cargue la página antes de scrollear
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            print("[INFO] Página cargada, comenzando scrolls...")
        except TimeoutException:
            print("[WARNING] No se pudo detectar el elemento 'article', pero continuamos con el scroll...")
        
        # Tomar captura de la página antes de scrollear
        self.driver.save_screenshot("before_scroll.png")
        print("[INFO] Captura guardada como before_scroll.png")
        
        # Verificar si hay posts visibles
        posts_before = self.driver.find_elements(By.XPATH, "//article//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        print(f"[INFO] Posts visibles antes de scroll: {len(posts_before)}")
        
        body = self.driver.find_element(By.TAG_NAME, "body")
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            # Usar JavaScript para scrollear más efectivamente
            self.driver.execute_script("window.scrollBy(0, 1000);")
            self._human_delay(4.5, 7.7)  # Aumentado el tiempo de espera
            
            # Cada 3 scrolls, esperamos más tiempo para que cargue el contenido
            if i % 3 == 0:
                print("[INFO] Pausa extendida para carga de contenido...")
                time.sleep(random.uniform(8, 12))
                # Tomar una captura intermedia
                self.driver.save_screenshot(f"scroll_{i}.png")

            # Si el número de scrolls alcanza el umbral, hacer una pausa larga
            if i % pause_every == 0:
                pause_time = random.uniform(60, 150)  # Entre 1 min (60s) y 2.5 min (150s)
                print(f"⏸️ [INFO] Pausa larga de {pause_time:.2f} segundos después de {i} scrolls...")
                time.sleep(pause_time)
        
        # Tomar captura de la página después de scrollear
        self.driver.save_screenshot("after_scroll.png")
        print("[INFO] Captura guardada como after_scroll.png")
        
        # Verificar posts después de scrollear
        posts_after = self.driver.find_elements(By.XPATH, "//article//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        print(f"[INFO] Posts visibles después de scroll: {len(posts_after)}")
        
        # Verificar si hay algún elemento que podríamos hacer clic
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"[INFO] Total de enlaces en la página: {len(all_links)}")
        
        # Mostrar algunos de los enlaces encontrados para diagnóstico
        href_count = 0
        for link in all_links[:20]:  # Limitamos a los primeros 20 para no saturar la consola
            try:
                href = link.get_attribute("href")
                if href and ("/p/" in href or "/reel/" in href):
                    print(f"[DEBUG] Enlace potencial: {href}")
                    href_count += 1
            except:
                pass
        
        print(f"[INFO] Enlaces con '/p/' o '/reel/': {href_count}")

    def scrape_profile(self, username):
        """Extrae posts del perfil de Instagram especificado."""
        print(f"\n🔍 [INFO] Abriendo perfil de {username}...")
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(5, 8)  # Aumentado tiempo de espera
        
        # Verificar que la página cargó correctamente
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("[INFO] Página de perfil cargada.")
            self.driver.save_screenshot("profile_loaded.png")
            
            # Mostrar título y URL para diagnóstico
            page_title = self.driver.title
            page_url = self.driver.current_url
            print(f"[INFO] Título de la página: {page_title}")
            print(f"[INFO] URL actual: {page_url}")
            
            # Ver el HTML para diagnóstico
            page_source = self.driver.page_source[:500]  # Primeros 500 caracteres
            print(f"[DEBUG] Muestra del HTML: {page_source}...")
            
        except TimeoutException:
            print("[ERROR] No se pudo cargar el perfil correctamente.")
            self.driver.save_screenshot("profile_error.png")
            return []
            
        # Verificar si la cuenta es privada
        try:
            private_text = self.driver.find_element(By.XPATH, "//*[contains(text(), 'This Account is Private') or contains(text(), 'Esta cuenta es privada')]")
            print(f"⚠️ [WARNING] La cuenta {username} es privada. No se pueden extraer posts.")
            self.driver.save_screenshot("private_account.png")
            return []
        except NoSuchElementException:
            print(f"[INFO] La cuenta {username} parece ser pública.")
            
        # Realizar scrolls para cargar más posts
        self._scroll_n_times(NUM_SCROLLS, 37)

        # Intentar abrir el primer post con selector mejorado
        if not self._click_first_post_improved():
            print(f"⚠️ [WARNING] No se pudo abrir el primer post de {username}. Saliendo...")
            return []

        self._human_delay(2.9, 4.9)

        posts_data = []
        for i in range(MAX_POSTS):
            try:
                print(f"\n📸 [INFO] Extrayendo post {i+1}/{MAX_POSTS}")
                post_data = self._extract_post_data()

                if post_data:
                    posts_data.append(post_data)
                    print(f"✅ Post {i+1} extraído con éxito.")
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

    def _click_first_post_improved(self):
        """Método mejorado para detectar y hacer clic en el primer post."""
        self._human_delay(2, 4)
        
        # Guardar captura antes de buscar posts
        self.driver.save_screenshot("before_click_post.png")
        print("[INFO] Captura guardada como before_click_post.png")
        
        try:
            # Múltiples selectores para encontrar posts en diferentes estructuras de Instagram
            selectors = [
                # 1. Selector general para posts en el feed (puede capturar posts, reels, y videos)
                "//article//a[contains(@href, '/p/') or contains(@href, '/reel/') or contains(@href, '/tv/')]",
                
                # 2. Selector específico para la cuadrícula de perfil
                "//div[contains(@role, 'presentation')]//a[contains(@href, '/p/')]",
                
                # 3. Selector alternativo para la estructura más reciente
                "//main//article//a[contains(@href, '/p/')]",
                
                # 4. Selector muy general (último recurso)
                "//a[contains(@href, '/p/')]"
            ]
            
            for selector in selectors:
                posts = self.driver.find_elements(By.XPATH, selector)
                print(f"[DEBUG] Selector '{selector}': encontrados {len(posts)} posts.")
                
                if posts:
                    # Encontramos posts, intentamos hacer clic en el primero
                    first_post = posts[0]
                    
                    # Asegurarnos que el post es visible
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_post)
                    self._human_delay(2, 3)
                    
                    # Imprimir el href para diagnóstico
                    post_href = first_post.get_attribute("href")
                    print(f"[DEBUG] Intentando hacer clic en post con href: {post_href}")
                    
                    # Intentar hacer clic de varias maneras
                    try:
                        # 1. Clic normal
                        first_post.click()
                        print("[DEBUG] Clic normal exitoso")
                    except Exception as e1:
                        print(f"[DEBUG] Clic normal falló: {e1}")
                        try:
                            # 2. Clic con JavaScript
                            self.driver.execute_script("arguments[0].click();", first_post)
                            print("[DEBUG] Clic con JS exitoso")
                        except Exception as e2:
                            print(f"[DEBUG] Clic con JS falló: {e2}")
                            try:
                                # 3. Clic con ActionChains
                                ActionChains(self.driver).move_to_element(first_post).click().perform()
                                print("[DEBUG] Clic con ActionChains exitoso")
                            except Exception as e3:
                                print(f"[DEBUG] Clic con ActionChains falló: {e3}")
                                continue  # Probar siguiente selector
                    
                    # Verificar si se abrió el modal del post
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//time"))
                        )
                        print("✅ Primer post abierto con éxito.")
                        self.driver.save_screenshot("post_opened.png")
                        return True
                    except:
                        print("[DEBUG] El post parece no haberse abierto correctamente. Intentando siguiente selector.")
                        continue
            
            # Intento alternativo - navegar directamente a un post
            print("[INFO] Intentando método alternativo - navegar directamente a un post...")
            try:
                # Buscar cualquier enlace que tenga /p/ y abrir directamente
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
                if links:
                    post_url = links[0].get_attribute("href")
                    print(f"[INFO] Navegando directamente a: {post_url}")
                    self.driver.get(post_url)
                    self._human_delay(3, 5)
                    self.driver.save_screenshot("direct_navigation.png")
                    
                    # Verificar si estamos en un post
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//time"))
                        )
                        print("✅ Navegación directa al post exitosa.")
                        return True
                    except:
                        print("[ERROR] La navegación directa no muestra un post válido.")
                        return False
                else:
                    print("[ERROR] No se encontraron enlaces a posts.")
                    return False
            except Exception as e:
                print(f"[ERROR] Error en navegación directa: {e}")
                return False
            
            # Si llegamos aquí, ninguno de los selectores funcionó
            print("❌ [ERROR] No se pudo abrir ningún post tras probar múltiples selectores.")
            return False

        except Exception as e:
            print(f"[ERROR] Error al intentar abrir el primer post: {e}")
            self.driver.save_screenshot("post_click_error.png")
            traceback.print_exc()
            return False

    def _extract_post_data(self):
        """Extrae datos del post abierto en el modal."""
        try:
            # Verificar que estamos en un post
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//time"))
                )
            except TimeoutException:
                print("[ERROR] No se detectó un post abierto. Tomando captura...")
                self.driver.save_screenshot("post_detection_error.png")
                return None

            post_url = self.driver.current_url
            print(f"[INFO] URL del post: {post_url}")

            # Extraer número de likes - varios selectores posibles
            try:
                like_selectors = [
                    "//section//a[contains(@href, 'liked_by')]/span",
                    "//section//a[contains(@href, 'liked_by')]",
                    "//span[contains(text(), 'likes')]",
                    "//span[contains(text(), 'Like')]"
                ]
                
                likes = "No disponible"
                for selector in like_selectors:
                    try:
                        likes_element = self.driver.find_element(By.XPATH, selector)
                        likes = likes_element.text.replace(",", "").strip()
                        if likes:
                            break
                    except:
                        continue
            except:
                likes = "No disponible"

            # Extraer fecha del post
            try:
                date_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
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
            print(f"[ERROR] No se pudo extraer datos del post: {e}")
            self.driver.save_screenshot("post_extraction_error.png")
            traceback.print_exc()
            return None

    def _extract_commentsV2(self):
        """Extrae hasta 20 comentarios del post y maneja imágenes/GIFs."""
        comments_data = {}
        
        try:
            # Encontrar todos los comentarios dentro del post (limitado a 20)
            comment_elements = self.driver.find_elements(By.XPATH, "//ul//li[descendant::time]")[:20]
            
            if not comment_elements:
                print("[INFO] No se encontraron comentarios con el selector principal. Probando alternativo...")
                # Selector alternativo
                comment_elements = self.driver.find_elements(By.XPATH, "//ul//div[contains(@class, 'comment')]")[:20]

            print(f"[INFO] Encontrados {len(comment_elements)} comentarios.")

            for comment in comment_elements:
                try:
                    # Extraer el nombre de usuario - múltiples intentos
                    username = "unknown"
                    try:
                        username = comment.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]").get_attribute("alt").replace("'s profile picture", "")
                    except NoSuchElementException:
                        try:
                            username = comment.find_element(By.XPATH, ".//a").text
                        except:
                            pass

                    # Intentar extraer el texto del comentario - múltiples intentos
                    comment_text = None
                    try:
                        comment_text = comment.find_element(By.XPATH, ".//h3/following-sibling::div//span").text
                    except NoSuchElementException:
                        try:
                            comment_text = comment.find_element(By.XPATH, ".//span[not(contains(@class, 'timestamp'))]").text
                        except:
                            pass

                    # Extraer la fecha del comentario
                    date = None
                    try:
                        date = comment.find_element(By.XPATH, ".//time").get_attribute("datetime")
                    except:
                        pass

                    # Extraer número de likes
                    likes = "0 likes"
                    try:
                        likes = comment.find_element(By.XPATH, ".//button/span[contains(text(), 'like')]").text
                    except:
                        pass

                    # Verificar si hay imagen en el comentario
                    image_url = None
                    try:
                        image_elements = comment.find_elements(By.XPATH, ".//img[not(contains(@alt, ' profile picture'))]")
                        if image_elements:
                            image_url = image_elements[0].get_attribute("src")
                    except:
                        pass

                    # Guardar los datos
                    if comment_text:
                        comments_data[username] = (comment_text, date, likes)
                    elif image_url:
                        comments_data[username] = ("image/GIF", image_url, date, likes)
                    else:
                        comments_data[username] = ("unknown", date, likes)

                except Exception as e:
                    print(f"⚠️ Error extrayendo un comentario: {e}")
                    continue

        except Exception as e:
            print(f"⚠️ No se pudieron extraer comentarios: {e}")
            traceback.print_exc()

        return comments_data

    def _author_comment(self):
        """Extrae el comentario del autor del post en Instagram."""
        try:
            # Múltiples selectores para encontrar el comentario del autor
            author_selectors = [
                "//ul//li[descendant::h1]",
                "//article//h1",
                "//div[@role='dialog']//div[contains(@class, 'caption')]",
                "//div[contains(@class, 'comment')]//div[contains(@class, 'owner')]"
            ]
            
            for selector in author_selectors:
                try:
                    author_comment_element = self.driver.find_element(By.XPATH, selector)
                    
                    # Extraer nombre de usuario
                    username = "unknown"
                    try:
                        username_element = author_comment_element.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]")
                        username = username_element.get_attribute("alt").replace("'s profile picture", "")
                    except:
                        try:
                            username_element = author_comment_element.find_element(By.XPATH, ".//a")
                            username = username_element.text
                        except:
                            pass
                    
                    # Extraer texto del comentario
                    comment_text = "No disponible"
                    try:
                        comment_text = author_comment_element.find_element(By.XPATH, ".//h1").text
                    except:
                        try:
                            comment_text = author_comment_element.find_element(By.XPATH, ".//span").text
                        except:
                            pass
                    
                    # Extraer hashtags
                    hashtags = []
                    try:
                        hashtags = [tag.text for tag in author_comment_element.find_elements(By.XPATH, ".//a[contains(@href, '/explore/tags/')]")]
                    except:
                        pass
                    
                    # Extraer menciones
                    mentions = []
                    try:
                        mentions = [mention.text for mention in author_comment_element.find_elements(By.XPATH, ".//a") if '@' in mention.text]
                    except:
                        pass
                    
                    return {
                        "author": username,
                        "comment": comment_text,
                        "hashtags": hashtags,
                        "mentions": mentions
                    }
                    
                except NoSuchElementException:
                    continue
            
            print("⚠️ No se encontró comentario del autor con ningún selector.")
            return None

        except Exception as e:
            print(f"⚠️ Error al extraer comentario del autor: {e}")
            return None

    def _click_next_post(self):
        """Hace clic en el botón 'Next' del modal para avanzar al siguiente post."""
        try:
            # Múltiples selectores para el botón Next
            next_selectors = [
                "//button[contains(., 'Next')]",
                "//button[contains(@aria-label, 'Next')]",
                "//button[contains(@aria-label, 'siguiente')]",
                "//svg[contains(@aria-label, 'Next')]/..",
                "//button[contains(@class, 'next')]"
            ]
            
            for selector in next_selectors:
                try:
                    next_button = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    
                    if next_button.is_displayed():
                        print("➡️ Botón Next detectado, intentando hacer clic...")
                        
                        # Mover el mouse al botón
                        ActionChains(self.driver).move_to_element(next_button).perform()
                        time.sleep(1)
                        
                        # Intentar hacer clic con diferentes métodos
                        try:
                            next_button.click()
                        except:
                            try:
                                self.driver.execute_script("arguments[0].click();", next_button)
                            except:
                                ActionChains(self.driver).move_to_element(next_button).click().perform()
                        
                        self._human_delay(3, 5)
                        
                        # Verificar si el clic tuvo éxito (la URL debería cambiar)
                        print("✅ Avanzando al siguiente post...")
                        return True
                        
                except:
                    continue
            
            # Si llegamos aquí, ningún selector funcionó
            print("⚠️ No se pudo encontrar el botón Next o no está visible.")
            return False

        except Exception as e:
            print(f"⚠️ No hay más posts disponibles o no se pudo hacer clic en 'Next': {e}")
            return False

    def save_to_csv(self, data, account):
        """Guarda los datos extraídos en un archivo CSV con formato 'instagram_posts_{ACCOUNT}_DD_MM_YYYY.csv'."""
        if not data:
            print("⚠️ No hay datos para guardar.")
            return

        # Convertir datos a formato tabular
        processed_data = []
        for post in data:
            post_data = {
                "url_post": post.get("url_post", ""),
                "likes": post.get("likes", ""),
                "fecha_post": post.get("fecha_post", ""),
                "author": post.get("author_comment", {}).get("author", "") if post.get("author_comment") else "",
                "comment": post.get("author_comment", {}).get("comment", "") if post.get("author_comment") else "",
                "hashtags": ", ".join(post.get("author_comment", {}).get("hashtags", [])) if post.get("author_comment") else "",
                "mentions": ", ".join(post.get("author_comment", {}).get("mentions", [])) if post.get("author_comment") else "",
            }
            
            # Añadir comentarios en forma plana (como columnas adicionales)
            comentarios = post.get("comentarios", {})
            for i, (user, comment_data) in enumerate(comentarios.items(), 1):
                if i > 5:  # Limitamos a 5 comentarios por post para no tener demasiadas columnas
                    break
                post_data[f"comentario_{i}_usuario"] = user
                if isinstance(comment_data, tuple):
                    post_data[f"comentario_{i}_texto"] = comment_data[0]
                    if len(comment_data) > 1:
                        post_data[f"comentario_{i}_fecha"] = comment_data[1]
                    if len(comment_data) > 2:
                        post_data[f"comentario_{i}_likes"] = comment_data[2]
                else:
                    post_data[f"comentario_{i}_texto"] = str(comment_data)
            
            processed_data.append(post_data)

        # Crear DataFrame y guardar a CSV
        df = pd.DataFrame(processed_data)
        date_str = datetime.now().strftime("%d_%m_%Y")
        filename = f"instagram_posts_{account}_{date_str}.csv"

        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✅ [INFO] Se guardaron {len(data)} filas en {filename}.")
        
        # También guardar una copia de los datos en JSON para preservar la estructura completa
        import json
        with open(f"instagram_posts_{account}_{date_str}.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ [INFO] Se guardó una copia en formato JSON para preservar la estructura completa.")

# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    scraper = InstagramScraper()
    try:
        # 1) Login
        scraper.login()

        # 2) Comienza el scraper
        print(f"\n[INFO] Scrapeando {ACCOUNT}")
        posts = scraper.scrape_profile(ACCOUNT)

        print(f"[INFO] {ACCOUNT} => {len(posts)} posts extraídos")

        # 3) Guardar en CSV
        if posts:
            scraper.save_to_csv(posts, ACCOUNT)
            print("\n[OK] Proceso completado con éxito.")
        else:
            print("\n[WARNING] No se pudieron extraer posts. Verifica las capturas de pantalla para diagnosticar el problema.")

    except Exception as e:
        print("[CRÍTICO] Error en la ejecución:", e)
        traceback.print_exc()
    finally:
        scraper.driver.quit()
        print("[INFO] Selenium cerrado.")