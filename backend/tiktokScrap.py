import time
import random
import numpy as np
import csv
import base64
import traceback
import pandas as pd
from fake_useragent import UserAgent
from datetime import datetime
import undetected_chromedriver as uc
#from tiktok_captcha_solver import TikTokCAPTCHASolver

from agents import agents
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome, ChromeOptions, ChromeService
from selenium.webdriver import Firefox, FirefoxOptions
from selenium.webdriver import Edge, EdgeOptions

from selenium.common.exceptions import MoveTargetOutOfBoundsException

#TODO: Alch estoy probando
# from google_scrap.move_mouse import MoveMouse
#from google_scrap.move_mouse import MouseMover
from proxy_auth import ProxyAuth

# =========================================================================
# CONFIGURACIÓN GENL
# =========================================================================

USERNAME = 'sofi_sevilla24'
PASSWORD = 'Saul&Sofi241120'

# Lista de cuentas a extraer
ACCOUNTS = [
 "platacard"
]
ACCOUNT = "platacard"

# Año mínimo a filtrar
# YEAR_FILTER = 2024
MAX_POSTS = 10 # Número máximo de pocleasts a extraer
NUM_SCROLLS = 3 #TODO: Revisar qué hace esto


# =========================================================================
# Logger
# =========================================================================
class Logger:
    
    @staticmethod
    def warning(text: str):
        print(f'⚠️  [WARNING] {text}')
    
    @staticmethod
    def info(text: str):
        print(f'ℹ️   [INFO] {text}')
    
    @staticmethod
    def error(text: str):
        print(f'‼️   [ERROR] {text}')
    
    @staticmethod
    def fatal_error(text: str):
        print(f'⛔  [FATAL ERROR] {text}')

