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
        """Pausa aleatoria entre acciones para simular comportamiento humano."""
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        time.sleep(total)

    def _scroll_n_times(self, times=10, pause_every=30, direction: str = 'down'):
        """Scroll hacia arriba o hacia abajo simulando comportamiento humano."""
        if direction == 'up':
            key = Keys.PAGE_UP
        else:
            key = Keys.PAGE_DOWN
        
        if times <= 0:
            print("🔕 [INFO] Skipping scrolling as times is set to 0.")
            return 
        
        body = self.driver.find_element(By.TAG_NAME, "body")
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            body.send_keys(key)
            self._human_delay(1.585, 3.4865)  # Pausa humana

            # Pausa larga después de varios scrolls para evitar detección
            if i % pause_every == 0:
                pause_time = random.uniform(60, 90)  # Entre 60 y 150 segundos
                print(f"⏸️ [INFO] Pausa larga de {pause_time:.2f} segundos después de {i} scrolls...")
                time.sleep(pause_time)

    def extract_likes(self):
        try:
            xpath = '//*[@id="top-level-buttons-computed"]/segmented-like-dislike-button-view-model/yt-smartimation/div/div/like-button-view-model/toggle-button-view-model/button-view-model/button/div[2]'
            likes = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
            return likes
        except TimeoutException:
            return "N/A"

    def extract_comment(self):
        try:
            self._human_delay(1, 2)  # Simular tiempo de carga
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)

            comment = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="content-text"]/span'))
            ).text
            return comment
        except Exception:
            return "N/A"
    def extract_views(self):
        try:
            # Primero intenta extraer el formato expandido
            xpath_expanded = '//*[@id="info"]/span[1]'
            views = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located((By.XPATH, xpath_expanded))
            ).text
            return views
        except TimeoutException:
            try:
                # Si no está expandido, intenta el formato simplificado
                xpath_simple = '//*[@id="info"]/span[1]'
                views = WebDriverWait(self.driver, 3).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_simple))
                ).text
                return views
            except TimeoutException:
                return "N/A"
    def extract_publish_date(self):
        try:
            # Primero intenta extraer la fecha en formato expandido
            xpath_expanded = '//*[@id="info"]/span[3]'  # Año completo
            date = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located((By.XPATH, xpath_expanded))
            ).text
            return date
        except TimeoutException:
            try:
                # Si no está expandida, intenta el formato simplificado ("hace x días")
                xpath_simple = '//*[@id="info"]/span[3]'
                date = WebDriverWait(self.driver, 3).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_simple))
                ).text
                return date
            except TimeoutException:
                return "N/A"

for channel in channels:
    print(f"\n📢 Procesando canal: {channel}")

    # 🔄 Rotar User-Agent para cada canal
    user_agent = random.choice(agents)
    
    # Configurar opciones para rotar User-Agent
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Ejecutar sin abrir ventana
    chrome_options.add_argument(f"user-agent={user_agent}")

    # ✅ Crear un nuevo navegador usando el mismo driver descargado previamente
    driver = webdriver.Chrome(service=service, options=chrome_options)

    scraper = YouTubeScraper(driver)

    try:
        driver.get(channel)
        scraper._human_delay(2, 4)  # Pausa inicial simulando tiempo de carga

        # Hacer scroll de manera natural
        scraper._scroll_n_times(times=5, pause_every=3)

        # Extraer enlaces y títulos de los videos
        videos = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]'))
        )
        titles = [video.get_attribute('title') for video in videos if video.get_attribute('title') is not None]
        links = [video.get_attribute('href') for video in videos if video.get_attribute('href') is not None]

        # Eliminar duplicados
        unique_links = list(set(links))
        unique_titles = [titles[links.index(link)] for link in unique_links]

        print(f"✅ {len(unique_links)} videos únicos encontrados")

        # Procesar solo los primeros 5 videos únicos por canal
        for link in unique_links[:5]:
            if link:
                print(f"🔎 Procesando video: {link}")
                driver.get(link)
                scraper._human_delay(2, 4)

                # Extraer título, descripción, likes y comentarios
                try:
                    title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
                    description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
                    likes = scraper.extract_likes()
                    comment = scraper.extract_comment()
                    # Extraer vistas y fecha de publicación
                    views = scraper.extract_views()
                    publish_date = scraper.extract_publish_date()
                except Exception:
                    title, description, likes, comment = "N/A", "N/A", "N/A", "N/A"

                # Guardar en lista
                # Guardar los datos
                data.append([channel, title, views, likes, description, comment, publish_date, link])

    except Exception as e:
        print(f"🚨 Error procesando canal {channel}: {e}")

    finally:
        # ✅ Cerrar navegador después de procesar cada canal para liberar memoria
        driver.quit()

# Guardar en CSV
csv_file = 'youtube_videos.csv'
with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Channel', 'Title', 'Likes', 'Description', 'Comment', 'Link'])
    writer.writerows(data)

print(f"\n✅ Datos escritos en '{csv_file}'")
