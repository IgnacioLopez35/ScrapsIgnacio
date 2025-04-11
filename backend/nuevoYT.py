from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time
import csv
import random
import re
import json

# Configuración de filtrado por fecha
DATE_FILTER = "last_3_months"  # Opciones: "last_5_months", "2024", "none"
MAX_VIDEOS_TO_CHECK = 100  # Máximo de videos a revisar para encontrar los que cumplen con el filtro
VIDEOS_TO_SCRAPE = 50  # Número de videos a scrapear por canal que cumplan el filtro
# Configuración global
MAX_RETRIES = 2
SCROLL_ATTEMPTS = 2
PAUSE_EVERY = 3
# Lista de User-Agents para desktop
agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

# Lista de canales a escrapear

channels = [
    #"https://www.youtube.com/@platacard/videos",
    #"https://www.youtube.com/@klar_mx/videos",
    "https://www.youtube.com/@numexico/videos",
    #"https://www.youtube.com/@MercadoPago/videos",
    #"https://www.youtube.com/@stori_mx/videos",
    #"https://www.youtube.com/c/Ual%C3%A1M%C3%A9xico/videos"
]

class YouTubeScraper:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def _human_delay(self, min_s=1.0, max_s=3.0):
        """Pausa aleatoria entre acciones para simular comportamiento humano."""
        time.sleep(random.uniform(min_s, max_s))

    def _scroll_to_bottom(self, times=5, pause_every=3):
        """Scroll hacia abajo de manera más confiable."""
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            
            # Scroll usando JavaScript
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self._human_delay(1.5, 3.0)
            
            # Calcular nueva altura
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                print("🔕 [INFO] No se detectó más contenido al hacer scroll.")
                break
            last_height = new_height
            
            # Pausa larga ocasional
            if i % pause_every == 0:
                pause_time = random.uniform(10, 25)
                print(f"⏸️ [INFO] Pausa larga de {pause_time:.2f} segundos después de {i} scrolls...")
                time.sleep(pause_time)

    def _wait_for_page_load(self, timeout=15):
        """Espera mejorada para carga de página."""
        try:
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        except TimeoutException:
            print("⚠️ [WARNING] La página tardó demasiado en cargar.")

    def extract_likes(self):
        """Extracción mejorada de likes."""
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

    def extract_comments(self):
        """Extrae todos los comentarios visibles del video."""
        try:
            self._human_delay(1, 2)
            
            # Scroll hasta comentarios
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            
            # Esperar sección de comentarios
            try:
                comments_section = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
                )
                self.driver.execute_script("arguments[0].scrollIntoView();", comments_section)
                time.sleep(2)
            except TimeoutException:
                print("⚠️ No se encontró la sección de comentarios")
                return "N/A"
            
            # Clic en "Ver más comentarios" si existe
            try:
                more_comments = self.driver.find_element(By.XPATH, '//*[@id="more-replies"]/a')
                more_comments.click()
                time.sleep(2)
            except NoSuchElementException:
                pass
            
            # Extraer todos los comentarios visibles
            comments = []
            comment_elements = self.driver.find_elements(By.XPATH, '//*[@id="content-text"]')
            
            for comment in comment_elements:
                if comment.text:
                    comments.append(comment.text.strip())
            
            return " | ".join(comments) if comments else "N/A"
            
        except Exception as e:
            print(f"⚠️ Error extrayendo comentarios: {str(e)}")
            return "N/A"

    def extract_views(self):
        """Extracción mejorada de vistas."""
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
        """
        Extrae la fecha de publicación.
        Si as_datetime=True, devuelve un objeto datetime (para filtrado).
        Si as_datetime=False, devuelve el texto original (para mostrar).
        """
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
        """Convierte el texto de fecha de YouTube a objeto datetime."""
        try:
            # Para fechas completas (ej. "15 ene 2024")
            if re.search(r"\d{1,2} \w{3} \d{4}", date_text):
                return datetime.strptime(date_text, "%d %b %Y")
            
            # Para "hace X días/semanas/meses"
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
            
            # Para fechas en formato "MM/DD/YYYY"
            elif re.search(r"\d{1,2}/\d{1,2}/\d{4}", date_text):
                return datetime.strptime(date_text, "%m/%d/%Y")
            
            return None
        except Exception:
            return None

    def _date_matches_filter(self, date_obj):
        """Verifica si una fecha cumple con el filtro establecido."""
        if not date_obj:
            return False
            
        if DATE_FILTER == "last_3_months":
            five_months_ago = datetime.now() - timedelta(days=85)  # ~5 meses
            return date_obj >= five_months_ago
            
        elif DATE_FILTER == "2024":
            return date_obj.year == 2024
            
        elif DATE_FILTER == "none":
            return True
            
        return False

