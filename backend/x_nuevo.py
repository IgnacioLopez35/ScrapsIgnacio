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

# Deshabilitar verificación SSL para evitar problemas de certificados
ssl._create_default_https_context = ssl._create_unverified_context

# Configuración de la ruta para importaciones
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.abspath(os.path.join(ruta_actual, "../../../"))
sys.path.append(ruta_raiz)

# Intentar importar módulos propios
try:
    from modules.agents import agents
except ImportError:
    pass  # Silenciar error si no existe

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

# Credenciales de X (Twitter)
X_EMAIL = "tucorreo@email.com"
X_USERNAME = "tu_nombre_usuario"
X_PASS = "tu_contraseña"

# Lista de usuarios a extraer
USERS = [
    "elonmusk"  # Reemplaza con el usuario que quieras extraer
]
USER = "elonmusk"

# Filtros avanzados
START_DATE = "01-01-2025"  # Formato DD-MM-YYYY, tweets a partir de esta fecha
END_DATE = "30-03-2025"    # Formato DD-MM-YYYY, tweets hasta esta fecha
MAX_TWEETS = 100           # Número máximo de tweets a extraer
NUM_SCROLLS = 15           # Reducido para optimizar
SAVE_SCREENSHOTS = False   # Desactivado por defecto para mejorar velocidad
BROWSER_TYPE = 'Chrome'    # Tipo de navegador: 'Chrome' únicamente para uc
ENABLE_HEADLESS = False    # Activar modo headless (sin interfaz gráfica)
MAX_RETRIES = 3            # Número máximo de reintentos para operaciones que pueden fallar
LOAD_REPLIES = True        # Establece a False para una extracción super rápida sin respuestas

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
            
            log_file = os.path.join(log_dir, f"twitter_scraper_{datetime.now().strftime('%Y%m%d')}.log")
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
class TwitterScraper:
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
        self._reply_selector_cache = {
            'user': None,
            'text': None,
            'date': None,
            'likes': None
        }
        
        # Diccionario con selectores actualizados para Twitter/X
        self.selectors = {
            # Selectores para tweets
            "tweets": [
                ".//article[@data-testid='tweet']",
                ".//div[@data-testid='cellInnerDiv']//article",
                ".//div[@data-testid='tweetText']//ancestor::article",
                ".//article[contains(@aria-labelledby, 'id__')]"
            ],
            # Selectores para contenido de tweets
            "tweet_content": [
                ".//div[@data-testid='tweetText']",
                ".//div[@lang and @dir='auto']"
            ],
            # Selectores para fechas de tweets
            "tweet_dates": [
                ".//time",
                ".//a[contains(@href, '/status/')]//time"
            ],
            # Selectores para métricas (retweets, likes, etc.)
            "metrics": [
                ".//div[@role='group']//span[@data-testid='app-text-transition-container']",
                ".//div[contains(@aria-label, 'likes') or contains(@aria-label, 'replies') or contains(@aria-label, 'Retweets')]"
            ],
            # Selectores para respuestas
            "replies": [
                ".//article[@data-testid='tweet'][contains(@tabindex, '-1')]",
                ".//div[@data-testid='cellInnerDiv']//article[not(@data-testid='tweet')]"
            ],
            # Selectores para expandir respuestas
            "expand_replies": [
                ".//div[@role='button'][contains(text(), 'Show replies') or contains(text(), 'Mostrar respuestas')]",
                ".//div[@role='button'][contains(text(), 'View more replies') or contains(text(), 'Ver más respuestas')]",
                ".//div[@role='button'][contains(text(), 'Show more replies') or contains(text(), 'Mostrar más respuestas')]"
            ],
            # Selectores para "Ver más" en tweets largos
            "see_more": [
                ".//div[@role='button'][contains(text(), 'Show more') or contains(text(), 'Mostrar más')]",
                ".//span[contains(text(), 'Show more') or contains(text(), 'Mostrar más')]"
            ],
            # Selectores para medios (imágenes, videos)
            "media": [
                ".//div[@data-testid='tweetPhoto']",
                ".//div[@data-testid='videoComponent']"
            ]
        }

    def _setup_screenshot_dir(self):
        """Crea directorio para capturas de pantalla"""
        if not SAVE_SCREENSHOTS:
            return None
            
        screenshot_dir = os.path.join("screenshots", f"twitter_{self.session_id}")
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

        # Configuraciones específicas para Twitter/X
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            "profile.managed_default_content_settings.images": 1,       # Cargar imágenes
            "profile.managed_default_content_settings.javascript": 1,   # Habilitar JavaScript
            "profile.managed_default_content_settings.plugins": 1,      # Habilitar plugins
            "profile.managed_default_content_settings.popups": 2,       # Bloquear popups
            "profile.managed_default_content_settings.geolocation": 2,  # Bloquear geolocalización
            "profile.managed_default_content_settings.media_stream": 2, # Bloquear acceso a cámara/micro
            "profile.default_content_setting_values.cookies": 1,        # Aceptar cookies
            "profile.block_third_party_cookies": False                  # Permitir cookies de terceros
        }
        options.add_experimental_option("prefs", prefs)

        # Usar perfil persistente para evitar login frecuente
        profile_dir = os.path.join(os.path.expanduser("~"), "twitter-scraper-profile")
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
            
            # Simular idiomas comunes para Twitter
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
        Devuelve un User-Agent optimizado para Twitter/X.
        """
        try:
            twitter_agents = [
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
            return random.choice(twitter_agents)
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
        """Maneja popups y diálogos comunes de Twitter/X."""
        try:
            # Lista de posibles popups y sus selectores
            popups = {
                "cookies": [
                    "//div[@role='button'][contains(text(), 'Accept')]",
                    "//div[@role='button'][contains(text(), 'Aceptar')]",
                    "//span[contains(text(), 'Accept all cookies')]//ancestor::div[@role='button']"
                ],
                "onboarding": [
                    "//div[@role='button'][contains(text(), 'Next')]",
                    "//div[@role='button'][contains(text(), 'Siguiente')]",
                    "//div[@role='button'][contains(text(), 'Skip for now')]",
                    "//div[@role='button'][contains(text(), 'Omitir por ahora')]"
                ],
                "notifications": [
                    "//div[@role='button'][contains(text(), 'Not now')]",
                    "//div[@role='button'][contains(text(), 'Ahora no')]"
                ],
                "modals": [
                    "//div[@role='button'][contains(text(), 'Close') or contains(text(), 'Cerrar')]",
                    "//div[@data-testid='app-bar-close']"
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
        """Verifica si ya hay una sesión activa de Twitter/X"""
        try:
            # Buscar elementos que indiquen sesión activa
            profile_indicators = [
                "//div[@data-testid='SideNav_AccountSwitcher_Button']",
                "//a[@data-testid='AppTabBar_Profile_Link']",
                "//a[@aria-label='Profile']",
                "//a[@aria-label='Perfil']",
                "//div[@data-testid='primaryColumn']//h2[contains(text(), 'Home') or contains(text(), 'Inicio')]"
            ]
            
            for indicator in profile_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                if elements and any(e.is_displayed() for e in elements):
                    return True
                    
            return False
        except:
            return False
            
    def _navigate_to_user(self, username):
        """
        Navega directamente al perfil de un usuario en X (Twitter).
        """
        Logger.info(f"Navegando al perfil de: @{username}")
        try:
            # Navegar directamente al perfil de usuario
            self.driver.get(f"https://twitter.com/{username}")
            self._human_delay(1.5, 2)
            
            # Verificar si estamos en la página correcta
            current_url = self.driver.current_url.lower()
            if username.lower() in current_url:
                Logger.success(f"Navegación al perfil de @{username} exitosa")
                return True
            else:
                Logger.warning(f"La URL actual no contiene el nombre de usuario: {current_url}")
                
                # Intentar navegar a través de la búsqueda
                self.driver.get(f"https://twitter.com/search?q=%40{username}&src=typed_query&f=user")
                self._human_delay(1.5, 2)
                
                # Buscar resultados que coincidan con el usuario
                user_result_selectors = [
                    f"//span[contains(text(), '@{username}')]//ancestor::a",
                    f"//a[contains(@href, '/{username}')]",
                    "//div[@data-testid='UserCell']//a"
                ]
                
                for selector in user_result_selectors:
                    try:
                        user_links = self.driver.find_elements(By.XPATH, selector)
                        for link in user_links:
                            if link.is_displayed() and username.lower() in link.get_attribute("href").lower():
                                self._human_click(link)
                                self._human_delay(1.5, 2)
                                
                                # Verificar si ahora estamos en el perfil
                                current_url = self.driver.current_url.lower()
                                if username.lower() in current_url:
                                    Logger.success(f"Navegación al perfil de @{username} exitosa mediante búsqueda")
                                    return True
                    except:
                        continue
                
                Logger.error(f"No se pudo navegar al perfil de @{username}")
                return False
        
        except Exception as e:
            Logger.error(f"Error navegando al perfil: {e}")
            return False
    
    def _get_tweet_id(self, tweet_element):
        """Extrae el ID único de un tweet para identificarlo"""
        try:
            # Intentar extraer del atributo de datos
            tweet_id = tweet_element.get_attribute("data-tweet-id")
            if tweet_id:
                return tweet_id
                
            # Intentar extraer de la URL
            link_elements = tweet_element.find_elements(By.XPATH, ".//a[contains(@href, '/status/')]")
            for link_elem in link_elements:
                href = link_elem.get_attribute("href")
                if href and "/status/" in href:
                    # Extraer el ID del tweet de la URL
                    tweet_id = href.split("/status/")[1].split("?")[0]
                    return tweet_id
        except:
            pass
        
        # Fallback: usar ID único del elemento
        try:
            return tweet_element.get_attribute("id") or "tweet_" + str(random.randint(10000, 99999))
        except:
            return "tweet_" + str(random.randint(10000, 99999))
            
    def _extract_tweets_one_by_one(self, username):
        """
        Extrae tweets de forma individual con precisión optimizada.
        """
        Logger.info("Iniciando extracción tweet por tweet (método acelerado)")
        
        # Lista para almacenar los tweets extraídos
        tweets_data = []
        tweets_processed = 0
        
        # Scrolls iniciales para cargar algunos tweets (más rápidos)
        self._scroll_with_pause(4, pause_every=2)
        
        # Selectores más precisos para encontrar tweets
        improved_selectors = [
            "//article[@data-testid='tweet']",
            "//div[@data-testid='cellInnerDiv']//article",
            "//div[@data-testid='tweetText']//ancestor::article"
        ]
        
        # Variable para controlar la paginación
        last_tweet_id = None
        max_extraction_attempts = 8  # Reducido para mayor velocidad
        consecutive_empty_scrolls = 0
        
        for attempt in range(max_extraction_attempts):
            # Encontrar tweets visibles de forma eficiente
            visible_tweets = []
            for selector in improved_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        visible_tweets = [e for e in elements if e.is_displayed()]
                        if visible_tweets:
                            break
                except:
                    continue
            
            if not visible_tweets:
                Logger.warning("No se encontraron tweets visibles. Haciendo scroll adicional.")
                self._scroll_with_pause(2, pause_every=1)
                consecutive_empty_scrolls += 1
                # Si no encontramos tweets después de varios intentos, salir
                if consecutive_empty_scrolls >= 3:
                    break
                continue
            else:
                consecutive_empty_scrolls = 0
            
            # Procesar cada tweet visible de forma eficiente
            new_tweets_found = False
            for tweet_element in visible_tweets:
                try:
                    # Obtener ID del tweet para verificar si ya lo procesamos
                    current_tweet_id = self._get_tweet_id(tweet_element)
                    
                    # Si ya procesamos este tweet, continuar con el siguiente
                    if current_tweet_id == last_tweet_id:
                        continue
                        
                    # Guardar este ID para no reprocesarlo
                    last_tweet_id = current_tweet_id
                    new_tweets_found = True
                    
                    # Scroll más rápido para centrar el tweet
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", tweet_element)
                    time.sleep(0.2)  # Reducido significativamente
                    
                    # Extraer datos del tweet
                    tweet_data = self._extract_tweet_data(tweet_element)
                    
                    # Verificar si el tweet está en el rango de fechas
                    if tweet_data and self._tweet_in_date_range(tweet_data):
                        # Expandir respuestas solo si es necesario
                        if LOAD_REPLIES:
                            self._expand_replies(tweet_element)
                            replies = self._extract_replies(tweet_element)
                            tweet_data["respuestas"] = replies
                        else:
                            tweet_data["respuestas"] = {}
                        
                        # Añadir a la lista de tweets
                        tweets_data.append(tweet_data)
                        tweets_processed += 1
                        
                        # Mostrar progreso menos frecuentemente
                        if tweets_processed % 10 == 0:
                            Logger.success(f"Procesados {tweets_processed} tweets válidos")
                        
                        # Verificar si alcanzamos el límite
                        if tweets_processed >= MAX_TWEETS:
                            Logger.info(f"Se alcanzó el límite de {MAX_TWEETS} tweets. Deteniendo extracción.")
                            break
                except Exception as e:
                    continue
            
            # Si alcanzamos el límite de tweets, salir
            if tweets_processed >= MAX_TWEETS:
                break
                
            # Si no encontramos nuevos tweets, hacer más scroll
            if not new_tweets_found:
                self._scroll_with_pause(2, pause_every=1)
            else:
                # Hacer scroll normal para cargar más tweets
                self._scroll_for_more_content()
                time.sleep(0.5)  # Optimizado
            
            # Si ya tenemos suficientes tweets, salir antes
            if len(tweets_data) >= MAX_TWEETS / 2 and attempt > 2:
                break
        
        return tweets_data
        
    def _extract_tweet_data(self, tweet_element):
        """Extrae datos de un tweet con selectores de alto rendimiento"""
        try:
            # 1. Extraer texto/contenido del tweet
            tweet_text = "No disponible"
            content_selectors = [
                ".//div[@data-testid='tweetText']",
                ".//div[@lang and @dir='auto']"
            ]
            
            # Usar primero el selector que funcionó anteriormente
            if self._content_selector_cache:
                try:
                    elements = tweet_element.find_elements(By.XPATH, self._content_selector_cache)
                    for element in elements:
                        if element.is_displayed() and element.text and len(element.text.strip()) > 1:
                            tweet_text = element.text.strip()
                            break
                except:
                    pass
                
            # Si no funcionó el caché, probar otros selectores
            if tweet_text == "No disponible":
                for selector in content_selectors:
                    try:
                        elements = tweet_element.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.text and len(element.text.strip()) > 1:
                                tweet_text = element.text.strip()
                                # Guardar selector exitoso en caché
                                self._content_selector_cache = selector
                                break
                        if tweet_text != "No disponible":
                            break
                    except:
                        continue
                
            # Expandir "Ver más" solo para textos que parecen truncados
            if tweet_text != "No disponible" and len(tweet_text) > 50 and ("..." in tweet_text or len(tweet_text.split()) > 20):
                try:
                    see_more_buttons = tweet_element.find_elements(By.XPATH, 
                        ".//div[@role='button'][contains(text(), 'Show more') or contains(text(), 'Mostrar más')]")
                    for btn in see_more_buttons:
                        if btn.is_displayed():
                            self._human_click(btn)
                            time.sleep(0.3)
                            
                            # Volver a leer el texto expandido con el selector que ya funcionó
                            if self._content_selector_cache:
                                try:
                                    elements = tweet_element.find_elements(By.XPATH, self._content_selector_cache)
                                    for element in elements:
                                        if element.is_displayed() and element.text:
                                            tweet_text = element.text.strip()
                                            break
                                except:
                                    pass
                            break
                except:
                    pass
            
            # 2. Extraer URL del tweet
            tweet_url = "No disponible"
            url_selectors = [
                ".//a[contains(@href, '/status/')][@role='link']",
                ".//time//ancestor::a"
            ]
            
            # Intentar primero con selector cacheado
            if self._url_selector_cache:
                try:
                    url_elements = tweet_element.find_elements(By.XPATH, self._url_selector_cache)
                    for url_elem in url_elements:
                        href = url_elem.get_attribute("href")
                        if href and "/status/" in href:
                            tweet_url = href
                            break
                except:
                    pass
                    
            # Si no funcionó el caché, probar con selectores comunes
            if tweet_url == "No disponible":
                for selector in url_selectors:
                    try:
                        url_elements = tweet_element.find_elements(By.XPATH, selector)
                        for url_elem in url_elements:
                            href = url_elem.get_attribute("href")
                            if href and "/status/" in href:
                                tweet_url = href
                                # Guardar selector exitoso
                                self._url_selector_cache = selector
                                break
                        if tweet_url != "No disponible":
                            break
                    except:
                        continue
            
            # 3. Extraer fecha del tweet
            tweet_date = "No disponible"
            date_selectors = [
                ".//time",
                ".//a[contains(@href, '/status/')]//time"
            ]
            
            for selector in date_selectors:
                try:
                    date_elements = tweet_element.find_elements(By.XPATH, selector)
                    for date_elem in date_elements:
                        # Verificar atributos primero (más rápido)
                        for attr in ["datetime", "title"]:
                            date_value = date_elem.get_attribute(attr)
                            if date_value and len(date_value) > 2:
                                tweet_date = date_value
                                break
                        
                        # Si no hay atributo con la fecha, usar el texto
                        if tweet_date == "No disponible" and date_elem.text and len(date_elem.text) > 1:
                            tweet_date = date_elem.text.strip()
                        
                        if tweet_date != "No disponible":
                            break
                    
                    if tweet_date != "No disponible":
                        break
                except:
                    continue
            
            # 4. Extraer métricas (retweets, likes, etc.)
            metrics = {
                "retweets": "0",
                "likes": "0",
                "replies": "0",
                "views": "0"
            }
            
            # Ubicar el contenedor de métricas
            metrics_selectors = [
                ".//div[@role='group']",
                ".//div[contains(@aria-label, 'retweets') or contains(@aria-label, 'likes')]//ancestor::div[@role='group']"
            ]
            
            metrics_container = None
            for selector in metrics_selectors:
                try:
                    containers = tweet_element.find_elements(By.XPATH, selector)
                    for container in containers:
                        if container.is_displayed():
                            metrics_container = container
                            break
                    if metrics_container:
                        break
                except:
                    continue
                    
            if metrics_container:
                # Extraer métricas específicas
                try:
                    # Retweets
                    retweet_elements = metrics_container.find_elements(By.XPATH, 
                        ".//div[contains(@aria-label, 'retweet') or contains(@aria-label, 'Retweet')]//span[@data-testid='app-text-transition-container']")
                    if retweet_elements and retweet_elements[0].is_displayed():
                        metrics["retweets"] = retweet_elements[0].text.strip() or "0"
                        
                    # Likes
                    like_elements = metrics_container.find_elements(By.XPATH, 
                        ".//div[contains(@aria-label, 'like') or contains(@aria-label, 'Like')]//span[@data-testid='app-text-transition-container']")
                    if like_elements and like_elements[0].is_displayed():
                        metrics["likes"] = like_elements[0].text.strip() or "0"
                    
                    # Respuestas
                    reply_elements = metrics_container.find_elements(By.XPATH, 
                        ".//div[contains(@aria-label, 'reply') or contains(@aria-label, 'Reply')]//span[@data-testid='app-text-transition-container']")
                    if reply_elements and reply_elements[0].is_displayed():
                        metrics["replies"] = reply_elements[0].text.strip() or "0"
                        
                    # Vistas
                    view_elements = tweet_element.find_elements(By.XPATH, 
                        ".//span[contains(text(), 'View') or contains(text(), 'Vista')]//ancestor::a//span[@data-testid='app-text-transition-container']")
                    if view_elements and view_elements[0].is_displayed():
                        metrics["views"] = view_elements[0].text.strip() or "0"
                except:
                    pass
            
            # 5. Extraer nombre de usuario y handle
            username = USER  # Por defecto, el usuario que estamos extrayendo
            user_handle = f"@{USER}"
            
            try:
                # Nombre de usuario
                username_elements = tweet_element.find_elements(By.XPATH, 
                    ".//div[@data-testid='User-Name']//span[not(contains(@data-testid, 'UserScreenName'))]")
                if username_elements and username_elements[0].is_displayed():
                    username = username_elements[0].text.strip()
                
                # Handle (@usuario)
                handle_elements = tweet_element.find_elements(By.XPATH, 
                    ".//div[@data-testid='User-Name']//span[@data-testid='User-Username']")
                if handle_elements and handle_elements[0].is_displayed():
                    user_handle = handle_elements[0].text.strip()
            except:
                pass
                
            # 6. Verificar si hay medios (fotos/videos)
            has_media = False
            media_count = 0
            
            try:
                # Buscar fotos
                photo_elements = tweet_element.find_elements(By.XPATH, ".//div[@data-testid='tweetPhoto']")
                if photo_elements and any(e.is_displayed() for e in photo_elements):
                    has_media = True
                    media_count += len(photo_elements)
                
                # Buscar videos
                video_elements = tweet_element.find_elements(By.XPATH, ".//div[@data-testid='videoComponent']")
                if video_elements and any(e.is_displayed() for e in video_elements):
                    has_media = True
                    media_count += len(video_elements)
            except:
                pass
            
            # Construir el diccionario de datos del tweet
            tweet_data = {
                "url_tweet": tweet_url,
                "usuario": username,
                "handle": user_handle,
                "texto_tweet": tweet_text,
                "fecha_tweet": tweet_date,
                "retweets": metrics["retweets"],
                "likes": metrics["likes"],
                "respuestas_count": metrics["replies"],
                "vistas": metrics["views"]
            }
            
            # Añadir información de medios si existen
            if has_media:
                tweet_data["tiene_media"] = True
                tweet_data["cantidad_media"] = media_count
            
            return tweet_data
            
        except Exception as e:
            Logger.error(f"Error extrayendo datos del tweet: {e}")
            return None
    
    def _expand_replies(self, tweet_element):
        """
        Expande respuestas con estrategia de intento múltiple optimizada.
        """
        if not LOAD_REPLIES:
            return
                
        try:
            # Selectores para expandir respuestas
            expand_selectors = [
                ".//div[@role='button'][contains(text(), 'Show replies') or contains(text(), 'Mostrar respuestas')]",
                ".//div[@role='button'][contains(text(), 'View more replies') or contains(text(), 'Ver más respuestas')]",
                ".//div[@role='button'][contains(text(), 'Show more replies') or contains(text(), 'Mostrar más respuestas')]"
            ]
            
            # Buscar botones de expansión
            expand_buttons = self._find_element_with_multiple_xpaths(
                tweet_element, expand_selectors, single=False)
                
            if expand_buttons:
                # Limitar a 1 solo botón para optimizar tiempo
                for button in expand_buttons[:1]:
                    try:
                        if button.is_displayed():
                            self._human_click(button)
                            time.sleep(1.0)  # Esperar un poco más para cargar respuestas
                    except:
                        pass
            
            # Expandir texto de respuestas largas (solo la primera, para optimizar)
            try:
                see_more_in_replies = tweet_element.find_elements(By.XPATH, 
                    ".//div[@role='button'][contains(text(), 'Show more') or contains(text(), 'Mostrar más')]")
                
                if see_more_in_replies and len(see_more_in_replies) > 0:
                    if see_more_in_replies[0].is_displayed():
                        self._human_click(see_more_in_replies[0])
                        time.sleep(0.2)  # Optimizado
            except:
                pass
                
        except Exception as e:
            Logger.warning(f"Error expandiendo respuestas: {e}")

    def _extract_replies(self, tweet_element):
        """
        Extrae respuestas a un tweet.
        """
        if not LOAD_REPLIES:
            return {}
                
        replies_data = {}
        
        try:
            # Buscar respuestas
            reply_elements = self._find_element_with_multiple_xpaths(
                tweet_element, self.selectors["replies"], single=False)
                
            if not reply_elements:
                return replies_data
            
            # Limitar a solo 10 respuestas para optimización
            reply_elements = reply_elements[:10]
            
            for i, reply in enumerate(reply_elements):
                try:
                    # Extraer nombre de usuario con caché
                    username = "Usuario desconocido"
                    user_selectors = [
                        ".//div[@data-testid='User-Name']//span[not(contains(@data-testid, 'UserScreenName'))]",
                        ".//span[@data-testid='User-Name']"
                    ]
                    
                    # Intentar primero con el selector cacheado
                    if self._reply_selector_cache['user']:
                        try:
                            user_elements = reply.find_elements(By.XPATH, self._reply_selector_cache['user'])
                            for user_elem in user_elements:
                                if user_elem.is_displayed() and user_elem.text and len(user_elem.text.strip()) > 1:
                                    username = user_elem.text.strip()
                                    break
                        except:
                            pass
                    
                    # Si no funciona el caché, probar otros selectores
                    if username == "Usuario desconocido":
                        for selector in user_selectors:
                            try:
                                user_elements = reply.find_elements(By.XPATH, selector)
                                for user_elem in user_elements:
                                    if user_elem.is_displayed() and user_elem.text and len(user_elem.text.strip()) > 1:
                                        username = user_elem.text.strip()
                                        self._reply_selector_cache['user'] = selector
                                        break
                                if username != "Usuario desconocido":
                                    break
                            except:
                                continue
                    
                    # Extraer handle (@usuario)
                    user_handle = "No disponible"
                    handle_selectors = [
                        ".//div[@data-testid='User-Name']//span[@data-testid='User-Username']",
                        ".//span[@data-testid='User-Username']"
                    ]
                    
                    for selector in handle_selectors:
                        try:
                            handle_elements = reply.find_elements(By.XPATH, selector)
                            for handle_elem in handle_elements:
                                if handle_elem.is_displayed() and handle_elem.text:
                                    user_handle = handle_elem.text.strip()
                                    break
                            if user_handle != "No disponible":
                                break
                        except:
                            continue
                    
                    # Extraer texto de la respuesta con caché
                    reply_text = "No disponible"
                    text_selectors = [
                        ".//div[@data-testid='tweetText']",
                        ".//div[@lang and @dir='auto']"
                    ]
                    
                    # Intentar primero con el selector cacheado
                    if self._reply_selector_cache['text']:
                        try:
                            text_elements = reply.find_elements(By.XPATH, self._reply_selector_cache['text'])
                            for text_elem in text_elements:
                                if text_elem.is_displayed() and text_elem.text and len(text_elem.text.strip()) > 1:
                                    reply_text = text_elem.text.strip()
                                    break
                        except:
                            pass
                    
                    # Si no funciona el caché, probar otros selectores
                    if reply_text == "No disponible":
                        for selector in text_selectors:
                            try:
                                text_elements = reply.find_elements(By.XPATH, selector)
                                for text_elem in text_elements:
                                    if text_elem.is_displayed() and text_elem.text and len(text_elem.text.strip()) > 1:
                                        reply_text = text_elem.text.strip()
                                        self._reply_selector_cache['text'] = selector
                                        break
                                if reply_text != "No disponible":
                                    break
                            except:
                                continue
                    
                    # Extraer fecha de la respuesta
                    reply_date = "No disponible"
                    date_selectors = [
                        ".//time",
                        ".//a[contains(@href, '/status/')]//time"
                    ]
                    
                    for selector in date_selectors:
                        try:
                            date_elements = reply.find_elements(By.XPATH, selector)
                            for date_elem in date_elements:
                                # Verificar atributos primero
                                for attr in ["datetime", "title"]:
                                    date_value = date_elem.get_attribute(attr)
                                    if date_value and len(date_value) > 2:
                                        reply_date = date_value
                                        break
                                
                                # Si no hay atributo con la fecha, usar el texto
                                if reply_date == "No disponible" and date_elem.text and len(date_elem.text) > 1:
                                    reply_date = date_elem.text.strip()
                                
                                if reply_date != "No disponible":
                                    break
                            
                            if reply_date != "No disponible":
                                break
                        except:
                            continue

                    # Extraer likes de la respuesta
                    reply_likes = "0"
                    like_selectors = [
                        ".//div[contains(@aria-label, 'like') or contains(@aria-label, 'Like')]//span[@data-testid='app-text-transition-container']"
                    ]
                    
                    for selector in like_selectors:
                        try:
                            like_elements = reply.find_elements(By.XPATH, selector)
                            for like_elem in like_elements:
                                if like_elem.is_displayed() and like_elem.text:
                                    reply_likes = like_elem.text.strip() or "0"
                                    break
                            if reply_likes != "0":
                                break
                        except:
                            continue
                    
                    # Verificar si hay imagen/video en la respuesta
                    has_media = False
                    try:
                        media_selectors = [
                            ".//div[@data-testid='tweetPhoto']",
                            ".//div[@data-testid='videoComponent']"
                        ]
                        
                        for selector in media_selectors:
                            media_elements = reply.find_elements(By.XPATH, selector)
                            if media_elements and any(img.is_displayed() for img in media_elements):
                                has_media = True
                                break
                    except:
                        pass
                    
                    # Guardar respuesta en el formato adecuado
                    reply_key = f"{username}_{user_handle}_{i}"  # Prevenir duplicados con índice
                    reply_data = {
                        "usuario": username,
                        "handle": user_handle,
                        "texto": reply_text,
                        "fecha": reply_date,
                        "likes": reply_likes
                    }
                    
                    if has_media:
                        reply_data["media"] = True
                        
                    replies_data[reply_key] = reply_data
                    
                except Exception as e:
                    continue
            
            return replies_data
            
        except Exception as e:
            Logger.error(f"Error extrayendo respuestas: {e}")
            return replies_data
    
    def _tweet_in_date_range(self, tweet_data):
        """
        Verifica si un tweet está dentro del rango de fechas configurado.
        """
        if "fecha_tweet" not in tweet_data or not tweet_data["fecha_tweet"]:
            return True  # Si no hay fecha, asumimos que está en rango
            
        fecha_texto = tweet_data["fecha_tweet"]
        
        # Optimización: Verificar primero si es una fecha reciente
        # Si encontramos términos de fechas relativas recientes, asumimos que está en el rango
        relative_terms = ["now", "ahora", "min", "mins", "h", "hour", "hours", "hora", "horas", 
                        "yesterday", "ayer", "today", "hoy", "sec", "segundo", "moment", "momento"]
        if any(term in fecha_texto.lower() for term in relative_terms):
            return True
            
        tweet_date = None
        
        # Intentar extraer fecha con método optimizado
        try:
            # Twitter a menudo usa formato ISO en el atributo datetime
            if "T" in fecha_texto and ":" in fecha_texto:
                # Formato ISO (2023-01-15T14:30:00.000Z)
                tweet_date = datetime.fromisoformat(fecha_texto.replace("Z", "+00:00"))
            
            # Formato común en Twitter UI (Jan 15, 2023)
            elif len(fecha_texto.split()) == 3 and "," in fecha_texto:
                try:
                    # Intentar método rápido para este formato específico
                    tweet_date = datetime.strptime(fecha_texto, "%b %d, %Y")
                except:
                    pass
            
            # Formato alternativo (15 Jan 2023)
            elif len(fecha_texto.split()) == 3:
                try:
                    for fmt in ["%d %b %Y", "%d %B %Y"]:
                        try:
                            tweet_date = datetime.strptime(fecha_texto, fmt)
                            break
                        except:
                            continue
                except:
                    pass
            
            # Si todavía no tenemos fecha, extraer números que parezcan año
            if tweet_date is None:
                import re
                year_match = re.search(r'\b(20\d{2})\b', fecha_texto)
                if year_match:
                    year = int(year_match.group(1))
                    # Si solo tenemos el año, verificar si está en el rango
                    if start_date.year <= year <= end_date.year:
                        return True
                
        except:
            # Si hay error, incluimos el tweet
            return True
        
        # Verificar si está en rango
        if tweet_date:
            return start_date <= tweet_date <= end_date
        
        # Por defecto incluir
        return True

    def login(self):
        """
        Inicia sesión en Twitter/X con manejo optimizado.
        """
        Logger.info("Iniciando proceso de login en Twitter/X...")
        try:
            # Cargar la página de login
            self.driver.get("https://twitter.com/login")
            self._human_delay(1, 1.5)  # Reducido
            
            # Aceptar cookies si aparece el diálogo
            self._handle_popups()
            
            # Verificar si ya estamos loggeados
            if self._check_already_logged_in():
                Logger.success("Ya hay una sesión activa. Omitiendo login.")
                return True
                
            # Buscar e introducir email/usuario
            try:
                # Twitter usa un proceso de login de múltiples pasos
                # Paso 1: Ingresar nombre de usuario
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "text"))
                )
                self._human_click(username_input)
                
                # Escribir email/username con velocidad optimizada
                for char in X_EMAIL if "@" in X_EMAIL else X_USERNAME:
                    username_input.send_keys(char)
                    time.sleep(random.uniform(0.01, 0.03))  # Más rápido
                    
                self._human_delay(0.1, 0.3)  # Reducido
                
                # Hacer clic en el botón de siguiente
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][contains(., 'Next') or contains(., 'Siguiente')]"))
                )
                self._human_click(next_button)
                self._human_delay(0.5, 1.0)  # Reducido
                
                # Si pide verificar usuario (en caso de email)
                try:
                    username_verify = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.NAME, "text"))
                    )
                    if username_verify.is_displayed():
                        # Escribir nombre de usuario
                        self._human_click(username_verify)
                        for char in X_USERNAME:
                            username_verify.send_keys(char)
                            time.sleep(random.uniform(0.01, 0.03))
                            
                        # Buscar y hacer clic en el botón de siguiente
                        verify_next = self.driver.find_element(By.XPATH, 
                            "//div[@role='button'][contains(., 'Next') or contains(., 'Siguiente')]")
                        self._human_click(verify_next)
                        self._human_delay(0.5, 1.0)
                except:
                    pass
                
                # Paso 2: Ingresar contraseña
                password_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                self._human_click(password_input)
                
                # Escribir contraseña con velocidad optimizada
                for char in X_PASS:
                    password_input.send_keys(char)
                    time.sleep(random.uniform(0.01, 0.03))  # Más rápido
                    
                self._human_delay(0.1, 0.3)  # Reducido
                
                # Hacer clic en el botón de login
                login_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][contains(., 'Log in') or contains(., 'Iniciar sesión')]"))
                )
                self._human_click(login_button)
                
                # Esperar a que complete el login
                self._human_delay(2, 3)  # Optimizado pero suficiente
                
                # Verificar resultado del login
                if "login" in self.driver.current_url or "i/flow" in self.driver.current_url:
                    self.save_screenshot("login_checkpoint")
                    
                    # Verificar si hay un paso adicional de verificación
                    if self._handle_verification():
                        Logger.success("Verificación adicional completada con éxito")
                    else:
                        Logger.error("Error en verificación adicional")
                        
                    return self._check_already_logged_in()
                    
                # Manejar diálogos post-login
                self._handle_popups()
                
                # Verificar login exitoso
                if self._check_already_logged_in() or "twitter.com/home" in self.driver.current_url:
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
            
    def _handle_verification(self):
        """Maneja pasos adicionales de verificación durante el login"""
        try:
            # Verificar si hay pantalla de 2FA
            code_input = None
            
            try:
                code_input = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.NAME, "text"))
                )
            except:
                pass
                
            if code_input and code_input.is_displayed():
                Logger.info("Se requiere código de verificación en dos factores (2FA)")
                auth_code = input("Por favor, ingrese el código de autenticación 2FA: ")
                
                for char in auth_code:
                    code_input.send_keys(char)
                    time.sleep(random.uniform(0.03, 0.07))
                    
                # Buscar y hacer clic en botón de confirmar
                verify_button = self.driver.find_element(By.XPATH, 
                    "//div[@role='button'][contains(., 'Verify') or contains(., 'Verificar') or contains(., 'Next') or contains(., 'Siguiente')]")
                self._human_click(verify_button)
                self._human_delay(1.5, 2)
                
                return True
                
            # Verificar si hay desafío de "unusual activity"
            unusual_activity = self.driver.find_elements(By.XPATH, 
                "//div[contains(text(), 'Unusual activity') or contains(text(), 'Actividad inusual')]")
                
            if unusual_activity and any(e.is_displayed() for e in unusual_activity):
                Logger.warning("Detectado desafío de actividad inusual")
                
                # Buscar campos de entrada (podría ser email, teléfono, etc.)
                challenge_input = self.driver.find_elements(By.XPATH, "//input")
                if challenge_input and any(e.is_displayed() for e in challenge_input):
                    visible_input = next((e for e in challenge_input if e.is_displayed()), None)
                    if visible_input:
                        challenge_value = input("Ingrese el valor solicitado para verificación: ")
                        self._human_click(visible_input)
                        for char in challenge_value:
                            visible_input.send_keys(char)
                            time.sleep(random.uniform(0.03, 0.07))
                            
                        # Buscar botón de confirmar
                        confirm_button = self.driver.find_element(By.XPATH, 
                            "//div[@role='button'][contains(., 'Submit') or contains(., 'Enviar') or contains(., 'Verify') or contains(., 'Verificar')]")
                        self._human_click(confirm_button)
                        self._human_delay(1.5, 2)
                        
                        return True
            
            return False
            
        except Exception as e:
            Logger.error(f"Error en verificación: {e}")
            return False
    
    def scrape_user(self, username):
        """
        Extrae tweets de un usuario de X (Twitter).
        """
        Logger.info(f"Iniciando extracción del usuario: @{username}")
        
        try:
            # 1. Navegar al perfil del usuario
            if not self._navigate_to_user(username):
                Logger.error(f"No se pudo navegar al perfil de @{username}")
                return []
            
            # 2. Extraer tweets uno por uno usando el método mejorado
            tweets_data = self._extract_tweets_one_by_one(username)
            
            # 3. Mensaje final
            if tweets_data:
                Logger.success(f"Extracción completada: {len(tweets_data)} tweets válidos extraídos de @{username}")
            else:
                Logger.warning(f"Finalizado sin tweets válidos extraídos de @{username}")
            
            return tweets_data
            
        except Exception as e:
            Logger.error(f"Error en scrape_user: {e}")
            self.save_screenshot("scrape_user_error")
            return []

    def save_to_csv(self, data, username):
        """
        Guarda los datos extraídos en un archivo CSV con manejo optimizado.
        """
        if not data:
            Logger.warning("No hay datos para guardar.")
            return None

        try:
            # Preparar los datos para CSV
            csv_data = []
            for tweet in data:
                # Convertir el diccionario de respuestas a formato JSON
                if "respuestas" in tweet:
                    respuestas_json = json.dumps(tweet["respuestas"], ensure_ascii=False)
                else:
                    respuestas_json = "{}"
                
                # Crear fila de datos
                row = {
                    "url_tweet": tweet.get("url_tweet", ""),
                    "usuario": tweet.get("usuario", ""),
                    "handle": tweet.get("handle", ""),
                    "texto_tweet": tweet.get("texto_tweet", "").replace("\n", " ").strip(),
                    "fecha_tweet": tweet.get("fecha_tweet", ""),
                    "retweets": tweet.get("retweets", ""),
                    "likes": tweet.get("likes", ""),
                    "respuestas_count": tweet.get("respuestas_count", ""),
                    "vistas": tweet.get("vistas", ""),
                    "tiene_media": "Sí" if tweet.get("tiene_media", False) else "No",
                    "cantidad_media": tweet.get("cantidad_media", "0"),
                    "respuestas": respuestas_json,
                    "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                csv_data.append(row)

            # Crear DataFrame y guardar como CSV
            df = pd.DataFrame(csv_data)
            date_str = datetime.now().strftime("%d_%m_%Y")
            filename = f"twitter_tweets_{username.lower()}_{date_str}.csv"

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
    print("  TWITTER/X SCRAPER AVANZADO (OPTIMIZADO)  ".center(80, "="))
    print("  Extrae tweets y respuestas con alta velocidad y precisión  ".center(80, "-"))
    print("="*80 + "\n")
    
    # Mostrar configuración actual
    print(f"📋 Configuración:")
    print(f"   - Usuarios a extraer: {', '.join(USERS)}")
    print(f"   - Periodo: {START_DATE} al {END_DATE}")
    print(f"   - Máximo de tweets: {MAX_TWEETS}")
    print(f"   - Navegador: {BROWSER_TYPE}")
    print(f"   - Modo headless: {'Activado' if ENABLE_HEADLESS else 'Desactivado'}")
    print(f"   - Cargar respuestas: {'Si' if LOAD_REPLIES else 'No'}")
    print("\n" + "-"*80 + "\n")
    
    # Crear instancia del scraper
    scraper = TwitterScraper()
    
    try:
        # 1) Login
        if not scraper.login():
            Logger.fatal_error("Login fallido. Abortando operación.")
            sys.exit(1)
            
        # Pequeña pausa después del login
        time.sleep(2)

        # 2) Comienza el scraper para cada usuario
        results = {}
        for username in USERS:
            Logger.info(f"Iniciando extracción de usuario: @{username}")
            tweets = scraper.scrape_user(username)
            results[username] = len(tweets)

            Logger.info(f"Guardando datos de @{username} ({len(tweets)} tweets)")
            scraper.save_to_csv(tweets, username)
            
            # Pausa entre usuarios para evitar sobrecargar
            if username != USERS[-1]:
                pause_time = random.uniform(3, 5)  # Reducido
                Logger.info(f"Pausa de {pause_time:.1f} segundos antes del siguiente usuario...")
                time.sleep(pause_time)
            
        # 3) Mostrar resumen final
        print("\n" + "="*50)
        print("  RESUMEN DE EXTRACCIÓN  ".center(50, "="))
        for username, count in results.items():
            status = "✅" if count > 0 else "⚠️"
            print(f"{status} @{username}: {count} tweets extraídos")
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