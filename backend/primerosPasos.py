from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs
import time
import csv
import random

# Lista de User-Agents (ya la tienes definida)
agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
    # ... (el resto de tu lista de User-Agents)
]

# Seleccionar un User-Agent aleatorio
user_agent = random.choice(agents)

# Configurar opciones para rotar User-Agent
chrome_options = Options()
chrome_options.add_argument("--headless")  # Ejecutar sin abrir ventana
chrome_options.add_argument(f"user-agent={user_agent}")  # Usar el User-Agent seleccionado

# Configurar el driver automáticamente con webdriver_manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL del canal de Plata Card
url = 'https://www.youtube.com/@PlataCard/videos'
driver.get(url)
time.sleep(5)

# Hacer scroll para cargar más videos
for _ in range(3):  # Hacer scroll 3 veces
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    time.sleep(2)  # Esperar a que se carguen los videos

# Esperar a que los enlaces de los videos estén presentes
try:
    videos = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]'))
    )
    titles = [video.get_attribute('title') for video in videos if video.get_attribute('title') is not None]
    links = [video.get_attribute('href') for video in videos if video.get_attribute('href') is not None]
except Exception as e:
    print(f"Error al encontrar los enlaces: {e}")
    titles = []
    links = []

# Eliminar duplicados de los enlaces y títulos
unique_links = list(set(links))  # Convertir a conjunto para eliminar duplicados
unique_titles = [titles[links.index(link)] for link in unique_links]  # Mantener los títulos correspondientes

print("Títulos únicos encontrados:", unique_titles[:5])  # Solo los primeros 5 títulos
print("Links únicos encontrados:", unique_links[:5])  # Solo los primeros 5 enlaces

data = []

# Procesar solo los primeros 5 videos únicos
for link in unique_links[:5]:
    if link:
        print(f"Procesando video: {link}")
        driver.get(link)
        time.sleep(3)

        # Hacer scroll para asegurar que todo el contenido cargue
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(2)

        # Extraer título
        try:
            title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
            print(f"Título: {title}")
        except Exception as e:
            print(f"Error al obtener el título: {e}")
            title = "N/A"

        # Extraer descripción
        try:
            description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
            print(f"Descripción: {description}")
        except Exception as e:
            print(f"Error al obtener la descripción: {e}")
            description = "N/A"


        # Extraer vistas
        try:
            # Primero intenta extraer el formato expandido
            xpath_expanded = '//*[@id="info"]/span[1]'
            views = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.XPATH, xpath_expanded))
            ).text
            
        except TimeoutException:
            try:
                # Si no está expandido, intenta el formato simplificado
                xpath_simple = '//*[@id="info"]/span[1]'
                views = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_simple))
                ).text
                
            except TimeoutException:
                views= "N/A"
        
        #extraer fecha
        try:
            # Primero intenta extraer la fecha en formato expandido
            xpath_expanded = '//*[@id="info"]/span[3]'  # Año completo
            date = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.XPATH, xpath_expanded))
            ).text
            
        except TimeoutException:
            try:
                # Si no está expandida, intenta el formato simplificado ("hace x días")
                xpath_simple = '//*[@id="info"]/span[3]'
                date = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_simple))
                ).text
                
            except TimeoutException:
                date= "N/A"

        # Extraer likes
        try:
            #likes = WebDriverWait(driver, 10).until(
                #EC.visibility_of_element_located((By.XPATH, '//*[@id="top-level-buttons-computed"]//yt-formatted-string'))
            #).text
            #likes = WebDriverWait(driver, 10).until(
            #EC.visibility_of_element_located((By.XPATH, '//div[contains(@class, "yt-spec-button-shape-next__button-text-content")]'))
            #).text
            #like_button = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//button[contains(@aria-label, "me gusta")]')))
            #ikes = like_button.get_attribute("aria-label").split()[0]  # Extraer el número de "Likes"
            # XPath directo copiado desde DevTools
            xpath = '//*[@id="top-level-buttons-computed"]/segmented-like-dislike-button-view-model/yt-smartimation/div/div/like-button-view-model/toggle-button-view-model/button-view-model/button/div[2]'
    
            # Esperar a que el botón de "Me gusta" sea visible
            likes = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
            ).text
        except TimeoutException:
            print("No se encontraron los likes dentro del tiempo de espera.")
            likes = "N/A"

        # Extraer un comentario
        try:
            # Hacer scroll para cargar comentarios
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)

            # Cambiar al iframe de los comentarios (si existe)
            try:
                iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//iframe[@id="comments-iframe"]'))
                )
                driver.switch_to.frame(iframe)
            except TimeoutException:
                print("No se encontró el iframe de comentarios.")
                comment = "N/A"
            else:
                # Extraer el comentario dentro del iframe
                try:
                    comment = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="content-text"]/span'))
                    ).text
                    print(f"Comentario: {comment}")
                except TimeoutException:
                    print("No se encontró el comentario dentro del iframe.")
                    comment = "N/A"
                finally:
                    # Volver al contenido principal
                    driver.switch_to.default_content()
        except Exception as e:
            print(f"Error al obtener el comentario: {e}")
            comment = "N/A"

        # Guardar en lista
        data.append([title, likes, description, comment, link, date, views])

# Guardar en CSV
with open('plata_card_videos.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Title', 'Likes', 'Description', 'Comment', 'Link', 'fecha', 'vistas'])
    writer.writerows(data)
    print(f"Datos escritos en el archivo: {file.name}")

# Cerrar navegador
driver.quit()