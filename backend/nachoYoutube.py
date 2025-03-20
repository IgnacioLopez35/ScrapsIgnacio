from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from agents import agents

# Configuración del proxy
PROXY_HOST = "gate.smartproxy.com"
PROXY_PORT = "1005"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "X3s_awrkk90gNbs0YX"

# Configura el proxy con autenticación
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
chrome_options.add_argument(f'--proxy-auth={PROXY_USER}:{PROXY_PASS}')
chrome_options.add_argument(f'--user-agent={random.choice(agents)}')

# Inicia el navegador
driver = webdriver.Chrome(options=chrome_options)

# Función para extraer datos de un video
def extract_video_data(url):
    driver.get(url)
    time.sleep(5)  # Espera a que la página cargue

    try:
        # Extraer título del video
        title = driver.find_element(By.XPATH, '//h1[@class="title style-scope ytd-video-primary-info-renderer"]').text

        # Extraer likes
        likes = driver.find_element(By.XPATH, '//*[@id="top-level-buttons-computed"]/ytd-toggle-button-renderer[1]/a').text

        # Extraer comentarios
        comments = driver.find_elements(By.XPATH, '//yt-formatted-string[@id="content-text"]')
        comments_text = [comment.text for comment in comments]

        return {
            "title": title,
            "likes": likes,
            "comments": comments_text
        }
    except Exception as e:
        print(f"Error extrayendo datos del video: {e}")
        return None

# Función principal
def scrape_youtube_channel(channel_url):
    driver.get(channel_url)
    time.sleep(5)

    # Hacer scroll para cargar más videos
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(2)

    # Extraer enlaces de los videos
    videos = driver.find_elements(By.XPATH, '//a[@id="thumbnail" and contains(@href, "/watch?v=")]')
    video_links = [video.get_attribute("href") for video in videos]

    # Extraer datos de cada video
    data = []
    for link in video_links:
        video_data = extract_video_data(link)
        if video_data:
            data.append(video_data)

    return data

# Ejecutar el scraper
channel_url = "https://www.youtube.com/@Platacard/videos"
data = scrape_youtube_channel(channel_url)
print(data)

# Cerrar el navegador
driver.quit()