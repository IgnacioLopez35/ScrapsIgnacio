from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from datetime import datetime, timedelta
import time
import csv
import random
import re
import json
import os
import threading
import queue

# Configuración
DATE_FILTER = "last_3_months"
MAX_VIDEOS_TO_CHECK = 100
VIDEOS_TO_SCRAPE = 50
MAX_RETRIES = 2
SCROLL_ATTEMPTS = 1
PAUSE_EVERY = 3
MAX_PARALLEL_BROWSERS = 4  # Número máximo de navegadores en paralelo

# User-Agents
agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

# Canales
channels = [
    "https://www.youtube.com/@platacard/videos",
    "https://www.youtube.com/@klar_mx/videos",
    "https://www.youtube.com/@numexico/videos",
    "https://www.youtube.com/@MercadoPago/videos",
    #"https://www.youtube.com/@stori_mx/videos",
    #"https://www.youtube.com/c/Ual%C3%A1M%C3%A9xico/videos"
]

class YouTubeScraper:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def _human_delay(self, min_s=1.0, max_s=3.0):
        time.sleep(random.uniform(min_s, max_s))

    def _scroll_to_bottom(self, times=5, pause_every=3):
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        
        for i in range(1, times + 1):
            print(f"🔽 Scroll {i}/{times}...")
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self._human_delay(1.5, 3.0)
            
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                print("🔕 No más contenido al hacer scroll")
                break
            last_height = new_height
            
            if i % pause_every == 0:
                pause_time = random.uniform(10, 25)
                print(f"⏸️ Pausa de {pause_time:.2f} segundos...")
                time.sleep(pause_time)

    def _wait_for_page_load(self, timeout=15):
        try:
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        except TimeoutException:
            print("⚠️ La página tardó en cargar")

    def _scroll_to_comments_section(self):
        try:
            self._human_delay(1, 2)
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            comments_section = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comments_section)
            time.sleep(3)
            return True
        except TimeoutException:
            print("⚠️ No se encontró la sección de comentarios")
            return False
        except Exception as e:
            print(f"⚠️ Error al navegar a comentarios: {str(e)}")
            return False

    def _load_more_comments(self):
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        
        for _ in range(6):
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self._human_delay(2, 3)
            
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                print("🛑 No más comentarios al hacer scroll")
                break
            last_height = new_height
            time.sleep(random.uniform(3, 5))

    def _extract_author(self, element):
        """Extrae el autor con múltiples estrategias"""
        try:
            # Método 1: Buscar por ID específico
            author = element.find_element(By.XPATH, './/a[@id="author-text"]//span').text.strip()
            if author: return author
            
            # Método 2: Buscar enlace de usuario/canal
            author = element.find_element(By.XPATH, './/a[contains(@href, "/user/") or contains(@href, "/channel/")]').text.strip()
            if author: return author
            
            # Método 3: JavaScript como último recurso
            author = self.driver.execute_script("""
                const author = arguments[0].querySelector('a#author-text, yt-formatted-string.author-text');
                return author ? author.innerText.trim() : '';
            """, element)
            if author: return author
        except:
            pass
        
        return "Usuario desconocido"

    def _extract_comment_text(self, element):
        """Versión mejorada para extraer texto de comentarios"""
        try:
            # Método principal - selector directo al contenido
            comment_text = element.find_element(By.XPATH, './/*[@id="content-text"]').text.strip()
            if comment_text:
                return comment_text
            
            # Método alternativo para comentarios con más estructura
            parts = element.find_elements(By.XPATH, './/*[@id="content-text"]//*')
            if parts:
                return " ".join([p.text for p in parts if p.text]).strip()
                
            # Último recurso - JavaScript
            return self.driver.execute_script("""
                const content = arguments[0].querySelector('#content-text');
                return content ? content.innerText.trim() : '[Contenido no disponible]';
            """, element)
        except Exception as e:
            print(f"⚠️ Error extrayendo texto de comentario: {str(e)}")
            return "[Contenido no disponible]"

    def _extract_likes(self, element):
        """Extrae likes con múltiples estrategias"""
        try:
            # Método 1: Desde el atributo aria-label
            likes = element.find_element(By.XPATH, './/span[@id="vote-count-middle"]').get_attribute("aria-label")
            if likes: return re.search(r'\d+', likes).group() or "0"
            
            # Método 2: Desde el texto visible
            likes = element.find_element(By.XPATH, './/span[@id="vote-count-middle"]').text.strip()
            if likes: return re.search(r'\d+', likes).group() or "0"
            
            # Método 3: JavaScript
            likes = self.driver.execute_script("""
                const likes = arguments[0].querySelector('span#vote-count-middle');
                if (!likes) return '0';
                
                return likes.getAttribute('aria-label')?.match(/\d+/)?.shift() || 
                       likes.innerText.match(/\d+/)?.shift() || '0';
            """, element)
            return likes
        except:
            return "0"

    def _extract_comment_date(self, element):
        """Extrae fecha con múltiples enfoques"""
        try:
            # Método 1: Elemento específico
            date = element.find_element(By.XPATH, '//*[@id="published-time-text"]/a').text.strip()
            if date: return date
            
            # Método 2: Texto que contiene "hace"
            date = element.find_element(By.XPATH, './/*[contains(text(), "hace")]').text.strip()
            if date: return date
            
            # Método 3: JavaScript
            date = self.driver.execute_script("""
                const dateEl = arguments[0].querySelector('yt-formatted-string#published-time-text a, a.published-time-text');
                return dateEl?.innerText.trim() || '';
            """, element)
            if date: return date
        except:
            pass
        
        return "Desconocido"

    def extract_main_comments(self, thread):
        """Versión mejorada para extracción de comentarios principales"""
        comment_data = {
            "id": thread.get_attribute("id") or f"comment_{int(time.time() * 1000)}",
            "author": self._extract_author(thread),
            "text": self._extract_comment_text(thread),
            "likes": self._extract_likes(thread),
            "date": self._extract_comment_date(thread),
            "replies": [],
            "reply_count": 0
        }
        return comment_data

    def expand_replies(self, thread):
        """Versión mejorada para expandir respuestas"""
        try:
            # Intenta encontrar el botón de varias formas
            reply_buttons = self.driver.execute_script("""
                const thread = arguments[0];
                // Buscar por texto
                const byText = Array.from(thread.querySelectorAll('yt-formatted-string')).find(el => 
                    el.textContent.match(/respuestas|replies/i)
                );
                // Buscar por atributo
                const byAria = Array.from(thread.querySelectorAll('[aria-label*="respuestas" i], [aria-label*="replies" i]'));
                
                return byText ? [byText] : byAria;
            """, thread)
            
            if reply_buttons:
                for button in reply_buttons:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", button)
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)  # Espera generosa para carga de respuestas
                        break
                    except Exception as e:
                        print(f"⚠️ Error al expandir respuestas: {str(e)}")
                        continue
        except Exception as e:
            print(f"⚠️ Error buscando botón de respuestas: {str(e)}")

    def extract_replies(self, thread):
        """Función mejorada para extraer respuestas"""
        replies = []
        
        try:
            replies_container = None
            try:
                replies_container = thread.find_element(By.XPATH, './/div[@id="replies"] | .//ytd-comment-replies-renderer')
            except:
                pass
            
            if replies_container:
                reply_elements = replies_container.find_elements(By.XPATH, './/ytd-comment-renderer')
                
                for reply in reply_elements:
                    try:
                        reply_data = {
                            "id": reply.get_attribute("id") or f"reply_{int(time.time() * 1000)}",
                            "author": self._extract_author(reply),
                            "text": self._extract_comment_text(reply),
                            "likes": self._extract_likes(reply),
                            "date": self._extract_comment_date(reply)
                        }
                        replies.append(reply_data)
                    except Exception as e:
                        print(f"⚠️ Error procesando respuesta: {str(e)}")
                        continue
        except Exception as e:
            print(f"⚠️ Error extrayendo respuestas: {str(e)}")
        
        return replies

    def extract_comments_with_replies_improved(self):
        """Método principal mejorado para extracción de comentarios"""
        comments_data = []
        
        try:
            # 1. Navegar a la sección de comentarios
            self._human_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            
            try:
                comments_section = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comments_section)
                time.sleep(2)
            except TimeoutException:
                print("⚠️ No se encontró la sección de comentarios")
                return json.dumps({"comments": [], "error": "comments_section_not_found"})
            
            # 2. Cargar más comentarios si es necesario
            self._load_more_comments()
            
            # 3. Extraer comentarios principales
            comment_threads = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, '//ytd-comment-thread-renderer'))
            )
            print(f"🔍 Encontrados {len(comment_threads)} hilos de comentarios")
            
            for i, thread in enumerate(comment_threads[:50]):  # Limitar a 50 comentarios principales
                try:
                    # Extraer datos básicos del comentario
                    comment_data = self.extract_main_comments(thread)
                    
                    # Manejar respuestas
                    if "respuestas" in thread.text.lower() or "replies" in thread.text.lower():
                        self.expand_replies(thread)
                        comment_data["replies"] = self.extract_replies(thread)
                        comment_data["reply_count"] = len(comment_data["replies"])
                    
                    comments_data.append(comment_data)
                    
                    # Pausa ocasional para parecer humano
                    if i % 5 == 0:
                        self._human_delay(1, 2)
                        
                except Exception as e:
                    print(f"🚨 Error procesando comentario {i+1}: {str(e)}")
                    continue
            
            print(f"✅ Extracción completada: {len(comments_data)} comentarios principales")
            return json.dumps({"comments": comments_data}, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"🚨 Error crítico extrayendo comentarios: {str(e)}")
            return json.dumps({"comments": [], "error": str(e)})

    def extract_likes(self):
        try:
            xpaths = [
                '//*[@id="top-level-buttons-computed"]//like-button-view-model//button//div[2]',
                '//*[@id="segmented-like-button"]/button/div[2]',
                '//div[@id="top-level-buttons-computed"]//yt-formatted-string',
                '//*[@id="button"]/yt-formatted-string'
            ]
            
            for xpath in xpaths:
                try:
                    likes = self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    return likes.text if likes.text else "N/A"
                except (TimeoutException, NoSuchElementException):
                    continue
            return "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo likes: {str(e)}")
            return "N/A"

    def extract_views(self):
        try:
            xpaths = [
                '//*[@id="info"]/span[1]',
                '//*[@id="count"]/ytd-video-view-count-renderer/span[1]',
                '//*[contains(text(), "vis")]',
                '//*[contains(text(), "views")]',
                '//div[contains(@class, "view-count")]'
            ]
            
            for xpath in xpaths:
                try:
                    views = self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    return views.text if views.text else "N/A"
                except (TimeoutException, NoSuchElementException):
                    continue
            
            return "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo vistas: {str(e)}")
            return "N/A"

    def extract_publish_date(self, as_datetime=False):
        try:
            xpaths = [
                '//*[@id="info"]/span[3]',
                '//*[contains(text(), "hace")]',
                '//*[contains(text(), "ago")]',
                '//*[contains(text(), "Publicado el")]',
                '//*[contains(text(), "Publicado")]',
                '//*[contains(text(), "20")]'
            ]
            
            for xpath in xpaths:
                try:
                    date_element = self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    date_text = date_element.text if date_element.text else "N/A"
                    
                    if as_datetime:
                        return self._parse_date(date_text)
                    return date_text
                    
                except (TimeoutException, NoSuchElementException):
                    continue
            return None if as_datetime else "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo fecha: {str(e)}")
            return None if as_datetime else "N/A"

    def _parse_date(self, date_text):
        try:
            if re.search(r"\d{1,2} \w{3} \d{4}", date_text):
                return datetime.strptime(date_text, "%d %b %Y")
            elif "hace" in date_text.lower():
                num = int(re.search(r"\d+", date_text).group())
                
                if "hora" in date_text.lower() or "hour" in date_text.lower():
                    delta = timedelta(hours=num)
                elif "día" in date_text.lower() or "day" in date_text.lower():
                    delta = timedelta(days=num)
                elif "semana" in date_text.lower() or "week" in date_text.lower():
                    delta = timedelta(weeks=num)
                elif "mes" in date_text.lower() or "month" in date_text.lower():
                    delta = timedelta(days=30 * num)
                else:
                    return None
                
                return datetime.now() - delta
            elif re.search(r"\d{1,2}/\d{1,2}/\d{4}", date_text):
                return datetime.strptime(date_text, "%m/%d/%Y")
            
            return None
        except Exception:
            return None

    def _date_matches_filter(self, date_obj):
        if not date_obj:
            return False
            
        if DATE_FILTER == "last_3_months":
            five_months_ago = datetime.now() - timedelta(days=85)
            return date_obj >= five_months_ago
            
        elif DATE_FILTER == "2024":
            return date_obj.year == 2024
            
        elif DATE_FILTER == "none":
            return True
            
        return False

