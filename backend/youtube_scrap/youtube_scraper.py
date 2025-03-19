
import os
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
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==================== CONFIGURACIÓN ====================

# Configuración de la API de YouTube
API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_IDS = [
    "UCwTKziMccZoy631_wbxk8wg",  # Disney Studios LA
    "UC1bOh2t2cLNzGvlRrD5fY-Q",  # Videocine
]
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

# Configuración de proxy (Bright Data)
PROXY_HOST = "brd.superproxy.io"
PROXY_PORT = "33335"
PROXY_USER = "brd-customer-hl_5c6b7303-zone-residential_proxy1"
PROXY_PASS = "your_proxy_password"

# ==================== CONEXIÓN API ====================
youtube = build("youtube", "v3", developerKey=API_KEY)

# ==================== FUNCIÓN PARA LIMPIAR DATOS ====================
def clean_text(text):
    if isinstance(text, str):
        text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'[^\x20-\x7E]', '', text)
        return text.strip()
    return text

# ==================== OBTENER VIDEOS (API) ====================
def get_all_videos(channel_id, start_date, end_date):
    videos = []
    next_page_token = None
    while True:
        try:
            request = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                publishedAfter=f"{start_date}T00:00:00Z",
                publishedBefore=f"{end_date}T23:59:59Z",
                maxResults=50,
                type="video",
                pageToken=next_page_token,
            )
            response = request.execute()
            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                title = clean_text(item["snippet"]["title"])
                description = clean_text(item["snippet"]["description"])
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description
                })
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        except HttpError as e:
            print(f"Error en la API: {e}")
            time.sleep(5)
    return videos

# ==================== SCRAPING CON SELENIUM ====================
def scrape_video_details(video_id):
    chrome_options = Options()
    chrome_options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        # Extraer número de likes (si está disponible)
        try:
            likes = driver.find_element(By.CSS_SELECTOR, "yt-formatted-string[aria-label*='Me gusta']").text
        except Exception:
            likes = None

        # Extraer número de comentarios (si está disponible)
        try:
            comments_section = driver.find_element(By.ID, "comments")
            driver.execute_script("arguments[0].scrollIntoView(true);", comments_section)
            time.sleep(random.uniform(2, 4))
            comments_count = driver.find_element(By.CSS_SELECTOR, "h2#count yt-formatted-string").text
        except Exception:
            comments_count = None

        return {
            "likes": likes,
            "comments_count": comments_count
        }

    except Exception as e:
        print(f"Error en Selenium: {e}")
    finally:
        driver.quit()

# ==================== FUNCIÓN PRINCIPAL ====================
def run_youtube_scraper():
    all_data = []

    for channel in CHANNEL_IDS:
        print(f"Obteniendo datos del canal: {channel}")
        videos = get_all_videos(channel, START_DATE, END_DATE)
        for video in videos:
            details = scrape_video_details(video["video_id"])
            video.update(details)
            all_data.append(video)

    # Guardar resultados en CSV
    df = pd.DataFrame(all_data)
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    df.to_csv("youtube_scraped_data.csv", index=False)
    print("Datos guardados en youtube_scraped_data.csv")

if __name__ == "__main__":
    run_youtube_scraper()