# =========================================================================
# CLASE SCRAPER
# =========================================================================
class TikTokScraper:
    def __init__(self, mobile=False, browser = 'Chrome'):
        self.mobile = mobile
        self.driver = self._setup_driver(browser)
        
        self.action = ActionChains(self.driver)
        self.mouse_mover = MouseMover(self.driver)
        self.solver = TikTokCAPTCHASolver(self.driver)

    def __del__(self):
        self.driver.quit()
    
    # TODO: Fix
    def move_mouse(self, element):
        # mm = MoveMouse()
        self.mouse_mover.move_mouse(element)
        
    def _setup_driver(self, browser):
        """
        Configura Selenium con el proxy residencial de SmartProxy.
        """
        
        PROXY_HOST = "gate.smartproxy.com"
        PROXY_PORT = "10001"
        PROXY_USER = "sp03mahcda"
        PROXY_PASS = "ax4as2g5_S2HHrmIjl"
        
        # PROXY_HOST = "192.168.1.67"
        # PROXY_PORT = "8080"
        # PROXY_USER = "sp03mahcda"
        # PROXY_PASS = "ax4as2g5_S2HHrmIjl"
        
        # Configuración del navegador
        # Opciones del navegador Chrome
        # options = uc.ChromeOptions()
        if browser=='Edge':
            options = EdgeOptions()
        elif browser=='Firefox':
            options = FirefoxOptions()
        else:
            options = ChromeOptions()
        
        # Define mobile emulation settings
        if self.mobile:
            mobile_emulation = {
                "deviceName": "iPhone X"
            }

            # Set Chrome options
            options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        # 🔒 Evita que los sitios detecten Selenium
        # options.add_argument("--disable-blink-features=AutomationControlled")
        # options.add_experimental_option("useAutomationExtension", False)
        # options.add_experimental_option("excludeSwitches", ["enable-automation"])

        # ⚡ Optimiza el rendimiento en servidores sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🖥️ Simula navegación real en una ventana maximizada
        options.add_argument("--start-maximized")
        # 🚀 Modo headless (sin interfaz gráfica)
        # options.add_argument("--headless=new")

        # 🔕 Evita notificaciones emergentes y bloqueos de pop-ups
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # 🔄 Cambia dinámicamente el User-Agent para evitar detección
        options.add_argument(f"--user-agent={self._random_user_agent()}")
        

        # 🔍 Evita filtración de IP real cuando se usan proxies
        options.add_argument("--disable-webrtc")
        
        # Configurar Proxy
        proxy = ProxyAuth(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
        options.add_extension(proxy.get_proxy_extension())
        
        # Configura el proxy con autenticación
        # options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
        # options.add_argument(f'--proxy-auth={PROXY_USER}:{PROXY_PASS}')

        # 🚀 Inicializa el navegador con opciones anti-detección
        # sudo pacman -S chromium
        # cp /bin/chromedriver /tmp/chromedriver
        # driver = uc.Chrome(options=options, use_subprocess=True, browser_executable_path="/bin/chromium", driver_executable_path="/tmp/chromedriver")
        if browser=='Edge':
            driver = Edge(options=options)
        elif browser=='Firefox':
            driver = Firefox(options=options)
        else:
            driver = Chrome(options=options)

        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        return driver

    def login(self):
        Logger.info("Iniciando sesión")
        self._human_delay(2,3)

        # PARA MOVIL
        if self.mobile:
            # Not now
            not_now = self.driver.find_element(By.XPATH, '//button[@data-e2e="alt-middle-cta-cancel-btn"]')
            self._human_click(not_now)
            
            # Open menu
            wrapper = self.driver.find_element(By.XPATH, '//div[@data-e2e="view-nav-arrow"]')
            self._human_click(wrapper)
        
        Logger.info('\tHaciendo click a botón de login')
        login_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@id, 'login-button')]")
        # class="TUXButton TUXButton--default TUXButton--medium TUXButton--primary css-18fmjv5-StyledLeftSidePrimaryButtonRedesign enq7hkb0"
        # WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//button[contains(@id, 'login-button')]")))
        # login_button = self.driver.find_element(By.XPATH, "//button[contains(@id, 'login-button')]")
        
        for login_button in login_buttons:
            if login_button.is_displayed():
                self._human_click(login_button)
                break
            else: print("Skipping honeypot")
        
        Logger.info('\tHaciendo click a botón de email')
        email_login_button = self.driver.find_elements(By.XPATH, '//div[@data-e2e="channel-item"]')[1]
        self._human_click(email_login_button)
        
        Logger.info('\tHaciendo click a botón de email o username')
        change_number2email_button = self.driver.find_element(By.XPATH, "//a[@href='/login/phone-or-email/email']")
        self._human_click(change_number2email_button)
        
        Logger.info('\tIngresando usuario')
        # WebDriverWait.until(EC.visibility_of_element_located((By.XPATH, '//div[@class="css-q83gm2-DivInputContainer etcs7ny0"]')))
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.XPATH, '//input[@name="username"]')))
        user_input = self.driver.find_element(By.XPATH, '//input[@name="username"]')
        self._human_click(user_input)
        self._human_type(user_input, USERNAME)
        
        Logger.info('\tIngresando contraseña')
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.XPATH, '//input[@name="username"]')))
        psw_input = self.driver.find_element(By.XPATH, '//input[@type="password"]')
        self._human_click(psw_input)
        self._human_type(psw_input, PASSWORD)
        
        Logger.info('\tLog In')
        login_button = self.driver.find_element(By.XPATH, "//button[contains(@data-e2e, 'login-button') and (@type='submit')]")
        self._human_click(login_button)
        
    def _random_user_agent(self):
        """
        Devuelve un User-Agent aleatorio para evitar detección.
        """
        # return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0"
        agent= random.choice(agents)
        while 'iPhone' in agent or 'Android' in agent: # Evitar agentes mobiles
            agent= random.choice(agents)
            
        return agent
    
    def _human_delay(self, min_s=1.0, max_s=3.0, search_captcha = True):
        """
        Pausa aleatoria entre acciones para simular comportamiento humano.
        """
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        
        # Aprovechar el tiempo para revisar si activamos un captcha
        if search_captcha and self.solver.find_captcha_imgs(timeout=total):
            self.solve_captcha()
            self.action.pause(total)
        else:
            time.sleep(total)
    
    def _scroll_n_times(self, times=10, pause_every=30, direction: str = 'down'):
        """
        Realiza scroll hacia abajo un número específico de veces en la página de perfil.
        Si `times` es 0, la función simplemente pasa.
        """
        
        if direction == 'up':
            key = Keys.PAGE_UP
        else:
            key = Keys.PAGE_DOWN
        
        if times <= 0:
            print("🔕 [INFO] Skipping scrolling as times is set to 0.")
            return 
        
        body = self.driver.find_element(By.TAG_NAME, "body")
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            body.send_keys(key)
            # self._human_delay(3.5, 6.7)  # Simular pausa humana
            self._human_delay(0.5, 1.5)  # Simular pausa humana

            # Si el número de scrolls alcanza el umbral, hacer una pausa larga
            if i % pause_every == 0:
                pause_time = random.uniform(60, 150)  # Entre 1 min (60s) y 2.5 min (150s)
                print(f"⏸️ [INFO] Pausa larga de {pause_time:.2f} segundos después de {i} scrolls...")
                time.sleep(pause_time)
                
    def _human_scroll(self, element):
        # self.action.scroll_to_element(element)
        target_x, target_y = element.location['x'], element.location['y']
        
        error = True
        
        if target_x > self.mouse_mover.start_x:
            direction = 'down'
        else: 
            direction = 'up'
        
        while error:
            try:
                self.move_mouse(element)
                error = False
            except MoveTargetOutOfBoundsException as e:
                self._scroll_n_times(1, direction=direction)
                target_x, target_y = element.location['x'], element.location['y']
                
                


    def _human_click(self, element: uc.WebElement):
        
        
        
        Logger.info(f"Moviendo el mouse a {element.location}")
        # self._human_scroll(element)
        
        if not self.mobile:
            self.move_mouse(element)
        
        self._human_delay(1, 1.5)
        self.action.click_and_hold().perform()
        # element.send_keys(Keys.ENTER)
        # self.driver.execute_script("arguments[0].click();", element)
        self._human_delay(0.01, 0.7)
        self.action.release().perform()
        
    def wander(self, seconds):
        self._human_delay(1,2)
        
        Logger.info(f"Wandering for {seconds} seconds")
        
        # Escoger un video aleatorio
        video = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/video/")]')
        video = np.random.choice(video[:3])
        self._human_click(video)
        
        start_time = time.time()
        actions = [Keys.DOWN, Keys.UP]
        
        while time.time()-start_time < seconds:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            action = np.random.choice(actions, p=[0.8, 0.2])
            Logger.info(f'\tEnviando clave: {action} | Tiempo restante: {round(seconds - (time.time()-start_time))}')
            body.send_keys(action)
            self._human_delay(5, 8)
            
        
    
    def _human_type(self, element, contenido: str):
        
        for letra in contenido:
            if letra in ['@', '_', '-', '*', '/', '-', '.']:
                self._human_delay(0.01, 0.02) # Tardar más para caracteres especiales
            self._human_delay(0.01,0.2, search_captcha=False)
            element.send_keys(letra)