def setup_chrome(channel_url, index):
    """Configura y devuelve una instancia de Chrome para un canal específico"""
    # Configurar opciones de Chrome
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Añadir parámetros para evitar detección de automatización
    options.add_argument(f"user-agent={random.choice(agents)}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Posicionar las ventanas (más pequeñas y mejor distribuidas)
    window_width = 700
    window_height = 500
    margin = 20
    position_x = (index % 2) * (window_width + margin) + 10
    position_y = (index // 2) * (window_height + margin) + 10
    options.add_argument(f"--window-position={position_x},{position_y}")
    options.add_argument(f"--window-size={window_width},{window_height}")
    
    # Crear y lanzar el navegador
    driver = webdriver.Chrome(options=options)
    
    return driver

def worker_thread(channel, index, results_queue):
    """Función de trabajo para cada hilo"""
    channel_name = channel.split('@')[-1].split('/')[0]
    print(f"\n🚀 [Worker {index+1}] Iniciando para canal: {channel_name}")
    
    try:
        # Configurar y abrir el navegador
        driver = setup_chrome(channel, index)
        
        # Visitar canal
        print(f"🌐 [Worker {index+1}] Accediendo a {channel}")
        driver.get(channel)
        
        # Configurar el scraper
        scraper = YouTubeScraper(driver)
        scraper._wait_for_page_load()
        
        # Hacer scroll para cargar videos
        scraper._scroll_to_bottom(times=SCROLL_ATTEMPTS, pause_every=PAUSE_EVERY)
        
        # Encontrar enlaces de videos
        videos = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]')))
        links = list({video.get_attribute('href') for video in videos if video.get_attribute('href')})
        
        print(f"✅ [Worker {index+1}] {len(links)} videos únicos encontrados")
        
        videos_processed = 0
        matching_videos = 0
        data = []
        
        # Procesar cada video
        for link in links:
            if not link or matching_videos >= VIDEOS_TO_SCRAPE or videos_processed >= MAX_VIDEOS_TO_CHECK:
                break
                
            videos_processed += 1
            print(f"\n🔎 [Worker {index+1}] Procesando video {videos_processed}: {link}")
            
            for video_attempt in range(MAX_RETRIES):
                try:
                    driver.get(link)
                    scraper._wait_for_page_load()
                    scraper._human_delay(2, 4)
                    
                    publish_date = scraper.extract_publish_date(as_datetime=True)
                    date_text = scraper.extract_publish_date(as_datetime=False)
                    
                    if not scraper._date_matches_filter(publish_date):
                        print(f"⏩ [Worker {index+1}] Video no cumple el filtro ({date_text}), saltando...")
                        break
                        
                    matching_videos += 1
                    print(f"🎯 [Worker {index+1}] Video cumple el filtro ({date_text}), extrayendo datos...")
                    
                    try:
                        title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
                        description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
                    except NoSuchElementException:
                        title, description = "N/A", "N/A"
                    
                    likes = scraper.extract_likes()
                    views = scraper.extract_views()
                    comments_json = scraper.extract_comments_with_replies_improved()
                    
                    data.append([
                        channel, 
                        title, 
                        views, 
                        likes, 
                        description, 
                        comments_json,
                        date_text, 
                        link
                    ])
                    break
                    
                except Exception as e:
                    print(f"⚠️ [Worker {index+1}] Intento {video_attempt + 1} fallido: {str(e)}")
                    if video_attempt == MAX_RETRIES - 1:
                        print(f"❌ [Worker {index+1}] No se pudo procesar el video")
                    time.sleep(random.uniform(2, 5))
        
        print(f"\n🎯 [Worker {index+1}] {matching_videos} videos encontrados que cumplen con el filtro '{DATE_FILTER}'")
        
        # Guardar datos en CSV
        if data:
            csv_file = f'youtube_videos_{channel_name}.csv'
            
            with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Channel', 'Title', 'Views', 'Likes', 'Description', 'Comments', 'Publish Date', 'Link'])
                writer.writerows(data)
            
            print(f"\n✅ [Worker {index+1}] Datos guardados en '{csv_file}'")
            print(f"📝 [Worker {index+1}] Total de videos obtenidos: {len(data)}")
        
        # Poner los resultados en la cola
        results_queue.put((index, True, matching_videos))
        
        # Mantener la ventana abierta para inspección
        print(f"🖥️ [Worker {index+1}] Navegador permanecerá abierto para inspección")
        
        # Volver al canal original
        driver.get(channel)
        
        # No cerrar el navegador, se mantiene abierto para inspección
        
    except Exception as e:
        print(f"🚨 [Worker {index+1}] Error crítico: {str(e)}")
        results_queue.put((index, False, 0))

def main():
    print(f"\n🔍 Iniciando scraping paralelo con filtro: '{DATE_FILTER}'")
    print(f"📊 Objetivo: {VIDEOS_TO_SCRAPE} videos por canal")
    print(f"🔎 Revisando hasta {MAX_VIDEOS_TO_CHECK} videos por canal")
    print(f"🖥️ Ejecutando {min(MAX_PARALLEL_BROWSERS, len(channels))} canales en paralelo\n")
    
    # Crear un directorio para guardar los resultados si no existe
    os.makedirs("resultados", exist_ok=True)
    
    # Cola para recoger resultados
    results_queue = queue.Queue()
    
    # Crear y lanzar hilos para cada canal
    threads = []
    for i, channel in enumerate(channels):
        thread = threading.Thread(target=worker_thread, args=(channel, i, results_queue))
        threads.append(thread)
        print(f"🧵 Preparando hilo {i+1} para canal: {channel}")
    
    # Iniciar todos los hilos
    print("\n🚀 Iniciando todos los hilos en paralelo...\n")
    for thread in threads:
        thread.start()
        time.sleep(1)  # Pequeño retraso para evitar conflictos al iniciar
    
    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()
    
    # Recolectar resultados
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # Mostrar resumen
    print("\n📊 Resumen de resultados:")
    successful = sum(1 for _, success, _ in results if success)
    total_videos = sum(count for _, success, count in results if success)
    
    print(f"✅ Canales procesados exitosamente: {successful}/{len(channels)}")
    print(f"📝 Total de videos obtenidos: {total_videos}")
    
    print("\n🎉 Proceso de scraping paralelo completado!")
    print("🖥️ Los navegadores permanecen abiertos para inspección.")
    print("⌨️ El programa se mantendrá en ejecución. Presiona Ctrl+C para terminar cuando estés listo.")
    
    # Mantener el programa en ejecución con los navegadores abiertos
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Programa terminado por el usuario.")

if __name__ == "__main__":
    main()