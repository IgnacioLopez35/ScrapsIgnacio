from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# Configurar Selenium
options = webdriver.ChromeOptions()
options.add_argument("--lang=es")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

url = "https://es.trustpilot.com/review/bravocredito.es"
driver.get(url)

# 1. Aceptar cookies (si aparecen)
try:
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@id="onetrust-accept-btn-handler"]'))
    ).click()
except:
    print("No se encontró el botón de cookies")

# 2. Esperar a que carguen las reseñas
time.sleep(3)  # Pequeña espera para evitar bloqueos

# 3. Extraer reseñas usando XPath
reviews = []

# Buscar todos los artículos que contienen reseñas
review_articles = driver.find_elements(By.XPATH, '//article[contains(@class, "styles_reviewCard__hcAvl")]')

for review in review_articles:
    try:
        # Extraer autor
        author = review.find_element(By.XPATH, './/span[contains(@class, "typography_heading-xxs__QKBS8")]').text
        
        # Extraer puntuación (ejemplo: "5" de "star-rating-50")
        rating = review.find_element(By.XPATH, './/div[contains(@class, "styles_reviewHeader__iU9Px")]').get_attribute("data-service-review-rating")
        
        # Extraer título
        title = review.find_element(By.XPATH, './/h2[contains(@class, "typography_heading-s__f7029")]').text
        
        # Extraer contenido del comentario (usando el XPath que compartiste, pero relativo)
        content = review.find_element(By.XPATH, './/p[contains(@class, "typography_body-l__KUYFJ")]').text
        
        # Extraer fecha
        date = review.find_element(By.XPATH, './/time').get_attribute("datetime")
        
        reviews.append({
            'Autor': author,
            'Puntuación': rating,
            'Título': title,
            'Contenido': content,
            'Fecha': date
        })
    except Exception as e:
        print(f"Error extrayendo una reseña: {e}")

# Guardar en CSV
if reviews:
    df = pd.DataFrame(reviews)
    df.to_csv("reseñas_bravocredito_xpath.csv", index=False, encoding='utf-8-sig')
    print(f"✅ {len(df)} reseñas guardadas en 'reseñas_bravocredito_xpath.csv'")
else:
    print("❌ No se encontraron reseñas.")

driver.quit()