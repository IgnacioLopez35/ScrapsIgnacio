
import time
import random
import pandas as pd
import unicodedata
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ==================== CONFIGURACIÓN ====================
# Configuración de Smart Proxy
PROXY_HOST = "proxy.smartproxy.com"
PROXY_PORT = "1006"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "tomvyfuT9ZG8R1x+p5"

# Lista de canales de YouTube
CHANNEL_URLS = [
    "https://www.youtube.com/@platacard"
]

# ==================== FUNCIÓN PARA LIMPIAR DATOS ====================
def clean_text(text):
    if isinstance(text, str):
        text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'[^ -~]', '', text)
        return text.strip()
    return text

# ==================== CLASE SCRAPER ====================
class YouTubeScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        options = uc.ChromeOptions()
        options.add_argument(f'--proxy-server=http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}')
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(version_main=134, options=options)
        return driver

    def scroll_page(self):
        scroll_pause_time = random.uniform(1, 2)
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scrape_channel(self, url):
        try:
            print(f"Accediendo a {url}")
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            self.scroll_page()

            videos = []
            video_elements = self.driver.find_elements(By.CSS_SELECTOR, 'ytd-grid-video-renderer')

            for video in video_elements:
                try:
                    title = video.find_element(By.ID, 'video-title').get_attribute('title')
                    url = video.find_element(By.ID, 'video-title').get_attribute('href')
                    views = video.find_element(By.CSS_SELECTOR, '#metadata-line span:nth-child(1)').text
                    date = video.find_element(By.CSS_SELECTOR, '#metadata-line span:nth-child(2)').text

                    videos.append({
                        "title": clean_text(title),
                        "url": url,
                        "views": clean_text(views),
                        "date": clean_text(date)
                    })
                except Exception as e:
                    print(f"Error al extraer datos del video: {e}")

            return videos

        except Exception as e:
            print(f"Error en scraping: {e}")

    def close(self):
        self.driver.quit()

# ==================== FUNCIÓN PRINCIPAL ====================
def run_youtube_scraper():
    scraper = YouTubeScraper()
    all_data = []

    for url in CHANNEL_URLS:
        videos = scraper.scrape_channel(url)
        if videos:
            all_data.extend(videos)

    # Guardar resultados en CSV
    df = pd.DataFrame(all_data)
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    df.to_csv("youtube_scraped_data.csv", index=False)
    print("Datos guardados en youtube_scraped_data.csv")

    scraper.close()

if __name__ == "__main__":
    run_youtube_scraper()
