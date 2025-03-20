
import time
import random
import pandas as pd
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

# ==================== CONFIGURACIÓN ====================
# Configuración de Smart Proxy
PROXY_HOST = "proxy.smartproxy.com"
PROXY_PORT = "1006"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "tomvyfuT9ZG8R1x+p5"

# Canal de YouTube a scrapear
CHANNEL_URL = "https://www.youtube.com/@platacard/videos"

# ==================== CLASE SCRAPER ====================
class YouTubeScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.data = []

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
        scroll_pause_time = random.uniform(2, 4)
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")

        for _ in range(10):  # Hacer scroll 10 veces
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scrape_videos(self):
        self.driver.get(CHANNEL_URL)
        time.sleep(random.uniform(2, 4))
        self.scroll_page()

        video_elements = self.driver.find_elements(By.XPATH, '//ytd-rich-grid-media')

        for video in video_elements:
            try:
                # Extraer título y URL
                title = video.find_element(By.XPATH, './/a[@id="video-title"]').get_attribute('title')
                url = video.find_element(By.XPATH, './/a[@id="video-title"]').get_attribute('href')

                # Extraer fecha de publicación
                date = video.find_element(By.XPATH, './/span[contains(@class, "inline-metadata-item")][2]').text
                if "2024" not in date and "2025" not in date:
                    continue

                # Abrir el video para extraer más datos
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))

                # Extraer número de likes
                try:
                    likes = self.driver.find_element(By.XPATH, '//yt-formatted-string[@aria-label][contains(@aria-label, "Me gusta")]').text
                except:
                    likes = None

                # Extraer número de comentarios
                try:
                    comments_section = self.driver.find_element(By.XPATH, '//*[@id="comments"]')
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", comments_section)
                    time.sleep(random.uniform(2, 4))
                    comments_count = self.driver.find_element(By.XPATH, '//*[@id="count"]/yt-formatted-string/span[1]').text
                except:
                    comments_count = None

                # Guardar datos
                self.data.append({
                    "title": title,
                    "url": url,
                    "date": date,
                    "likes": likes,
                    "comments_count": comments_count
                })

            except Exception as e:
                print(f"Error scraping video: {e}")

    def save_data(self):
        df = pd.DataFrame(self.data)
        df.dropna(inplace=True)
        df.drop_duplicates(inplace=True)
        df.to_csv("youtube_scraped_data.csv", index=False)
        print("Datos guardados en youtube_scraped_data.csv")

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            print(f"Error cerrando el navegador: {e}")

# ==================== FUNCIÓN PRINCIPAL ====================
def run_youtube_scraper():
    scraper = YouTubeScraper()
    scraper.scrape_videos()
    scraper.save_data()
    scraper.close()

if __name__ == "__main__":
    run_youtube_scraper()
