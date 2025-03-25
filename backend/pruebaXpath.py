from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import random

# Lista de User-Agents
agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

# Lista de canales a escrapear
channels = [
    "https://www.youtube.com/@PlataCard/videos",
    "https://www.youtube.com/@numexico/videos"
]

# Configuración global
MAX_RETRIES = 2
SCROLL_ATTEMPTS = 3
PAUSE_EVERY = 3
VIDEOS_TO_SCRAPE = 10  # Número de videos a scrapear por canal

class YouTubeScraper:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def _human_delay(self, min_s=1.0, max_s=3.0):
        """Pausa aleatoria entre acciones para simular comportamiento humano."""
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0.5, base + gauss_factor)  # Mínimo 0.5 segundos
        time.sleep(total)

    def _scroll_to_bottom(self, times=5, pause_every=3):
        """Scroll hacia abajo de manera más confiable."""
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            
            # Scroll usando JavaScript para mayor confiabilidad
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            
            self._human_delay(1.5, 3.0)  # Pausa humana
            
            # Calcular nueva altura y verificar si llegamos al final
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

    def _wait_for_page_load(self, timeout=10):
        """Espera a que la página termine de cargar."""
        try:
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            print("⚠️ [WARNING] La página tardó demasiado en cargar.")

    def extract_likes(self):
        try:
            # XPath más flexible para likes
            xpaths = [
                '//*[@id="top-level-buttons-computed"]//like-button-view-model//button//div[2]',
                '//*[@id="segmented-like-button"]/button/div[2]',
                '//*[@id="button"]/yt-formatted-string'
            ]
            
            for xpath in xpaths:
                try:
                    likes = self.wait.until(
                        EC.visibility_of_element_located((By.XPATH, xpath)))
                    return likes.text if likes.text else "N/A"
                except (TimeoutException, NoSuchElementException):
                    continue
            return "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo likes: {str(e)}")
            return "N/A"

    def extract_comment(self):
        try:
            self._human_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)

            # Intentar varios selectores posibles
            selectors = [
                (By.XPATH, '//*[@id="content-text"]/span'),
                (By.CSS_SELECTOR, '#content-text'),
                (By.CSS_SELECTOR, '.yt-core-attributed-string')
            ]
            
            for selector in selectors:
                try:
                    comment = self.wait.until(EC.visibility_of_element_located(selector))
                    return comment.text if comment.text else "N/A"
                except (TimeoutException, NoSuchElementException):
                    continue
            return "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo comentarios: {str(e)}")
            return "N/A"

    def extract_views(self):
        try:
            # Múltiples patrones para vistas
            xpaths = [
                '//*[@id="info"]/span[1]',
                '//*[@id="count"]/ytd-video-view-count-renderer/span[1]',
                '//*[contains(text(), "vis")]'
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

    def extract_publish_date(self):
        try:
            # Múltiples patrones para fecha
            xpaths = [
                '//*[@id="info"]/span[3]',
                '//*[contains(text(), "hace")]',
                '//*[contains(text(), "ago")]',
                '//*[contains(text(), "20")]'  # Para años como 2022, 2023
            ]
            
            for xpath in xpaths:
                try:
                    date = self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    return date.text if date.text else "N/A"
                except (TimeoutException, NoSuchElementException):
                    continue
            return "N/A"
        except Exception as e:
            print(f"⚠️ Error extrayendo fecha: {str(e)}")
            return "N/A"

def process_channel(channel_url, service):
    print(f"\n📢 Procesando canal: {channel_url}")
    data = []
    
    # Configurar opciones
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={random.choice(agents)}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Crear driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    scraper = YouTubeScraper(driver)
    
    try:
        # Intento con reintentos
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(channel_url)
                scraper._wait_for_page_load()
                scraper._human_delay(2, 4)
                
                # Hacer scroll de manera confiable
                scraper._scroll_to_bottom(times=SCROLL_ATTEMPTS, pause_every=PAUSE_EVERY)
                
                # Extraer enlaces de videos
                videos = scraper.wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]')))
                links = list({video.get_attribute('href') for video in videos if video.get_attribute('href')})
                
                print(f"✅ {len(links)} videos únicos encontrados")
                
                # Procesar videos
                for link in links[:VIDEOS_TO_SCRAPE]:
                    if not link:
                        continue
                        
                    print(f"🔎 Procesando video: {link}")
                    
                    for video_attempt in range(MAX_RETRIES):
                        try:
                            driver.get(link)
                            scraper._wait_for_page_load()
                            scraper._human_delay(2, 4)
                            
                            # Extraer metadatos
                            try:
                                title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
                                description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
                            except NoSuchElementException:
                                title, description = "N/A", "N/A"
                            
                            # Extraer otros datos
                            likes = scraper.extract_likes()
                            comment = scraper.extract_comment()
                            views = scraper.extract_views()
                            publish_date = scraper.extract_publish_date()
                            
                            # Guardar datos
                            data.append([
                                channel_url, 
                                title, 
                                views, 
                                likes, 
                                description, 
                                comment, 
                                publish_date, 
                                link
                            ])
                            break  # Salir del loop de reintentos si tuvo éxito
                            
                        except Exception as e:
                            print(f"⚠️ Intento {video_attempt + 1} fallido para {link}: {str(e)}")
                            if video_attempt == MAX_RETRIES - 1:
                                data.append([channel_url, "ERROR", "N/A", "N/A", "N/A", "N/A", "N/A", link])
                            time.sleep(random.uniform(2, 5))
                
                break  # Salir del loop de reintentos si tuvo éxito
                
            except Exception as e:
                print(f"⚠️ Intento {attempt + 1} fallido para canal {channel_url}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(random.uniform(5, 10))
                
    except Exception as e:
        print(f"🚨 Error crítico procesando canal {channel_url}: {str(e)}")
    finally:
        driver.quit()
        return data

def main():
    # Descargar el driver
    service = Service(ChromeDriverManager().install())
    all_data = []
    
    for channel in channels:
        channel_data = process_channel(channel, service)
        all_data.extend(channel_data)
        time.sleep(random.uniform(5, 15))  # Pausa entre canales
    
    # Guardar en CSV
    csv_file = 'youtube_videos.csv'
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Channel', 'Title', 'Views', 'Likes', 'Description', 'Comment', 'Publish Date', 'Link'])
        writer.writerows(all_data)
    
    print(f"\n✅ Datos escritos en '{csv_file}'")

if __name__ == "__main__":
    main()