import time
import subprocess
from obsws_python import ReqClient

# Configura aquí tu video y duración
youtube_url = "https://www.skymas.mx/webclient/#/live"
duracion_grabacion = 30  # segundos

# 1. Abrir Chrome en modo kiosko (pantalla completa sin bordes)
subprocess.Popen([
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--kiosk",
    youtube_url
])

# 2. Espera unos segundos a que se abra el video
time.sleep(5)

# 3. Conectar a OBS y empezar a grabar
client = ReqClient(host="localhost", port=4455, password=None)

print("🎥 Iniciando grabación...")
client.start_record()

# 4. Espera mientras graba
time.sleep(duracion_grabacion)

# 5. Detener grabación
client.stop_record()
print("✅ Grabación finalizada.")


