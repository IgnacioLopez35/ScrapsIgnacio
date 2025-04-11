from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
import re
import os
from datetime import datetime

class FacebookScraper:
    def __init__(self, email, password, page_url, posts_limit=10, headless=False):
        """
        Inicializa el scraper de Facebook
        
        Args:
            email (str): Email para iniciar sesión en Facebook
            password (str): Contraseña para iniciar sesión
            page_url (str): URL de la página de Facebook a scrapear
            posts_limit (int): Número máximo de posts a extraer
            headless (bool): Si el navegador debe ejecutarse en modo headless
        """
        self.email = email
        self.password = password
        self.page_url = page_url
        self.posts_limit = posts_limit
        
        # Configurar opciones de Chrome
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        
        # Usar ChromeDriver instalado con Homebrew
        try:
            # Primero intentar con la detección automática
            self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"Error con detección automática: {str(e)}")
            print("Intentando con rutas específicas de Homebrew...")
            
            # Rutas comunes de Homebrew
            possible_paths = [
                "/usr/local/bin/chromedriver",
                "/opt/homebrew/bin/chromedriver"
            ]
            
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        print(f"Usando ChromeDriver en: {path}")
                        service = Service(path)
                        self.driver = webdriver.Chrome(service=service, options=options)
                        break
                except Exception as err:
                    print(f"Error con {path}: {str(err)}")
            else:
                raise Exception("No se pudo inicializar ChromeDriver. Verifica la instalación.")
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self):
        """Inicia sesión en Facebook"""
        try:
            self.driver.get("https://www.facebook.com/")
            
            # Aceptar cookies si aparece el diálogo
            try:
                cookies_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(string(), 'cookies') or contains(string(), 'Cookie')]")))
                cookies_button.click()
            except:
                print("No se encontró diálogo de cookies o ya fue aceptado")
            
            # Ingresar email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            email_field.send_keys(self.email)
            
            # Ingresar contraseña
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.send_keys(self.password)
            
            # Hacer clic en el botón de inicio de sesión
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Esperar a que se cargue la página principal
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))
            print("Inicio de sesión exitoso!")
            return True
            
        except Exception as e:
            print(f"Error al iniciar sesión: {str(e)}")
            return False
            
    def go_to_page(self):
        """Navega a la página de Facebook especificada"""
        try:
            self.driver.get(self.page_url)
            # Esperar a que la página se cargue
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))
            print(f"Navegación exitosa a {self.page_url}")
            return True
        except Exception as e:
            print(f"Error al navegar a la página: {str(e)}")
            return False
            
    def _extract_post_text(self, post):
        """Extrae el texto de una publicación"""
        try:
            # Intentar encontrar el texto de la publicación
            text_element = post.find_element(By.XPATH, ".//div[contains(@class, 'ecm0bbzt')]")
            return text_element.text
        except NoSuchElementException:
            # Prueba con un selector diferente si el primero falla
            try:
                text_element = post.find_element(By.XPATH, ".//div[contains(@data-ad-comet-preview, 'message')]")
                return text_element.text
            except:
                return "No se pudo extraer el texto"
                
    def _extract_likes(self, post):
        """Extrae el número de likes de una publicación"""
        try:
            # Intentar encontrar el contador de likes
            like_element = post.find_element(By.XPATH, ".//span[contains(@class, 'x1e558r4')]")
            likes_text = like_element.text
            
            # Extraer solo los números
            likes = re.search(r'\d+', likes_text)
            if likes:
                return int(likes.group())
            return 0
        except:
            return 0
            
    def _extract_comments_count(self, post):
        """Extrae el número de comentarios de una publicación"""
        try:
            # Intentar encontrar el contador de comentarios
            comments_element = post.find_element(By.XPATH, ".//span[contains(text(), 'comentario')]")
            comments_text = comments_element.text
            
            # Extraer solo los números
            comments = re.search(r'\d+', comments_text)
            if comments:
                return int(comments.group())
            return 0
        except:
            return 0
            
    def _expand_comments(self, post):
        """Expande todos los comentarios de una publicación"""
        try:
            # Hacer clic en "Ver comentarios" si existe
            try:
                view_comments = post.find_element(By.XPATH, ".//span[contains(text(), 'Ver') and contains(text(), 'comentario')]")
                view_comments.click()
                time.sleep(2)
            except:
                pass
                
            # Expandir respuestas a comentarios
            try:
                more_replies_buttons = post.find_elements(By.XPATH, ".//span[contains(text(), 'respuesta') or contains(text(), 'Ver más comentarios')]")
                for button in more_replies_buttons:
                    button.click()
                    time.sleep(1)
            except:
                pass
                
            # Expandir comentarios largos
            try:
                more_text_buttons = post.find_elements(By.XPATH, ".//div[contains(text(), 'Ver más')]")
                for button in more_text_buttons:
                    button.click()
                    time.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            print(f"Error al expandir comentarios: {str(e)}")
            
    def _extract_comments(self, post):
        """Extrae todos los comentarios de una publicación"""
        self._expand_comments(post)
        
        comments = []
        try:
            # Buscar todos los elementos de comentarios
            comment_elements = post.find_elements(By.XPATH, ".//div[@aria-label='Comentario']")
            
            for comment in comment_elements:
                try:
                    # Extraer el autor del comentario
                    author = comment.find_element(By.XPATH, ".//a[@role='link']").text
                    
                    # Extraer el texto del comentario
                    text = comment.find_element(By.XPATH, ".//div[contains(@class, 'ecm0bbzt')]").text
                    
                    # Añadir a la lista de comentarios
                    comments.append({
                        "autor": author,
                        "texto": text
                    })
                except:
                    continue
            
            return comments
        except Exception as e:
            print(f"Error al extraer comentarios: {str(e)}")
            return []
            
    def _scroll_down(self, scrolls=5, scroll_pause=2):
        """Hace scroll hacia abajo para cargar más publicaciones"""
        for _ in range(scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            
    def extract_posts(self):
        """Extrae las publicaciones de la página"""
        all_posts_data = []
        
        try:
            # Hacer scroll para cargar publicaciones
            self._scroll_down(scrolls=3)
            
            # Encontrar todas las publicaciones
            post_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']")
            
            # Limitar la cantidad de publicaciones a procesar
            post_count = min(len(post_elements), self.posts_limit)
            
            print(f"Encontradas {len(post_elements)} publicaciones. Procesando {post_count}...")
            
            for i in range(post_count):
                post = post_elements[i]
                
                # Extraer información de la publicación
                post_text = self._extract_post_text(post)
                likes = self._extract_likes(post)
                comments_count = self._extract_comments_count(post)
                comments = self._extract_comments(post)
                
                # Almacenar los datos
                post_data = {
                    "texto": post_text,
                    "likes": likes,
                    "num_comentarios": comments_count,
                    "comentarios": comments
                }
                
                all_posts_data.append(post_data)
                print(f"Procesada publicación {i+1}/{post_count}")
                
            return all_posts_data
                
        except Exception as e:
            print(f"Error al extraer publicaciones: {str(e)}")
            return all_posts_data
            
    def save_to_csv(self, data, filename=None):
        """Guarda los datos en un archivo CSV"""
        if not filename:
            filename = f"platacard_fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        # Crear una lista plana para el CSV
        flat_data = []
        
        for post_idx, post in enumerate(data):
            # Si no hay comentarios, añadir una fila solo con datos del post
            if not post['comentarios']:
                flat_data.append({
                    'post_id': post_idx + 1,
                    'post_texto': post['texto'],
                    'post_likes': post['likes'],
                    'post_num_comentarios': post['num_comentarios'],
                    'comentario_autor': '',
                    'comentario_texto': ''
                })
            else:
                # Añadir una fila para cada comentario
                for comment in post['comentarios']:
                    flat_data.append({
                        'post_id': post_idx + 1,
                        'post_texto': post['texto'],
                        'post_likes': post['likes'],
                        'post_num_comentarios': post['num_comentarios'],
                        'comentario_autor': comment['autor'],
                        'comentario_texto': comment['texto']
                    })
                    
        # Crear el DataFrame y guardar como CSV
        df = pd.DataFrame(flat_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Datos guardados en {filename}")
        
    def close(self):
        """Cierra el navegador"""
        self.driver.quit()

# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    EMAIL = "lopezlopezjoseignacio35@gmail.com"  # Reemplazar con tu email de Facebook
    PASSWORD = "buenosdiasAlegria666"      # Reemplazar con tu contraseña
    PAGE_URL = "https://www.facebook.com/platacard?locale=es_LA"  # URL de la página de Platacard
    POSTS_LIMIT = 10                # Número de publicaciones a extraer
    
    # Iniciar el scraper
    scraper = FacebookScraper(
        email=EMAIL,
        password=PASSWORD,
        page_url=PAGE_URL,
        posts_limit=POSTS_LIMIT,
        headless=False  # Cambiar a True para ejecutar en segundo plano
    )
    
    try:
        # Iniciar sesión
        if scraper.login():
            # Navegar a la página
            if scraper.go_to_page():
                # Extraer publicaciones
                posts_data = scraper.extract_posts()
                
                # Guardar datos en CSV
                scraper.save_to_csv(posts_data)
    finally:
        # Cerrar el navegador
        scraper.close()