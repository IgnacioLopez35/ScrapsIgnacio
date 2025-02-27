import os
import requests
import json
import tweepy
import pytz
import time
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils import * 


# Definir la zona horaria de la Ciudad de México
mexico_tz = pytz.timezone("America/Mexico_City")

# Obtener la fecha y hora actual en la zona horaria de Ciudad de México
now_mexico = datetime.now(mexico_tz)

# Calcular la fecha de inicio (24 horas antes)
start_time_mexico = now_mexico - timedelta(hours=24)

# Convertir las fechas al formato UTC requerido por la API de Twitter
start_time_utc = start_time_mexico.astimezone(pytz.utc)
end_time_utc = now_mexico.astimezone(pytz.utc)

# Convertir a formato ISO 8601
start_time_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
end_time_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


print(f"📅 Rango de fechas: {start_time_str} - {end_time_str}")

# Función para convertir UTC a hora de CDMX
def convertir_hora_utc_a_cdmx(fecha_utc):
    try:
        if "." in fecha_utc:
            utc_dt = datetime.strptime(fecha_utc, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            utc_dt = datetime.strptime(fecha_utc, "%Y-%m-%dT%H:%M:%SZ")
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        return utc_dt.astimezone(mexico_tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"⚠️ Error al convertir fecha: {fecha_utc} -> {e}")
        return fecha_utc  # Devuelve la original si falla

# Convertir a formato ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
start_time_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
end_time_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
print(start_time_str)
print(end_time_str)

# Especificar la ruta del archivo .env
dotenv_path = f"{path_env}.env"  # Ruta absoluta
# dotenv_path = os.path.join(os.getcwd(), "config", ".env")  # Ruta relativa

# Cargar las variables de entorno desde la ruta especificada
load_dotenv(dotenv_path=dotenv_path)
api_key = os.getenv("API_X_KEY")
api_secret_key = os.getenv("API_X_SECRET_KEY")
access_token = os.getenv("ACCESS_X_TOKEN")
access_token_secret = os.getenv("ACCESS_X_TOKEN_SECRET")
#bearer_token = os.getenv("BEARER_X_TOKEN")
BEARER_TOKEN = os.getenv("BEARER_X_TOKEN")
USER_ID  = os.getenv("USER_X_ID")

# Autenticación con Tweepy
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Obtener el ID de la cuenta de Cinépolis
USERNAME = "cinepolis"  # Nombre de usuario en X (Twitter)
try:
    # Obtener el ID del usuario de Twitter de forma dinámica
    user_data = client.get_user(username=USERNAME)
    if user_data.data:
        USER_ID = user_data.data.id
        print(f"✅ User ID obtenido dinámicamente: {USER_ID}")
        time.sleep(60)
    else:
        print("❌ No se encontró el usuario. Verifica si el nombre es correcto.")
        exit()
except tweepy.TweepyException as e:
    print(f"❌ Error al obtener User ID: {e}")
    exit()
#
# URL correcta para obtener tweets de un usuario específico
url = f"https://api.twitter.com/2/users/{USER_ID}/tweets"

# Encabezados de la solicitud
headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}
#organic_metrics
#public_metrics
# Parámetros de búsqueda (últimos 2 tweets)
params = {
    "max_results": 5,
    "tweet.fields": "article,created_at,public_metrics,text,author_id,entities",
    "media.fields": "url,public_metrics,duration_ms",
    "start_time":start_time_str,
    "end_time":end_time_str,
    "exclude": "retweets,replies"  # Evita respuestas y retweets
}



# Realizar la petición GET a la API de X
response = requests.get(url, headers=headers, params=params)
print(response.headers)

# Verificar si la respuesta fue exitosa
if response.status_code == 200:
    data = response.json()

    # Verificar si hay tweets en la respuesta
    if "data" not in data or not data["data"]:
        print("⚠️ No se encontraron tweets en el rango de fechas especificado.")
        exit()

    # Convertir la fecha de UTC a CDMX en cada tweet
    for tweet in data["data"]:
        tweet["created_at_cdmx"] = convertir_hora_utc_a_cdmx(tweet["created_at"])

    
    # Guardar el JSON en un archivo
    json_filename = "tweets_cinepolis.json"
    with open(json_filename, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)
    
    print(f"✅ Tweets guardados en {json_filename}")
    print(json.dumps(data, indent=2, ensure_ascii=False))  # Mostrar el JSON en consola
else:
    print(f"❌ Error {response.status_code}: {response.text}")

# Cargar la respuesta JSON guardada anteriormente
json_filename = "tweets_cinepolis.json"


# Procesar tweets y calcular métricas
tweets_metrics = []

for tweet in data["data"]:
    tweet_id = tweet["id"]
    text = tweet["text"]
    created_at = tweet["created_at_cdmx"]
    retweets = tweet["public_metrics"]["retweet_count"]
    replies = tweet["public_metrics"]["reply_count"]
    likes = tweet["public_metrics"]["like_count"]
    quotes = tweet["public_metrics"]["quote_count"]
    bookmarks = tweet["public_metrics"]["bookmark_count"]
    impressions = tweet["public_metrics"]["impression_count"]

    # Calcular engagement
    engagement = retweets + replies + likes + quotes + bookmarks

    # Obtener segundos vistos si están disponibles
    segundos_vistos = tweet.get("media", {}).get("duration_ms", 0) / 1000  # Convertir de ms a s

    # Guardar métricas
    tweets_metrics.append({
        "Tweet ID": tweet_id,
        "Texto": text,
        "Fecha_CDMX": created_at,
        "Retweets": retweets,
        "Respuestas": replies,
        "Likes": likes,
        "Citas": quotes,
        "Guardados": bookmarks,
        "Impresiones": impressions,
        "Engagement": engagement,
        "Segundos Vistos": segundos_vistos
    })

# Crear DataFrame y guardar CSV
df_tweets = pd.DataFrame(tweets_metrics)
df_tweets.head()
csv_filename = "engagement_tweets.csv"
df_tweets.to_csv(csv_filename, index=False, encoding="utf-8")

print(f"✅ Archivo CSV guardado exitosamente: {csv_filename}")

