from google.cloud import storage
import os

BUCKET_NAME = "vboxio-off"
CARPETA_BUCKET = "mex/nu9ve/recording"  # cambia a la ruta que necesites
DIRECTORIO_VIDEOS = "/home/ignacio_lopez"
EXTENSION = ".mkv"

def subir_videos_a_bucket():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    for archivo in os.listdir(DIRECTORIO_VIDEOS):
        if archivo.endswith(EXTENSION):
            ruta_local = os.path.join(DIRECTORIO_VIDEOS, archivo)
            blob = bucket.blob(f"{CARPETA_BUCKET}/{archivo}")
            blob.upload_from_filename(ruta_local)
            print(f"✅ Subido: {archivo} → gs://{BUCKET_NAME}/{CARPETA_BUCKET}/")

subir_videos_a_bucket()
