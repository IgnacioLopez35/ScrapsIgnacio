import sys
import os
import ssl
import time
import random
import csv
import json
import traceback
import pandas as pd
from pathlib import Path
from fake_useragent import UserAgent
from datetime import datetime, timedelta
import undetected_chromedriver as uc
import re

# Deshabilitar verificación SSL para evitar problemas de certificados
ssl._create_default_https_context = ssl._create_unverified_context

# Configuración de la ruta para importaciones
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.abspath(os.path.join(ruta_actual, "../../../"))
sys.path.append(ruta_raiz)

# Importaciones de modulos propios
from agents import agents

# Importaciones de Selenium
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    StaleElementReferenceException,
    ElementNotInteractableException,
    WebDriverException
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================

# Credenciales de Facebook
FB_EMAIL = "francisco.recendiz@wivboost.com"
FB_PASS = "WivboostAI@"

# Lista de páginas a extraer
PAGES = [
    "platacard"  # Reemplaza con la página que quieras extraer
]
PAGE = "platacard"

# Filtros avanzados
START_DATE = "01-01-2025"  # Formato DD-MM-YYYY, posts a partir de esta fecha
END_DATE = "30-03-2025"    # Formato DD-MM-YYYY, posts hasta esta fecha
MAX_POSTS = 100            # Número máximo de posts a extraer
NUM_SCROLLS = 15           # Reducido para optimizar
SAVE_SCREENSHOTS = False   # Desactivado por defecto para mejorar velocidad
BROWSER_TYPE = 'Chrome'    # Tipo de navegador: 'Chrome' únicamente para uc
ENABLE_HEADLESS = False    # Activar modo headless (sin interfaz gráfica)
MAX_RETRIES = 3            # Número máximo de reintentos para operaciones que pueden fallar
LOAD_COMMENTS = True       # Establece a False para una extracción super rápida sin comentarios

# Optimización de tiempos
SCROLL_DELAY_MIN = 0.3     # Reducido de 0.5 a 0.3
SCROLL_DELAY_MAX = 0.7     # Reducido de 1.0 a 0.7
CLICK_DELAY_MIN = 0.1      # Reducido de 0.2 a 0.1
CLICK_DELAY_MAX = 0.3      # Reducido de 0.5 a 0.3
WAIT_TIMEOUT = 3           # Reducido de 5 a 3 segundos

# Conversión de fechas para filtrado
try:
    start_date = datetime.strptime(START_DATE, "%d-%m-%Y")
    end_date = datetime.strptime(END_DATE, "%d-%m-%Y")
except ValueError:
    print("⚠️ [WARNING] Formato de fecha incorrecto. Usando valores predeterminados.")
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
# =========================================================================
# Logger
# =========================================================================
class Logger:
    COLORS = {
        'RESET': '\033[0m',
        'INFO': '\033[94m',      # Azul
        'SUCCESS': '\033[92m',   # Verde
        'WARNING': '\033[93m',   # Amarillo
        'ERROR': '\033[91m',     # Rojo
        'FATAL': '\033[91;1m'    # Rojo brillante
    }
    
    EMOJIS = {
        'INFO': 'ℹ️',
        'SUCCESS': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'FATAL': '⛔'
    }
    
    @staticmethod
    def _log(level, text, save_to_file=True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji = Logger.EMOJIS.get(level, '')
        color = Logger.COLORS.get(level, Logger.COLORS['RESET'])
        reset = Logger.COLORS['RESET']
        
        log_message = f"{color}{emoji} [{level}] {timestamp}: {text}{reset}"
        print(log_message)
        
        if save_to_file:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, f"facebook_scraper_{datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                # Versión sin colores para el archivo
                f.write(f"[{level}] {timestamp}: {text}\n")
    
    @staticmethod
    def info(text):
        Logger._log('INFO', text)
    
    @staticmethod
    def success(text):
        Logger._log('SUCCESS', text)
    
    @staticmethod
    def warning(text):
        Logger._log('WARNING', text)
    
    @staticmethod
    def error(text):
        Logger._log('ERROR', text)
    
    @staticmethod
    def fatal_error(text):
        Logger._log('FATAL', text)
# =========================================================================
# CLASE SCRAPER
# =========================================================================
class FacebookScraper:
    def __init__(self):
        self.operation_count = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_dir = self._setup_screenshot_dir()
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)
        
        # Cache de selectores y estrategias
        self._xpath_cache = {}
        self._click_strategy_cache = {}
        self._content_selector_cache = None
        self._url_selector_cache = None
        self._comment_selector_cache = {
            'user': None,
            'text': None,
            'date': None,
            'likes': None
        }
        
        # Diccionario con selectores actualizados para Facebook
        self.selectors = {
            # Botones para expandir comentarios
            "expand_comments": [
                ".//span[contains(text(), 'comentarios')]",
                ".//span[contains(text(), 'comments')]",
                ".//div[@aria-label='Leave a comment']",
                ".//div[@aria-label='Deja un comentario']",
                ".//span[@data-testid='UFI2CommentsCount']",
                ".//div[contains(@aria-label, 'Comment')]",
                ".//div[contains(@class, 'x1y1aw1k') and contains(text(), 'comment')]"
            ],
            # Selectores para posts - Optimizados
            "posts": [
                ".//div[@role='article' and @aria-labelledby]", 
                ".//div[@role='article']",
                ".//div[@data-pagelet='FeedUnit']",
                ".//div[contains(@class, 'x1lliihq')]//div[@role='article']",
                ".//div[contains(@class, 'x78zum5')]//div[@role='article']"
            ],
            # Selectores para contenido de posts - Optimizados
            "post_content": [
                ".//div[@data-ad-preview='message']",
                ".//div[@data-ad-comet-preview='message']",
                ".//div[contains(@class, 'xdj266r')]",
                ".//div[contains(@class, 'x1iorvi4')]",
                ".//div[@dir='auto' and contains(@class, 'x1lliihq')]",
                ".//div[contains(@class, 'x1tlxs6b')]//div[@dir='auto']"
            ],
            # Selectores para fechas de posts - Optimizados
            "post_dates": [
                ".//a[contains(@href, '/posts/')]//span",
                ".//a[contains(@href, '/permalink/')]//span",
                ".//span[@class='x4k7w5x x1h91t0o x1h9r5lt x1jfb8zj xv2umb2 x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1qrby5j']",
                ".//a//span[contains(@class, 'x4k7w5x')]",
                ".//span[@data-testid='story-time']", 
                ".//a[contains(@href, '/posts/') or contains(@href, '/permalink/')]",
                ".//span[contains(@class, 'x1i10hfl')]//span[contains(@class, 'x4k7w5x')]"
            ],
            # Selectores para reacciones - Optimizados
            "reactions": [
                ".//span[@class='xt0b8zv xvy4d1p']",
                ".//span[contains(@class, 'x1e558r4')]",
                ".//span[@data-testid='like-count']",
                ".//span[contains(@class, 'x16n37ib')][contains(@class, 'x1rg5ohu')]",
                ".//span[contains(@aria-label, 'reactions') or contains(@aria-label, 'reacciones')]",
                ".//div[@aria-label='Like' or @aria-label='Me gusta']//span"
            ],
            # Selectores para comentarios - Optimizados
            "comments": [
                ".//div[@aria-label and contains(@aria-label, 'Comment by')]", 
                ".//div[@data-testid='comment']",
                ".//div[contains(@class, 'x1y1aw1k') and contains(@class, 'xwib8y2')]",
                ".//div[@role='article' and contains(@class, 'x1n2onr6')]",
                ".//div[contains(@class, 'x1y1aw1k')][contains(@class, 'x1pi30zi')]",
                ".//ul[contains(@class, 'x1n2onr6')]//li"
            ],
            # Selectores para más respuestas - Optimizados
            "more_replies": [
                ".//span[contains(text(), 'View more replies')]",
                ".//span[contains(text(), 'Ver más respuestas')]",
                ".//span[contains(text(), 'more comment')]",
                ".//span[contains(text(), 'más comentarios')]",
                ".//div[@role='button'][contains(text(), 'respuestas') or contains(text(), 'replies')]"
            ],
            # Selectores para "Ver más" en comentarios
            "see_more": [
                ".//div[contains(@class, 'x1i10hfl') and contains(text(), 'Ver más')]",
                ".//div[contains(@class, 'x1i10hfl') and contains(text(), 'See more')]",
                ".//span[contains(text(), 'Ver más')]",
                ".//span[contains(text(), 'See more')]",
                ".//div[contains(text(), 'Ver más') or contains(text(), 'See more')]"
            ]
        }

    def _setup_screenshot_dir(self):
        """Crea directorio para capturas de pantalla"""
        if not SAVE_SCREENSHOTS:
            return None
            
        screenshot_dir = os.path.join("screenshots", f"facebook_{self.session_id}")
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        return screenshot_dir
    
    def save_screenshot(self, name=None):
        """Guarda captura de pantalla solo si está activado"""
        if not SAVE_SCREENSHOTS or not self.screenshot_dir:
            return None
            
        try:
            if name is None:
                name = f"screenshot_{datetime.now().strftime('%H%M%S')}"
            
            filename = os.path.join(self.screenshot_dir, f"{name}.png")
            self.driver.save_screenshot(filename)
            Logger.info(f"Captura de pantalla guardada: {filename}")
            return filename
        except:
            return None
            
    def _setup_driver(self):
        """
        Configura el driver con opciones anti-detección optimizadas.
        """
        # Configuración del navegador
        options = uc.ChromeOptions()
        
        # Protección anti-detección
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Optimización de rendimiento
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        
        # Modo headless (si está activado)
        if ENABLE_HEADLESS:
            options.add_argument("--headless=new")
            
        # Bloqueo de notificaciones y popups
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # User-Agent realista
        user_agent = self._random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")

        # Prevención de fugas WebRTC
        options.add_argument("--disable-webrtc")

        # Configuraciones específicas para Facebook
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            "profile.managed_default_content_settings.images": 1,       # Cargar imágenes
            "profile.managed_default_content_settings.javascript": 1,   # Habilitar JavaScript
            "profile.managed_default_content_settings.plugins": 1,      # Habilitar plugins
            "profile.managed_default_content_settings.popups": 2,       # Bloquear popups
            "profile.managed_default_content_settings.geolocation": 2,  # Bloquear geolocalización
            "profile.managed_default_content_settings.media_stream": 2, # Bloquear acceso a cámara/micro
            "profile.default_content_setting_values.cookies": 1,        # Aceptar cookies
            "profile.block_third_party_cookies": False                 # Necesario para Facebook
        }
        options.add_experimental_option("prefs", prefs)

        # Usar perfil persistente para evitar login frecuente
        profile_dir = os.path.join(os.path.expanduser("~"), "fb-scraper-profile")
        options.add_argument(f"--user-data-dir={profile_dir}")

        # Configurar proxy con autenticación (opcional)
        try:
            from modules.proxy_auth import ProxyAuth
            PROXY_HOST = "gate.smartproxy.com"
            PROXY_PORT = "10001"
            PROXY_USER = "sp03mahcda"
            PROXY_PASS = "ax4as2g5_S2HHrmIjl"
            
            proxy = ProxyAuth(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
            options.add_extension(proxy.get_proxy_extension())
        except Exception as e:
            Logger.warning(f"Proxy no configurado: {e}")
        # Inicializar el driver con undetected chromedriver
        try:
            driver = uc.Chrome(options=options, use_subprocess=True)
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(2)  # Reducido para mejor rendimiento
            
            # Aplicar scripts de evasión
            self._apply_stealth_js(driver)
            
            Logger.success("Driver inicializado correctamente")
            return driver
        except Exception as e:
            Logger.fatal_error(f"Error inicializando driver: {e}")
            raise

    def _apply_stealth_js(self, driver):
        """Aplica scripts JavaScript para evadir detección."""
        try:
            # Ocultar WebDriver
            driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """)
            
            # Simular plugins del navegador
            driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    return [
                        {description: "Chrome PDF Plugin", filename: "internal-pdf-viewer", name: "Chrome PDF Plugin"},
                        {description: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", name: "Chrome PDF Viewer"},
                        {description: "Native Client", filename: "internal-nacl-plugin", name: "Native Client"}
                    ];
                }
            });
            """)
            
            # Simular idiomas comunes para Facebook
            driver.execute_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es-MX', 'es']
            });
            """)
            
            # Simular plataforma de Windows
            driver.execute_script("""
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            """)
            
            # Deshabilitar automation mode de Chrome
            driver.execute_script("""
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            return driver
        except Exception as e:
            Logger.error(f"Error aplicando scripts stealth: {e}")
            return driver

    def _random_user_agent(self):
        """
        Devuelve un User-Agent optimizado para Facebook.
        """
        try:
            facebook_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ]
            
            # Intentar usar fake_useragent primero
            try:
                ua = UserAgent()
                chrome_ua = ua.chrome
                if chrome_ua and not any(term in chrome_ua.lower() for term in ['mobile', 'android', 'iphone']):
                    return chrome_ua
            except:
                pass
                
            # Fallback a lista predefinida
            return random.choice(facebook_agents)
        except:
            # Fallback a un user agent conocido
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    def _human_delay(self, min_s=0.5, max_s=1.0):
        """
        Pausa aleatoria optimizada entre acciones para simular comportamiento humano.
        """
        # Incrementar contador de operaciones
        self.operation_count += 1
        
        # Optimizar tiempos basados en contador
        if self.operation_count > 50:
            # Después de varias operaciones, reducir tiempos
            min_s *= 0.6
            max_s *= 0.6
        
        # Generar pausa con distribución natural
        total = max(0.05, min_s + random.random() * (max_s - min_s))
        
        # Reducir probabilidad de pausas largas
        if random.random() < 0.08:  # 8% de probabilidad 
            # Micro pausa para aceleración
            total = random.uniform(0.03, 0.10)
        
        time.sleep(total)
        
        # Verificar popups con menor frecuencia
        if self.operation_count % 10 == 0:
            self._handle_popups()
        
        return total

    def _handle_popups(self):
        """Maneja popups y diálogos comunes de Facebook."""
        try:
            # Lista de posibles popups y sus selectores
            popups = {
                "cookies": [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'Aceptar')]",
                    "//button[contains(text(), 'Allow')]"
                ],
                "notifications": [
                    "//button[contains(text(), 'Not Now')]",
                    "//button[contains(text(), 'Ahora no')]"
                ],
                "account_switch": [
                    "//button[contains(text(), 'Continue as')]",
                    "//button[contains(text(), 'Continuar como')]"
                ]
            }
            
            for popup_name, selectors in popups.items():
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                element.click()
                                Logger.info(f"Popup '{popup_name}' cerrado")
                                time.sleep(0.2)  # Reducido
                                break
                    except:
                        continue
                
        except:
            pass  # Silenciar errores en manejo de popups

    def _find_element_with_multiple_xpaths(self, parent, xpath_list, single=True, timeout=2):
        """
        Busca elementos usando múltiples XPaths con caché para mayor eficiencia.
        """
        if parent is None:
            parent = self.driver
            
        # Para búsquedas críticas, usar caché de XPaths funcionales
        cache_key = str(xpath_list)[:50]  # Usar primeros 50 chars como clave
        if cache_key in self._xpath_cache:
            # Intentar primero el último XPath exitoso
            try:
                xpath = self._xpath_cache[cache_key]
                if single:
                    elements = parent.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed():
                            return element
                else:
                    elements = parent.find_elements(By.XPATH, xpath)
                    visible_elements = [e for e in elements if e.is_displayed()]
                    if visible_elements:
                        return visible_elements
            except:
                pass
                
        for xpath in xpath_list:
            try:
                if single:
                    # Búsqueda directa sin esperas para mayor velocidad
                    elements = parent.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed():
                            # Guardar XPath exitoso en caché
                            self._xpath_cache[cache_key] = xpath
                            return element
                else:
                    elements = parent.find_elements(By.XPATH, xpath)
                    visible_elements = [e for e in elements if e.is_displayed()]
                    if visible_elements:
                        # Guardar XPath exitoso en caché
                        self._xpath_cache[cache_key] = xpath
                        return visible_elements
            except:
                continue
                
        return None if single else []

    def _human_click(self, element, force_js=False):
        """
        Realiza un clic optimizado con estrategia de intento múltiple.
        """
        if element is None:
            return False
            
        # Asegurar que el elemento está visible con scrolling mínimo
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", element)
            time.sleep(0.05)  # Pausa mínima
        except:
            pass
        
        # Si ya tenemos un método de clic exitoso para este tipo de elemento, usarlo primero
        element_class = element.get_attribute("class") or ""
        element_type = element.tag_name + "-" + element_class[:20]
        
        if element_type in self._click_strategy_cache:
            try:
                strategy = self._click_strategy_cache[element_type]
                if strategy == 'direct':
                    element.click()
                    return True
                elif strategy == 'js':
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                elif strategy == 'action':
                    self.action.move_to_element(element).click().perform()
                    return True
            except:
                pass
        
        # Intentar diferentes métodos de clic en orden de preferencia
        methods = []
        
        if not force_js:
            # Método 1: Click directo (más rápido)
            methods.append(('direct', lambda: element.click()))
            # Método 2: ActionChains (más natural)
            methods.append(('action', lambda: self.action.move_to_element(element).click().perform()))
        
        # Método 3: JavaScript click (siempre como opción)
        methods.append(('js', lambda: self.driver.execute_script("arguments[0].click();", element)))
        
        # Intentar cada método
        for method_name, method_func in methods:
            try:
                method_func()
                # Guardar estrategia exitosa
                self._click_strategy_cache[element_type] = method_name
                return True
            except:
                continue
                
        return False

    def _scroll_with_pause(self, times=10, pause_every=5):
        """
        Realiza scroll con patrones optimizados para mayor velocidad.
        """
        if times <= 0:
            return
            
        Logger.info(f"Realizando {times} scrolls para cargar contenido...")
        
        for i in range(1, times + 1):
            # Scroll con altura variable pero mayor para cubrir más contenido
            scroll_amount = random.randint(700, 1000)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            # Mostrar progreso cada 5 scrolls
            if i % 5 == 0 or i == times:
                Logger.info(f"Scroll {i}/{times}")
            
            # Pausa entre scrolls (optimizada y reducida)
            delay = max(0.3, SCROLL_DELAY_MIN * 0.7)
            time.sleep(delay)
            
            # Pausas cada cierto número de scrolls (reducidas)
            if i % pause_every == 0 and random.random() < 0.5:  # 50% de probabilidad
                # Micro-scroll aleatorio para simular comportamiento natural
                self.driver.execute_script("window.scrollBy(0, -80);")
                time.sleep(0.1)
                self.driver.execute_script("window.scrollBy(0, 80);")
                time.sleep(0.1)
    
    def _scroll_for_more_content(self):
        """Scroll optimizado para cargar más contenido"""
        try:
            # Calcular altura aleatoria de scroll
            scroll_height = random.randint(600, 900)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
        except:
            # Fallback a método tradicional si falla el script
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)

    def _check_already_logged_in(self):
        """Verifica si ya hay una sesión activa de Facebook"""
        try:
            # Buscar elementos que indiquen sesión activa
            profile_indicators = [
                "//div[@aria-label='Your profile']",
                "//div[@aria-label='Tu perfil']",
                "//div[contains(@class, 'x1i10hfl') and contains(@class, 'xjbqb8w')]//img",
                "//a[@aria-label='Home']",
                "//a[@aria-label='Inicio']"
            ]
            
            for indicator in profile_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                if elements and any(e.is_displayed() for e in elements):
                    return True
                    
            return False
        except:
            return False
    def _search_and_navigate_to_page(self, page_name):
        """
        Busca una página usando el buscador de Facebook y navega a ella.
        Método acelerado para mayor eficiencia.
        """
        Logger.info(f"Buscando página: {page_name} usando el buscador de Facebook")
        try:
            # Navegar a Facebook directamente a la URL del buscador
            self.driver.get(f"https://www.facebook.com/search/pages?q={page_name}")
            self._human_delay(1, 1.5)  # Reducido significativamente
        
            # Buscar resultados que coincidan con la página (optimizado)
            page_result_selectors = [
                f"//a[contains(text(), '{page_name}') and @role='link']//ancestor::div[contains(@class, 'x1ja2u2z')]",
                f"//span[contains(text(), '{page_name}')]//ancestor::a[@role='link']",
                "//div[contains(@aria-label, 'Page')]//a",
                "//div[contains(@aria-label, 'Página')]//a",
                f"//a[contains(@href, '{page_name}')]"
            ]
        
            # Buscar y hacer clic en la página en los resultados
            page_link = None
            for selector in page_result_selectors:
                try:
                    links = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((By.XPATH, selector))
                    )
                    for link in links:
                        if link.is_displayed() and link.get_attribute("href") and "facebook.com" in link.get_attribute("href"):
                            page_link = link
                            break
                    if page_link:
                       break
                except:
                    continue
        
            if page_link:
                self._human_click(page_link)
                self._human_delay(1.5, 2)  # Reducido
            
                # Verificar si estamos en la página correcta
                current_url = self.driver.current_url.lower()
                if page_name.lower() in current_url:
                    Logger.success(f"Navegación a página {page_name} exitosa usando búsqueda")
                    return True
        
            # Si no encontramos, intentar navegación directa a /posts
            Logger.info(f"Intentando navegación directa a posts de {page_name}")
            self.driver.get(f"https://www.facebook.com/{page_name}/posts/")
            self._human_delay(1.5, 2)
            return "facebook.com" in self.driver.current_url
    
        except Exception as e:
           Logger.error(f"Error navegando a través del buscador: {e}")
           return False
    
    def _get_post_url(self, post_element):
        """Extrae la URL única de un post para identificarlo"""
        try:
            url_patterns = ['/posts/', '/permalink/', 'story_fbid=', '/photo.php?', '/videos/']
            url_elements = post_element.find_elements(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/permalink/') or contains(@href, 'story_fbid=')]")
            
            for url_elem in url_elements:
                href = url_elem.get_attribute("href")
                if href and any(pattern in href for pattern in url_patterns):
                    return href
        except:
            pass
        
        # Fallback: usar ID único del elemento
        try:
            return post_element.get_attribute("id") or "post_" + str(random.randint(10000, 99999))
        except:
            return "post_" + str(random.randint(10000, 99999))
    def _get_next_post(self, current_post):
        """
        Encuentra el siguiente post después del post actual en la página.
        
        Args:
            current_post: El elemento del post actual
            
        Returns:
            El elemento del siguiente post si se encuentra, None en caso contrario
        """
        try:
            # 1. Intentar encontrar el siguiente post por posición en el DOM
            next_post = None
            try:
                # Buscar el siguiente elemento de artículo después del actual
                next_post = self.driver.execute_script("""
                    var currentPost = arguments[0];
                    var allPosts = document.querySelectorAll('div[role="article"]');
                    var currentIndex = Array.from(allPosts).indexOf(currentPost);
                    
                    if (currentIndex !== -1 && currentIndex < allPosts.length - 1) {
                        return allPosts[currentIndex + 1];
                    }
                    return null;
                """, current_post)
                
                if next_post:
                    Logger.info("Siguiente post encontrado por posición en el DOM")
                    return next_post
            except:
                pass
                
            # 2. Método alternativo: hacer scroll y buscar nuevos posts
            # Hacer scroll después del post actual
            self.driver.execute_script("""
                var currentPost = arguments[0];
                var rect = currentPost.getBoundingClientRect();
                window.scrollTo(0, window.pageYOffset + rect.bottom + 50);
            """, current_post)
            time.sleep(1)
            
            # Buscar posts que no sean el actual
            current_id = current_post.get_attribute("id") or ""
            
            for selector in self.selectors["posts"]:
                posts = self.driver.find_elements(By.XPATH, selector)
                for post in posts:
                    post_id = post.get_attribute("id") or ""
                    
                    # Verificar que no sea el mismo post
                    if post_id != current_id and post.is_displayed():
                        # Asegurarse de que está debajo del post actual
                        is_below = self.driver.execute_script("""
                            var current = arguments[0];
                            var candidate = arguments[1];
                            var currentRect = current.getBoundingClientRect();
                            var candidateRect = candidate.getBoundingClientRect();
                            return candidateRect.top > currentRect.bottom;
                        """, current_post, post)
                        
                        if is_below:
                            Logger.info("Siguiente post encontrado por scroll")
                            return post
            
            return None
        except Exception as e:
            Logger.error(f"Error buscando siguiente post: {e}")
            return None

    def _navigate_to_next_post(self, current_post):
        """
        Navega al siguiente post después del actual.
        
        Args:
            current_post: El elemento del post actual
            
        Returns:
            True si la navegación fue exitosa, False en caso contrario
        """
        next_post = self._get_next_post(current_post)
        
        if next_post:
            # Centrar el siguiente post en la ventana
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", next_post)
            time.sleep(0.5)
            
            # Verificar si el post es visible
            is_visible = self.driver.execute_script("""
                var elem = arguments[0];
                var rect = elem.getBoundingClientRect();
                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );
            """, next_post)
            
            if is_visible:
                Logger.success("Navegación a siguiente post exitosa")
                return True
            else:
                # Si no es completamente visible, hacer un segundo intento con scroll
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_post)
                time.sleep(0.5)
                Logger.info("Segundo intento de navegación a siguiente post")
                return True
        
        # Si no se pudo encontrar el siguiente post, hacer scroll general
        Logger.warning("No se encontró un siguiente post específico, haciendo scroll general")
        self._scroll_for_more_content()
        time.sleep(1)
        
        # Verificar si aparecieron nuevos posts
        current_url = current_post.get_attribute("data-url") or ""
        
        new_posts = []
        for selector in self.selectors["posts"]:
            posts = self.driver.find_elements(By.XPATH, selector)
            for post in posts:
                post_url = post.get_attribute("data-url") or ""
                if post_url != current_url and post.is_displayed():
                    new_posts.append(post)
        
        if new_posts:
            # Navegar al primer nuevo post encontrado
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", new_posts[0])
            time.sleep(0.5)
            Logger.info("Navegación a un nuevo post después de scroll")
            return True
        
        return False
    def _extract_posts_one_by_one(self, page_name):
        """
        Extrae posts de forma individual con mejoras para avanzar al siguiente post.
        """
        Logger.info("Iniciando extracción post por post (método mejorado)")
        
        # Lista para almacenar los posts extraídos
        posts_data = []
        posts_processed = 0
        processed_urls = set()

        # Navegar directamente a la página de posts
        direct_posts_url = f"https://www.facebook.com/{page_name}/posts/"
        self.driver.get(direct_posts_url)
        self._human_delay(1.5, 2)  # Reducido
        
        # Scrolls iniciales para cargar algunos posts
        self._scroll_with_pause(4, pause_every=2)
        
        # Selectores mejorados para encontrar posts
        improved_selectors = [
            "//div[@role='article' and contains(@id, 'mall_post_')]",
            "//div[@data-pagelet='PageFeedContent']//div[@role='article']",
            "//div[contains(@class, 'x1yztbdb')]//div[@role='article']",
            "//div[@role='feed']//div[@role='article']",
        ]
        
        # Variable para controlar la paginación
        posts_found = []
        consecutive_empty_scrolls = 0
        
        # Primera fase: encontrar posts disponibles
        for attempt in range(8):  # Limitado a 8 intentos
            # Encontrar posts visibles
            visible_posts = []
            for selector in improved_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        visible_posts = [e for e in elements if e.is_displayed()]
                        if visible_posts:
                            break
                except:
                    continue
            
            if not visible_posts:
                Logger.warning("No se encontraron posts visibles. Haciendo scroll adicional.")
                self._scroll_with_pause(2, pause_every=1)
                consecutive_empty_scrolls += 1
                if consecutive_empty_scrolls >= 3:
                    break
                continue
            else:
                # Guardar referencia a los posts encontrados
                posts_found = visible_posts
                consecutive_empty_scrolls = 0
                Logger.info(f"Se encontraron {len(posts_found)} posts visibles.")
                break
        
        # Segunda fase: procesar cada post individualmente
        for post_index, post_element in enumerate(posts_found):
            if posts_processed >= MAX_POSTS:
                Logger.info(f"Se alcanzó el límite de {MAX_POSTS} posts. Deteniendo extracción.")
                break
                
            try:
                # Obtener URL del post para verificar si ya lo procesamos
                current_post_url = self._get_post_url(post_element)
                
                # Si ya procesamos este post, continuar con el siguiente
                if current_post_url in processed_urls:
                    continue
                    
                # Centrar el post en la ventana para mejor visibilidad
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", post_element)
                time.sleep(0.5)  # Breve pausa
                
                # Extraer datos del post
                post_data = self._extract_post_data_improved(post_element)
                
                # Verificar si el post está en el rango de fechas
                if post_data and self._post_in_date_range(post_data):
                    Logger.info(f"Procesando post {posts_processed+1}/{MAX_POSTS}: {post_data['url_post']}")
                    
                    # Expandir comentarios de forma más efectiva
                    if LOAD_COMMENTS:
                        self._expandir_todos_comentarios(post_element)
                        comments = self._extract_comments(post_element)
                        post_data["comentarios"] = comments
                    else:
                        post_data["comentarios"] = {}
                    
                    # Añadir a la lista de posts y marcar como procesado
                    posts_data.append(post_data)
                    processed_urls.add(post_data["url_post"])
                    posts_processed += 1
                    
                    # Mostrar progreso
                    Logger.success(f"Procesado post {posts_processed}/{MAX_POSTS}")
                
                # Hacer scroll para mostrar el siguiente post si hay más disponibles
                if post_index < len(posts_found) - 1:
                    next_post = posts_found[post_index + 1]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", next_post)
                    time.sleep(0.5)  # Breve pausa
                    
            except Exception as e:
                Logger.error(f"Error procesando post: {e}")
                continue
                
            # Si alcanzamos el límite de posts, salir
            if posts_processed >= MAX_POSTS:
                break
                
            # Si necesitamos más posts, hacer scroll para cargar nuevos
            if post_index == len(posts_found) - 1 and posts_processed < MAX_POSTS:
                Logger.info("Haciendo scroll para cargar más posts...")
                self._scroll_with_pause(3, pause_every=2)
                
                # Buscar nuevos posts después del scroll
                new_posts = []
                for selector in improved_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            new_posts = [e for e in elements if e.is_displayed() and e not in posts_found]
                            if new_posts:
                                break
                    except:
                        continue
                        
                if new_posts:
                    posts_found.extend(new_posts)
                    Logger.info(f"Se encontraron {len(new_posts)} posts nuevos después del scroll.")
        
        return posts_data
    def _extract_post_data_improved(self, post_element):
        """Versión optimizada de extracción de datos de post con selectores de alto rendimiento"""
        try:
            # 1. Extraer texto/contenido del post
            post_text = "No disponible"
            improved_content_selectors = [
                ".//div[@data-ad-preview='message']",
                ".//div[@data-ad-comet-preview='message']",
                ".//div[contains(@class, 'xdj266r')]",
                ".//div[contains(@class, 'x1iorvi4')]",
                ".//div[@dir='auto' and contains(@class, 'x1lliihq')]",
                ".//div[contains(@class, 'x1tlxs6b')]//div[@dir='auto']",
                ".//div[contains(@class, 'xgqcy7u') and contains(@class, 'x1y1aw1k')]"
            ]
            
            # Usar primero el selector que funcionó anteriormente
            if self._content_selector_cache:
                try:
                    elements = post_element.find_elements(By.XPATH, self._content_selector_cache)
                    for element in elements:
                        if element.is_displayed() and element.text and len(element.text.strip()) > 1:
                            post_text = element.text.strip()
                            break
                except:
                    pass
                
            # Si no funcionó el caché, probar otros selectores
            if post_text == "No disponible":
                for selector in improved_content_selectors:
                    try:
                        elements = post_element.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.text and len(element.text.strip()) > 1:
                                post_text = element.text.strip()
                                # Guardar selector exitoso en caché
                                self._content_selector_cache = selector
                                break
                        if post_text != "No disponible":
                            break
                    except:
                        continue
                
            # Expandir "Ver más" solo para textos que parecen truncados
            if post_text != "No disponible" and len(post_text) > 50 and ("..." in post_text or len(post_text.split()) > 20):
                try:
                    see_more_buttons = post_element.find_elements(By.XPATH, 
                        ".//div[contains(text(), 'Ver más') or contains(text(), 'See more')]")
                    for btn in see_more_buttons:
                        if btn.is_displayed():
                            self._human_click(btn)
                            time.sleep(0.3)
                            
                            # Volver a leer el texto expandido con el selector que ya funcionó
                            if self._content_selector_cache:
                                try:
                                    elements = post_element.find_elements(By.XPATH, self._content_selector_cache)
                                    for element in elements:
                                        if element.is_displayed() and element.text:
                                            post_text = element.text.strip()
                                            break
                                except:
                                    pass
                            break
                except:
                    pass
            
            # 2. Extraer URL del post
            post_url = "No disponible"
            url_patterns = ['/posts/', '/permalink/', 'story_fbid=', '/photo.php?', '/videos/']
            
            # Intentar primero con selector cacheado
            if self._url_selector_cache:
                try:
                    url_elements = post_element.find_elements(By.XPATH, self._url_selector_cache)
                    for url_elem in url_elements:
                        href = url_elem.get_attribute("href")
                        if href and any(pattern in href for pattern in url_patterns):
                            # Limpiar URL
                            if '?' in href and not any(p in href.split('?')[0] for p in ['/photo.php', '/video.php']):
                                post_url = href.split('?')[0]
                            else:
                                post_url = href
                            break
                except:
                    pass
                    
            # Si no funcionó el caché, probar con selectores comunes
            if post_url == "No disponible":
                url_selectors = [
                    ".//a[contains(@href, '/posts/')]",
                    ".//a[contains(@href, '/permalink/')]",
                    ".//a[contains(@href, 'story_fbid=')]"
                ]
                
                for selector in url_selectors:
                    try:
                        url_elements = post_element.find_elements(By.XPATH, selector)
                        for url_elem in url_elements:
                            href = url_elem.get_attribute("href")
                            if href and any(pattern in href for pattern in url_patterns):
                                # Limpiar URL
                                if '?' in href and not any(p in href.split('?')[0] for p in ['/photo.php', '/video.php']):
                                    post_url = href.split('?')[0]
                                else:
                                    post_url = href
                                # Guardar selector exitoso
                                self._url_selector_cache = selector
                                break
                        if post_url != "No disponible":
                            break
                    except:
                        continue
            
            # 3. Extraer fecha del post (optimizado)
            post_date = "No disponible"
            date_selectors = [
                ".//span[@class='x4k7w5x x1h91t0o x1h9r5lt xv2umb2']",
                ".//a[contains(@href, '/posts/')]//span[@class='x4k7w5x']",
                ".//a//span[contains(@class, 'x4k7w5x') and contains(@class, 'xdj266r')]",
                ".//a[contains(@href, '/posts/')]//span",
                ".//a[contains(@href, '/permalink/')]//span",
                ".//span[contains(@class, 'x4k7w5x')]",
                ".//span[@data-testid='story-time']",
                ".//a[contains(@href, '/posts/') or contains(@href, '/permaLink/')]",
                ".//span[contains(@class, 'x1i10hfl')]//span[contains(@class, 'x4k7w5x')]"
            ]
            
            for selector in date_selectors:
                try:
                    date_elements = post_element.find_elements(By.XPATH, selector)
                    for date_elem in date_elements:
                        # Verificar atributos primero (más rápido)
                        for attr in ["title", "data-tooltip-content", "aria-label"]:
                            date_value = date_elem.get_attribute(attr)
                            if date_value and len(date_value) > 2:
                                post_date = date_value
                                break
                        
                        # Si no hay atributo con la fecha, usar el texto
                        if post_date == "No disponible" and date_elem.text and len(date_elem.text) > 1:
                            post_date = date_elem.text.strip()
                        
                        if post_date != "No disponible":
                            break
                    
                    if post_date != "No disponible":
                        break
                except:
                    continue
            
            # Extraer reacciones/likes 
            reactions = self._extract_reactions_improved(post_element)
            comment_count = self._get_comment_count(post_element)
            author = PAGE
            author_selectors = [
                ".//h3[contains(@class, 'x1heor9g')]//a",
                ".//span[contains(@class, 'x3nfvp2')]//a",
                ".//h2[contains(@class, 'x1heor9g')]//span"
            ]
            
            for selector in author_selectors:
                try:
                    author_elements = post_element.find_elements(By.XPATH, selector)
                    for author_elem in author_elements:
                        if author_elem and len(author_elem.text) > 1:
                            author = author_elem.text.strip()
                            break
                    if author != PAGE:
                        break
                except:
                    continue
                
            return {
                "url_post": post_url,
                "author": author,
                "texto_post": post_text,
                "fecha_post": post_date,
                "reacciones": reactions,
                "total_comentarios": comment_count
            }
        except Exception as e:
            Logger.error(f"Error extrayendo datos del post: {e}")
            return None
    def _click_ver_mas_comentarios(self, post_element):
        """
        Función especializada para hacer clic en el botón "Ver más comentarios".
        Utiliza múltiples estrategias, incluyendo el XPath específico proporcionado.
        """
        Logger.info("Buscando botón 'Ver más comentarios'...")
        
        # Lista de selectores para el botón "Ver más comentarios"
        ver_mas_selectors = [
            # XPath específico proporcionado (simplificado para mayor compatibilidad)
            "//div[contains(@class, 'x1i10hfl')][contains(@class, 'xjbqb8w')]//span[contains(text(), 'más comentarios')]",
            
            # Selectores alternativos
            ".//span[contains(text(), 'Ver más comentarios')]",
            ".//span[contains(text(), 'View more comments')]",
            ".//div[contains(text(), 'Ver más comentarios')]",
            ".//div[contains(text(), 'View more comments')]",
            ".//div[@role='button'][contains(., 'más comentarios')]",
            ".//div[@role='button'][contains(., 'more comments')]",
            
            # Búsqueda específica dentro del post
            ".//div[contains(@class, 'x1i10hfl')]//span[contains(text(), 'comentarios')]",
            ".//div[contains(@role, 'button')]//span[contains(text(), 'más')]"
        ]
        
        # Estrategia 1: Búsqueda dentro del post
        for selector in ver_mas_selectors:
            try:
                buttons = post_element.find_elements(By.XPATH, selector)
                for button in buttons:
                    if button.is_displayed():
                        Logger.info(f"Botón 'Ver más comentarios' encontrado con selector: {selector}")
                        
                        # Asegurarse de que el botón es visible scrolleando hacia él
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        
                        # Intentar hacer clic con múltiples métodos
                        try:
                            # Método 1: Clic directo
                            button.click()
                            Logger.success("Clic directo exitoso en 'Ver más comentarios'")
                            time.sleep(1.5)  # Esperar a que carguen los comentarios
                            return True
                        except:
                            try:
                                # Método 2: JavaScript click
                                self.driver.execute_script("arguments[0].click();", button)
                                Logger.success("Clic JavaScript exitoso en 'Ver más comentarios'")
                                time.sleep(1.5)
                                return True
                            except:
                                try:
                                    # Método 3: ActionChains
                                    actions = ActionChains(self.driver)
                                    actions.move_to_element(button).click().perform()
                                    Logger.success("Clic ActionChains exitoso en 'Ver más comentarios'")
                                    time.sleep(1.5)
                                    return True
                                except:
                                    Logger.warning("No se pudo hacer clic con ningún método")
            except:
                continue
                
        # Estrategia 2: Búsqueda en todo el documento (cuando el botón está fuera del post_element)
        Logger.info("Buscando 'Ver más comentarios' en toda la página...")
        try:
            # Buscar específicamente el botón en toda la página
            ver_mas_buttons = self.driver.find_elements(By.XPATH, 
                "//span[contains(text(), 'Ver más comentarios') or contains(text(), 'View more comments')]")
            
            for button in ver_mas_buttons:
                if button.is_displayed():
                    # Verificar si el botón está cerca del post actual
                    is_related = self.driver.execute_script("""
                        var button = arguments[0];
                        var post = arguments[1];
                        var postRect = post.getBoundingClientRect();
                        var buttonRect = button.getBoundingClientRect();
                        
                        // El botón debe estar cerca del post verticalmente
                        return Math.abs(buttonRect.top - postRect.bottom) < 500;
                    """, button, post_element)
                    
                    if is_related:
                        Logger.info("Botón 'Ver más comentarios' encontrado cerca del post actual")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        
                        # Intentar hacer clic con JavaScript (más confiable para elementos fuera del viewport)
                        try:
                            self.driver.execute_script("arguments[0].click();", button)
                            Logger.success("Clic exitoso en 'Ver más comentarios' (búsqueda global)")
                            time.sleep(1.5)
                            return True
                        except:
                            pass
        except:
            pass
        
        # Estrategia 3: Usar el XPath completo específico que proporcionaste
        try:
            exact_xpath = "//*[@id='mount_0_0_K0']/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[4]/div[2]/div/div[2]/div[2]/div[3]/div/div/div/div/div/div/div/div/div/div/div/div[13]/div/div/div[4]/div/div/div[3]/div/div[2]/span/span"
            
            # Modificar para que sea más flexible (los IDs dinámicos pueden cambiar)
            flexible_xpath = "//div[@id[starts-with(., 'mount_0_')]]/div/div[1]/div/div[3]//span/span[contains(text(), 'comentarios')]"
            
            ver_mas_button = None
            try:
                ver_mas_button = self.driver.find_element(By.XPATH, flexible_xpath)
            except:
                try:
                    # Intentar con el XPath exacto como último recurso
                    ver_mas_button = self.driver.find_element(By.XPATH, exact_xpath)
                except:
                    pass
            
            if ver_mas_button and ver_mas_button.is_displayed():
                Logger.info("Botón 'Ver más comentarios' encontrado con XPath específico")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ver_mas_button)
                time.sleep(0.5)
                
                try:
                    self.driver.execute_script("arguments[0].click();", ver_mas_button)
                    Logger.success("Clic exitoso en 'Ver más comentarios' (XPath específico)")
                    time.sleep(1.5)
                    return True
                except:
                    pass
        except:
            pass
            
        Logger.warning("No se pudo encontrar o hacer clic en el botón 'Ver más comentarios'")
        return False
    def _expandir_todos_comentarios(self, post_element):
       """
       Intenta expandir todos los comentarios de un post usando múltiples estrategias.
       Hace varios intentos para asegurar que se muestren todos los comentarios.
       
       Args:
           post_element: El elemento del post donde expandir los comentarios
       """
       if not LOAD_COMMENTS:
           return
           
       Logger.info("Iniciando expansión completa de comentarios...")
       
       # Paso 1: Hacer clic en el contador de comentarios para expandirlos inicialmente
       try:
           comment_counter = self._find_element_with_multiple_xpaths(
               post_element, 
               [".//span[contains(text(), 'comentarios')]", 
               ".//span[contains(text(), 'comments')]"]
           )
           
           if comment_counter:
               self._human_click(comment_counter)
               time.sleep(2)
               Logger.info("Contador de comentarios expandido")
       except:
           pass
       
       # Paso 2: Hacer varios intentos para expandir todos los comentarios
       max_attempts = 5  # Número máximo de intentos
       for attempt in range(max_attempts):
           Logger.info(f"Intento {attempt+1}/{max_attempts} de expandir comentarios")
           
           # Intentar hacer clic en el botón "Ver más comentarios"
           click_success = self._click_ver_mas_comentarios(post_element)
           
           if not click_success:
               # Si no se pudo hacer clic, verificar si ya están todos expandidos
               # Esto se hace buscando el botón "Ver más comentarios" de nuevo
               try:
                   ver_mas_visible = False
                   ver_mas_buttons = self.driver.find_elements(By.XPATH, 
                       "//span[contains(text(), 'Ver más comentarios') or contains(text(), 'View more comments')]")
                   
                   for button in ver_mas_buttons:
                       if button.is_displayed():
                           # Verificar si está relacionado con el post actual
                           is_related = self.driver.execute_script("""
                               var button = arguments[0];
                               var post = arguments[1];
                               var postRect = post.getBoundingClientRect();
                               var buttonRect = button.getBoundingClientRect();
                               return Math.abs(buttonRect.top - postRect.bottom) < 500;
                           """, button, post_element)
                           
                           if is_related:
                               ver_mas_visible = True
                               break
                   
                   if not ver_mas_visible:
                       Logger.success("Todos los comentarios expandidos o no hay más para expandir")
                       break  # Salir del bucle si no hay más botones visibles
               except:
                   # Si hay error al verificar, asumir que ya están expandidos
                   break
           
           # Breve pausa entre intentos
           time.sleep(1.5)
       
       # Paso 3: Expandir "Ver más" en comentarios individuales
       try:
           see_more_buttons = post_element.find_elements(By.XPATH, 
               ".//div[contains(@class, 'x1i10hfl')][contains(text(), 'Ver más') or contains(text(), 'See more')]")
           
           for i, button in enumerate(see_more_buttons[:10]):  # Limitar a 10 para optimizar
               if button.is_displayed():
                   Logger.info(f"Expandiendo texto en comentario {i+1}")
                   self._human_click(button)
                   time.sleep(0.3)
       except:
           pass
       
       # Paso 4: Expandir respuestas (replies)
       try:
           reply_buttons = post_element.find_elements(By.XPATH, 
               ".//span[contains(text(), 'respuesta') or contains(text(), 'reply') or contains(text(), 'Responder')]")
           
           for i, button in enumerate(reply_buttons[:5]):  # Limitar a 5 para optimizar
               if button.is_displayed():
                   Logger.info(f"Expandiendo respuestas {i+1}")
                   self._human_click(button)
                   time.sleep(0.8)
       except:
           pass
           
       Logger.info("Proceso de expansión de comentarios completado")
    def _extract_reactions_improved(self, post_element):
        """ Metodo para extraer numero total de reacciones (likes) con diferentes estrategias"""
        reactions = "0"
        try:
            reaction_selectors = [ 
                ".//span[contains(@class, 'x1e558r4')]",
                ".//span[@class='xt0b8zv xvy4d1p']",
                ".//span[contains(@class, 'x16n37ib')][contains(@class, 'x1rg5ohu')]",
                
            ]
        except:
            pass
    
    def _get_comment_count(self, post_element): 
       """
       Extrae el número total de comentarios del post
       """
       comment_count = "0"
       try:
           count_selectors = [
               ".//span[contains(text(), 'comentarios')]/span[1]",
               ".//span[contains(text(), 'comments')]/span[1]",
               ".//a[contains(@href, 'comments')]/span[1]",
               ".//*[contains(text(), 'comentarios') or contains(text(), 'comments')]",
               ".//div[contains(@class, 'x1i10hfl')]//span[contains(text(), 'comment') or contains(text(), 'comentario')]"
           ]
           
           for selector in count_selectors:
               try:
                   elements = post_element.find_elements(By.XPATH, selector)
                   for element in elements:
                       if element.is_displayed():
                           text = element.text.strip()
                           import re
                           nums = re.findall(r'\d+', text)
                           if nums:
                               return nums[0]
               except:
                   continue

           try:
               count_js = self.driver.execute_script("""
                   const postElement = arguments[0];
                   const commentElements = postElement.querySelectorAll('span:not([style*="display:none"]):not([style*="visibility:hidden"])');
                                                     
                   for (const elem of commentElements){
                       const text = elem.textContent || '';
                       if ((text.includes('comment') || text.includes('comentario')) && /\\d/.test(text)) {
                           const match = text.match(/\\d+/);
                           return match ? match[0] : "0";
                       }
                   }                             
                   return "0";                                                                                                      
               """, post_element)
               
               if count_js and count_js != "0" and any(c.isdigit() for c in count_js):
                   return count_js
           except:
               pass
               
       except Exception as e:
           Logger.error(f"Error obteniendo contador de comentarios: {e}")
       
       return comment_count

    def _extract_comments(self, post_element):
       """
       Extrae comentarios con estrategia optimizada para mayor velocidad.
       """
       if not LOAD_COMMENTS:
           return {}
               
       comments_data = {}
       
       try:
           # Limitar a solo buscar comentarios en el post, no en diálogos
           comment_elements = self._find_element_with_multiple_xpaths(
               post_element, self.selectors["comments"], single=False)
               
           if not comment_elements:
               return comments_data
           
           # Limitar a solo 10 comentarios para optimización
           comment_elements = comment_elements[:10]
           
           for i, comment in enumerate(comment_elements):
               try:
                   # Extraer nombre de usuario con caché
                   username = "Usuario desconocido"
                   user_selectors = [
                       ".//a[contains(@href, '/user/')]",
                       ".//span[contains(@class, 'xt0psk2')]",
                       ".//h3[contains(@class, 'x1heor9g')]//span",
                       ".//a[@role='link']//span[contains(@class, 'x3nfvp2')]"
                   ]
                   
                   # Intentar primero con el selector cacheado
                   if self._comment_selector_cache['user']:
                       try:
                           user_elements = comment.find_elements(By.XPATH, self._comment_selector_cache['user'])
                           for user_elem in user_elements:
                               if user_elem.is_displayed() and user_elem.text and len(user_elem.text) > 1:
                                   username = user_elem.text.strip()
                                   break
                       except:
                           pass
                   
                   # Si no funciona el caché, probar otros selectores
                   if username == "Usuario desconocido":
                       for selector in user_selectors:
                           try:
                               user_elements = comment.find_elements(By.XPATH, selector)
                               for user_elem in user_elements:
                                   if user_elem.is_displayed() and user_elem.text and len(user_elem.text) > 1:
                                       username = user_elem.text.strip()
                                       self._comment_selector_cache['user'] = selector
                                       break
                               if username != "Usuario desconocido":
                                   break
                           except:
                               continue
                   
                   # Extraer texto del comentario con caché
                   comment_text = "No disponible"
                   text_selectors = [
                       ".//div[contains(@class, 'xdj266r') and not(contains(@class, 'xt0psk2'))]",
                       ".//div[@dir='auto' and not(contains(@class, 'xt0psk2'))]//span",
                       ".//div[contains(@class, 'x1cy8zhl')]//div[@dir='auto' and not(ancestor::h3)]",
                       ".//div[contains(@class, 'xdj266r')]",
                       ".//div[contains(@dir, 'auto')]",
                       ".//div[contains(@class, 'x1cy8zhl')]//div[@dir='auto']"
                   ]
                   
                   # Intentar primero con el selector cacheado
                   if self._comment_selector_cache['text']:
                       try:
                           text_elements = comment.find_elements(By.XPATH, self._comment_selector_cache['text'])
                           for text_elem in text_elements:
                               if text_elem.is_displayed() and text_elem.text and len(text_elem.text.strip()) > 1:
                                   comment_text = text_elem.text.strip()
                                   break
                       except:
                           pass
                   
                   # Si no funciona el caché, probar otros selectores
                   if comment_text == "No disponible":
                       for selector in text_selectors:
                           try:
                               text_elements = comment.find_elements(By.XPATH, selector)
                               for text_elem in text_elements:
                                   if text_elem.is_displayed() and text_elem.text and len(text_elem.text.strip()) > 1:
                                       comment_text = text_elem.text.strip()
                                       self._comment_selector_cache['text'] = selector
                                       break
                               if comment_text != "No disponible":
                                   break
                           except:
                               continue
                   
                   # Extraer fecha del comentario (simplificado)
                   comment_date = "No disponible"
                   date_selectors = [
                       ".//a//span[contains(@class, 'x4k7w5x')]",
                       ".//span[contains(@class, 'x1qjc9v5')]//a"
                   ]
                   
                   for selector in date_selectors:
                       try:
                           date_elements = comment.find_elements(By.XPATH, selector)
                           for date_elem in date_elements:
                               if date_elem.is_displayed() and date_elem.text:
                                   comment_date = date_elem.text.strip()
                                   break
                               
                               # Intentar obtener atributo title
                               title_attr = date_elem.get_attribute("title")
                               if title_attr and len(title_attr) > 2:
                                   comment_date = title_attr
                                   break
                           if comment_date != "No disponible":
                               break
                       except:
                           continue

                   # Extraer likes del comentario (simplificado)
                   comment_likes = "0"
                   likes_selectors = [
                       ".//span[contains(@class, 'x16hj40l')]",
                       ".//span[contains(@class, 'xt0b8zv')]"
                   ]
                   
                   for selector in likes_selectors:
                       try:
                           likes_elements = comment.find_elements(By.XPATH, selector)
                           for like_elem in likes_elements:
                               like_text = like_elem.text.strip()
                               if like_text and any(c.isdigit() for c in like_text):
                                   comment_likes = ''.join(c for c in like_text if c.isdigit() or c == 'K' or c == 'M')
                                   
                                   # Convertir K y M a números
                                   if 'K' in comment_likes:
                                       comment_likes = str(int(float(comment_likes.replace('K', '')) * 1000))
                                   elif 'M' in comment_likes:
                                       comment_likes = str(int(float(comment_likes.replace('M', '')) * 1000000))
                                       
                                   if not comment_likes:
                                       comment_likes = "0"
                                   break
                           if comment_likes != "0":
                               break
                       except:
                           continue
                   
                   # Verificar si hay imagen en el comentario (simplificado)
                   has_image = False
                   try:
                       image_selectors = [
                           ".//div[@data-visualcompletion='media-vc-image']",
                           ".//img[contains(@src, 'scontent')]"
                       ]
                       
                       for selector in image_selectors:
                           image_elements = comment.find_elements(By.XPATH, selector)
                           if image_elements and any(img.is_displayed() for img in image_elements):
                               has_image = True
                               break
                   except:
                       pass
                   
                   # Guardar comentario en el formato adecuado
                   comment_key = f"{username}_{i}"  # Prevenir duplicados con índice
                   if has_image:
                       comments_data[comment_key] = {
                           "texto": comment_text,
                           "fecha": comment_date,
                           "likes": comment_likes,
                           "imagen": True
                       }
                   else:
                       comments_data[comment_key] = {
                           "texto": comment_text,
                           "fecha": comment_date,
                           "likes": comment_likes
                       }
                   
               except Exception as e:
                   continue
           
           return comments_data
           
       except Exception as e:
           Logger.error(f"Error extrayendo comentarios: {e}")
           return comments_data
    def _post_in_date_range(self, post_data):
        """
        Verifica si un post está dentro del rango de fechas configurado.
        Optimizado para mayor velocidad y precisión.
        """
        if "fecha_post" not in post_data or not post_data["fecha_post"]:
            return True  # Si no hay fecha, asumimos que está en rango
            
        fecha_texto = post_data["fecha_post"]
        
        # Optimización: Verificar primero si es una fecha reciente
        # Si encontramos términos de fechas relativas recientes, asumimos que está en el rango
        relative_terms = ["yesterday", "ayer", "hrs", "hour", "hora", "min", "sec", "seg", 
                         "today", "hoy", "just now", "ahora", "momento"]
        if any(term in fecha_texto.lower() for term in relative_terms):
            return True
            
        post_date = None
        
        # Intentar extraer fecha con método optimizado
        try:
            # Formato ISO completo (2023-01-15T14:30:00)
            if "T" in fecha_texto and ":" in fecha_texto:
                post_date = datetime.fromisoformat(fecha_texto.replace("Z", "+00:00"))
            
            # Formato común en español (15 de enero de 2023)
            elif " de " in fecha_texto.lower():
                meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, 
                        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
                partes = fecha_texto.lower().split(" de ")
                if len(partes) >= 3:
                    try:
                        dia = int(''.join(c for c in partes[0] if c.isdigit()))
                        mes = None
                        for mes_nombre, mes_num in meses.items():
                            if mes_nombre in partes[1]:
                                mes = mes_num
                                break
                        ano = int(''.join(c for c in partes[2] if c.isdigit()))
                        if dia and mes and ano:
                            post_date = datetime(ano, mes, dia)
                    except:
                        pass
            
            # Formato de fecha con día y mes abreviado (15 Jan 2023, 15 Ene 2023)
            elif len(fecha_texto.split()) == 3:
                # Extraer rápidamente partes numéricas para intentar parsear como fecha
                parts = fecha_texto.split()
                if any(c.isdigit() for c in parts[0]) and any(c.isdigit() for c in parts[2]):
                    try:
                        # Intentar métodos rápidos para extraer la fecha
                        for fmt in ["%d %b %Y", "%d %B %Y"]:
                            try:
                                post_date = datetime.strptime(fecha_texto, fmt)
                                break
                            except:
                                continue
                    except:
                        pass
            
            # Si todavía no tenemos fecha, extraer números que parezcan año para simplificar
            if post_date is None:
                import re
                year_match = re.search(r'\b(20\d{2})\b', fecha_texto)
                if year_match:
                    year = int(year_match.group(1))
                    # Si solo tenemos el año, verificar si está en el rango
                    if start_date.year <= year <= end_date.year:
                        return True
                
        except:
            # Si hay error, incluimos el post
            return True
        
        # Verificar si está en rango
        if post_date:
            return start_date <= post_date <= end_date
        
        # Por defecto incluir
        return True
    def login(self):
        """
        Inicia sesión en Facebook con manejo optimizado.
        """
        Logger.info("Iniciando proceso de login en Facebook...")
        try:
            # Cargar la página de login
            self.driver.get("https://www.facebook.com/")
            self._human_delay(1, 1.5)  # Reducido
            
            # Aceptar cookies si aparece el diálogo
            self._handle_popups()
            
            # Verificar si ya estamos loggeados
            if self._check_already_logged_in():
                Logger.success("Ya hay una sesión activa. Omitiendo login.")
                return True
                
            # Buscar e introducir email
            try:
                email_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                self._human_click(email_input)
                
                # Escribir email con velocidad optimizada
                for char in FB_EMAIL:
                    email_input.send_keys(char)
                    time.sleep(random.uniform(0.01, 0.03))  # Más rápido
                    
                self._human_delay(0.1, 0.3)  # Reducido
                
                # Buscar e introducir contraseña
                password_input = self.driver.find_element(By.ID, "pass")
                self._human_click(password_input)
                
                # Escribir contraseña con velocidad optimizada
                for char in FB_PASS:
                    password_input.send_keys(char)
                    time.sleep(random.uniform(0.01, 0.03))  # Más rápido
                    
                self._human_delay(0.1, 0.3)  # Reducido
                
                # Hacer clic en el botón de login
                login_button = self.driver.find_element(By.XPATH, "//button[@name='login']")
                self._human_click(login_button)
                
                # Esperar a que complete el login
                self._human_delay(2, 3)  # Optimizado pero suficiente
                
                # Verificar resultado del login
                if "login" in self.driver.current_url or "checkpoint" in self.driver.current_url:
                    self.save_screenshot("login_checkpoint")
                    
                    if "checkpoint" in self.driver.current_url:
                        Logger.error("Checkpoint de seguridad detectado. Verificación adicional requerida.")
                        self._handle_checkpoint()
                    else:
                        Logger.error("Error de autenticación. Verifica credenciales.")
                        
                    return self._check_already_logged_in()
                    
                # Manejar diálogos post-login
                self._handle_popups()
                
                # Verificar login exitoso
                if self._check_already_logged_in() or "facebook.com" in self.driver.current_url:
                    Logger.success("Login completado exitosamente")
                    return True
                else:
                    Logger.error("Login falló - URL inesperada")
                    self.save_screenshot("login_failed")
                    return False
            except Exception as e:
                Logger.error(f"Error en proceso de login: {e}")
                self.save_screenshot("login_exception")
                return False                
        except Exception as e:
            Logger.error(f"Error en proceso de login: {e}")
            self.save_screenshot("login_exception")
            return False

    def _handle_checkpoint(self):
        """Maneja la pantalla de checkpoint/2FA de Facebook"""
        try:
            # Buscar campo de código
            code_input = self.driver.find_element(By.XPATH, "//input[contains(@id, 'approvals_code')]")
            if code_input:
                Logger.info("Se requiere código de verificación en dos factores (2FA)")
                auth_code = input("Por favor, ingrese el código de autenticación 2FA: ")
                
                for char in auth_code:
                    code_input.send_keys(char)
                    time.sleep(random.uniform(0.03, 0.07))
                    
                # Buscar y hacer clic en botón de continuar
                continue_button = self.driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'Continue') or contains(text(), 'Submit') or contains(text(), 'Continuar')]")
                self._human_click(continue_button)
                self._human_delay(1.5, 2)
                
                # Verificar si hay que guardar navegador
                save_browser_button = self.driver.find_elements(By.XPATH,
                    "//button[contains(text(), 'Save Browser') or contains(text(), 'Not Now') or contains(text(), 'Guardar')]")
                if save_browser_button:
                    self._human_click(save_browser_button[0])
                    self._human_delay(0.8, 1.2)
                
                return True
        except Exception as e:
            Logger.error(f"Error manejando checkpoint: {e}")
            return False
    
    def scrape_page(self, page_name):
        """
        Extrae posts de una página de Facebook - Versión optimizada.
        """
        Logger.info(f"Iniciando extracción de la página: {page_name}")
        
        try:
            # 1. Buscar y navegar a la página usando el buscador
            search_successful = self._search_and_navigate_to_page(page_name)
            
            # Si la búsqueda falla, intentar navegación directa
            if not search_successful:
                Logger.info("Intentando navegación directa a la página...")
                self.driver.get(f"https://www.facebook.com/{page_name}/")
                self._human_delay(1.2, 1.8)
            
            # 2. Navegar a la sección de posts
            if "/posts" not in self.driver.current_url.lower():
                Logger.info("Navegando a la sección de posts...")
                direct_posts_url = f"https://www.facebook.com/{page_name}/posts/"
                self.driver.get(direct_posts_url)
                self._human_delay(1.2, 1.8)
            
            # 3. Extraer posts uno por uno usando el método mejorado
            posts_data = self._extract_posts_one_by_one(page_name)
            
            # 4. Mensaje final
            if posts_data:
                Logger.success(f"Extracción completada: {len(posts_data)} posts válidos extraídos de {page_name}")
            else:
                Logger.warning(f"Finalizado sin posts válidos extraídos de {page_name}")
            
            return posts_data
            
        except Exception as e:
            Logger.error(f"Error en scrape_page: {e}")
            self.save_screenshot("scrape_page_error")
            return []
    def save_to_csv(self, data, page):
       """
       Guarda los datos extraídos en un archivo CSV con manejo optimizado.
       """
       if not data:
           Logger.warning("No hay datos para guardar.")
           return None

       try:
           # Preparar los datos para CSV
           csv_data = []
           for post in data:
               # Convertir el diccionario de comentarios a formato JSON
               if "comentarios" in post:
                   comentarios_json = json.dumps(post["comentarios"], ensure_ascii=False)
               else:
                   comentarios_json = "{}"
               
               # Crear fila de datos
               row = {
                   "url_post": post.get("url_post", ""),
                   "author": post.get("author", ""),
                   "texto_post": post.get("texto_post", "").replace("\n", " ").strip(),
                   "fecha_post": post.get("fecha_post", ""),
                   "reacciones": post.get("reacciones", ""),
                   "comentarios": comentarios_json,
                   "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
               }
               csv_data.append(row)

           # Crear DataFrame y guardar como CSV
           df = pd.DataFrame(csv_data)
           date_str = datetime.now().strftime("%d_%m_%Y")
           filename = f"facebook_posts_{page.lower()}_{date_str}.csv"

           # Guardar con manejo de caracteres especiales
           df.to_csv(filename, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
           
           # Obtener ruta absoluta para facilitar localización
           abs_path = os.path.abspath(filename)
           Logger.success(f"Se guardaron {len(data)} filas en {filename}")
           Logger.info(f"Ruta completa: {abs_path}")
           
           # Generar comando para abrir en Finder (macOS) o Explorer (Windows)
           if sys.platform == 'darwin':  # macOS
               Logger.info(f"Para abrir en Finder, ejecuta: open -R \"{abs_path}\"")
           elif sys.platform == 'win32':  # Windows
               Logger.info(f"Para abrir en Explorer, ejecuta: explorer /select,\"{abs_path}\"")
           
           return abs_path
           
       except Exception as e:
           Logger.error(f"Error guardando datos en CSV: {e}")
           return None
# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    # Banner de inicio
    print("\n" + "="*80)
    print("  FACEBOOK SCRAPER AVANZADO (OPTIMIZADO)  ".center(80, "="))
    print("  Extrae posts y comentarios con alta velocidad y precisión  ".center(80, "-"))
    print("="*80 + "\n")
    
    # Mostrar configuración actual
    print(f"📋 Configuración:")
    print(f"   - Cuentas a extraer: {', '.join(PAGES)}")
    print(f"   - Periodo: {START_DATE} al {END_DATE}")
    print(f"   - Máximo de posts: {MAX_POSTS}")
    print(f"   - Navegador: {BROWSER_TYPE}")
    print(f"   - Modo headless: {'Activado' if ENABLE_HEADLESS else 'Desactivado'}")
    print(f"   - Cargar comentarios: {'Si' if LOAD_COMMENTS else 'No'}")
    print("\n" + "-"*80 + "\n")
    
    # Crear instancia del scraper
    scraper = FacebookScraper()
    
    try:
        # 1) Login
        if not scraper.login():
            Logger.fatal_error("Login fallido. Abortando operación.")
            sys.exit(1)
            
        # Pequeña pausa después del login
        time.sleep(2)

        # 2) Comienza el scraper para cada página
        results = {}
        for page in PAGES:
            Logger.info(f"Iniciando extracción de página: {page}")
            posts = scraper.scrape_page(page)
            results[page] = len(posts)

            Logger.info(f"Guardando datos de {page} ({len(posts)} posts)")
            scraper.save_to_csv(posts, page)
            
            # Pausa entre páginas para evitar sobrecargar
            if page != PAGES[-1]:
                pause_time = random.uniform(3, 5)  # Reducido
                Logger.info(f"Pausa de {pause_time:.1f} segundos antes de la siguiente página...")
                time.sleep(pause_time)
            
        # 3) Mostrar resumen final
        print("\n" + "="*50)
        print("  RESUMEN DE EXTRACCIÓN  ".center(50, "="))
        for page, count in results.items():
            status = "✅" if count > 0 else "⚠️"
            print(f"{status} {page}: {count} posts extraídos")
        print("="*50 + "\n")
        
        Logger.success("Proceso completado exitosamente")

    except KeyboardInterrupt:
        Logger.warning("Operación interrumpida por el usuario")
    except Exception as e:
        Logger.fatal_error(f"Error crítico en la ejecución: {e}")
    finally:
        # Captura final para avisarle al usuario que se cerrará el navegador
        try:
            input("\nPresiona Enter para cerrar el navegador y finalizar...")
        except:
            pass
            
        try:
            scraper.driver.quit()
            Logger.info("Navegador cerrado correctamente")
        except:
            Logger.warning("Error al cerrar el navegador")