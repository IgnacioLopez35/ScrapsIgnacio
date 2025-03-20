from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

# Configuración de Smart Proxy
PROXY_HOST = "proxy.smartproxy.com"
PROXY_PORT = "1006"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "X3s_awrkk90gNbs0YX"

# Configura el proxy con autenticación
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
chrome_options.add_argument(f'--proxy-auth={PROXY_USER}:{PROXY_PASS}')

# Inicia el navegador con las opciones de proxy
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL del canal de Platacard
url_canal = "https://www.youtube.com/@Platacard/videos"

# Abre la página del canal
driver.get(url_canal)
time.sleep(5)

# Desplázate hacia abajo para cargar más videos
for _ in range(3):
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    time.sleep(2)

# Espera a que los videos se carguen
wait = WebDriverWait(driver, 20)  # Aumenta el tiempo de espera
videos = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[@id="thumbnail" and contains(@href, "/watch?v=")]')))

# Filtra los videos de 2024
video_links = []
for video in videos:
    link = video.get_attribute("href")
    if link and "2024" in link:  # Ajusta esta condición según la fecha de publicación
        video_links.append(link)

# Función para extraer comentarios y likes
def extraer_datos_video(url):
    driver.get(url)
    time.sleep(5)

    # Extraer likes
    try:
        likes = driver.find_element(By.XPATH, '//*[@id="top-level-buttons-computed"]/ytd-toggle-button-renderer[1]/a').text
    except:
        likes = "No disponible"

    # Extraer comentarios
    try:
        comentarios = driver.find_elements(By.XPATH, '//yt-formatted-string[@id="content-text"]')
        comentarios_texto = [comentario.text for comentario in comentarios]
    except:
        comentarios_texto = []

    return likes, comentarios_texto

# Recopila datos de todos los videos
datos_videos = []
for link in video_links:
    likes, comentarios = extraer_datos_video(link)
    datos_videos.append({
        "url": link,
        "likes": likes,
        "comentarios": comentarios
    })

# Guarda los datos en un archivo CSV
df = pd.DataFrame(datos_videos)
df.to_csv("platacard_videos_2024.csv", index=False)

# Cierra el navegador
driver.quit()