from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
import datetime
import re
import os
import random

class LinkedInScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        
        # Configurar opciones de Chrome con máxima evasión de detección
        self.chrome_options = Options()
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Opcional: usar un user-agent de móvil - a veces LinkedIn muestra diferentes interfaces
        # self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1')
        
        # Iniciar el driver
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)  # Aumentar tiempo de espera a 20 segundos
        
    def espera_aleatoria(self, min_tiempo=2, max_tiempo=5):
        """Espera un tiempo aleatorio para simular comportamiento humano"""
        tiempo = random.uniform(min_tiempo, max_tiempo)
        time.sleep(tiempo)
        
    def login(self):
        """Iniciar sesión en LinkedIn con simulación de comportamiento humano"""
        try:
            # Abrir página de inicio de sesión
            self.driver.get("https://www.linkedin.com/login")
            self.espera_aleatoria(3, 6)
            
            # Ingresar credenciales con simulación de tipeo humano
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            for char in self.email:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            
            self.espera_aleatoria(1, 2)
            
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            for char in self.password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            
            self.espera_aleatoria(1, 2)
            
            # Hacer clic en el botón de inicio de sesión
            login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            self.driver.execute_script("arguments[0].click();", login_button)
            
            # Esperar a que se cargue la página principal
            self.wait.until(EC.presence_of_element_located((By.ID, "global-nav")))
            self.espera_aleatoria(3, 5)
            print("Inicio de sesión exitoso")
            return True
            
        except Exception as e:
            print(f"Error al iniciar sesión: {str(e)}")
            return False
    
    def extraer_publicacion(self, url_publicacion):
        """Método principal para extraer todos los datos de una publicación"""
        try:
            print(f"Navegando a: {url_publicacion}")
            self.driver.get(url_publicacion)
            
            # Esperar a que la página cargue completamente
            self.espera_aleatoria(10, 15)
            
            # ESTRATEGIA AGRESIVA: Mantener la página abierta y hacer scroll durante un tiempo prolongado
            print("Preparando la página para extracción...")
            
            # 1. Hacer varios scrolls para asegurarse de que todo el contenido esté cargado
            for _ in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.espera_aleatoria(2, 3)
                self.driver.execute_script("window.scrollTo(0, 0);")
                self.espera_aleatoria(1, 2)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                self.espera_aleatoria(1, 2)
            
            # 2. Intentar expandir comentarios con fuerza
            print("Intentando expandir comentarios...")
            try:
                # Intentar hacer clic en todos los elementos que podrían expandir comentarios
                posibles_elementos = [
                    "//button[contains(text(), 'comentarios')]",
                    "//span[contains(text(), 'comentarios')]/..",
                    "//span[contains(@class, 'social-details-social-counts__comments-count')]/..",
                    "//button[contains(@aria-label, 'comentarios')]",
                    "//li[contains(@class, 'social-details-social-counts__comments')]",
                    "//span[contains(text(), 'Ver')]/.."
                ]
                
                for selector in posibles_elementos:
                    try:
                        elementos = self.driver.find_elements(By.XPATH, selector)
                        for elemento in elementos:
                            if elemento.is_displayed():
                                print(f"Haciendo clic en: {elemento.text}")
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                                self.espera_aleatoria(1, 2)
                                self.driver.execute_script("arguments[0].click();", elemento)
                                self.espera_aleatoria(4, 6)
                    except Exception as e:
                        print(f"Error al intentar hacer clic: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error general al expandir comentarios: {str(e)}")
            
            # 3. Más scroll y espera
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.espera_aleatoria(3, 5)
            
            # ESTRATEGIA ALTERNATIVA: Extraer con JavaScript para evitar problemas de DOM
            print("Extrayendo datos usando JavaScript...")
            datos_publicacion = self.extraer_datos_js()
            
            # Si el script JavaScript no funciona, intentar con los métodos tradicionales
            if not datos_publicacion or 'autor' not in datos_publicacion or not datos_publicacion['autor']:
                print("JavaScript no tuvo éxito, intentando con métodos tradicionales...")
                datos_publicacion = self.extraer_datos_tradicional()
            
            # Guardar también la página HTML completa para análisis posterior
            try:
                html_completo = self.driver.page_source
                with open(f"linkedin_publicacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "w", encoding="utf-8") as f:
                    f.write(html_completo)
                print("HTML completo guardado para análisis posterior")
            except Exception as e:
                print(f"Error al guardar HTML: {str(e)}")
            
            return datos_publicacion
            
        except Exception as e:
            print(f"Error en la extracción principal: {str(e)}")
            return {}
    
    def extraer_datos_js(self):
        """Extrae datos usando JavaScript directamente para mayor flexibilidad"""
        try:
            # Script JavaScript que extrae todos los datos relevantes
            js_script = """
            // Función para limpiar texto
            function limpiarTexto(texto) {
                if (!texto) return '';
                return texto.replace(/\\s+/g, ' ').trim();
            }
            
            // Objeto para almacenar los datos
            let datos = {
                autor: '',
                cargo_autor: '',
                fecha: '',
                texto: '',
                reacciones: '0',
                comentarios: '0',
                texto_comentarios: [],
                compartidos: '0',
                tiene_imagen: 'No',
                tiene_video: 'No',
                enlace_externo: 'No'
            };
            
            // Extraer autor (probando múltiples selectores)
            const selectoresAutor = [
                'span.update-components-actor__name',
                'span.feed-shared-actor__name',
                'a.update-components-actor__meta-link span',
                'a.feed-shared-actor__meta-link span'
            ];
            
            for (let selector of selectoresAutor) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.autor = limpiarTexto(elementos[0].textContent);
                    break;
                }
            }
            
            // Extraer cargo
            const selectoresCargo = [
                'span.update-components-actor__description',
                'span.feed-shared-actor__description',
                'div.update-components-actor__description',
                'div.feed-shared-actor__description'
            ];
            
            for (let selector of selectoresCargo) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.cargo_autor = limpiarTexto(elementos[0].textContent);
                    break;
                }
            }
            
            // Extraer fecha
            const selectoresFecha = [
                'span.update-components-actor__sub-description',
                'span.feed-shared-actor__sub-description',
                'span.social-details-social-activity span.visually-hidden'
            ];
            
            for (let selector of selectoresFecha) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.fecha = limpiarTexto(elementos[0].textContent);
                    break;
                }
            }
            
            // Extraer texto de la publicación
            const selectoresTexto = [
                'div.update-components-update-v2__commentary',
                'div.feed-shared-update-v2__description',
                'div.feed-shared-text',
                'div.update-components-text',
                'span.break-words'
            ];
            
            for (let selector of selectoresTexto) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.texto = limpiarTexto(elementos[0].textContent);
                    break;
                }
            }
            
            // Extraer reacciones
            const selectoresReacciones = [
                'span.social-details-social-counts__reactions-count',
                'button[aria-label*="reacciones"] span',
                'span.social-details-social-counts__social-proof-fallback-number',
                'span.reactions-react-button__reactions-count'
            ];
            
            for (let selector of selectoresReacciones) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    let texto = limpiarTexto(elementos[0].textContent);
                    datos.reacciones = texto.replace(/[^0-9.]/g, '');
                    break;
                }
            }
            
            // Extraer contador de comentarios
            const selectoresComentarios = [
                'span.social-details-social-counts__comments-count',
                'button[aria-label*="comentarios"] span',
                'li.social-details-social-counts__comments'
            ];
            
            for (let selector of selectoresComentarios) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    let texto = limpiarTexto(elementos[0].textContent);
                    datos.comentarios = texto.replace(/[^0-9]/g, '');
                    break;
                }
            }
            
            // PARTE CRÍTICA: Extraer los comentarios
            // Intentar varios selectores para encontrar contenedores de comentarios
            const selectoresContenedorComentarios = [
                'div.comments-comments-list',
                'div.feed-shared-update-v2__comments-container',
                'div.comments-container',
                'div.update-components-comments',
                'article.comments-comment-item',
                'div.comments-comment-item'
            ];
            
            let encontradoComentarios = false;
            
            for (let selector of selectoresContenedorComentarios) {
                if (encontradoComentarios) break;
                
                const contenedores = document.querySelectorAll(selector);
                if (contenedores.length === 0) continue;
                
                // Ahora buscamos comentarios dentro de estos contenedores
                for (let contenedor of contenedores) {
                    // Buscar comentarios individuales de diferentes formas
                    const comentariosItems = contenedor.querySelectorAll(
                        'article.comments-comment-item, ' +
                        'div.comments-comment-item, ' + 
                        'div.comments-comment-item__main-content'
                    );
                    
                    if (comentariosItems.length > 0) {
                        encontradoComentarios = true;
                        
                        for (let item of comentariosItems) {
                            // Buscar autor del comentario
                            const autorElem = item.querySelector(
                                'span.comments-comment-item__author-name, ' +
                                'span.comments-post-meta__name, ' +
                                'a.comments-post-meta__actor-link span, ' +
                                'span.hoverable-link-text'
                            );
                            
                            // Buscar texto del comentario
                            const textoElem = item.querySelector(
                                'div.comments-comment-item-content-body, ' +
                                'div.feed-shared-text-view, ' +
                                'div.comments-comment-item__main-content, ' +
                                'span.break-words, ' +
                                'p, ' +
                                'div.feed-shared-text'
                            );
                            
                            if (autorElem && textoElem) {
                                const autor = limpiarTexto(autorElem.textContent);
                                const texto = limpiarTexto(textoElem.textContent);
                                if (autor && texto) {
                                    datos.texto_comentarios.push(autor + ': ' + texto);
                                }
                            } else if (textoElem) {
                                const texto = limpiarTexto(textoElem.textContent);
                                if (texto) {
                                    datos.texto_comentarios.push('Anónimo: ' + texto);
                                }
                            }
                        }
                    }
                }
            }
            
            // Si no se encuentran comentarios pero el contador dice que hay, actualizar el mensaje
            if (datos.texto_comentarios.length === 0 && parseInt(datos.comentarios) > 0) {
                console.log('No se pudieron extraer los comentarios, aunque el contador indica que hay: ' + datos.comentarios);
            }
            
            // Extraer compartidos
            const selectoresCompartidos = [
                'span.social-details-social-counts__shares-count',
                'button[aria-label*="compartidos"] span',
                'li.social-details-social-counts__shares'
            ];
            
            for (let selector of selectoresCompartidos) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    let texto = limpiarTexto(elementos[0].textContent);
                    datos.compartidos = texto.replace(/[^0-9]/g, '');
                    break;
                }
            }
            
            // Detectar si hay imagen
            const selectoresImagen = [
                'div.feed-shared-image',
                'div.update-components-image',
                'div.feed-shared-update-v2__content img',
                'div.feed-shared-image__container'
            ];
            
            for (let selector of selectoresImagen) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.tiene_imagen = 'Sí';
                    break;
                }
            }
            
            // Detectar si hay video
            const selectoresVideo = [
                'div.feed-shared-linkedin-video',
                'div.update-components-linkedin-video',
                'div.feed-shared-update-v2__content video',
                'div.feed-shared-video'
            ];
            
            for (let selector of selectoresVideo) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.tiene_video = 'Sí';
                    break;
                }
            }
            
            // Detectar si hay enlace externo
            const selectoresEnlace = [
                'a.feed-shared-article__meta-link',
                'a.update-components-article__meta-link',
                'a.feed-shared-article__link',
                'a.feed-shared-external-link'
            ];
            
            for (let selector of selectoresEnlace) {
                const elementos = document.querySelectorAll(selector);
                if (elementos.length > 0) {
                    datos.enlace_externo = elementos[0].href || 'Sí';
                    break;
                }
            }
            
            return datos;
            """
            
            # Ejecutar el script JavaScript
            resultado = self.driver.execute_script(js_script)
            print("Resultado de extracción JavaScript:", resultado)
            
            # Añadir ID y URL
            if resultado:
                resultado['id'] = 1
                resultado['url'] = self.driver.current_url
            
            return resultado
        
        except Exception as e:
            print(f"Error al extraer datos con JavaScript: {str(e)}")
            return {}
    
    def extraer_datos_tradicional(self):
        """Método tradicional de extracción con Selenium"""
        datos_publicacion = {
            'id': 1,
            'autor': "No disponible",
            'cargo_autor': "No disponible",
            'fecha': "No disponible",
            'texto': "No disponible",
            'reacciones': "0",
            'comentarios': "0",
            'texto_comentarios': [],
            'compartidos': "0",
            'url': self.driver.current_url,
            'tiene_imagen': "No",
            'tiene_video': "No",
            'enlace_externo': "No"
        }
        
        try:
            # Autor
            try:
                autor = self.driver.find_element(By.XPATH, "//span[contains(@class, 'feed-shared-actor__name') or contains(@class, 'update-components-actor__name')]").text
                datos_publicacion['autor'] = autor
            except:
                pass
            
            # Cargo
            try:
                cargo = self.driver.find_element(By.XPATH, "//span[contains(@class, 'feed-shared-actor__description') or contains(@class, 'update-components-actor__description')]").text
                datos_publicacion['cargo_autor'] = cargo
            except:
                pass
            
            # Fecha
            try:
                fecha = self.driver.find_element(By.XPATH, "//span[contains(@class, 'feed-shared-actor__sub-description') or contains(@class, 'update-components-actor__sub-description')]").text
                datos_publicacion['fecha'] = fecha
            except:
                pass
            
            # Texto
            try:
                texto = self.driver.find_element(By.XPATH, "//div[contains(@class, 'feed-shared-update-v2__description') or contains(@class, 'update-components-update-v2__commentary')]").text
                datos_publicacion['texto'] = texto
            except:
                pass
            
            # Reacciones
            try:
                reacciones = self.driver.find_element(By.XPATH, "//span[contains(@class, 'social-details-social-counts__reactions-count')]").text
                reacciones = re.sub(r'[^0-9]', '', reacciones)
                datos_publicacion['reacciones'] = reacciones
            except:
                pass
            
            # Comentarios
            try:
                comentarios = self.driver.find_element(By.XPATH, "//li[contains(@class, 'social-details-social-counts__comments')]").text
                comentarios = re.sub(r'[^0-9]', '', comentarios)
                datos_publicacion['comentarios'] = comentarios
            except:
                pass
            
            # Intento específico para extraer comentarios
            try:
                # Hacer scroll hasta la sección de comentarios
                comentarios_seccion = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'comments-comment-item')]")
                if comentarios_seccion:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comentarios_seccion[0])
                    self.espera_aleatoria(4, 6)
                    
                    # Intentar capturar los comentarios
                    comentarios_elementos = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'comments-comment-item')]")
                    for comentario in comentarios_elementos:
                        try:
                            autor = comentario.find_element(By.XPATH, ".//span[contains(@class, 'comments-comment-item__author-name')]").text
                            texto = comentario.find_element(By.XPATH, ".//div[contains(@class, 'comments-comment-item-content-body')]").text
                            datos_publicacion['texto_comentarios'].append(f"{autor}: {texto}")
                        except:
                            pass
            except:
                pass
            
            # Compartidos
            try:
                compartidos = self.driver.find_element(By.XPATH, "//li[contains(@class, 'social-details-social-counts__shares')]").text
                compartidos = re.sub(r'[^0-9]', '', compartidos)
                datos_publicacion['compartidos'] = compartidos
            except:
                pass
            
            # Tiene imagen
            try:
                tiene_imagen = self.driver.find_element(By.XPATH, "//div[contains(@class, 'feed-shared-image')]")
                datos_publicacion['tiene_imagen'] = "Sí"
            except:
                pass
            
            # Tiene video
            try:
                tiene_video = self.driver.find_element(By.XPATH, "//div[contains(@class, 'feed-shared-linkedin-video')]")
                datos_publicacion['tiene_video'] = "Sí"
            except:
                pass
            
            # Enlace externo
            try:
                enlace = self.driver.find_element(By.XPATH, "//a[contains(@class, 'feed-shared-article__meta-link')]").get_attribute('href')
                datos_publicacion['enlace_externo'] = enlace
            except:
                pass
                
            return datos_publicacion
            
        except Exception as e:
            print(f"Error en la extracción tradicional: {str(e)}")
            return datos_publicacion
    
    def guardar_como_csv(self, datos, nombre_archivo="publicacion_linkedin.csv"):
        """Guardar datos en CSV"""
        try:
            # Si datos['texto_comentarios'] es una lista, convertirla a cadena
            if isinstance(datos['texto_comentarios'], list):
                datos['texto_comentarios'] = '|||'.join(datos['texto_comentarios'])
            
            # Convertir a DataFrame y guardar
            df = pd.DataFrame([datos])
            df.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
            print(f"Datos guardados exitosamente en {nombre_archivo}")
            return True
        except Exception as e:
            print(f"Error al guardar CSV: {str(e)}")
            return False
    
    def cerrar_navegador(self):
        """Cerrar el navegador"""
        self.espera_aleatoria(3, 5)
        self.driver.quit()
        print("Navegador cerrado")

# Ejemplo de uso
if __name__ == "__main__":
    # Reemplazar con tus credenciales de LinkedIn
    EMAIL = "fredyperezm123@gmail.com"
    PASSWORD = "buenosdiasAlegria789"
    
    # URL de la publicación específica
    URL_PUBLICACION = "https://www.linkedin.com/posts/activity-7323389269622894594-GMEH/?utm_medium=ios_app&rcm=ACoAACcl2JIBPUpPP5QiW-rFCJe__ylEAzaDoMU&utm_source=social_share_send&utm_campaign=copy_link"
    
    # Crear una instancia del scraper
    scraper = LinkedInScraper(EMAIL, PASSWORD)
    
    # Iniciar sesión
    if scraper.login():
        # Extraer datos de la publicación con el nuevo enfoque
        datos_publicacion = scraper.extraer_publicacion(URL_PUBLICACION)
        
        # Guardar datos en CSV
        if datos_publicacion:
            scraper.guardar_como_csv(datos_publicacion, "publicacion_linkedin_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
        else:
            print("No se pudieron extraer datos")
    
    # Cerrar el navegador
    scraper.cerrar_navegador()