import logging
from datetime import datetime
from http_client import HttpClient
import requests
import json
import tweepy
import pytz
import time
from datetime import datetime, timedelta

# Configurar logger
logger = logging.getLogger()

class XAPI:
    """Cliente para la API de X (Twitter)"""
    
    def __init__(self, credentials):
        self.bearer_token = credentials.get('bearer_token')
        self.api_key = credentials.get('api_key')
        self.api_key_secret = credentials.get('api_key_secret')
        # Autenticación con Tweepy
        self.client = tweepy.Client(bearer_token=self.bearer_token)

        # Configurar headers para peticiones manuales con requests
        self.headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
    
    # Función para convertir UTC a hora de CDMX
    def convertir_hora_utc_a_cdmx(self,fecha_utc):
        mexico_tz = pytz.timezone("America/Mexico_City")
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
        
    def get_data_json(self):
        # Definir la zona horaria de la Ciudad de México
        mexico_tz = pytz.timezone("America/Mexico_City")

        # Obtener la fecha y hora actual en la zona horaria de Ciudad de México
        now_mexico = datetime.now(mexico_tz)

        # Calcular la fecha de inicio (24 horas antes)
        start_time_mexico = now_mexico - timedelta(hours=48)

        # Convertir las fechas al formato UTC requerido por la API de Twitter
        start_time_utc = start_time_mexico.astimezone(pytz.utc)
        end_time_utc = now_mexico.astimezone(pytz.utc)

        # Convertir a formato ISO 8601
        start_time_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


        print(f"📅 Rango de fechas: {start_time_str} - {end_time_str}")



        # Convertir a formato ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
        start_time_str = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_str = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(start_time_str)
        print(end_time_str)


        USERNAME = "cinepolis"
        # Obtener el ID del usuario de Twitter de forma dinámica
        # user_data = self.client.get_user(username=USERNAME)
        # if user_data.data:
        #     USER_ID = user_data.data.id
        #     print(f"✅ User ID obtenido dinámicamente: {USER_ID}")
        #     time.sleep(45)
        # else:
        #     print("❌ No se encontró el usuario. Verifica si el nombre es correcto.")
        #     exit()

        #url = f"https://api.twitter.com/2/users/{USER_ID}/tweets"
        url = f"https://api.twitter.com/2/users/40355149/tweets"
        params = {
            "max_results": 10,
            "tweet.fields": "article,created_at,public_metrics,text,author_id,entities",
            "media.fields": "url,public_metrics,duration_ms",
            "expansions": "attachments.media_keys",
            "start_time":start_time_str,
            "end_time":end_time_str,
            "exclude": "retweets,replies"  # Evita respuestas y retweets
        }
        try:
            # Hacer la petición a la API
            response = requests.get(url, headers=self.headers, params=params)

            # Verificar el código de respuesta HTTP
            if response.status_code == 200:
                data = response.json()

                # Si la API no devuelve tweets, loguear advertencia
                if "data" not in data or not data["data"]:
                    logger.warning("⚠️ No se encontraron tweets en el rango de fechas especificado.")
                    return {}  # Retorna un diccionario vacío en lugar de `exit()`

                # Convertir la fecha de UTC a CDMX en cada tweet
                for tweet in data["data"]:
                    tweet["created_at_cdmx"] = self.convertir_hora_utc_a_cdmx(tweet["created_at"])

                return data  # ✅ Devuelve la respuesta correctamente

            elif response.status_code == 401:
                logger.error("❌ Error 401: No autorizado. Verifica las credenciales de API.")
            elif response.status_code == 403:
                logger.error("❌ Error 403: Acceso prohibido. Puede ser una restricción de permisos.")
            elif response.status_code == 429:
                logger.error("⚠️ Error 429: Se excedió el límite de solicitudes. Intenta más tarde.")
            else:
                logger.error(f"❌ Error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en la conexión con la API de Twitter: {e}")

        return {}
    
    def transform_data(self,data):

        if not data or "data" not in data:
            print("NO HAY DATOS...")
            return []  # Retorna una lista vacía si no hay datos
    
        media_details = {}
        if "includes" in data and "media" in data["includes"]:
            for media in data["includes"]["media"]:
                media_details[media["media_key"]] = media
        
        # Procesar tweets y calcular métricas
        tweets_metrics = []

        for tweet in data["data"]:
            tweet_id = tweet["id"]
            text = tweet["text"]
            created_at = self.convertir_hora_utc_a_cdmx(tweet["created_at"])
            retweets = tweet["public_metrics"]["retweet_count"]
            replies = tweet["public_metrics"]["reply_count"]
            likes = tweet["public_metrics"]["like_count"]
            quotes = tweet["public_metrics"]["quote_count"]
            bookmarks = tweet["public_metrics"].get("bookmark_count", 0)
            impressions = tweet["public_metrics"].get("impression_count", 0)

            # Calcular engagement
            engagement = retweets + replies + likes + quotes + bookmarks

            # Detectar si es un video
            is_video = False
            video_views = None
            segundos_vistos = None

            if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                for media_key in tweet["attachments"]["media_keys"]:
                    if media_key in media_details:
                        media_info = media_details[media_key]
                        if media_info["type"] == "video":
                            is_video = True
                            video_views = media_info.get("public_metrics", {}).get("view_count", None)
                            segundos_vistos = media_info.get("duration_ms", 0) / 1000

            # Agregar tweet al array
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
                "Es_Video": is_video,
                "Video_Views": video_views if is_video else "N/A",
                "Segundos_Vistos": segundos_vistos if is_video else "N/A"
            })

        return tweets_metrics  # ✅ Ahora se retorna después de procesar todos los tweets


    
    def export_data_for_dashboard(self):
        """Exportar datos para el dashboard"""
        try:
            # Obtener datos
            raw_data = self.get_data_json()
            
            if not raw_data:  # Si no hay datos, devolver estructura vacía
                logger.warning("⚠️ No se encontraron datos de Twitter.")
                return {
                    "platform": "x",
                    "tweets": [],
                    "error": "No se encontraron datos",
                    "updated_at": datetime.now().isoformat()
                }

            # Procesar data
            data = self.transform_data(raw_data)

            # Formatear datos para el dashboard
            return {
                "platform": "x",
                "tweets": data,
                "updated_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error al exportar datos de X para el dashboard: {e}")
            return {
                "platform": "x",
                "tweets": [],
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }
