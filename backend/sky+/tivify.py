from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def automatizar_tivify(email, password, canal_deseado):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("Accediendo a Tivify...")
        driver.get("https://www.tivify.tv")
        
        # Esperar a que la página cargue
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        print("Buscando botón de inicio de sesión...")
        try:
            # Intentar varios selectores posibles
            login_attempts = [
                (By.XPATH, "//button[contains(., 'Iniciar sesión')]"),
                (By.XPATH, "//a[contains(., 'Iniciar sesión')]"),
                (By.CSS_SELECTOR, "[data-testid='login-button']"),
                (By.ID, "loginButton")
            ]
            
            for by, selector in login_attempts:
                try:
                    login_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    login_button.click()
                    print("Botón de inicio de sesión encontrado")
                    break
                except:
                    continue
            else:
                raise Exception("No se pudo encontrar el botón de inicio de sesión")
                
            # Continuar con el proceso de login...
            
        except Exception as e:
            print(f"Error: {str(e)}")
            driver.save_screenshot("error.png")
            raise
            
    finally:
        driver.quit()

# Ejecutar
automatizar_tivify("tu_email", "tu_contraseña", "Canal deseado")