import requests

# Configuración del proxy
PROXY_HOST = "gate.smartproxy.com"
PROXY_PORT = "1006"
PROXY_USER = "sp03mahcda"
PROXY_PASS = "X3s_awrkk90gNbs0YX"

# URL de prueba
url = "http://httpbin.org/ip"

# Configura el proxy
proxies = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
}

# Realiza la solicitud
try:
    response = requests.get(url, proxies=proxies)
    print(response.json())  # Deberías ver la IP del proxy
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")