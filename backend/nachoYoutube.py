import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from agents import agents


class YouTubeScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)

    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de Bright Data.
        """
        PROXY_HOST = "gate.smartproxy.com"
        PROXY_PORT = "10001"
        PROXY_USER = "sp03mahcda"
        PROXY_PASS = "ax4as2g5_S2HHrmIjl"

        # Configuración del navegador
        options = uc.ChromeOptions()

        # 🔒 Evita que los sitios detecten Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")

        # ⚡ Optimiza el rendimiento en servidores sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🚀 Modo headless (sin interfaz gráfica)
        options.add_argument("--headless=new")

        # 🔕 Evita notificaciones emergentes y bloqueos de pop-ups
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # 🔄 Cambia dinámicamente el User-Agent para evitar detección
        options.add_argument(f"--user-agent={self._random_user_agent()}")

        # 🔍 Evita filtración de IP real cuando se usan proxies
        options.add_argument("--disable-webrtc")

        # Configura el proxy con autenticación
        options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
        options.add_argument(f'--proxy-auth={PROXY_USER}:{PROXY_PASS}')

        # 🚀 Inicializa el navegador con opciones anti-detección
        driver = uc.Chrome(options=options, use_subprocess=True)

        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        return driver

    def _random_user_agent(self):
        """
        Devuelve un User-Agent aleatorio para evitar detección.
        """
        return random.choice(agents)

    def _human_delay(self, min_s=1.0, max_s=3.0):
        """
        Pausa aleatoria entre acciones para simular comportamiento humano.
        """
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.3)
        total = max(0, base + gauss_factor)
        time.sleep(total)

    def scrape_youtube_channel(self, channel_url):
        """
        Extrae datos del canal de YouTube.
        """
        self.driver.get(channel_url)
        self._human_delay(3, 5)

        # Desplázate hacia abajo para cargar más videos
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self._human_delay(2, 4)
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Extraer enlaces de los videos
        videos = self.driver.find_elements(By.XPATH, '//a[@id="thumbnail" and contains(@href, "/watch?v=")]')
        video_links = [video.get_attribute("href") for video in videos]

        # Extraer datos de cada video
        data = []
        for link in video_links:
            self._human_delay(3, 5)
            video_data = self._extract_video_data(link)
            if video_data:
                data.append(video_data)

        return data

    def _extract_video_data(self, url):
        """
        Extrae datos de un video de YouTube.
        """
        self.driver.get(url)
        self._human_delay(3, 5)

        try:
            # Extraer título del video
            title = self.driver.find_element(By.XPATH,
                                             '//h1[@class="title style-scope ytd-video-primary-info-renderer"]').text

            # Extraer likes
            likes = self.driver.find_element(By.XPATH,
                                             '//*[@id="top-level-buttons-computed"]/ytd-toggle-button-renderer[1]/a').text

            # Extraer comentarios
            comments = self.driver.find_elements(By.XPATH, '//yt-formatted-string[@id="content-text"]')
            comments_text = [comment.text for comment in comments]

            return {
                "url": url,
                "title": title,
                "likes": likes,
                "comments": comments_text
            }
        except Exception as e:
            print(f"Error extrayendo datos del video: {e}")
            return None

    def close(self):
        """
        Cierra el navegador.
        """
        self.driver.quit()


#Ejemplo de uso
if __name__ == "__main__":
    scraper = YouTubeScraper()
    try:
        # Scrapear un canal de YouTube
        channel_url = "https://www.youtube.com/@Platacard/videos"
        data = scraper.scrape_youtube_channel(channel_url)
        print(data)  # Imprime los datos extraídos
    finally:
        # Cerrar el navegador
        scraper.close()