#===========================================================================

#SUPPORT

#===========================================================================
    def scrape_profile(self, username):
        """Extrae posts del perfil de Tiktok especificado."""
        Logger.info("Abriendo TikTok")
        self.driver.get(f"https://www.tiktok.com/")
        
        self._human_delay(5,7)
        self.wander(60)
        
        # self._human_delay(3, 5)
        # self.login()
        self._human_delay(6, 10)
        
        Logger.info("Buscando el perfil")
        buttons_buscar = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@data-e2e, 'search')]")
                ))
        
        buttons_buscar = self.driver.find_elements(By.XPATH, "//button[contains(@data-e2e, 'search')]")
        for btn_buscar in buttons_buscar:
            try:
                self._human_click(btn_buscar)
                break
            except:
                continue
        
        self._human_delay(1,3)
        # Moviendo el mouse
        # self._human_click(btn_buscar)
        # self._human_delay(2, 5)
        
        # Buscando la cuenta
        Logger.info('\tIngresando usuario')
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//input[@data-e2e="search-user-input"]')))
        search_box = self.driver.find_elements(By.XPATH, '//input[@data-e2e="search-user-input"]')[1]
        self._human_click(search_box)
        self._human_type(search_box, f'@{username}')
        self._human_delay(2, 4)
        search_box.send_keys(Keys.ENTER)
        self._human_delay(7, 11)
        
        # # CAPTCHA
        # Logger.info("Resolviendo CAPTCHA")
        # self.solve_captcha()
        # self._human_delay(5, 10)
        
        
        # Intenta dar click en la cuenta
        # Primero buscar users
        # Logger.info("Yendo a la sección de usuarios")
        # users = WebDriverWait(self.driver, 6).until(
        #         EC.presence_of_element_located((By.XPATH, '//div[div[text() = "Users"]]')
        #         ))
        # self._human_delay(1,3)
        # self._human_click(users)
        
        Logger.info("Dando click en la cuenta")
        cuenta = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((By.XPATH, f"//a[@href ='/@{username}' and @data-e2e='search-user-info-container']")
                ))
        self._human_delay(1,3)
        self._human_click(cuenta)
        self._human_delay(2, 5)
        
        # print(f"\n🔍 [INFO] Abriendo perfil de {username}...")
        # self.driver.get(f"https://www.tiktok.com/@{username}/")
        # self._human_delay(3.1, 5.9)
        self._human_delay(1.9, 3.9)

        self._scroll_n_times(NUM_SCROLLS)
        self._scroll_n_times(NUM_SCROLLS-1, direction='up')

        # Intentar abrir el primer post
        if not self._click_first_post():
            print(f"⚠️ [WARNING] No se pudo abrir el primer  post de {username}. Saliendo...")
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
                self._human_delay(3, 5)
                # Intentar ir al siguiente post
                if not self._click_next_post():
                    print("⚠️ [INFO] No hay más posts disponibles o no se pudo hacer clic en 'Next'. Terminando extracción.")
                    break  # Salimos del loop si no hay más posts

            except Exception as e:
                print(f"❌ [ERROR] Ocurrió un problema con el post {i+1}: {e}")
                traceback.print_exc()  # Muestra el error completo para depuración

        print(f"\n✅ [INFO] Extracción completada: {len(posts_data)} posts obtenidos de {username}.")
        return posts_data
        
    def _click_first_post(self):
        """
        Busca y hace clic en el primer post visible con:
        - Un <a> cuyo href contenga 'account/'
        - Un <div> con 'padding-bottom: 133.'
        """
        self._human_delay(2.9, 4.1)
        try:
            # Encuentra todos los elementos <a> que contienen 'account/' en su href
            # posts = self.driver.find_elements(By.XPATH, f"//a[contains(@href, '{ACCOUNT}/video/') and descendant::div[contains(@style, 'padding-bottom: 133.')]]")
            posts = self.driver.find_elements(By.XPATH, f"//a[contains(@href, '{ACCOUNT}/video/')]")
            # posts = self.driver.find_elements(By.CLASS_NAME, "css-1mdo0pl-AVideoContainer e19c29qe4")

            if not posts:
                print("⚠️ No se encontraron posts con los criterios especificados después del scroll.")
                self.driver.save_screenshot("error_screenshot.png")  # Guardar una captura de pantalla
                return False

            # Seleccionar el primer post de la lista
            last_post = posts[0]

            # Asegurar que el post es visible antes de hacer clic
            self.driver.execute_script("arguments[0].scrollIntoView();", last_post)
            self._human_delay(1, 1.5)
            
            self._human_click(last_post)
            # Move mouse
            # mouse_tracker = self.driver.find_element(By.ID, "mouse-tracker")
            # Logger.info(f"Mouse position: {mouse_tracker.location}")
            # self.move_mouse(last_post)
            # Logger.info(f"Mouse position: {mouse_tracker.location}")
            
            # self.driver.execute_script("arguments[0].click();", last_post)  # Clic usando JavaScript
            self._human_delay(2.3, 3.6)
            print("✅ primer post del renglón abierto con éxito.")
            return True
        except Exception as e:
            print("[ERROR] No se pudo abrir el primer post visible después del scroll:", e)
            self.driver.save_screenshot("error_screenshot.png")  # Guardar una captura de pantalla
            print("[INFO] Captura de pantalla guardada como error_screenshot.png")
            return False
    
    def _extract_post_data(self):
        """Extrae datos del post abierto en el modal."""

        try:
            post_url = self.driver.current_url

            # Extraer número de likes
            try:
                likes_element = self.driver.find_element(By.XPATH, "//strong[@data-e2e=\"browse-like-count\"]")
                likes = likes_element.text.replace(",", "").strip()  # Eliminar comas y espacios
            except:
                likes = "No disponible"
                print("⚠️ [WARNING] No se pudieron extraer los likes")

            # Extraer fecha del post
            try:
                #TODO: Verificar que funcione o buscar dónde viene la fecha
                date_element = self.driver.find_element(By.TAG_NAME, "time")
                post_date = date_element.get_attribute("datetime")
            except:
                post_date = "No disponible"
                print("⚠️ [WARNING] No se pudo extraer la fecha")

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
    
    def _extract_commentsV2(self):
        """Extrae hasta 20 comentarios del post y maneja imágenes/GIFs."""
        comments_data = []
        
        try:
            # Encontrar todos los comentarios dentro del post (limitado a 20)
            #TODO: View replies
            print("🗩 [INFO] Extrayendo comentarios")
            comment_elements = self.driver.find_elements(By.XPATH, "//div[p[starts-with(@data-e2e, 'comment-level')]] | //div[span[starts-with(@data-e2e, 'comment-level')]]")[:20]
            if not comment_elements:
                Logger.info("No se encontraron comentarios, posible CAPTCHA")
                
                Logger.info("Buscando comentarios de nuevo")
                comment_elements = self.driver.find_elements(By.XPATH, "//div[p[starts-with(@data-e2e, 'comment-level')]] | //div[span[starts-with(@data-e2e, 'comment-level')]]")[:20]
                
                if len(comment_elements) == 0:
                    self.driver.save_screenshot("error_comments_screenshot.png")  # Guardar una captura de pantalla
                
            
            for comment in comment_elements:
                try:
                    # Extraer el nombre de usuario buscando el enlace dentro del comentario
                    try:
                        user = comment.find_element(By.XPATH, ".//a[span[starts-with(@data-e2e, 'comment-username')]]").get_attribute('href')
                    except NoSuchElementException:
                        user = "unknown"
                        Logger.warning("No se encontró el nombre del usuario")

                    # Intentar extraer el texto del comentario
                    try:
                        comment_text = comment.find_element(By.XPATH, ".//p[starts-with(@data-e2e, 'comment-level')]/span").text
                    except NoSuchElementException:
                        comment_text = None  # Puede ser una imagen/GIF
                        Logger.warning("Error al leer comentario")

                    # Extraer la fecha del comentario buscando el elemento <time>
                    try: 
                        date, likes = comment.find_elements(By.XPATH, ".//span[@class='TUXText TUXText--tiktok-sans TUXText--weight-normal']")
                    except Exception as e:
                        Logger.warning("Not found date nor likes")
                        Logger.warning(e)
                        self.driver.save_screenshot("error_likes_screenshot.png")
                        
                    # try:
                    #     date = comment.find_element(By.XPATH, ".//time").get_attribute("datetime")
                    # except NoSuchElementException:
                    #     date = None  # Si no se encuentra la fecha
                    #     Logger.warning("No se encontró la fecha")

                    # # Extraer número de likes buscando botones con texto "likes"
                    # try:
                    #     likes = comment.find_element(By.XPATH, ".//div[starts-with(@aria-label, 'Like video')]").text
                    #     likes = likes[len('Like video '): ]
                    # except NoSuchElementException as e:
                    #     likes = "0 likes"  # Si no tiene likes visibles
                    #     Logger.warning("No se encontraron los likes")
                    #     Logger.warning(e)
                        
                    
                    # Agregar los comentarios
                    comments_data.append({'username': user, 'texto': comment_text, 'fecha': date, 'likes': likes})
                    # Guardar los datos correctamente
                    # if comment_text:
                    #     comments_data[username] = (comment_text, date, likes)
                    # else:
                    #     comments_data[username] = ("unknown", date, likes)  # Si no tiene texto ni imagen

                except Exception as e:
                    print(f"⚠️ Error extrayendo un comentario: {e}")
                    continue  # Saltar al siguiente comentario en caso de error

        except Exception as e:
            print(f"⚠️ No se pudieron extraer comentarios: {e}")

        return comments_data
    
    def _author_comment(self):
        """Extrae el comentario del autor del post en Instagram."""
        
        # 1. Esperar que el contenido sea visible
        # 2. Buscar el botón "more", si está entonces hacer click
            # css-1kmeri5-ButtonExpand e1mzilcj2
        # 3. Extraer el texto
        Logger.info('Extrayendo descripción del video')
        try:
            # Buscar el primer comentario dentro del post (usualmente el del autor)
            author_comment_element = self.driver.find_element(By.XPATH, "//div[@data-e2e='browse-video-desc']")

            # Extraer el texto completo del comentario
            comment_text = ''.join([ comment.text for comment in author_comment_element.find_elements(By.XPATH, './/*') ])

            # Extraer hashtags (#)
            hashtags = [tag.text for tag in author_comment_element.find_elements(By.XPATH, ".//a[contains(@href, '/tag/')]")]

            # Extraer menciones (@)
            mentions = [mention.text for mention in author_comment_element.find_elements(By.XPATH, ".//a[contains(@href, '@')]")]

            print(f"✅ Descripción extraida: {comment_text} | hashtags: {hashtags} | menciones: {mentions}")
            
            return {
                # "author": username,
                "comment": comment_text,
                "hashtags": hashtags,
                "mentions": mentions
            }

        except NoSuchElementException:
            print("⚠️ No se encontró comentario del autor.")
            return None
    
    def _click_next_post(self):
        """Hace clic en el botón 'Next' del modal para avanzar al siguiente post."""
        try:
            # Esperar a que el botón Next esté visible y clickeable
            next_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'next')]"))
            )
            
            # Verificar si el botón está realmente visible
            if next_button.is_displayed():
                print("➡️ Botón Next detectado, intentando hacer clic...")

                self._human_delay(1.1515, 4.89562)
                time.sleep(1)

                # Hacer clic en el botón Next
                # self.driver.execute_script("arguments[0].click();", next_button)
                self._human_click(next_button)
                self._human_delay(3, 5)

                print("✅ Avanzando al siguiente post...")
                return True
            else:
                print("⚠️ El botón Next está presente pero no visible.")
                return False

        except Exception as e:
            print("⚠️ No hay más posts disponibles o no se pudo hacer clic en 'Next'.", e)
            return False
    
    def solve_captcha(self):
        
        self.solver.find_captcha_imgs()
        self.solver.solve()
        self.solver.drag_slider()
        
        pass
        
    
    def save_to_csv(self, data, account):
        """Guarda los datos extraídos en un archivo CSV con formato 'instagram_posts_{ACCOUNT}_DD_MM_YYYY.csv'."""
        if not data:
            print("⚠️ No hay datos para guardar.")
            return

        df = pd.DataFrame(data)
        date_str = datetime.now().strftime("%d_%m_%Y")
        filename = f"tiktok_posts_{account}_{date_str}.csv"

        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"[INFO] Se guardaron {len(data)} filas en {filename}.")
    
# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    scraper = TikTokScraper(browser='Edge')
    try:
        # 1) Login
        # scraper.login()

        # 2) Comienza el scraper
        
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
        input("Cerrar?")
        scraper.driver.close()
        print("[INFO] Selenium cerrado.")