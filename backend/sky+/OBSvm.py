import time
import subprocess
from obsws_python import ReqClient
duracion = 600  # segundos

# Conecta a OBS
client = ReqClient(host="localhost", port=4455, password=None)

print("🎥 Iniciando grabación...")
client.start_record()

# Graba
time.sleep(duracion)

# Detiene
client.stop_record()
print("✅ Grabación finalizada.")