def process_channel(channel_url, service):
    print(f"\n📢 Procesando canal: {channel_url}")
    data = []
    
    # Configurar opciones del navegador
    chrome_options = Options()
    #chrome_options.add_argument("--headless=new") #---------------
    chrome_options.add_argument(f"user-agent={random.choice(agents)}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Crear driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    scraper = YouTubeScraper(driver)
    
    try:
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(channel_url)
                scraper._wait_for_page_load()
                scraper._human_delay(2, 4)
                
                # Hacer scroll para cargar videos
                scraper._scroll_to_bottom(times=SCROLL_ATTEMPTS, pause_every=PAUSE_EVERY)
                
                # Extraer enlaces de videos
                videos = scraper.wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]')))
                links = list({video.get_attribute('href') for video in videos if video.get_attribute('href')})
                
                print(f"✅ {len(links)} videos únicos encontrados (buscando {VIDEOS_TO_SCRAPE} que cumplan el filtro)")
                
                videos_processed = 0
                matching_videos = 0
                
                # Procesar videos hasta encontrar los que cumplen el filtro
                for link in links:
                    if not link or matching_videos >= VIDEOS_TO_SCRAPE or videos_processed >= MAX_VIDEOS_TO_CHECK:
                        break
                        
                    videos_processed += 1
                    print(f"\n🔎 Procesando video {videos_processed}: {link}")
                    
                    for video_attempt in range(MAX_RETRIES):
                        try:
                            driver.get(link)
                            scraper._wait_for_page_load()
                            scraper._human_delay(2, 4)
                            
                            # Extraer y verificar fecha
                            publish_date = scraper.extract_publish_date(as_datetime=True)
                            date_text = scraper.extract_publish_date(as_datetime=False)
                            
                            if not scraper._date_matches_filter(publish_date):
                                print(f"⏩ Video no cumple el filtro ({date_text}), saltando...")
                                break
                                
                            matching_videos += 1
                            print(f"🎯 Video cumple el filtro ({date_text}), extrayendo datos...")
                            
                            # Extraer metadatos
                            try:
                                title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
                                description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
                            except NoSuchElementException:
                                title, description = "N/A", "N/A"
                            
                            # Extraer otros datos
                            likes = scraper.extract_likes()
                            comments = scraper.extract_comments()
                            views = scraper.extract_views()
                            
                            # Guardar datos
                            data.append([
                                channel_url, 
                                title, 
                                views, 
                                likes, 
                                description, 
                                comments, 
                                date_text, 
                                link
                            ])
                            break
                            
                        except Exception as e:
                            print(f"⚠️ Intento {video_attempt + 1} fallido: {str(e)}")
                            if video_attempt == MAX_RETRIES - 1:
                                print("❌ No se pudo procesar el video")
                            time.sleep(random.uniform(2, 5))
                
                print(f"\n🎯 {matching_videos} videos encontrados que cumplen con el filtro '{DATE_FILTER}'")
                break
                
            except Exception as e:
                print(f"⚠️ Intento {attempt + 1} fallido para canal: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    print("❌ No se pudo procesar el canal")
                time.sleep(random.uniform(5, 10))
                
    except Exception as e:
        print(f"🚨 Error crítico: {str(e)}")
    finally:
        driver.quit()
        return data

def main():
    # Configuración inicial
    service = Service(ChromeDriverManager().install())
    
    print(f"\n🔍 Iniciando scraping con filtro: '{DATE_FILTER}'")
    print(f"📊 Objetivo: {VIDEOS_TO_SCRAPE} videos por canal que cumplan el filtro")
    print(f"🔎 Revisando hasta {MAX_VIDEOS_TO_CHECK} videos por canal\n")
    
    # Procesar cada canal y guardar en CSV individual
    for channel in channels:
        channel_data = process_channel(channel, service)
        
        if not channel_data:
            print(f"⚠️ No se obtuvieron datos para el canal {channel}")
            continue
        
        # Crear nombre de archivo basado en el nombre del canal
        channel_name = channel.split('@')[-1].split('/')[0]
        csv_file = f'youtube_videos_{channel_name}.csv'
        
        # Guardar en CSV
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Channel', 'Title', 'Views', 'Likes', 'Description', 'Comments', 'Publish Date', 'Link'])
            writer.writerows(channel_data)
        
        print(f"\n✅ Datos del canal {channel_name} guardados en '{csv_file}'")
        print(f"📝 Total de videos obtenidos: {len(channel_data)}")
        
        time.sleep(random.uniform(5, 15))

if __name__ == "__main__":
    main()