from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import random

# Lista de User-Agents
agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
]

# Lista de canales a escrapear
channels = [
    "https://www.youtube.com/@PlataCard/videos",
    "https://www.youtube.com/@DisneyStudiosLA/videos",
    "https://www.youtube.com/@ParamountMexico/videos",
    "https://www.youtube.com/@videocine/videos",
    "https://www.youtube.com/@SonypicturesMexicoOficial/videos",
    "https://www.youtube.com/@DiamondFilmsLatam/videos",
    "https://www.youtube.com/@universalpicturesmx/videos",
    "https://www.youtube.com/@warnerbrosmexico/videos",
    "https://www.youtube.com/@CorazonFilms/videos"
]

# ✅ Descargar el driver solo una vez
service = Service(ChromeDriverManager().install())

# Lista para almacenar todos los datos
data = []

class YouTubeScraper:
    def __init__(self, driver):
        self.driver = driver

    def _human_delay(self, min_s=1.0, max_s=3.0):
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        time.sleep(total)

    def _scroll_to_element(self, xpath):
        """Scroll hacia un elemento específico para asegurar que esté visible"""
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            self._human_delay(1, 2)
        except Exception:
            pass

    def extract_title(self):
        try:
            title = self.driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
            return title if title else "Sin título"
        except Exception:
            return "Sin título"

    def extract_likes(self):
        try:
            xpath = '//*[@id="top-level-buttons-computed"]//button[contains(@aria-label, "me gusta")]'
            self._scroll_to_element(xpath)
            likes = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return likes if likes else "0"
        except Exception:
            return "0"

    def extract_comment(self):
        try:
            xpath = '//*[@id="content-text"]'
            self._scroll_to_element(xpath)
            comment = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return comment if comment else "Sin comentarios"
        except Exception:
            return "Sin comentarios"

    def extract_views(self):
        try:
            xpath = '//span[contains(text(),"visualizaciones")]'
            self._scroll_to_element(xpath)
            views = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return views if views else "0"
        except Exception:
            return "0"

    def extract_publish_date(self):
        try:
            xpath = '//span[contains(text(),"20")]'
            self._scroll_to_element(xpath)
            date = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return date if date else "Fecha desconocida"
        except Exception:
            return "Fecha desconocida"

    def extract_description(self):
        try:
            # Si el botón de "Mostrar más" está presente, hacemos clic en él
            try:
                show_more_button = self.driver.find_element(By.XPATH, '//tp-yt-paper-button[@id="expand"]')
                self.driver.execute_script("arguments[0].click();", show_more_button)
                self._human_delay(1, 2)
            except Exception:
                pass

            # Extraer la descripción después de expandirla
            xpath = '//*[@id="description"]//yt-formatted-string'
            self._scroll_to_element(xpath)
            description = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return description if description else "Sin descripción"
        except Exception:
            return "Sin descripción"

# 🔄 LOOP para recorrer los canales
for channel in channels:
    print(f"\n📢 Procesando canal: {channel}")

    user_agent = random.choice(agents)
    
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        scraper = YouTubeScraper(driver)

        driver.get(channel)
        scraper._human_delay(2, 4)

        # ✅ Scroll limitado solo para cargar videos visibles
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, window.innerHeight/2);")
            scraper._human_delay(2, 3)

        videos = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]'))
        )
        titles = [video.get_attribute('title') for video in videos if video.get_attribute('title')]
        links = [video.get_attribute('href') for video in videos if video.get_attribute('href')]

        if len(titles) != len(links):
            min_length = min(len(titles), len(links))
            titles = titles[:min_length]
            links = links[:min_length]

        for link in links[:5]:
            driver.get(link)
            scraper._human_delay(2, 4)

            title = scraper.extract_title()
            description = scraper.extract_description()
            views = scraper.extract_views()
            likes = scraper.extract_likes()
            comment = scraper.extract_comment()
            publish_date = scraper.extract_publish_date()

            data.append([channel, title, views, likes, description, comment, publish_date, link])

    except Exception as e:
        print(f"🚨 Error procesando canal {channel}: {e}")

    finally:
        driver.quit()

# ✅ Guardar en CSV
csv_file = 'youtube_videos.csv'
with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Channel', 'Title', 'Views', 'Likes', 'Description', 'Comment', 'Publish Date', 'Link'])
    writer.writerows(data)

print(f"\n✅ Datos escritos en '{csv_file}'")
