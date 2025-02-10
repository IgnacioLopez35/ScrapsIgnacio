import time
import random
import json
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ajusta la ruta a tu ChromeDriver
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"

INSTAGRAM_USERNAME = "redzone_rr"
INSTAGRAM_PASSWORD = "provisional2628"

def setup_driver():
    chrome_options = Options()
    # Modo no-headless para depurar y ver la ventana
    # (Si quieres headless, descomenta la línea de abajo)
    # chrome_options.add_argument("--headless")

    # User-Agent normal
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument(f"--user-agent={user_agent}")

    # Desactivar algunas huellas de automatización
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver

def instagram_forced_login(driver, username, password):
    """Abre Instagram en la URL de login y fuerza el inicio de sesión."""
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)  # Damos un pequeño respiro para que cargue
        
        # Aceptar cookies (si aparece el banner).
        # El texto exacto depende del idioma. Ajusta si hace falta.
        try:
            accept_cookies = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar todas las cookies')]")
            accept_cookies.click()
            time.sleep(2)
            print("[INFO] Cookies aceptadas.")
        except:
            pass

        # Espera a que aparezca el campo "username"
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        # Rellena el usuario
        user_input = driver.find_element(By.NAME, "username")
        user_input.clear()
        user_input.send_keys(username)

        # Rellena la contraseña
        pass_input = driver.find_element(By.NAME, "password")
        pass_input.clear()
        pass_input.send_keys(password)

        # Clic en "submit"
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        print("[INFO] Credenciales enviadas, esperando la respuesta...")

        # Esperamos a que desaparezca el campo "username" => login exitoso
        # o en su defecto, aparezca otro elemento que indique que ya cargó la home.
        try:
            WebDriverWait(driver, 15).until_not(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            print("[INFO] Login completado (desapareció el campo username).")
        except:
            # Si sigue ahí, tal vez hay un error de credenciales o un checkpoint
            print("[WARNING] Es posible que no se haya completado el login.")
        
        # (Opcional) Imprime la URL actual y parte del contenido para inspeccionar
        print("[DEBUG] URL tras login:", driver.current_url)
        page_source = driver.page_source[:1000]  # solo 1000 chars para no saturar
        print("[DEBUG] Parte del page_source:\n", page_source)

    except Exception as e:
        print("[ERROR] en instagram_forced_login:", e)
        traceback.print_exc()

def main():
    driver = setup_driver()
    try:
        instagram_forced_login(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        # Espera unos segundos para observar
        time.sleep(5)

        # Revisa si realmente estás logueado.
        # Por ejemplo, intenta abrir la home "instagram.com" y ver si te muestra feed.
        driver.get("https://www.instagram.com/")
        time.sleep(5)
        print("[INFO] URL tras home:", driver.current_url)

        # Imprime parte del contenido
        print("[INFO] page_source de home:\n", driver.page_source[:1000])

        # Aquí podrías continuar con tu scraping si estás logueado
        # ...
        
    finally:
        driver.quit()
        print("[INFO] Finalizado.")

if __name__ == "__main__":
    main()





