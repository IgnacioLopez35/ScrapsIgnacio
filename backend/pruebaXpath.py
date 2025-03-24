import time
import random
import csv
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========================== CONFIGURACIÓN ==========================
CHANNELS = [
    "https://www.youtube.com/@DisneyStudiosLA",
    "https://www.youtube.com/@ParamountMexico",
    "https://www.youtube.com/@Videocine",
    "https://www.youtube.com/@SonyPicturesMX",
    "https://www.youtube.com/@DiamondFilmsMexico",
    "https://www.youtube.com/@UniversalPicturesMX",
    "https://www.youtube.com/@WarnerBrosMX",
    "https://www.youtube.com/@CorazonFilms"
]

# ===================== CLASE YOUTUBE SCRAPER =====================
class YouTubeScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        """Configura Selenium sin proxy"""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        # options.add_argument("--headless")  # Opcional: Ejecutar en modo headless
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        driver = webdriver.Chrome(options=options)
        return driver

    def _human_delay(self, min_s=1.0, max_s=3.0):
        """Pausa aleatoria para evitar detección"""
        time.sleep(random.uniform(min_s, max_s))

    def _scroll_human(self, times=3):
        """Simula scroll en la página"""
        body = self.driver.find_element(By.TAG_NAME, "body")
        for _ in range(times):
            body.send_keys(Keys.PAGE_DOWN)
            self._human_delay(1.5, 3.0)

    def scrape_channel(self, channel_url):
        """Extrae videos de un canal y sus métricas"""
        print(f"[INFO] Abriendo canal: {channel_url}")
        self.driver.get(channel_url + "/videos")
        
        # Esperar a que los videos estén presentes
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@id='thumbnail' and contains(@href, '/watch?v=')]"))
            )
        except Exception as e:
            print(f"[ERROR] No se pudieron cargar los videos: {str(e)}")
            return []
        
        self._scroll_human(times=5)
        video_elements = self.driver.find_elements(By.XPATH, "//a[@id='thumbnail' and contains(@href, '/watch?v=')]")
        print(f"[INFO] Encontrados {len(video_elements)} videos.")
        
        videos_data = []
        for video in video_elements[:10]:  # Limitar a 10 videos por canal
            try:
                # Obtener la URL y el título del video
                video_url = video.get_attribute("href")
                video_title = video.get_attribute("title")
                print(f"[INFO] Procesando video: {video_title}")
                
                # Navegar a la página del video
                self.driver.get(video_url)
                self._human_delay(3, 5)
                
                # Extraer métricas del video
                likes = self._extract_likes()
                views = self._extract_views()
                comments = self._extract_comments()
                upload_date = self._extract_upload_date()
                
                # Guardar los datos
                videos_data.append({
                    "title": video_title,
                    "url": video_url,
                    "likes": likes,
                    "views": views,
                    "comments": comments,
                    "upload_date": upload_date
                })
                
                # Volver a la página del canal para continuar con el siguiente video
                self.driver.back()
                self._human_delay(3, 5)
                
                # Re-localizar los elementos después de volver
                video_elements = self.driver.find_elements(By.XPATH, "//a[@id='thumbnail' and contains(@href, '/watch?v=')]")
                
            except Exception as e:
                print(f"[ERROR] No se pudo extraer info del video: {str(e)}")
                continue
        
        return videos_data

    def _extract_likes(self):
        """Extrae el número de likes del video"""
        try:
            likes_elem = self.driver.find_element(By.XPATH, "//yt-formatted-string[@id='text' and @class='style-scope ytd-toggle-button-renderer']")
            likes_text = likes_elem.text.replace(",", "")
            return int(likes_text) if likes_text.isdigit() else 0
        except:
            return 0

    def _extract_views(self):
        """Extrae el número de visualizaciones del video"""
        try:
            views_elem = self.driver.find_element(By.XPATH, "//span[@class='view-count style-scope ytd-video-view-count-renderer']")
            views_text = views_elem.text.replace(",", "").replace("views", "").strip()
            return int(views_text) if views_text.isdigit() else 0
        except:
            return 0

    def _extract_comments(self):
        """Cuenta el número de comentarios visibles"""
        try:
            self._scroll_human(times=3)
            comments = self.driver.find_elements(By.XPATH, "//ytd-comment-thread-renderer")
            return len(comments)
        except:
            return 0

    def _extract_upload_date(self):
        """Extrae la fecha de subida del video"""
        try:
            date_elem = self.driver.find_element(By.XPATH, "//yt-formatted-string[@class='style-scope ytd-video-primary-info-renderer']")
            return date_elem.text
        except:
            return "No disponible"

    def save_to_csv(self, data, filename):
        """Guarda los datos en CSV"""
        if not data:
            print("[WARNING] No hay datos para guardar.")
            return
        
        keys = data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"[INFO] Se guardó {len(data)} filas en {filename}.")

    def close(self):
        self.driver.quit()

# ============================ EJECUCIÓN ============================
if __name__ == "__main__":
    scraper = YouTubeScraper()
    try:
        all_videos = []
        for channel in CHANNELS:
            videos = scraper.scrape_channel(channel)
            all_videos.extend(videos)
            print(f"[INFO] {len(videos)} videos extraídos de {channel}")
            time.sleep(random.randint(5, 15))
        
        scraper.save_to_csv(all_videos, "youtube_videos_2024.csv")
        print("[✅] Extracción completa!")
    
    except Exception as e:
        print(f"[CRÍTICO] Error en la ejecución: {str(e)}")
        traceback.print_exc()
    
    finally:
        scraper.close()
        print("[INFO] Selenium cerrado.")