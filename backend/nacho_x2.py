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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re 

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
X_EMAIL = "ignacio.lopez@wivboost.com"
X_USERNAME = "NachoMACN777"
X_PASS = "Sidoresilasisoln777"

# Lista de usuarios a extraer
USERS = [
    "soynumx"  # Reemplaza con el usuario que quieras extraer
]
USER = "soynumx"

# Filtros avanzados
START_DATE = "01-01-2025"  # Formato DD-MM-YYYY, tweets a partir de esta fecha
END_DATE = "02-04-2025"    # Formato DD-MM-YYYY, tweets hasta esta fecha
MAX_TWEETS = 500           # Número máximo de tweets a extraer
NUM_SCROLLS = 30           # Reducido para optimizar
SAVE_SCREENSHOTS = False   # Desactivado por defecto para mejorar velocidad
BROWSER_TYPE = 'Chrome'    # Tipo de navegador: 'Chrome' únicamente para uc
ENABLE_HEADLESS = True    # Activar modo headless (sin interfaz gráfica)
MAX_RETRIES = 3            # Número máximo de reintentos para operaciones que pueden fallar
LOAD_REPLIES = True        # Establece a False para una extracción super rápida sin respuestas

# Optimización de tiempos
SCROLL_DELAY_MIN = 1.5     # Reducido de 0.5 a 0.3
SCROLL_DELAY_MAX = 3.0     # Reducido de 1.0 a 0.7
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
                "//article[@data-testid='tweet']",
                "//div[@data-testid='cellInnerDiv']//article[contains(@tabindex, '-1')]",
                "//div[@role='article']"
            ],
            "tweet_content": [
                ".//div[@data-testid='tweetText']",
                ".//div[@lang]",
                ".//div[contains(@class, 'tweet-text')]"
            ],
            # Selectores para fechas de tweets
            "tweet_dates": [
                ".//time",
                ".//a[contains(@href, '/status/')]//time"
            ],
            # Selectores para métricas (retweets, likes, etc.)
            "metrics": [
                ".//div[@role='group']//span[@data-testid='app-text-transition-container']",
                ".//div[@data-testid='reply']//span",
                ".//div[@data-testid='retweet']//span",
                ".//div[@data-testid='like']//span",
                "//*[@id='id__34a7a38t7l8']/div[4]/a/div/div[2]/span/span"
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
                ".//div[@data-testid='videoComponent']",
                ".//div[contains(@aria-label, 'Image')]",
                ".//div[contains(@aria-label, 'Video')]"
            ]
        }

    def _check_media_presence(self, element):
        """Verifica si un tweet tiene medios adjuntos"""
        try:
            media_selectors = [
                ".//div[@data-testid='tweetPhoto']",
                ".//div[@data-testid='videoComponent']",
                ".//div[contains(@aria-label, 'Image')]",
                ".//div[contains(@aria-label, 'Video')]"
            ]
            
            for selector in media_selectors:
                if element.find_elements(By.XPATH, selector):
                    return True
            return False
        except:
            return False
    
    def optimized_tweet_extraction(self, username):
        Logger.info("Iniciando extracción optimizada de tweets")
    
        tweets_data = []
        
        # Intentar con la vista de búsqueda avanzada por fecha primero
        search_success = self.search_tweets_by_date_range(username)
        if not search_success:
            # Si falla, volver al timeline normal
            self._navigate_to_user(username)
        
        # Esperar a que cargue la página
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']"))
            )
        except TimeoutException:
            Logger.error("No se cargaron los tweets en el tiempo esperado")
            return tweets_data
        
        # Realizar scrolls iniciales para cargar contenido
        self._scroll_with_pause(3, pause_every=1)
        
        # Inicializar variables de control
        processed_urls = set()  # Para evitar procesar tweets duplicados
        last_position = self.driver.execute_script("return window.pageYOffset;")
        same_position_count = 0
        
        for scroll_attempt in range(NUM_SCROLLS):
            try:
                # Verificar si estamos atascados en el scroll
                current_position = self.driver.execute_script("return window.pageYOffset;")
                if last_position == current_position:
                    same_position_count += 1
                    if same_position_count > 3:
                        Logger.warning("No se detectó movimiento después de 3 intentos. Reintentando...")
                        self.driver.execute_script("window.scrollBy(0, 1000);")
                        time.sleep(1.5)
                        same_position_count = 0
                else:
                    same_position_count = 0
                last_position = current_position
                
                # Buscar tweets visibles
                tweet_elements = []
                try:
                    tweet_elements = self.driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
                    if not tweet_elements:
                        tweet_elements = self.driver.find_elements(By.XPATH, "//div[@data-testid='cellInnerDiv']//article")
                except:
                    pass
                    
                if not tweet_elements:
                    Logger.warning("No se encontraron tweets visibles. Haciendo scroll...")
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
                    continue
                    
                # Filtrar tweets visibles
                visible_tweets = [e for e in tweet_elements if self._is_element_visible(e)]
                
                if not visible_tweets:
                    Logger.warning("Hay tweets en el DOM pero no son visibles. Haciendo scroll...")
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
                    continue
                    
                # Procesar tweets visibles
                new_tweets = 0
                for tweet_element in visible_tweets:
                    try:
                        # Obtener URL del tweet para identificarlo de forma única
                        tweet_url = self._get_tweet_url(tweet_element)
                        if not tweet_url or tweet_url in processed_urls:
                            continue
                        
                        # Marcar como procesado
                        processed_urls.add(tweet_url)
                        
                        # Extraer datos básicos del tweet
                        tweet_data = self._extract_tweet_data(tweet_element)
                        if not tweet_data:
                            continue
                            
                        # Verificar si está en el rango de fechas
                        if not self._tweet_in_date_range(tweet_data):
                            continue
                        
                        # Extraer respuestas y métricas
                        if LOAD_REPLIES:
                            Logger.info(f"Extrayendo respuestas para tweet: {tweet_url}")
                            replies, metrics = self._extract_replies_with_js(tweet_element)
                            
                            # Update the tweet data with metrics
                            if metrics:
                                tweet_data["retweets"] = metrics.get("retweets", "0")
                                tweet_data["likes"] = metrics.get("likes", "0")
                                tweet_data["respuestas_count"] = metrics.get("respuestas_count", "0")
                                tweet_data["vistas"] = metrics.get("vistas", "0")
                                
                            tweet_data["respuestas"] = replies
                        else:
                            tweet_data["respuestas"] = {}
                        
                        # Añadir a la lista final
                        tweets_data.append(tweet_data)
                        new_tweets += 1
                        
                        Logger.info(f"Tweet {len(tweets_data)} extraído con {len(tweet_data.get('respuestas', {}))} respuestas")
                        
                        # Verificar si alcanzamos el límite
                        if len(tweets_data) >= MAX_TWEETS:
                            Logger.info(f"Se alcanzó el límite de {MAX_TWEETS} tweets")
                            break
                    except Exception as e:
                        Logger.error(f"Error procesando tweet: {str(e)[:100]}")
                        continue
                        
                Logger.info(f"Encontrados {new_tweets} nuevos tweets (Total: {len(tweets_data)})")
                
                # Si alcanzamos el límite, salir
                if len(tweets_data) >= MAX_TWEETS:
                    break
                    
                # Scroll para cargar más contenido
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                Logger.error(f"Error durante la extracción: {str(e)[:100]}")
                # No salir del bucle, intentar con el siguiente scroll
                continue
                
        return tweets_data
    
    def _is_element_visible(self, element):
        """Verifica si un elemento está visible en la página"""
        try:
            return element.is_displayed() and element.size['height'] > 0
        except:
            return False
    
    def _get_tweet_url(self, tweet_element):
        """Extrae la URL de un tweet"""
        try:
            url_elements = tweet_element.find_elements(By.XPATH, ".//a[contains(@href, '/status/')]")
            for url_elem in url_elements:
                href = url_elem.get_attribute("href")
                if href and "/status/" in href:
                    return href
        except:
            pass
        return None
    
    def extract_tweet_with_js(self, tweet_element):
        """Extrae datos de un tweet usando JavaScript directo (más robusto)"""
        try:
            tweet_data = self.driver.execute_script(
                """
                const tweet = arguments[0];
                
                // Función para extraer texto seguro
                function getText(element) {
                    return element ? element.textContent.trim() : '';
                }
                
                // Extraer texto - selector actualizado
                const textEl = tweet.querySelector('div[data-testid="tweetText"], div[lang]');
                const text = getText(textEl);
                
                // Extraer URL
                let url = '';
                const linkEl = tweet.querySelector('a[href*="/status/"]');
                if (linkEl) url = linkEl.href;
                
                // Extraer fecha
                let date = '';
                const timeEl = tweet.querySelector('time');
                if (timeEl) date = timeEl.getAttribute('datetime') || getText(timeEl);
                
                // Extraer usuario
                const userEl = tweet.querySelector('div[data-testid="User-Name"]');
                let username = '';
                let handle = '';
                
                if (userEl) {
                    const nameEl = userEl.querySelector('span:not([data-testid])');
                    const handleEl = userEl.querySelector('span[data-testid="User-Username"]');
                    
                    username = getText(nameEl);
                    handle = getText(handleEl);
                }
                
                // Extraer métricas
                const metrics = {
                    replies: '0',
                    retweets: '0',
                    likes: '0',
                    views: '0'
                };
                
                // Selectores actualizados para métricas
                const replyEl = tweet.querySelector('[data-testid="reply"] span');
                const retweetEl = tweet.querySelector('[data-testid="retweet"] span');
                const likeEl = tweet.querySelector('[data-testid="like"] span');
                const viewEl = tweet.querySelector('[aria-label*="view"] span');
                
                if (replyEl) metrics.replies = getText(replyEl);
                if (retweetEl) metrics.retweets = getText(retweetEl);
                if (likeEl) metrics.likes = getText(likeEl);
                if (viewEl) metrics.views = getText(viewEl);
                
                // Verificar medios
                const mediaElements = tweet.querySelectorAll('div[data-testid="tweetPhoto"], div[data-testid="videoComponent"]');
                const hasMedia = mediaElements.length > 0;
                
                return {
                    text: text,
                    url: url,
                    date: date,
                    username: username,
                    handle: handle,
                    metrics: metrics,
                    hasMedia: hasMedia,
                    mediaCount: mediaElements.length
                };
                """, tweet_element)
            
            if not tweet_data:
                return None
                
            # Formatear los datos
            return {
                "url_tweet": tweet_data.get('url', ''),
                "usuario": tweet_data.get('username', ''),
                "handle": tweet_data.get('handle', ''),
                "texto_tweet": tweet_data.get('text', ''),
                "fecha_tweet": tweet_data.get('date', ''),
                "retweets": tweet_data.get('metrics', {}).get('retweets', '0'),
                "likes": tweet_data.get('metrics', {}).get('likes', '0'),
                "respuestas_count": tweet_data.get('metrics', {}).get('replies', '0'),
                "vistas": tweet_data.get('metrics', {}).get('views', '0'),
                "tiene_media": "Sí" if tweet_data.get('hasMedia', False) else "No",
                "cantidad_media": str(tweet_data.get('mediaCount', 0)),
                "respuestas": self._extract_replies_with_js(tweet_element) if LOAD_REPLIES else {}
            }
            
        except Exception as e:
            Logger.error(f"Error extrayendo tweet con JS: {str(e)[:200]}")
            return None
        
    def _extract_replies_with_js(self, tweet_element):
        """
        Enhanced method to extract replies from tweets by opening each tweet
        and scrolling to reveal all comments
        """
        try:
            # 1. Get tweet URL
            tweet_url = None
            try:
                url_elements = tweet_element.find_elements(By.XPATH, ".//a[contains(@href, '/status/')]")
                for url_elem in url_elements:
                    href = url_elem.get_attribute("href")
                    if href and "/status/" in href:
                        tweet_url = href
                        break
            except Exception as e:
                Logger.error(f"Error getting tweet URL: {str(e)[:100]}")
                return {}
                
            if not tweet_url:
                Logger.warning("No URL found for tweet, cannot extract replies")
                return {}
                
            # 2. Open the tweet in current window
            Logger.info(f"Opening tweet to extract comments: {tweet_url}")
            current_url = self.driver.current_url
            
            # Navigate to tweet
            self.driver.get(tweet_url)
            time.sleep(3)  # Wait for page to load
            
            # 3. First, extract tweet metrics (retweets, likes, etc.) from the open tweet
            metrics = self._extract_metrics_from_open_tweet()
            
            # Store metrics in the current tweet_data object
            # We'll return to the calling function later
            
            # 4. Extract replies
            replies = {}
            
            try:
                # Wait for page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']"))
                )
                
                # 4.1 Scroll down a few times to reveal comments
                for _ in range(3):
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1.5)
                
                # 4.2 Click "Show more replies" or similar buttons if present
                show_more_selectors = [
                    "//span[contains(text(), 'Show more replies')]",
                    "//span[contains(text(), 'Mostrar más respuestas')]",
                    "//div[@role='button'][contains(text(), 'Show')]",
                    "//div[@role='button'][contains(., 'more repl')]"
                ]
                
                for selector in show_more_selectors:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, selector)
                        for button in buttons[:2]:  # Limit to first 2 buttons to avoid endless clicking
                            if button.is_displayed():
                                Logger.info(f"Clicking 'Show more replies' button")
                                button.click()
                                time.sleep(2)
                    except Exception as e:
                        continue
                
                # 4.3 Get all reply elements with updated selectors
                reply_selectors = [
                    "//div[@data-testid='cellInnerDiv'][.//article[not(@data-testid='tweet')]]",
                    "//div[contains(@class, 'css-1dbjc4n r-1udh08x')][.//article[not(@data-testid='tweet')]]",
                    "//article[not(@data-testid='tweet')][.//div[@data-testid='User-Name']]"
                ]
                
                reply_elements = []
                for selector in reply_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            reply_elements = elements
                            Logger.info(f"Found {len(elements)} potential replies using selector")
                            break
                    except:
                        continue
                
                # If we still don't have replies, try a more generic approach
                if not reply_elements:
                    try:
                        # Get the main tweet first
                        main_tweet = self.driver.find_element(By.XPATH, "//article[@data-testid='tweet']")
                        
                        # Find all articles that come after the main tweet
                        all_articles = self.driver.find_elements(By.XPATH, "//article")
                        reply_elements = [article for article in all_articles if article != main_tweet]
                        Logger.info(f"Found {len(reply_elements)} potential replies using fallback method")
                    except:
                        pass
                
                # 4.4 Process each reply with more robust extraction
                for index, reply in enumerate(reply_elements):
                    try:
                        reply_data = {}
                        
                        # 4.4.1 Extract user info
                        try:
                            # Try primary selector for username
                            user_elements = reply.find_elements(By.XPATH, 
                                ".//div[@data-testid='User-Name']//span[not(@data-testid='User-Username')]")
                            
                            if user_elements:
                                reply_data["usuario"] = user_elements[0].text.strip()
                            else:
                                # Fallback to a more generic selector
                                name_elements = reply.find_elements(By.XPATH, 
                                    ".//div[contains(@class, 'css-1dbjc4n r-1awozwy')]//span[not(contains(@data-testid, 'User-Username'))]")
                                if name_elements:
                                    reply_data["usuario"] = name_elements[0].text.strip()
                                else:
                                    reply_data["usuario"] = f"unknown_user_{index}"
                            
                            # Handle extraction
                            handle_elements = reply.find_elements(By.XPATH, 
                                ".//span[@data-testid='User-Username']")
                            if handle_elements:
                                reply_data["handle"] = handle_elements[0].text.strip()
                            else:
                                reply_data["handle"] = f"@unknown_{index}"
                        except Exception as e:
                            Logger.warning(f"Error extracting user info: {str(e)[:100]}")
                            reply_data["usuario"] = f"unknown_user_{index}"
                            reply_data["handle"] = f"@unknown_{index}"
                        
                        # 4.4.2 Extract reply text with multiple selector attempts
                        try:
                            text_selectors = [
                                ".//div[@data-testid='tweetText']",
                                ".//div[@lang]",
                                ".//div[contains(@class, 'css-1dbjc4n')][./span]"
                            ]
                            
                            reply_text = ""
                            for selector in text_selectors:
                                text_elements = reply.find_elements(By.XPATH, selector)
                                if text_elements:
                                    reply_text = text_elements[0].text.strip()
                                    if reply_text:
                                        break
                            
                            reply_data["texto"] = reply_text
                        except Exception as e:
                            Logger.warning(f"Error extracting reply text: {str(e)[:100]}")
                            reply_data["texto"] = ""
                        
                        # 4.4.3 Extract date
                        try:
                            time_elements = reply.find_elements(By.XPATH, ".//time")
                            if time_elements:
                                reply_date = time_elements[0].get_attribute("datetime")
                                if not reply_date:
                                    reply_date = time_elements[0].text.strip()
                            else:
                                # Try alternate selectors for date
                                date_elements = reply.find_elements(By.XPATH, 
                                    ".//span[contains(@class, 'css-1dbjc4n')][contains(text(), ':')]")
                                if date_elements:
                                    reply_date = date_elements[0].text.strip()
                                else:
                                    reply_date = ""
                            
                            reply_data["fecha"] = reply_date
                        except Exception as e:
                            Logger.warning(f"Error extracting date: {str(e)[:100]}")
                            reply_data["fecha"] = ""
                        
                        # 4.4.4 Extract likes using multiple selectors
                        try:
                            like_selectors = [
                                ".//div[@data-testid='like']//span",
                                ".//div[contains(@aria-label, 'Like')]//span",
                                ".//div[contains(@aria-label, 'Me gusta')]//span"
                            ]
                            
                            likes = "0"
                            for selector in like_selectors:
                                like_elements = reply.find_elements(By.XPATH, selector)
                                if like_elements:
                                    likes = like_elements[0].text.strip() or "0"
                                    break
                            
                            reply_data["likes"] = likes
                        except Exception as e:
                            Logger.warning(f"Error extracting likes: {str(e)[:100]}")
                            reply_data["likes"] = "0"
                        
                        # 4.4.5 Check for media
                        try:
                            media_selectors = [
                                ".//div[@data-testid='tweetPhoto']",
                                ".//div[@data-testid='videoComponent']",
                                ".//div[contains(@style, 'background-image')]"
                            ]
                            
                            media_count = 0
                            for selector in media_selectors:
                                media_elements = reply.find_elements(By.XPATH, selector)
                                media_count += len(media_elements)
                            
                            reply_data["tiene_media"] = media_count > 0
                            reply_data["media_count"] = media_count
                        except Exception as e:
                            Logger.warning(f"Error detecting media: {str(e)[:100]}")
                            reply_data["tiene_media"] = False
                            reply_data["media_count"] = 0
                        
                        # Add to replies dictionary
                        replies[f"reply_{index}"] = reply_data
                    except Exception as e:
                        Logger.warning(f"Error processing reply {index}: {str(e)[:100]}")
                        continue
                
                Logger.info(f"Extracted {len(replies)} replies successfully")
            except Exception as e:
                Logger.error(f"Error extracting replies: {str(e)[:200]}")
            
            # 5. Return to the original URL
            self.driver.get(current_url)
            time.sleep(2)
            
            # Return both the metrics and replies
            return replies, metrics
        except Exception as e:
            Logger.error(f"Error in _extract_replies_with_js: {str(e)[:200]}")
            
            # Ensure we return to the original URL
            try:
                if self.driver.current_url != current_url:
                    self.driver.get(current_url)
                    time.sleep(2)
            except:
                pass
                
            return {}, {}
    
    def _extract_metrics_from_open_tweet(self):
        """
        Extract metrics (retweets, likes, etc.) from an open tweet page
        with multiple selector attempts
        """
        metrics = {
            "retweets": "0",
            "likes": "0",
            "respuestas_count": "0",
            "vistas": "0"
        }
        
        try:
            # 1. Metrics container - multiple attempts with different selectors
            metrics_selectors = [
                "//article[@data-testid='tweet']//div[@role='group']",
                "//div[@data-testid='cellInnerDiv'][1]//div[@role='group']",
                "//article[1]//div[@role='group']"
            ]
            
            metrics_container = None
            for selector in metrics_selectors:
                try:
                    containers = self.driver.find_elements(By.XPATH, selector)
                    if containers and containers[0].is_displayed():
                        metrics_container = containers[0]
                        break
                except:
                    continue
            
            if not metrics_container:
                # Try JavaScript approach to find metrics
                try:
                    metrics_js = self.driver.execute_script("""
                        const metricsData = {};
                        
                        // Try to find retweets
                        const retweetEls = document.querySelectorAll('[data-testid="retweet"] span');
                        if (retweetEls.length > 0) metricsData.retweets = retweetEls[0].textContent.trim();
                        
                        // Try to find likes
                        const likeEls = document.querySelectorAll('[data-testid="like"] span');
                        if (likeEls.length > 0) metricsData.likes = likeEls[0].textContent.trim();
                        
                        // Try to find replies
                        const replyEls = document.querySelectorAll('[data-testid="reply"] span');
                        if (replyEls.length > 0) metricsData.replies = replyEls[0].textContent.trim();
                        
                        // Try to find views
                        const viewEls = document.querySelectorAll('a[href*="/analytics"] span');
                        if (viewEls.length > 0) metricsData.views = viewEls[0].textContent.trim();
                        
                        return metricsData;
                    """)
                    
                    if metrics_js:
                        metrics["retweets"] = metrics_js.get("retweets", "0") or "0"
                        metrics["likes"] = metrics_js.get("likes", "0") or "0"
                        metrics["respuestas_count"] = metrics_js.get("replies", "0") or "0"
                        metrics["vistas"] = metrics_js.get("views", "0") or "0"
                except:
                    pass
                
                return metrics
            
            # 2. Extract specific metrics with multiple selector attempts
            
            # 2.1 Retweets
            retweet_selectors = [
                ".//div[@data-testid='retweet']//span",
                ".//div[contains(@aria-label, 'Retweet')]//span",
                ".//a[contains(@href, '/retweets')]//span"
            ]
            
            for selector in retweet_selectors:
                try:
                    elements = metrics_container.find_elements(By.XPATH, selector)
                    if elements and elements[0].is_displayed():
                        metrics["retweets"] = elements[0].text.strip() or "0"
                        break
                except:
                    continue
            
            # 2.2 Likes
            like_selectors = [
                ".//div[@data-testid='like']//span",
                ".//div[contains(@aria-label, 'Like')]//span",
                ".//a[contains(@href, '/likes')]//span"
            ]
            
            for selector in like_selectors:
                try:
                    elements = metrics_container.find_elements(By.XPATH, selector)
                    if elements and elements[0].is_displayed():
                        metrics["likes"] = elements[0].text.strip() or "0"
                        break
                except:
                    continue
            
            # 2.3 Replies
            reply_selectors = [
                ".//div[@data-testid='reply']//span",
                ".//div[contains(@aria-label, 'Reply')]//span",
                ".//a[contains(@href, '#replies')]//span"
            ]
            
            for selector in reply_selectors:
                try:
                    elements = metrics_container.find_elements(By.XPATH, selector)
                    if elements and elements[0].is_displayed():
                        metrics["respuestas_count"] = elements[0].text.strip() or "0"
                        break
                except:
                    continue
            
            # 2.4 Views
            view_selectors = [
                ".//a[contains(@href, '/analytics')]//span",
                ".//div[contains(@aria-label, 'View')]//span",
                ".//div[contains(text(), 'Views')]//following-sibling::div//span"
            ]
            
            for selector in view_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)  # Search in whole page
                    if elements and elements[0].is_displayed():
                        metrics["vistas"] = elements[0].text.strip() or "0"
                        break
                except:
                    continue
                    
        except Exception as e:
            Logger.error(f"Error extracting metrics: {str(e)[:100]}")
        
        return metrics

    def search_tweets_by_date_range(self, username):
        """Usa la búsqueda avanzada para encontrar tweets en un rango de fechas"""
        try:
            # Fix for the 'str' object has no attribute 'strftime' error
            # Convert string dates to datetime objects if they aren't already
            if isinstance(START_DATE, str):
                since_date = datetime.strptime(START_DATE, "%d-%m-%Y").strftime("%Y-%m-%d")
            else:
                since_date = START_DATE.strftime("%Y-%m-%d")
                
            if isinstance(END_DATE, str):
                until_date = datetime.strptime(END_DATE, "%d-%m-%Y").strftime("%Y-%m-%d")
            else:
                until_date = END_DATE.strftime("%Y-%m-%d")
            
            search_url = f"https://twitter.com/search?q=from%3A{username}%20since%3A{since_date}%20until%3A{until_date}&src=typed_query"
            
            Logger.info(f"Buscando tweets por rango de fechas: {since_date} hasta {until_date}")
            self.driver.get(search_url)
            time.sleep(5)  # Esperar a que cargue la página
            
            # Verificar si la búsqueda se aplicó correctamente
            current_url = self.driver.current_url.lower()
            if f"from:{username}".lower() in current_url and "since:" in current_url:
                return True
            return False
        except Exception as e:
            Logger.error(f"Error en búsqueda por fechas: {e}")
            return False

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
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        try:
            driver = uc.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
                version_main=134
            )
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
        """Scroll optimizado para cargar todo el contenido"""
        Logger.info(f"Realizando {times} scrolls para cargar contenido...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(1, times + 1):
            # Scroll hasta el fondo
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 2.5))  # Espera más larga para cargar
            
            # Calcular nueva altura y comparar
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                Logger.info("No hay más contenido al hacer scroll")
                break
                
            last_height = new_height
            
            # Mostrar progreso
            if i % 3 == 0:
                Logger.info(f"Scroll {i}/{times} - Altura actual: {new_height}px")
            
            # Pausa aleatoria para parecer humano
            if i % pause_every == 0:
                time.sleep(random.uniform(0.5, 1.5))
        


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
                ".//div[@lang and @dir='auto']",
                "//*[@id='id__wh2mbpr30k']"
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
                        "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[1]/div[1]/div/article/div/div/div[2]/div[2]/div[2]/button")
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
                ".//a[contains(@href, '/status/')]//time",
                "//*[@id='id__fnwnzobch5h']/div[2]/div/div[3]/a/time"
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
                ".//div[contains(@aria-label, 'retweets') or contains(@aria-label, 'likes')]//ancestor::div[@role='group']",
                "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[4]/div[1]/div/article/div/div/div[2]/div[2]/div[4]/div"
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
                
            # 6. Verificar si hay medios adjuntos (fotos/videos)
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
        Extrae respuestas a un tweet con selectores actualizados y manejo robusto.
        Devuelve un diccionario con las respuestas estructuradas.
        """
        replies_data = {}
        
        if not LOAD_REPLIES:
            return replies_data
            
        try:
            # Selectores actualizados para encontrar elementos de respuestas
            reply_elements = self._find_element_with_multiple_xpaths(
                tweet_element, [
                    ".//div[@data-testid='reply']//ancestor::div[@data-testid='tweet']",
                    ".//div[contains(@data-testid, 'reply')]//ancestor::article",
                    ".//div[@role='article' and contains(@tabindex, '-1')]",
                    ".//div[@data-testid='cellInnerDiv']//article[contains(@tabindex, '-1')]"
                ], single=False)
            
            if not reply_elements:
                return replies_data
                
            # Limitar el número de respuestas para optimizar el rendimiento
            max_replies = 20  # Puedes ajustar este valor según necesidades
            reply_elements = reply_elements[:max_replies]
            
            for i, reply in enumerate(reply_elements):
                try:
                    # 1. Extraer usuario que respondió
                    user_element = self._find_element_with_multiple_xpaths(reply, [
                        ".//div[@data-testid='User-Name']//span[not(contains(@data-testid, 'UserScreenName'))]",
                        ".//span[@data-testid='User-Name']",
                        ".//span[contains(@class, 'username')]"
                    ])
                    username = user_element.text if user_element else f"unknown_user_{i}"
                    
                    # 2. Extraer handle (@usuario)
                    handle_element = self._find_element_with_multiple_xpaths(reply, [
                        ".//div[@data-testid='User-Name']//span[@data-testid='UserScreenName']",
                        ".//span[contains(@class, 'usertag')]",
                        ".//span[contains(text(), '@')]"
                    ])
                    user_handle = handle_element.text if handle_element else f"@unknown_{i}"
                    
                    # 3. Extraer texto de la respuesta
                    text_element = self._find_element_with_multiple_xpaths(reply, [
                        ".//div[@data-testid='tweetText']",
                        ".//div[@lang and @dir='auto']",
                        ".//div[contains(@class, 'tweet-text')]"
                    ])
                    reply_text = text_element.text if text_element else ""
                    
                    # 4. Extraer fecha de la respuesta
                    date_element = self._find_element_with_multiple_xpaths(reply, [
                        ".//time",
                        ".//a[contains(@href, '/status/')]//time"
                    ])
                    reply_date = date_element.get_attribute("datetime") if date_element else ""
                    
                    # 5. Extraer métricas de la respuesta (likes)
                    likes_element = self._find_element_with_multiple_xpaths(reply, [
                        ".//div[contains(@aria-label, 'Like') or contains(@aria-label, 'Me gusta')]//span",
                        ".//div[@data-testid='like']//span",
                        ".//span[contains(@class, 'like-count')]"
                    ])
                    reply_likes = likes_element.text if likes_element else "0"
                    
                    # 6. Verificar si tiene medios adjuntos
                    has_media = False
                    media_elements = self._find_element_with_multiple_xpaths(reply, [
                        ".//div[@data-testid='tweetPhoto']",
                        ".//div[@data-testid='videoComponent']",
                        ".//div[contains(@aria-label, 'Image') or contains(@aria-label, 'Imagen')]",
                        ".//div[contains(@aria-label, 'Video')]"
                    ], single=False)
                    has_media = len(media_elements) > 0
                    
                    # 7. Construir estructura de datos de la respuesta
                    reply_key = f"reply_{i}_{username[:20]}"
                    replies_data[reply_key] = {
                        "usuario": username.strip(),
                        "handle": user_handle.strip(),
                        "texto": reply_text.replace("\n", " ").strip(),
                        "fecha": reply_date,
                        "likes": reply_likes,
                        "tiene_media": has_media,
                        "media_count": len(media_elements) if has_media else 0
                    }
                    
                except Exception as e:
                    Logger.warning(f"Error extrayendo respuesta {i}: {str(e)[:100]}")
                    continue
                    
        except Exception as e:
            Logger.error(f"Error en _extract_replies: {str(e)[:200]}")
            self.save_screenshot("extract_replies_error")
        
        return replies_data
    
    def _tweet_in_date_range(self, tweet_data):
        """Verifica si un tweet está dentro del rango de fechas configurado
    
        Args:
            tweet_data (dict): Diccionario con los datos del tweet, debe contener 'fecha_tweet'
        
        Returns:
            bool: True si el tweet está en el rango o no se puede determinar, False si está fuera
        """
        if "fecha_tweet" not in tweet_data or not tweet_data["fecha_tweet"]:
            return True  # Si no hay fecha, incluir por defecto

        fecha_texto = tweet_data["fecha_tweet"].strip()
        if not fecha_texto:
            return True
            
        # 1. Manejar fechas relativas (prioridad alta)
        lower_text = fecha_texto.lower()
        relative_terms = ['hora', 'hour', 'min', 'segundo', 'second', 'hoy', 'today', 'ayer', 'yesterday']
        if any(term in lower_text for term in relative_terms):
            return True
        
        # Asegurarnos de que start_date y end_date son objetos datetime
        # y están en formato "naive" (sin zona horaria)
        local_start_date = start_date
        local_end_date = end_date
        
        if isinstance(local_start_date, str):
            local_start_date = datetime.strptime(local_start_date, "%d-%m-%Y")
        
        if isinstance(local_end_date, str):
            local_end_date = datetime.strptime(local_end_date, "%d-%m-%Y")
        
        # 2. Intentar parsear fecha ISO (formato de API)
        try:
            if "T" in fecha_texto:
                # Manejar diferentes formatos ISO (con/sin Z, con/sin milisegundos)
                iso_date = fecha_texto.replace("Z", "")
                if "+" in iso_date:
                    # Remover la parte de zona horaria
                    iso_date = iso_date.split("+")[0]
                
                # Parsear la fecha sin zona horaria
                if "." in iso_date:  # Tiene milisegundos
                    tweet_date = datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%f")
                else:
                    tweet_date = datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S")
                    
                return local_start_date <= tweet_date <= local_end_date
        except ValueError:
            pass  # Si falla, probar otros formatos
        
        # 3. Manejar formatos específicos de Twitter UI
        month_map = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        # Patrones de fecha ordenados por probabilidad de aparición
        date_patterns = [
            # Formato "22 de mar de 2025" (español)
            (r'(?P<day>\d{1,2})\s+de\s+(?P<month>[a-z]{3})\s+de\s+(?P<year>\d{4})', None),
            # Formato "Mar 22, 2025" (inglés)
            (r'(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})', None),
            # Formato "2025-03-22"
            (r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})', None),
            # Formato "15 mar 2025" (alternativo)
            (r'(?P<day>\d{1,2})\s+(?P<month>[a-z]{3})\s+(?P<year>\d{4})', None),
        ]
        
        for pattern, _ in date_patterns:
            try:
                match = re.search(pattern, fecha_texto, re.IGNORECASE)
                if match:
                    groups = match.groupdict()
                    day = int(groups['day'])
                    
                    # Manejar mes (puede ser texto o número)
                    month_str = groups.get('month', '')
                    if month_str.isdigit():
                        month = int(month_str)
                    else:
                        month = month_map.get(month_str.lower()[:3], 1)
                    
                    year = int(groups['year'])
                    
                    # Crear objeto datetime y comparar
                    tweet_date = datetime(year, month, day)
                    return local_start_date <= tweet_date <= local_end_date
            except (ValueError, KeyError):
                continue  # Si hay error con un formato, probar el siguiente
        
        # 4. Si ningún patrón coincidió, registrar advertencia
        Logger.warning(f"No se pudo parsear la fecha del tweet: {fecha_texto}")
        return True  # Incluir por defecto si no se puede determinar


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
                    EC.element_to_be_clickable((By.XPATH, "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]"))
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
                            "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]")
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
                    EC.element_to_be_clickable((By.XPATH, "//*[@id='layers']/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button"))
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
            tweets_data = self.optimized_tweet_extraction(username)
            
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