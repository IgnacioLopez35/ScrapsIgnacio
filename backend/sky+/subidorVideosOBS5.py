import os
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from google.cloud import storage
from obswebsocket import obsws, requests

CARPETA_OBS = "/home/ignacio_lopez"
BUCKET_NAME = "vboxio-off"
RUTA_BUCKET = "mex/nu9ve/recording"
TIEMPO_TOTAL_SEGUNDOS = 1200  # 12 horas
ANTIGUEDAD_MINIMA_SEG = 60  # Esperar al menos 1 minuto de antigüedad

def subir_a_gcs(ruta_local):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    nombre_archivo = os.path.basename(ruta_local)
    blob = bucket.blob(f"{RUTA_BUCKET}/{nombre_archivo}")
    try:
        blob.upload_from_filename(ruta_local)
        print(f"✅ Subido: {nombre_archivo}")
    except Exception as e:
        print(f"❌ Error al subir {nombre_archivo}: {e}")

def esperar_archivo_completo(path, intentos=30, espera=2):
    tam_prev = -1
    for _ in range(intentos):
        if not os.path.exists(path):
            time.sleep(espera)
            continue
        tam_actual = os.path.getsize(path)
        if tam_actual > 0 and tam_actual == tam_prev:
            return True
        tam_prev = tam_actual
        time.sleep(espera)
    return False

# Evitar archivos ya subidos múltiples veces
archivos_subidos = set()

class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".mkv") and event.src_path not in archivos_subidos:
            tiempo_mod = os.path.getmtime(event.src_path)
            edad_archivo = time.time() - tiempo_mod

            if edad_archivo >= ANTIGUEDAD_MINIMA_SEG:
                print(f"📦 Archivo listo: {event.src_path}")
                if esperar_archivo_completo(event.src_path):
                    subir_a_gcs(event.src_path)
                    archivos_subidos.add(event.src_path)
                else:
                    print(f"⚠️ Archivo no estable: {event.src_path}")

def controlar_obs():
    print("📽️ Inicializando subida automática y grabación OBS...")

    observer = Observer()
    handler = Handler()
    observer.schedule(handler, path=CARPETA_OBS, recursive=False)
    observer.start()

    try:
        print("🔌 Conectando a OBS...")
        ws = obsws("localhost", 4455)
        ws.connect()

        print("✅ Grabación iniciada")
        ws.call(requests.StartRecord())

        time.sleep(TIEMPO_TOTAL_SEGUNDOS)

        ws.call(requests.StopRecord())
        print("⏹️ Grabación detenida")
        ws.disconnect()

    finally:
        observer.stop()
        observer.join()
        print("🧹 Finalizado.")

if __name__ == "__main__":
    controlar_obs()
