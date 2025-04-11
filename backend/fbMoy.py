def _extract_date(self, post):
        """Extrae la fecha de publicación"""
        try:
            # Intentar múltiples selectores para encontrar la fecha
            date_selectors = [
                ".//span[contains(@class, 'x4k7w5x') and contains(@class, 'x1h91t0o')]",
                ".//a[contains(@class, 'x1i10hfl')]//span[contains(@class, 'x4k7w5x')]",
                ".//span[contains(@class, 'x4k7w5x')]//a",
                ".//span[contains(text(), 'h') or contains(text(), 'd') or contains(text(), 'min')]",
                ".//a//span[contains(text(), 'h') or contains(text(), 'min') or contains(text(), 'seg')]",
                ".//abbr[@data-tooltip-content]",  # Para publicaciones antiguas
                ".//span[contains(@aria-label, ':')]",  # Buscar spans que contengan tiempos tipo 12:34
                ".//span[contains(text(), 'de abril') or contains(text(), 'de marzo') or contains(text(), 'de mayo') or contains(text(), 'de enero') or contains(text(), 'de febrero') or contains(text(), 'de junio') or contains(text(), 'de julio') or contains(text(), 'de agosto') or contains(text(), 'de septiembre') or contains(text(), 'de octubre') or contains(text(), 'de noviembre') or contains(text(), 'de diciembre')]"
            ]
            
            for selector in date_selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            date_text = element.text.strip()
                            if date_text and (any(time_unit in date_text.lower() for time_unit in ['h', 'min', 'seg', 'hr', 'ayer', 'hoy']) or 
                                              any(month in date_text.lower() for month in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or
                                              re.search(r'\d{1,2}:\d{2}', date_text)):
                                print(f"Fecha encontrada: {date_text}")
                                return date_text
                except:
                    continue
                    
            # Intentar con la fecha de la propiedad data-tooltip-content si está disponible
            try:
                abbr_element = post.find_element(By.XPATH, ".//abbr")
                date_tooltip = abbr_element.get_attribute("data-tooltip-content")
                if date_tooltip:
                    return date_tooltip
            except:
                pass
                
            return "Fecha no disponible"
        except Exception as e:
            print(f"Error al extraer fecha: {str(e)}")
            return "Fecha no disponible"
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
        
        # Usar el Service Manager de Selenium para descargar y gestionar el driver automáticamente
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        
        try:
            print("Intentando iniciar Chrome con WebDriver Manager...")
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("Chrome iniciado exitosamente con WebDriver Manager")
        except Exception as e:
            print(f"Error al iniciar Chrome: {str(e)}")
            raise Exception("No se pudo inicializar ChromeDriver. Verifica la instalación.")
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self):
        """Inicia sesión en Facebook con manejo mejorado de errores y tiempo de espera"""
        try:
            print("Iniciando navegación a Facebook...")
            self.driver.get("https://www.facebook.com/")
            
            # Esperar a que la página se cargue completamente
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)  # Espera adicional para asegurar carga completa
            
            # Aceptar cookies si aparece el diálogo (múltiples intentos con diferentes selectores)
            cookies_selectors = [
                "//button[contains(string(), 'cookies') or contains(string(), 'Cookie')]",
                "//button[contains(text(), 'Permitir') or contains(text(), 'Aceptar')]",
                "//button[contains(@class, 'x1lliihq')]",
                "//button[@aria-label='Permitir todas las cookies']"
            ]
            
            for selector in cookies_selectors:
                try:
                    cookies_buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in cookies_buttons:
                        if button.is_displayed():
                            button.click()
                            print(f"Diálogo de cookies aceptado con selector: {selector}")
                            time.sleep(1)
                            break
                except:
                    continue
            
            # Verificar si ya hay sesión iniciada
            try:
                already_logged_in = False
                logged_in_indicators = [
                    "//div[@aria-label='Cuenta']",
                    "//div[@aria-label='Tu perfil']",
                    "//a[contains(@href, '/me/')]",
                    "//div[contains(@class, 'x1i10hfl') and contains(@class, 'xjbqb8w')]//span[contains(@class, 'x3nfvp2')]"
                ]
                
                for indicator in logged_in_indicators:
                    try:
                        if self.driver.find_element(By.XPATH, indicator).is_displayed():
                            already_logged_in = True
                            break
                    except:
                        pass
                
                if already_logged_in:
                    print("Ya hay una sesión iniciada en Facebook")
                    return True
            except:
                # No hay sesión, continuar con el inicio de sesión
                pass
            
            # Capturar una imagen de la página de login para diagnóstico
            try:
                screenshot_path = f"fb_login_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Captura de pantalla guardada en {screenshot_path}")
            except Exception as e:
                print(f"No se pudo guardar captura de pantalla: {str(e)}")
            
            # Detectar el formulario y los campos de inicio de sesión
            try:
                # Ingresar email
                email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
                email_field.clear()  # Limpiar el campo primero
                email_field.send_keys(self.email)
                print("Email ingresado")
                
                # Ingresar contraseña
                password_field = self.driver.find_element(By.ID, "pass")
                password_field.clear()  # Limpiar el campo primero
                password_field.send_keys(self.password)
                print("Contraseña ingresada")
                
                # Hacer clic en el botón de inicio de sesión
                login_button = self.driver.find_element(By.NAME, "login")
                login_button.click()
                print("Botón de inicio de sesión pulsado")
                
                # Esperar a que se complete el inicio de sesión (tiempo más largo)
                time.sleep(8)
                
                # Comprobar si hay mensaje de error
                try:
                    error_messages = self.driver.find_elements(By.XPATH, "//div[@role='alert']")
                    for error in error_messages:
                        if error.is_displayed():
                            print(f"Error de inicio de sesión detectado: {error.text}")
                            return False
                except:
                    # No hay mensaje de error, probablemente el inicio de sesión fue exitoso
                    pass
                
                # Verificar si hay desafío de seguridad o verificación adicional
                try:
                    security_challenges = [
                        "//input[@name='approvals_code']",  # Código de verificación
                        "//input[@id='captcha_response']",  # Captcha
                        "//button[contains(text(), 'Continuar')]",  # Pantalla de confirmación
                        "//h2[contains(text(), 'Verificar tu identidad')]",  # Verificación de identidad
                        "//span[contains(text(), 'Confirmar tu identidad')]"  # Otra forma de verificación
                    ]
                    
                    for challenge in security_challenges:
                        try:
                            if self.driver.find_element(By.XPATH, challenge).is_displayed():
                                print(f"Se detectó un desafío de seguridad/verificación adicional: {challenge}")
                                # Capturar imagen para ver qué desafío es
                                screenshot_path = f"fb_security_challenge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                self.driver.save_screenshot(screenshot_path)
                                print(f"Captura del desafío guardada en {screenshot_path}")
                                print("Es posible que necesites iniciar sesión manualmente en Facebook")
                                return False
                        except:
                            pass
                except:
                    pass
                
                # Intentar confirmar inicio de sesión con múltiples indicadores
                success_indicators = [
                    "//div[@role='main']",
                    "//div[@aria-label='Cuenta']",
                    "//div[@aria-label='Tu perfil']",
                    "//a[contains(@href, '/me/')]",
                    "//div[contains(@class, 'x1i10hfl') and contains(@class, 'xjbqb8w')]//span[contains(@class, 'x3nfvp2')]",
                    "//input[@placeholder='Buscar en Facebook']",
                    "//div[@aria-label='Crear']"
                ]
                
                for indicator in success_indicators:
                    try:
                        if self.driver.find_element(By.XPATH, indicator).is_displayed():
                            print(f"Inicio de sesión confirmado con indicador: {indicator}")
                            return True
                    except:
                        pass
                
                # Si llegamos aquí, intentemos una última verificación de URL
                current_url = self.driver.current_url
                if "facebook.com/home" in current_url or "facebook.com/?sk=h_chr" in current_url:
                    print(f"Inicio de sesión confirmado por URL: {current_url}")
                    return True
                
                # Si aún no podemos confirmar, tomemos otra captura para ver dónde estamos
                try:
                    screenshot_path = f"fb_after_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Captura después del intento de inicio de sesión guardada en {screenshot_path}")
                    print(f"URL actual: {self.driver.current_url}")
                except:
                    pass
                
                print("No se pudo confirmar el inicio de sesión, pero intentaremos continuar")
                return False
                
            except Exception as e:
                print(f"Error durante el proceso de inicio de sesión: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error general al iniciar sesión: {str(e)}")
            return False
            
    def go_to_page(self):
        """Navega a la página de Facebook especificada"""
        try:
            print(f"Navegando a {self.page_url}...")
            self.driver.get(self.page_url)
            
            # Esperar a que la página se cargue
            time.sleep(5)  # Espera inicial
            
            # Verificar si estamos en la página correcta
            current_url = self.driver.current_url
            if "login" in current_url or "checkpoint" in current_url:
                print(f"Redirección a página de login detectada: {current_url}")
                print("Probablemente necesitas iniciar sesión manualmente o resolver un desafío de seguridad")
                
                # Intentar capturar una imagen para diagnóstico
                try:
                    screenshot_path = f"fb_redirect_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Captura guardada en {screenshot_path}")
                except:
                    pass
                
                return False
            
            # Esperar a que se cargue el contenido principal
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))
                print(f"Navegación exitosa a {self.page_url}")
                
                # Esperar un poco más para que se cargue el contenido dinámico
                time.sleep(3)
                
                # Intentar aceptar cualquier diálogo que pueda aparecer al entrar a la página
                self._handle_popups()
                
                return True
            except TimeoutException:
                # Si no encontramos el elemento principal, verificar si al menos hay publicaciones
                try:
                    articles = self.driver.find_elements(By.XPATH, "//div[@role='article']")
                    if articles and len(articles) > 0:
                        print(f"Elementos de publicación encontrados en {self.page_url}")
                        return True
                    else:
                        print("No se encontraron publicaciones en la página")
                        return False
                except:
                    print("Error al verificar publicaciones")
                    return False
        except Exception as e:
            print(f"Error al navegar a la página: {str(e)}")
            return False
            
    def _handle_popups(self):
        """Maneja diálogos y popups que pueden aparecer durante la navegación"""
        try:
            # Lista de selectores para botones de cierre de diálogos
            close_selectors = [
                "//div[@aria-label='Cerrar']",
                "//div[@aria-label='Close']",
                "//button[contains(text(), 'Cerrar')]",
                "//button[contains(text(), 'Close')]",
                "//button[contains(text(), 'No, gracias')]",
                "//button[contains(text(), 'No, thanks')]",
                "//button[contains(text(), 'Ahora no')]",
                "//button[contains(text(), 'Not now')]",
                "//div[@role='dialog']//div[@aria-label='Cerrar']"
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in close_buttons:
                        if button.is_displayed():
                            button.click()
                            print(f"Se cerró un diálogo con selector: {selector}")
                            time.sleep(1)
                except:
                    continue
        except Exception as e:
            print(f"Error al manejar popups: {str(e)}")
            
    def __del__(self):
        """Destructor para asegurar que el navegador se cierre"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("Navegador cerrado por destructor")
        except:
            pass
            
    def _extract_post_text(self, post):
        """Extrae el texto de una publicación"""
        try:
            # Intentar múltiples selectores para el texto de la publicación
            selectors = [
                ".//div[contains(@class, 'ecm0bbzt')]",
                ".//div[contains(@data-ad-comet-preview, 'message')]",
                ".//div[@data-ad-preview='message']",
                ".//div[starts-with(@class, 'kvgmc6g5 cxmmr5t8')]",
                ".//span[@dir='auto']//ancestor::div[3]",
                ".//div[@dir='auto']",
                ".//div[contains(@class, 'xdj266r')]",
                ".//div[contains(@class, 'x1iorvi4')]//div[@dir='auto']"
            ]
            
            for selector in selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text
                        if text and len(text) > 5:  # Verificar que el texto tenga al menos 5 caracteres
                            print(f"Texto encontrado con selector: {selector}")
                            return text
                except:
                    continue
                    
            # Si llegamos aquí, intentar hacer clic para expandir el post
            try:
                see_more_buttons = post.find_elements(By.XPATH, ".//div[contains(text(), 'Ver más')]")
                for button in see_more_buttons:
                    button.click()
                    time.sleep(1)
                
                # Intentar de nuevo después de expandir
                for selector in selectors:
                    try:
                        elements = post.find_elements(By.XPATH, selector)
                        for element in elements:
                            text = element.text
                            if text and len(text) > 5:
                                return text
                    except:
                        continue
            except:
                pass
                
            return "No se pudo extraer el texto"
        except Exception as e:
            print(f"Error al extraer texto: {str(e)}")
            return "No se pudo extraer el texto"
                
    def _extract_likes(self, post):
        """Extrae el número de likes/reacciones de una publicación"""
        try:
            # Intentar múltiples selectores para los likes/reacciones
            selectors = [
                ".//span[contains(@class, 'x1e558r4')]",
                ".//span[contains(@class, 'xlyipyv')]",
                ".//span[contains(text(), 'Me gusta')]//ancestor::div[2]//span[@class]",
                ".//div[@aria-label='Me gusta']//span",
                ".//span[contains(text(), 'personas')]",
                ".//span[contains(@class, 'x193iq5w')]",
                ".//div[contains(@class, 'x1n2onr6')]//span[contains(@class, 'xt0psk2')]"
            ]
            
            for selector in selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            likes_text = element.text
                            
                            # Buscar números en el texto
                            likes_match = re.search(r'\b\d+\b', likes_text)
                            if likes_match:
                                print(f"Likes encontrados: {likes_match.group()}")
                                return int(likes_match.group())
                except:
                    continue
            
            # Intentar detectar el botón de me gusta o reacciones
            reaction_selectors = [
                ".//div[@aria-label='Me gusta']",
                ".//div[@aria-label='Me encanta']",
                ".//div[@aria-label='Reaccionar']",
                ".//span[@class='x1e558r4']"
            ]
            
            for selector in reaction_selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    if elements and len(elements) > 0:
                        # Contar las reacciones visibles
                        print(f"Encontradas {len(elements)} reacciones")
                        
                        # Intentar obtener el texto asociado
                        for element in elements:
                            # Intentar encontrar el texto de conteo cerca del botón de reacción
                            try:
                                count_element = element.find_element(By.XPATH, "..//span")
                                if count_element and count_element.text:
                                    num_match = re.search(r'\d+', count_element.text)
                                    if num_match:
                                        return int(num_match.group())
                            except:
                                pass
                        
                        # Si no podemos obtener el número exacto, al menos sabemos que hay alguna reacción
                        return len(elements)
                except:
                    continue
            
            return 0
        except Exception as e:
            print(f"Error al extraer likes: {str(e)}")
            return 0
            
    def _extract_comments_count(self, post):
        """Extrae el número de comentarios de una publicación"""
        try:
            # Intentar múltiples selectores para los comentarios
            selectors = [
                ".//span[contains(text(), 'comentario')]",
                ".//span[contains(text(), 'coment')]",
                ".//a[contains(text(), 'comentario')]",
                ".//a[contains(@href, 'comment')]",
                ".//span[contains(@class, 'x193iq5w')]//span[contains(text(), 'coment')]"
            ]
            
            for selector in selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    for element in elements:
                        comments_text = element.text
                        # Buscar números en el texto
                        comments_match = re.search(r'\b\d+\b', comments_text)
                        if comments_match:
                            print(f"Comentarios encontrados con selector: {selector}")
                            return int(comments_match.group())
                except:
                    continue
                    
            # Contar directamente los comentarios visibles
            try:
                comments = post.find_elements(By.XPATH, ".//div[@aria-label='Comentario']")
                if comments:
                    print(f"Encontrados {len(comments)} comentarios visibles")
                    return len(comments)
            except:
                pass
                
            return 0
        except Exception as e:
            print(f"Error al extraer número de comentarios: {str(e)}")
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
            # Buscar todos los elementos de comentarios con múltiples selectores
            selectors = [
                ".//div[@aria-label='Comentario']",
                ".//div[contains(@class, 'x1y332i5')]",  # Clase común para contenedores de comentarios
                ".//div[contains(@class, 'ecm0bbzt') and contains(@class, 'e5nlhep0')]",
                ".//ul[contains(@class, 'x1o0d4y7')]//li",  # Lista de comentarios
                ".//div[@role='article']//div[@role='article']",  # Comentarios como artículos anidados
                ".//div[contains(@class, 'x1pi30zi')]",  # Contenedor de comentarios en algunas páginas
                ".//div[contains(@class, 'x1r8uery')]"   # Otro contenedor común de comentarios
            ]
            
            comment_elements = []
            for selector in selectors:
                try:
                    elements = post.find_elements(By.XPATH, selector)
                    if elements and len(elements) > 0:
                        print(f"Encontrados {len(elements)} comentarios con selector: {selector}")
                        comment_elements = elements
                        break
                except:
                    continue
            
            for comment in comment_elements:
                try:
                    # Intentar extraer el autor del comentario con múltiples selectores
                    author = "Usuario desconocido"
                    author_selectors = [
                        ".//a[@role='link']",
                        ".//span[contains(@class, 'x3nfvp2')]",
                        ".//h3[contains(@class, 'x1heor9g')]",
                        ".//span[@dir='auto' and @class]//ancestor::a",
                        ".//div[contains(@class, 'x1i10hfl')]//span",
                        ".//span[contains(@class, 'xt0psk2')]"
                    ]
                    
                    for selector in author_selectors:
                        try:
                            author_element = comment.find_element(By.XPATH, selector)
                            if author_element.is_displayed() and author_element.text and len(author_element.text) > 0:
                                author = author_element.text
                                break
                        except:
                            continue
                    
                    # Intentar extraer el texto del comentario con múltiples selectores
                    text = "No se pudo extraer el comentario"
                    text_selectors = [
                        ".//div[contains(@class, 'ecm0bbzt')]",
                        ".//div[@dir='auto']",
                        ".//span[@dir='auto']/ancestor::div[1]",
                        ".//div[contains(@class, 'x1xlr1w8')]",
                        ".//div[contains(@class, 'xdj266r')]",
                        ".//div[contains(@class, 'x11i5rnm')]",
                        ".//div[contains(@class, 'x16tdsg8')]"
                    ]
                    
                    for selector in text_selectors:
                        try:
                            text_elements = comment.find_elements(By.XPATH, selector)
                            for text_element in text_elements:
                                if text_element.is_displayed() and text_element.text and len(text_element.text) > 1:
                                    # Verificar que el texto no sea el nombre del autor
                                    if text_element.text != author and len(text_element.text) > len(author):
                                        text = text_element.text
                                        break
                            if text != "No se pudo extraer el comentario":
                                break
                        except:
                            continue
                    
                    # Intentar extraer la fecha del comentario
                    comment_date = "Fecha no disponible"
                    date_selectors = [
                        ".//span[contains(@class, 'x4k7w5x')]",
                        ".//span[contains(text(), 'h') or contains(text(), 'min')]",
                        ".//a//span[contains(@class, 'x1iorvi4')]"
                    ]
                    
                    for selector in date_selectors:
                        try:
                            date_elements = comment.find_elements(By.XPATH, selector)
                            for date_element in date_elements:
                                if date_element.is_displayed() and date_element.text:
                                    date_text = date_element.text.strip()
                                    if any(time_unit in date_text.lower() for time_unit in ['h', 'min', 'hr', 'seg', 'd']):
                                        comment_date = date_text
                                        break
                            if comment_date != "Fecha no disponible":
                                break
                        except:
                            continue
                    
                    # Añadir a la lista de comentarios si tenemos autor o texto válido
                    if (author != "Usuario desconocido" or text != "No se pudo extraer el comentario") and text != author:
                        comments.append({
                            "autor": author,
                            "texto": text,
                            "fecha": comment_date
                        })
                except Exception as comment_error:
                    print(f"Error al procesar un comentario: {str(comment_error)}")
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
            # Hacer scroll lentamente para cargar publicaciones
            self._scroll_down(scrolls=5, scroll_pause=3)
            
            # Esperar un poco para que todo se cargue correctamente
            time.sleep(3)
            
            # Intentar hacer clic en cualquier diálogo que pueda interferir
            try:
                dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
                for dialog in dialogs:
                    close_buttons = dialog.find_elements(By.XPATH, ".//div[@aria-label='Cerrar']")
                    for button in close_buttons:
                        try:
                            button.click()
                            print("Se cerró un diálogo")
                            time.sleep(1)
                        except:
                            pass
            except:
                pass
            
            # Encontrar todas las publicaciones con múltiples selectores
            selectors = [
                "//div[@role='article']",
                "//div[contains(@class, 'x1yztbdb')]",
                "//div[contains(@class, 'x1ja2u2z') and contains(@class, 'x1qjc9v5')]"
            ]
            
            # Intentar encontrar publicaciones
            post_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) > 0:
                        print(f"Encontradas {len(elements)} publicaciones con selector: {selector}")
                        post_elements = elements
                        break
                except Exception as e:
                    print(f"Error al buscar publicaciones con selector {selector}: {str(e)}")
                    continue
            
            # Verificar que se hayan encontrado publicaciones
            if not post_elements or len(post_elements) == 0:
                raise Exception("No se encontraron publicaciones. Verifica que estés en la página correcta.")
            
            # Limitar la cantidad de publicaciones a procesar
            post_count = min(len(post_elements), self.posts_limit)
            
            print(f"Encontradas {len(post_elements)} publicaciones. Procesando {post_count}...")
            
            # Procesar cada publicación una por una
            for i in range(post_count):
                try:
                    # Obtener un elemento fresco para evitar el error "stale element reference"
                    # Esto es crucial para evitar problemas después de hacer scroll
                    post_elements = self.driver.find_elements(By.XPATH, selectors[0])
                    
                    if i >= len(post_elements):
                        print(f"No se pudo obtener la publicación {i+1}/{post_count}")
                        all_posts_data.append({
                            "texto": "Error: Publicación no disponible",
                            "likes": 0,
                            "fecha": "Fecha no disponible",
                            "num_comentarios": 0,
                            "comentarios": []
                        })
                        continue
                        
                    post = post_elements[i]
                    
                    # Hacer scroll hasta la publicación para asegurar que es visible
                    # Usar un pequeño offset vertical para evitar problemas con headers flotantes
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post)
                    time.sleep(1.5)  # Esperar más tiempo después del scroll
                    
                    # Extraer información de la publicación
                    post_text = self._extract_post_text(post)
                    likes = self._extract_likes(post)
                    post_date = self._extract_date(post)
                    comments_count = self._extract_comments_count(post)
                    
                    # Para los comentarios, intentar expandirlos primero
                    try:
                        self._expand_comments(post)
                        comments = self._extract_comments(post)
                    except Exception as e:
                        print(f"Error al extraer comentarios para publicación {i+1}: {str(e)}")
                        comments = []
                    
                    # Almacenar los datos
                    post_data = {
                        "texto": post_text,
                        "likes": likes,
                        "fecha": post_date,
                        "num_comentarios": comments_count,
                        "comentarios": comments
                    }
                    
                    all_posts_data.append(post_data)
                    print(f"Procesada publicación {i+1}/{post_count}")
                    
                except Exception as e:
                    print(f"Error al procesar publicación {i+1}: {str(e)}")
                    # Crear una entrada vacía para mantener el conteo
                    all_posts_data.append({
                        "texto": f"Error al procesar esta publicación: {str(e)}",
                        "likes": 0,
                        "fecha": "Fecha no disponible",
                        "num_comentarios": 0,
                        "comentarios": []
                    })
                
            return all_posts_data
                
        except Exception as e:
            print(f"Error al extraer publicaciones: {str(e)}")
            return all_posts_data
            
    def save_to_csv(self, data, filename=None):
        """Guarda los datos en un archivo CSV con formato mejorado"""
        if not filename:
            filename = f"platacard_fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        # Crear una lista plana para el CSV con formato mejorado
        flat_data = []
        
        for post_idx, post in enumerate(data):
            # Si no hay comentarios, añadir una fila solo con datos del post
            if not post['comentarios']:
                flat_data.append({
                    'post_id': post_idx + 1,
                    'post_texto': post['texto'],
                    'post_likes': post['likes'],
                    'post_fecha': post['fecha'],
                    'post_num_comentarios': post['num_comentarios'],
                    'comentario_autor': '',
                    'comentario_texto': '',
                    'comentario_fecha': ''
                })
            else:
                # Añadir una fila para cada comentario
                for comment in post['comentarios']:
                    flat_data.append({
                        'post_id': post_idx + 1,
                        'post_texto': post['texto'],
                        'post_likes': post['likes'],
                        'post_fecha': post['fecha'],
                        'post_num_comentarios': post['num_comentarios'],
                        'comentario_autor': comment['autor'],
                        'comentario_texto': comment['texto'],
                        'comentario_fecha': comment.get('fecha', 'Fecha no disponible')
                    })
                    
        # Crear el DataFrame y guardar como CSV
        df = pd.DataFrame(flat_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Datos guardados en {filename}")
        
        # También guardar una versión JSON con todos los datos estructurados
        try:
            json_filename = filename.replace('.csv', '.json')
            with open(json_filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=2)
            print(f"Datos guardados en formato JSON: {json_filename}")
        except Exception as e:
            print(f"Error al guardar JSON: {str(e)}")

    def close(self):
        """Cierra el navegador"""
        try:
            self.driver.quit()
            print("Navegador cerrado correctamente")
        except Exception as e:
            print(f"Error al cerrar el navegador: {str(e)}")

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
        login_successful = scraper.login()
        
        # Si el inicio de sesión falló pero queremos continuar de todos modos
        # (por si ya hay una sesión activa en el navegador)
        if not login_successful:
            print("El inicio de sesión automático falló, pero intentaremos continuar...")
            
        # Navegar a la página
        if scraper.go_to_page():
            # Extraer publicaciones
            posts_data = scraper.extract_posts()
            
            # Guardar datos en CSV
            if posts_data and len(posts_data) > 0:
                scraper.save_to_csv(posts_data)
            else:
                print("No se extrajeron datos. Revisa los mensajes de error.")
        else:
            print("No se pudo navegar a la página. El script se detendrá.")
    except Exception as e:
        print(f"Error general durante la ejecución: {str(e)}")
    finally:
        # Cerrar el navegador
        scraper.close()