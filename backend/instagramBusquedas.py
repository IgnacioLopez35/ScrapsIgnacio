import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

# Add the project root to the Python path so Python can find the modules directory
sys.path.append(project_root)

# Now you can import from modules
from agents import agents
import time
import random
import csv
import traceback
import pandas as pd
from fake_useragent import UserAgent
from datetime import datetime
import undetected_chromedriver as uc
import re

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================

# Credenciales de Instagram *incrustadas* directamente
INSTA_USER = "ignacio.lopez@wivboost.com"
INSTA_PASS = "buenosdiasAlegria777"

# Cuenta a extraer - IMPORTANTE: cámbialo a la cuenta deseada
# Nueva configuración para búsquedas
# URLs directas a scrapear - AQUÍ ES DONDE PONES TUS ENLACES
TARGET_URLS = [
    "https://www.instagram.com/explore/search/keyword/?q=feria%20de%20sevilla",
    #"https://www.instagram.com/explore/tags/feriadeabril/",
    # "https://www.instagram.com/explore/locations/123456/sevilla/",  # Ejemplo de ubicación
    # "https://www.instagram.com/some_account/",  # También funciona con perfiles
    # Agrega aquí todos los enlaces que quieras scrapear
]

# Año mínimo a filtrar
YEAR_FILTER = 2025
MAX_POSTS = 47 # Número máximo de posts a extraer
NUM_SCROLLS = 10  # Aumentado para cargar más posts

# =========================================================================
# CLASE SCRAPER
# =========================================================================
class InstagramScraper:
    def __init__(self):
        self.driver = self._setup_driver()
        self.action = ActionChains(self.driver)
        self.debug_mode = True  # Activa el modo debug para más información




    def _identify_url_type(self, url):
        """
        Identifica el tipo de página de Instagram basándose en la URL
        """
        url_lower = url.lower()
        
        if "/explore/tags/" in url_lower:
            hashtag = url.split("/explore/tags/")[1].split("/")[0]
            return "hashtag", hashtag
        elif "/explore/locations/" in url_lower:
            location_info = url.split("/explore/locations/")[1].split("/")
            location_id = location_info[0] if location_info else "unknown"
            location_name = location_info[1] if len(location_info) > 1 else "unknown"
            return "location", f"{location_id}_{location_name}"
        elif "/explore/" in url_lower:
            return "explore", "general_explore"
        elif url_lower.count("/") >= 3:  # Posible perfil de usuario
            try:
                username = url.split("/")[3].split("?")[0]  # Obtener nombre de usuario
                return "profile", username
            except:
                return "unknown", "unknown"
        else:
            return "unknown", "unknown"

    def scrape_from_url(self, target_url):
        """
        Scraper principal que extrae posts directamente desde una URL dada
        """
        print(f"\n🔗 [INFO] Iniciando scraping desde URL: {target_url}")
        
        try:
            # 1. Identificar tipo de URL
            url_type, identifier = self._identify_url_type(target_url)
            print(f"[INFO] Tipo de URL identificado: {url_type} - {identifier}")
            
            # 2. Navegar directamente a la URL
            print(f"[INFO] Navegando a: {target_url}")
            self.driver.get(target_url)
            self._human_delay(3, 5)
            
            # 3. Verificar que la página cargó correctamente
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                print("[INFO] Página cargada correctamente.")
                
                # Mostrar información de la página
                page_title = self.driver.title
                current_url = self.driver.current_url
                print(f"[INFO] Título: {page_title}")
                print(f"[INFO] URL final: {current_url}")
                
            except TimeoutException:
                print("[ERROR] No se pudo cargar la página correctamente.")
                return []
            
            # 4. Verificar si hay contenido accesible
            if self._check_page_accessibility():
                print("[INFO] Página accesible, procediendo con extracción...")
            else:
                print("[WARNING] La página puede tener restricciones de acceso.")
                return []
            
            # 5. Realizar scrolls para cargar más contenido
            print("[INFO] Cargando más contenido...")
            self._scroll_n_times(NUM_SCROLLS)
            
            # Guardar captura para debugging
            safe_filename = self._create_safe_filename(target_url)
            screenshot_name = f"url_scraping_{safe_filename}.png"
            self.driver.save_screenshot(screenshot_name)
            print(f"[INFO] Captura guardada: {screenshot_name}")
            
            # 6. Extraer URLs de posts de la página
            post_urls = self._get_posts_from_current_page(MAX_POSTS)
            
            if not post_urls:
                print(f"[WARNING] No se encontraron posts en: {target_url}")
                # Guardar HTML para debugging
                html_filename = f"page_source_{safe_filename}.html"
                with open(html_filename, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                print(f"[INFO] HTML guardado para debugging: {html_filename}")
                return []
            
            print(f"[INFO] Encontrados {len(post_urls)} posts para procesar")
            
            # 7. Extraer datos de cada post
            posts_data = []
            
            for i, post_url in enumerate(post_urls, 1):
                try:
                    print(f"\n📸 [INFO] Procesando post {i}/{len(post_urls)}: {post_url}")
                    
                    # Visitar el post individual
                    self.driver.get(post_url)
                    self._human_delay(1, 2)
                    
                    # Extraer datos del post
                    post_data = self._extract_post_data_with_source(target_url, url_type, identifier)
                    
                    if post_data:
                        posts_data.append(post_data)
                        print(f"✅ Post {i} extraído con éxito.")
                        print(f"   Usuario: {post_data.get('usuario_post', 'N/A')}")
                        print(f"   Likes: {post_data.get('likes', 'N/A')}")
                    else:
                        print(f"⚠️ [WARNING] No se pudo extraer datos del post {i}.")
                    
                    # Pausa entre posts para evitar rate limits
                    if i < len(post_urls):
                        pause_time = random.uniform(0.8, 2.0)
                        time.sleep(pause_time)
                        
                except Exception as e:
                    print(f"❌ [ERROR] Error procesando post {i}: {e}")
                    continue
            
            print(f"\n✅ [INFO] Scraping completado: {len(posts_data)} posts extraídos de {target_url}")
            return posts_data
            
        except Exception as e:
            print(f"[ERROR] Error en scrape_from_url: {e}")
            traceback.print_exc()
            return []

    def _check_page_accessibility(self):
        """
        Verifica si la página es accesible y no está bloqueada o privada
        """
        try:
            # Buscar indicadores de contenido restringido
            restricted_indicators = [
                "This Account is Private",
                "Esta cuenta es privada",
                "Content Unavailable",
                "Contenido no disponible",
                "Sorry, this page isn't available",
                "Esta página no está disponible"
            ]
            
            page_text = self.driver.page_source.lower()
            
            for indicator in restricted_indicators:
                if indicator.lower() in page_text:
                    print(f"[WARNING] Contenido restringido detectado: {indicator}")
                    return False
            
            # Verificar si hay artículos/posts visibles
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            if len(articles) > 0:
                print(f"[INFO] Se detectaron {len(articles)} artículos en la página")
                return True
            
            # Verificar si hay imágenes de posts (fallback)
            post_images = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'instagram')]")
            if len(post_images) > 3:  # Más de 3 imágenes sugiere contenido
                print(f"[INFO] Se detectaron {len(post_images)} imágenes de posts")
                return True
            
            print("[WARNING] No se detectó contenido accesible en la página")
            return False
            
        except Exception as e:
            print(f"[WARNING] Error verificando accesibilidad: {e}")
            return True  # Asumir accesible si hay error

    def _get_posts_from_current_page(self, max_posts=MAX_POSTS):
        """
        Extrae URLs de posts de la página actual (sea hashtag, ubicación, perfil, etc.)
        Versión mejorada que funciona con cualquier tipo de página de Instagram
        """
        post_urls = []
        
        print("[INFO] Extrayendo URLs de posts de la página actual...")
        
        # Método 1: Buscar enlaces directos a posts/reels
        print("[INFO] Método 1: Enlaces directos...")
        try:
            direct_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            
            for link in direct_links:
                try:
                    href = link.get_attribute("href")
                    if href and ("instagram.com" in href or href.startswith("/")):
                        # Convertir enlaces relativos a absolutos
                        if href.startswith("/"):
                            href = f"https://www.instagram.com{href}"
                        
                        if href not in post_urls:
                            post_urls.append(href)
                            if self.debug_mode and len(post_urls) <= 5:
                                print(f"[DEBUG] Encontrado: {href}")
                except:
                    continue
                    
            print(f"[INFO] Encontrados {len(post_urls)} enlaces directos")
        except Exception as e:
            print(f"[WARNING] Error en método 1: {e}")
        
        # Método 2: Buscar en artículos si no hay suficientes enlaces
        if len(post_urls) < max_posts:
            print("[INFO] Método 2: Búsqueda en artículos...")
            try:
                articles = self.driver.find_elements(By.TAG_NAME, "article")
                
                for article in articles:
                    try:
                        article_links = article.find_elements(By.TAG_NAME, "a")
                        for link in article_links:
                            href = link.get_attribute("href")
                            if href and (("/p/" in href) or ("/reel/" in href)):
                                if href.startswith("/"):
                                    href = f"https://www.instagram.com{href}"
                                
                                if href not in post_urls:
                                    post_urls.append(href)
                                    
                    except:
                        continue
                        
                print(f"[INFO] Total después de artículos: {len(post_urls)}")
            except Exception as e:
                print(f"[WARNING] Error en método 2: {e}")
        
        # Método 3: Análisis de HTML como último recurso
        if len(post_urls) < max_posts:
            print("[INFO] Método 3: Análisis de HTML...")
            try:
                html = self.driver.page_source
                
                # Patrones para encontrar enlaces a posts
                patterns = [
                    r'href="(https://www\.instagram\.com/[^/]+/(?:p|reel)/[^"]+)"',
                    r'href="(/[^/]+/(?:p|reel)/[^"]+)"',
                    r'"permalink":"([^"]*(?:/p/|/reel/)[^"]*)"'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    for match in matches:
                        href = match
                        if href.startswith("/"):
                            href = f"https://www.instagram.com{href}"
                        
                        # Limpiar caracteres de escape si es necesario
                        href = href.replace("\\", "")
                        
                        if href not in post_urls and ("instagram.com" in href):
                            post_urls.append(href)
                            
                print(f"[INFO] Total después de HTML: {len(post_urls)}")
            except Exception as e:
                print(f"[WARNING] Error en método 3: {e}")
        
        # Eliminar duplicados y limitar cantidad
        unique_urls = list(dict.fromkeys(post_urls))  # Mantiene orden, elimina duplicados
        limited_urls = unique_urls[:max_posts]
        
        print(f"[INFO] URLs finales: {len(limited_urls)} (de {len(unique_urls)} únicos encontrados)")
        
        return limited_urls

    def _extract_post_data_with_source(self, source_url, url_type, identifier):
        """
        Extrae datos del post incluyendo información sobre la fuente (URL original)
        """
        try:
            # Usar el método base existente
            post_data = self._extract_post_data()
            
            if not post_data:
                return None
            
            # Agregar información de la fuente
            post_data["url_fuente"] = source_url
            post_data["tipo_fuente"] = url_type
            post_data["identificador_fuente"] = identifier
            post_data["metodo_extraccion"] = "url_directa"
            
            # Extraer usuario del post
            try:
                if post_data.get("author_comment") and isinstance(post_data["author_comment"], dict):
                    post_data["usuario_post"] = post_data["author_comment"].get("author", "desconocido")
                else:
                    post_data["usuario_post"] = "desconocido"
            except:
                post_data["usuario_post"] = "desconocido"
            
            return post_data
            
        except Exception as e:
            print(f"[ERROR] Error extrayendo datos con fuente: {e}")
            return None

    def _create_safe_filename(self, url):
        """
        Crea un nombre de archivo seguro a partir de una URL
        """
        # Remover protocolo y caracteres problemáticos
        safe_name = url.replace("https://", "").replace("http://", "")
        safe_name = re.sub(r'[^\w\-_.]', '_', safe_name)
        # Limitar longitud
        return safe_name[:50]

    def save_url_results_to_csv(self, data, source_url):
        """
        Guarda los datos extraídos de una URL específica
        """
        if not data:
            print("⚠️ No hay datos para guardar.")
            return None

        try:
            # Procesar datos para CSV
            processed_data = []
            for post in data:
                post_data = {
                    "url_fuente": post.get("url_fuente", ""),
                    "tipo_fuente": post.get("tipo_fuente", ""),
                    "identificador_fuente": post.get("identificador_fuente", ""),
                    "usuario_post": post.get("usuario_post", ""),
                    "url_post": post.get("url_post", ""),
                    "likes": post.get("likes", ""),
                    "fecha_post": post.get("fecha_post", ""),
                    "author": post.get("author_comment", {}).get("author", "") if post.get("author_comment") else "",
                    "comment": post.get("author_comment", {}).get("comment", "") if post.get("author_comment") else "",
                    "hashtags": ", ".join(post.get("author_comment", {}).get("hashtags", [])) if post.get("author_comment") else "",
                    "mentions": ", ".join(post.get("author_comment", {}).get("mentions", [])) if post.get("author_comment") else "",
                }
                
                # Añadir comentarios
                comentarios = post.get("comentarios", {})
                for i, (user, comment_data) in enumerate(comentarios.items(), 1):
                    if i > 5:  # Limitar comentarios
                        break
                    post_data[f"comentario_{i}_usuario"] = user
                    if isinstance(comment_data, tuple):
                        post_data[f"comentario_{i}_texto"] = comment_data[0]
                        if len(comment_data) > 1:
                            post_data[f"comentario_{i}_fecha"] = comment_data[1]
                        if len(comment_data) > 2:
                            post_data[f"comentario_{i}_likes"] = comment_data[2]
                    else:
                        post_data[f"comentario_{i}_texto"] = str(comment_data)
                
                processed_data.append(post_data)

            # Crear nombre de archivo
            safe_url_name = self._create_safe_filename(source_url)
            date_str = datetime.now().strftime("%d_%m_%Y")
            filename = f"instagram_url_{safe_url_name}_{date_str}.csv"

            # Guardar CSV
            df = pd.DataFrame(processed_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"✅ [INFO] {len(data)} posts guardados en: {filename}")
            
            # Guardar JSON también
            import json
            json_filename = f"instagram_url_{safe_url_name}_{date_str}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ [INFO] Copia JSON guardada: {json_filename}")
            
            return filename
            
        except Exception as e:
            print(f"[ERROR] Error guardando resultados: {e}")
            return None



    

    


    def _navigate_to_search(self, search_query, search_type='general'):
        """
        Navega a la página de búsqueda de Instagram según el tipo especificado
        """
        print(f"[INFO] Navegando a búsqueda: '{search_query}' (tipo: {search_type})")
        
        try:
            if search_type == 'hashtag' or search_query.startswith('#'):
                # Búsqueda por hashtag
                hashtag = search_query.replace('#', '').strip()
                search_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                print(f"[INFO] Búsqueda de hashtag: {search_url}")
                
            elif search_type == 'location':
                # Búsqueda por ubicación (requiere ID de ubicación, más complejo)
                print("[WARNING] Búsqueda por ubicación no implementada completamente")
                search_url = f"https://www.instagram.com/explore/locations/"
                
            elif search_type == 'people':
                # Búsqueda de personas/cuentas
                search_url = f"https://www.instagram.com/explore/search/keyword/?q={search_query.replace(' ', '%20')}"
                print(f"[INFO] Búsqueda de personas: {search_url}")
                
            else:
                # Búsqueda general usando la función de explorar
                # Instagram no tiene una URL directa para búsquedas generales, 
                # así que usamos la página de explorar y luego buscamos
                search_url = "https://www.instagram.com/explore/"
                print(f"[INFO] Búsqueda general, iremos a explorar y buscaremos: '{search_query}'")
            
            self.driver.get(search_url)
            self._human_delay(3, 5)
            
            # Si es búsqueda general, usar la barra de búsqueda
            if search_type == 'general':
                try:
                    print("[INFO] Buscando barra de búsqueda...")
                    
                    # Múltiples selectores para la barra de búsqueda
                    search_selectors = [
                        "//input[@placeholder='Search']",
                        "//input[@placeholder='Buscar']", 
                        "//input[@aria-label='Search input']",
                        "//input[contains(@placeholder, 'earch')]",
                        "//div[@role='button'][contains(., 'Search')]",
                        "//span[contains(., 'Search')]//ancestor::div[@role='button']"
                    ]
                    
                    search_input = None
                    for selector in search_selectors:
                        try:
                            search_input = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print(f"[INFO] Encontrada barra de búsqueda con selector: {selector}")
                            break
                        except:
                            continue
                    
                    if search_input:
                        print(f"[INFO] Escribiendo término de búsqueda: '{search_query}'")
                        search_input.click()
                        self._human_delay(0.5, 1)
                        search_input.clear()
                        search_input.send_keys(search_query)
                        self._human_delay(1, 2)
                        
                        # Presionar Enter o buscar botón de búsqueda
                        search_input.send_keys(Keys.RETURN)
                        self._human_delay(2, 4)
                        
                        # Esperar a que carguen los resultados
                        print("[INFO] Esperando resultados de búsqueda...")
                        time.sleep(3)
                        
                    else:
                        print("[WARNING] No se encontró barra de búsqueda, continuando con explorar...")
                        
                except Exception as e:
                    print(f"[WARNING] Error usando barra de búsqueda: {e}")
            
            # Verificar que la página cargó correctamente
            current_url = self.driver.current_url
            print(f"[INFO] URL actual después de navegación: {current_url}")
            
            if "instagram.com" in current_url:
                print(f"[SUCCESS] Navegación a búsqueda exitosa")
                return True
            else:
                print(f"[ERROR] Error navegando a búsqueda")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error navegando a búsqueda: {e}")
            return False

    def scrape_search_results(self, search_query, search_type='general'):
        """
        Extrae posts de los resultados de búsqueda de Instagram
        """
        print(f"\n🔍 [INFO] Iniciando extracción de búsqueda: '{search_query}'")
        
        try:
            # 1. Navegar a la búsqueda
            if not self._navigate_to_search(search_query, search_type):
                print(f"[ERROR] No se pudo navegar a la búsqueda: '{search_query}'")
                return []
            
            # 2. Esperar a que cargue el contenido
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
                print("[INFO] Contenido de búsqueda cargado.")
            except TimeoutException:
                print("[WARNING] No se detectaron artículos inmediatamente, continuando...")
            
            # 3. Realizar scrolls para cargar más contenido
            print("[INFO] Cargando más contenido con scrolls...")
            self._scroll_n_times(NUM_SCROLLS)
            
            # Guardar captura después de scrolls
            self.driver.save_screenshot(f"search_results_{search_query.replace(' ', '_')}.png")
            print(f"[INFO] Captura de resultados guardada")
            
            # 4. Obtener URLs de posts de los resultados de búsqueda
            post_urls = self._get_search_post_urls(search_query, MAX_POSTS)
            
            if not post_urls:
                print(f"[WARNING] No se encontraron posts para la búsqueda: '{search_query}'")
                return []
            
            # 5. Extraer datos de cada post
            posts_data = []
            
            for i, post_url in enumerate(post_urls, 1):
                try:
                    print(f"\n📸 [INFO] Procesando post {i}/{len(post_urls)}: {post_url}")
                    
                    # Visitar el post
                    self.driver.get(post_url)
                    self._human_delay(1, 2)
                    
                    # Extraer datos del post
                    post_data = self._extract_post_data_for_search(search_query, search_type)
                    
                    if post_data:
                        posts_data.append(post_data)
                        print(f"✅ Post {i} extraído con éxito.")
                    else:
                        print(f"⚠️ [WARNING] No se pudo extraer datos del post {i}.")
                    
                    # Pausa entre posts
                    if i < len(post_urls):
                        pause_time = random.uniform(0.8, 1.8)
                        time.sleep(pause_time)
                        
                except Exception as e:
                    print(f"❌ [ERROR] Error procesando post {i}: {e}")
                    continue
            
            print(f"\n✅ [INFO] Extracción de búsqueda completada: {len(posts_data)} posts obtenidos para '{search_query}'")
            return posts_data
            
        except Exception as e:
            print(f"[ERROR] Error en scrape_search_results: {e}")
            traceback.print_exc()
            return []

    def _get_search_post_urls(self, search_query, max_urls=MAX_POSTS):
        """
        Método para encontrar URLs de posts en resultados de búsqueda
        Adaptado para funcionar con páginas de búsqueda en lugar de perfiles
        """
        post_urls = []
        
        print("[INFO] Buscando enlaces a posts en resultados de búsqueda...")
        
        # Método 1: Buscar enlaces directos en la página de búsqueda
        print("[INFO] Método 1: Buscando enlaces directos en resultados...")
        direct_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        
        for link in direct_links:
            try:
                href = link.get_attribute("href")
                if href and (("/p/" in href) or ("/reel/" in href)):
                    # En búsquedas, no filtramos por usuario específico
                    if "instagram.com" in href and href not in post_urls:
                        post_urls.append(href)
                        if self.debug_mode:
                            print(f"[DEBUG] Encontrado enlace en búsqueda: {href}")
            except Exception as e:
                if self.debug_mode:
                    print(f"[DEBUG] Error al procesar enlace: {e}")
                continue
        
        print(f"[INFO] Encontrados {len(post_urls)} enlaces directos")
        
        # Método 2: Buscar en artículos si no tenemos suficientes
        if len(post_urls) < max_urls:
            print("[INFO] Método 2: Buscando en artículos...")
            
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            
            for article in articles:
                try:
                    article_links = article.find_elements(By.TAG_NAME, "a")
                    for link in article_links:
                        href = link.get_attribute("href")
                        if href and (("/p/" in href) or ("/reel/" in href)):
                            if "instagram.com" in href and href not in post_urls:
                                post_urls.append(href)
                                if self.debug_mode:
                                    print(f"[DEBUG] Encontrado enlace en artículo: {href}")
                except Exception as e:
                    if self.debug_mode:
                        print(f"[DEBUG] Error procesando artículo: {e}")
                    continue
        
        # Método 3: Analizar HTML completo si aún necesitamos más
        if len(post_urls) < max_urls:
            print("[INFO] Método 3: Analizando HTML completo...")
            
            html = self.driver.page_source
            
            # Buscar todos los enlaces a posts/reels
            pattern1 = r'href="(https?://(?:www\.)?instagram\.com/[^/]+/(?:p|reel)/[^"]+)"'
            pattern2 = r'href="(/[^/]+/(?:p|reel)/[^"]+)"'
            
            links1 = re.findall(pattern1, html, re.IGNORECASE)
            links2 = re.findall(pattern2, html, re.IGNORECASE)
            
            # Añadir enlaces encontrados
            for link in links1:
                if link not in post_urls:
                    post_urls.append(link)
                    if self.debug_mode:
                        print(f"[DEBUG] Encontrado en HTML (absoluto): {link}")
            
            for link in links2:
                full_link = f"https://www.instagram.com{link}"
                if full_link not in post_urls:
                    post_urls.append(full_link)
                    if self.debug_mode:
                        print(f"[DEBUG] Encontrado en HTML (relativo): {full_link}")
        
        # Eliminar duplicados y limitar
        unique_post_urls = list(dict.fromkeys(post_urls))  # Mantiene orden y elimina duplicados
        
        print(f"[INFO] Total de URLs únicos encontrados: {len(unique_post_urls)}")
        
        return unique_post_urls[:max_urls]

    def _extract_post_data_for_search(self, search_query, search_type):
        """
        Extrae datos del post adaptado para búsquedas
        Similar a _extract_post_data pero incluye información de la búsqueda
        """
        try:
            # Usar el método base existente
            post_data = self._extract_post_data()
            
            if not post_data:
                return None
            
            # Agregar información específica de la búsqueda
            post_data["termino_busqueda"] = search_query
            post_data["tipo_busqueda"] = search_type
            post_data["tipo_extraccion"] = "busqueda"
            
            # Extraer información del usuario del post (ya que ahora puede ser cualquier usuario)
            try:
                # El usuario ya se extrae en _author_comment, pero asegurémonos de tenerlo
                if post_data.get("author_comment") and isinstance(post_data["author_comment"], dict):
                    post_data["usuario_post"] = post_data["author_comment"].get("author", "desconocido")
                else:
                    post_data["usuario_post"] = "desconocido"
            except:
                post_data["usuario_post"] = "desconocido"
            
            return post_data
            
        except Exception as e:
            print(f"[ERROR] Error extrayendo datos de post de búsqueda: {e}")
            return None

    def save_search_to_csv(self, data, search_query, search_type):
        """
        Guarda los datos de búsqueda en CSV con formato específico
        """
        if not data:
            print("⚠️ No hay datos de búsqueda para guardar.")
            return

        try:
            # Procesar datos para CSV
            processed_data = []
            for post in data:
                post_data = {
                    "termino_busqueda": post.get("termino_busqueda", ""),
                    "tipo_busqueda": post.get("tipo_busqueda", ""),
                    "usuario_post": post.get("usuario_post", ""),
                    "url_post": post.get("url_post", ""),
                    "likes": post.get("likes", ""),
                    "fecha_post": post.get("fecha_post", ""),
                    "author": post.get("author_comment", {}).get("author", "") if post.get("author_comment") else "",
                    "comment": post.get("author_comment", {}).get("comment", "") if post.get("author_comment") else "",
                    "hashtags": ", ".join(post.get("author_comment", {}).get("hashtags", [])) if post.get("author_comment") else "",
                    "mentions": ", ".join(post.get("author_comment", {}).get("mentions", [])) if post.get("author_comment") else "",
                }
                
                # Añadir comentarios
                comentarios = post.get("comentarios", {})
                for i, (user, comment_data) in enumerate(comentarios.items(), 1):
                    if i > 5:  # Limitar a 5 comentarios
                        break
                    post_data[f"comentario_{i}_usuario"] = user
                    if isinstance(comment_data, tuple):
                        post_data[f"comentario_{i}_texto"] = comment_data[0]
                        if len(comment_data) > 1:
                            post_data[f"comentario_{i}_fecha"] = comment_data[1]
                        if len(comment_data) > 2:
                            post_data[f"comentario_{i}_likes"] = comment_data[2]
                    else:
                        post_data[f"comentario_{i}_texto"] = str(comment_data)
                
                processed_data.append(post_data)

            # Crear DataFrame y guardar
            df = pd.DataFrame(processed_data)
            
            # Crear nombre de archivo seguro
            safe_query = re.sub(r'[^\w\s-]', '', search_query).strip()
            safe_query = re.sub(r'[-\s]+', '_', safe_query)[:30]
            
            date_str = datetime.now().strftime("%d_%m_%Y")
            filename = f"instagram_search_{safe_query}_{search_type}_{date_str}.csv"

            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"✅ [INFO] Se guardaron {len(data)} posts de búsqueda en {filename}")
            
            # También guardar JSON
            import json
            json_filename = f"instagram_search_{safe_query}_{search_type}_{date_str}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"✅ [INFO] Copia en JSON guardada: {json_filename}")
            
            return filename
            
        except Exception as e:
            print(f"[ERROR] Error guardando datos de búsqueda: {e}")
            return None




    def _setup_driver(self):
        """
        Configura Selenium con el proxy residencial de Bright Data.
        """
        PROXY_HOST = "gate.smartproxy.com"
        PROXY_PORT = "1005"
        PROXY_USER = "sp03mahcda"
        PROXY_PASS = "X3s_awrkk90gNbs0YX"

        proxy_options = {
            "proxy": {
                "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
                "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
                "no_proxy": "localhost,127.0.0.1",
            }
        }
        
        # Configuración del navegador Chrome
        options = uc.ChromeOptions()
        
        # 🔒 Evita que los sitios detecten Selenium
        options.add_argument("--disable-blink-features=AutomationControlled")

        # ⚡ Optimiza el rendimiento en servidores sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 🖥️ Simula navegación real en una ventana maximizada
        options.add_argument("--start-maximized")
        
        # NO USAR HEADLESS MODE - Causa problemas
        # options.add_argument("--headless=new")

        # 🔕 Evita notificaciones emergentes y bloqueos de pop-ups
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")

        # 🔄 Cambia dinámicamente el User-Agent para evitar detección
        options.add_argument(f"--user-agent={self._random_user_agent()}")

        # 🔍 Evita filtración de IP real cuando se usan proxies
        options.add_argument("--disable-webrtc")
        
        # 🚀 Inicializa el navegador sin subprocess
        driver = uc.Chrome(options=options)

        # Reducido el tiempo de espera para mayor velocidad
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        return driver

    def _random_user_agent(self):
        """
        Devuelve un User-Agent aleatorio para evitar detección.
        """
        return random.choice(agents)
        
    def _human_delay(self, min_s=0.5, max_s=1.5):
        """
        Pausa aleatoria entre acciones para simular comportamiento humano.
        Reducido para mayor velocidad.
        """
        base = random.uniform(min_s, max_s)
        gauss_factor = random.gauss(0, 0.2)
        total = max(0, base + gauss_factor)
        time.sleep(total)

    def login(self):
        """
        Inicia sesión en Instagram con las credenciales.
        """
        print("[INFO] Iniciando proceso de login...")
        self.driver.get("https://www.instagram.com/")
        self._human_delay(3, 5)  # Reducido para mayor velocidad

        try:
            # Aceptar cookies (múltiples intentos con diferentes textos)
            cookie_buttons = [
                "//button[contains(., 'Permitir')]", 
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Allow')]",
                "//button[contains(., 'Aceptar')]"
            ]
            
            for btn_xpath in cookie_buttons:
                try:
                    allow_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, btn_xpath))
                    )
                    allow_btn.click()
                    self._human_delay(0.5, 1)
                    print("[INFO] Cookies aceptadas.")
                    break
                except:
                    continue
                    
        except:
            print("[INFO] No se detectó diálogo de cookies o ya fueron aceptadas.")

        try:
            # Esperar a que los campos de login estén disponibles
            print("[INFO] Buscando campos de login...")
            username_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_input = self.driver.find_element(By.NAME, "password")

            print("[INFO] Campos de login encontrados, ingresando credenciales...")
            # Escribir usuario y contraseña más rápido
            username_input.send_keys(INSTA_USER)
            self._human_delay(0.2, 0.5)
            password_input.send_keys(INSTA_PASS)

            # Click en "Iniciar sesión"
            print("[INFO] Buscando botón de login...")
            login_btn = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            print("[INFO] Haciendo clic en botón de login...")
            login_btn.click()

            # Esperar más tiempo para el login
            print("[INFO] Esperando el proceso de login...")
            self._human_delay(5, 8)  # Reducido para mayor velocidad
            
            # Verificar si hay diálogos adicionales post-login y manejarlos
            try:
                # Botón "Not Now" para guardar información
                print("[INFO] Buscando diálogos post-login...")
                not_now_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                print("[INFO] Encontrado diálogo 'Not Now', haciendo clic...")
                not_now_btn.click()
                self._human_delay(1, 2)
            except:
                print("[INFO] No se encontró diálogo 'Not Now' para guardar info.")
                
            try:
                # Botón "Not Now" para notificaciones
                not_now_notif = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                print("[INFO] Encontrado diálogo de notificaciones, haciendo clic en 'Not Now'...")
                not_now_notif.click()
                self._human_delay(1, 2)
            except:
                print("[INFO] No se encontró diálogo de notificaciones.")

            # Verificar si el login fue exitoso
            if "login" in self.driver.current_url:
                print("[ERROR] La URL sigue conteniendo 'login', posible error de autenticación.")
                raise Exception("Error de autenticación (quizás 2FA o captcha).")
            else:
                print("[INFO] Login completado correctamente.")
        except Exception as e:
            print("[ERROR] en login:", e)
            traceback.print_exc()
            raise

    def _scroll_n_times(self, times=12, pause_every=3):
        """
        Realiza scroll hacia abajo de forma rápida para cargar más posts.
        """
        if times <= 0:
            print("🔕 [INFO] Skipping scrolling as times is set to 0.")
            return 
        
        # Realizar scrolls rápidos
        for i in range(1, times + 1):
            print(f"🔽 [INFO] Scroll {i}/{times}...")
            # Usar JavaScript para scrollear más rápido
            self.driver.execute_script("window.scrollBy(0, 1000);")
            self._human_delay(0.8, 1.8)  # Ligeramente más largo para asegurar carga
            
            # Cada pocos scrolls, pausa más larga para carga
            if i % pause_every == 0:
                print("[INFO] Pausa para carga de contenido...")
                time.sleep(3)  # Pausa para carga de contenido
                
                # Verificar si se han cargado posts
                if self.debug_mode:
                    # Buscar elementos que parecen posts
                    articles = self.driver.find_elements(By.TAG_NAME, "article")
                    print(f"[DEBUG] Artículos en la página: {len(articles)}")
                    
                    # Intentar encontrar contenedores de imágenes/media
                    media_containers = self.driver.find_elements(By.XPATH, "//div[contains(@style, 'padding-bottom')]")
                    print(f"[DEBUG] Posibles contenedores de media: {len(media_containers)}")

    def _get_post_urls_robust(self, username, max_urls=MAX_POSTS):
        """
        Método mejorado y robusto para encontrar URLs de posts de Instagram.
        Utiliza múltiples estrategias para detectar enlaces a posts.
        """
        post_urls = []
        
        print("[INFO] Buscando enlaces a posts con múltiples métodos...")
        
        # Método 1: Buscar directamente enlaces que contengan /p/ o /reel/
        print("[INFO] Método 1: Buscando enlaces directos a posts/reels...")
        direct_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        
        for link in direct_links:
            try:
                href = link.get_attribute("href")
                if href and (("/p/" in href) or ("/reel/" in href)):
                    # Verificamos si pertenece a la cuenta que estamos scrapeando
                    if f"instagram.com/{username.lower()}/" in href.lower() or f"/{username.lower()}/" in href.lower():
                        post_urls.append(href)
                        if self.debug_mode:
                            print(f"[DEBUG] Encontrado enlace directo: {href}")
            except Exception as e:
                if self.debug_mode:
                    print(f"[DEBUG] Error al procesar enlace: {e}")
                continue
                
        print(f"[INFO] Encontrados {len(post_urls)} enlaces directos a posts/reels")
        
        # Si no encontramos suficientes enlaces con el método 1, probamos el método 2
        if len(post_urls) < max_urls:
            print("[INFO] Método 2: Buscando enlaces usando artículos...")
            
            # Buscar todos los artículos (suelen contener posts)
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            
            for article in articles:
                try:
                    # Buscar enlaces dentro de artículos
                    article_links = article.find_elements(By.TAG_NAME, "a")
                    for link in article_links:
                        href = link.get_attribute("href")
                        if href and (("/p/" in href) or ("/reel/" in href)):
                            if f"instagram.com/{username.lower()}/" in href.lower() or f"/{username.lower()}/" in href.lower():
                                if href not in post_urls:  # Evitar duplicados
                                    post_urls.append(href)
                                    if self.debug_mode:
                                        print(f"[DEBUG] Encontrado enlace en artículo: {href}")
                except Exception as e:
                    if self.debug_mode:
                        print(f"[DEBUG] Error al procesar artículo: {e}")
                    continue
        
        # Método 3: Analizar el HTML completo de la página si aún necesitamos más enlaces
        if len(post_urls) < max_urls:
            print("[INFO] Método 3: Analizando HTML completo...")
            
            # Obtener el HTML completo de la página
            html = self.driver.page_source
            
            # Buscar todos los enlaces a posts/reels usando expresiones regulares
            pattern1 = f'href="(https?://(?:www\\.)?instagram\\.com/{username}/(?:p|reel)/[^"]+)"'
            pattern2 = f'href="(/{username}/(?:p|reel)/[^"]+)"'
            
            links1 = re.findall(pattern1, html, re.IGNORECASE)
            links2 = re.findall(pattern2, html, re.IGNORECASE)
            
            # Convertir enlaces relativos a absolutos
            for link in links2:
                full_link = f"https://www.instagram.com{link}"
                if full_link not in post_urls:
                    post_urls.append(full_link)
                    if self.debug_mode:
                        print(f"[DEBUG] Encontrado enlace en HTML (relativo): {full_link}")
            
            # Añadir enlaces absolutos encontrados
            for link in links1:
                if link not in post_urls:
                    post_urls.append(link)
                    if self.debug_mode:
                        print(f"[DEBUG] Encontrado enlace en HTML (absoluto): {link}")
        
        # Método 4: Si todo lo anterior falla, como último recurso, buscar divs que parecen contener posts
        if len(post_urls) < max_urls:
            print("[INFO] Método 4: Buscando divs de posts...")
            
            # En Instagram, los posts suelen tener un contenedor con padding-bottom para mantener la relación de aspecto
            divs = self.driver.find_elements(By.XPATH, "//div[contains(@style, 'padding-bottom')]")
            
            for div in divs:
                try:
                    # Intentar encontrar el enlace más cercano
                    parent = div
                    for _ in range(5):  # Buscar hasta 5 niveles arriba
                        if parent:
                            parent = parent.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute("href")
                                if href and (("/p/" in href) or ("/reel/" in href)):
                                    if f"instagram.com/{username.lower()}/" in href.lower() or f"/{username.lower()}/" in href.lower():
                                        if href not in post_urls:
                                            post_urls.append(href)
                                            if self.debug_mode:
                                                print(f"[DEBUG] Encontrado enlace en div: {href}")
                                            break
                except Exception as e:
                    if self.debug_mode:
                        print(f"[DEBUG] Error buscando enlaces en divs: {e}")
                    continue
        
        # Eliminar duplicados manteniendo el orden
        unique_post_urls = []
        seen = set()
        for url in post_urls:
            if url not in seen:
                seen.add(url)
                unique_post_urls.append(url)
        
        print(f"[INFO] Encontrados {len(unique_post_urls)} URLs únicos de posts para {username}")
        
        # Limitar al máximo número de posts
        return unique_post_urls[:max_urls]

    def scrape_profile(self, username):
        """Extrae posts del perfil de Instagram especificado utilizando navegación directa."""
        print(f"\n🔍 [INFO] Abriendo perfil de {username}...")
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(2, 4)  # Reducido para mayor velocidad
        
        # Verificar que la página cargó correctamente
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("[INFO] Página de perfil cargada.")
            
            # Mostrar título y URL para diagnóstico
            page_title = self.driver.title
            page_url = self.driver.current_url
            print(f"[INFO] Título de la página: {page_title}")
            print(f"[INFO] URL actual: {page_url}")
            
            # Guardar captura de la página inicial
            self.driver.save_screenshot("profile_page.png")
            print("[INFO] Captura del perfil guardada como profile_page.png")
            
        except TimeoutException:
            print("[ERROR] No se pudo cargar el perfil correctamente.")
            return []
            
        # Verificar si la cuenta es privada
        try:
            private_text = self.driver.find_element(By.XPATH, "//*[contains(text(), 'This Account is Private') or contains(text(), 'Esta cuenta es privada')]")
            print(f"⚠️ [WARNING] La cuenta {username} es privada. No se pueden extraer posts.")
            return []
        except NoSuchElementException:
            print(f"[INFO] La cuenta {username} parece ser pública.")
            
        # Realizar scrolls rápidos para cargar más posts
        self._scroll_n_times(NUM_SCROLLS)
        
        # Guardar captura después de scrolls
        self.driver.save_screenshot("after_scrolls.png")
        print("[INFO] Captura después de scrolls guardada como after_scrolls.png")

        # Usar el método robusto para obtener URLs de posts
        post_urls = self._get_post_urls_robust(username, MAX_POSTS)
        
        if not post_urls:
            print(f"⚠️ [WARNING] No se encontraron URLs de posts para {username}. Saliendo...")
            # Guardar el HTML para diagnóstico
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("[INFO] HTML de la página guardado en page_source.html para diagnóstico")
            return []
            
        # Ahora tenemos una lista de URLs de posts, procedemos a visitarlos uno por uno
        posts_data = []
        
        for i, post_url in enumerate(post_urls, 1):
            try:
                print(f"\n📸 [INFO] Procesando post {i}/{len(post_urls)}: {post_url}")
                
                # Visitar directamente la URL del post
                self.driver.get(post_url)
                self._human_delay(1, 2)  # Reducido para mayor velocidad
                
                # Extraer datos del post
                post_data = self._extract_post_data()
                
                if post_data:
                    posts_data.append(post_data)
                    print(f"✅ Post {i} extraído con éxito.")
                else:
                    print(f"⚠️ [WARNING] No se pudo extraer datos del post {i}.")
                    
                # Breve pausa entre posts para evitar límites de rate
                if i < len(post_urls):
                    pause_time = random.uniform(0.5, 1.5)
                    print(f"[INFO] Pausa de {pause_time:.2f} segundos antes del siguiente post...")
                    time.sleep(pause_time)
                    
            except Exception as e:
                print(f"❌ [ERROR] Error procesando post {i}: {e}")
                traceback.print_exc()
                continue

        print(f"\n✅ [INFO] Extracción completada: {len(posts_data)} posts obtenidos de {username}.")
        return posts_data

    def _extract_post_data(self):
        """Extrae datos del post abierto."""
        try:
            # Verificar que estamos en un post
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//time"))
                )
            except TimeoutException:
                print("[ERROR] No se detectó un post abierto.")
                return None

            post_url = self.driver.current_url
            print(f"[INFO] URL del post: {post_url}")

            # Extraer número de likes - varios selectores posibles
            try:
                like_selectors = [
                    "//section//a[contains(@href, 'liked_by')]/span",
                    "//section//a[contains(@href, 'liked_by')]",
                    "//span[contains(text(), 'likes')]",
                    "//span[contains(text(), 'Me gusta')]",
                    "//span[contains(text(), 'Like')]"
                ]
                
                likes = "No disponible"
                for selector in like_selectors:
                    try:
                        likes_element = self.driver.find_element(By.XPATH, selector)
                        likes = likes_element.text.replace(",", "").strip()
                        if likes:
                            break
                    except:
                        continue
            except:
                likes = "No disponible"

            # Extraer fecha del post
            try:
                date_element = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
                post_date = date_element.get_attribute("datetime")
            except:
                post_date = "No disponible"

            # Extraer comment del autor
            author_comment = self._author_comment()
            
            # Extraer comentarios
            comments = self._extract_comments()

            print(f"✅ Post extraído: {post_url} | Likes: {likes} | Fecha: {post_date}")

            return {
                "url_post": post_url,
                "author_comment": author_comment,
                "likes": likes,
                "fecha_post": post_date,
                "comentarios": comments
            }

        except Exception as e:
            print(f"[ERROR] No se pudo extraer datos del post: {e}")
            traceback.print_exc()
            return None

    def _extract_comments(self):
        """Extrae hasta 10 comentarios del post (reducido para mayor velocidad)."""
        comments_data = {}
        
        try:
            # Múltiples intentos con diferentes selectores para encontrar comentarios
            comment_selectors = [
                "//ul//li[descendant::time]",  # Selector original
                "//ul//div[contains(@class, 'comment')]",  # Selector alternativo
                "//div[@role='dialog']//ul//li",  # Selector general para comentarios
                "//article//ul//li[.//a]"  # Selector basado en estructura común
            ]
            
            comment_elements = []
            
            for selector in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        comment_elements = elements[:10]  # Limitamos a 10 comentarios para mayor velocidad
                        print(f"[INFO] Encontrados {len(comment_elements)} comentarios con selector: {selector}")
                        break
                except:
                    continue
            
            if not comment_elements:
                print("[INFO] No se encontraron comentarios con ningún selector.")
                return comments_data

            for comment in comment_elements:
                try:
                    # Extraer el nombre de usuario - múltiples intentos
                    username = "unknown"
                    try:
                        username = comment.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]").get_attribute("alt").replace("'s profile picture", "")
                    except NoSuchElementException:
                        try:
                            username = comment.find_element(By.XPATH, ".//a").text
                        except:
                            pass

                    # Intentar extraer el texto del comentario - múltiples intentos
                    comment_text = None
                    try:
                        comment_text = comment.find_element(By.XPATH, ".//h3/following-sibling::div//span").text
                    except NoSuchElementException:
                        try:
                            comment_text = comment.find_element(By.XPATH, ".//span[not(contains(@class, 'timestamp'))]").text
                        except:
                            try:
                                # Intentar encontrar cualquier texto en el comentario
                                comment_text = comment.text
                            except:
                                pass

                    # Extraer la fecha del comentario
                    date = None
                    try:
                        date = comment.find_element(By.XPATH, ".//time").get_attribute("datetime")
                    except:
                        pass

                    # Extraer número de likes
                    likes = "0 likes"
                    try:
                        likes = comment.find_element(By.XPATH, ".//button/span[contains(text(), 'like')]").text
                    except:
                        pass

                    # Verificar si hay imagen en el comentario
                    image_url = None
                    try:
                        image_elements = comment.find_elements(By.XPATH, ".//img[not(contains(@alt, ' profile picture'))]")
                        if image_elements:
                            image_url = image_elements[0].get_attribute("src")
                    except:
                        pass

                    # Guardar los datos
                    if comment_text:
                        comments_data[username] = (comment_text, date, likes)
                    elif image_url:
                        comments_data[username] = ("image/GIF", image_url, date, likes)
                    else:
                        comments_data[username] = ("unknown", date, likes)

                except Exception as e:
                    print(f"⚠️ Error extrayendo un comentario: {e}")
                    continue

        except Exception as e:
            print(f"⚠️ No se pudieron extraer comentarios: {e}")
            traceback.print_exc()

        return comments_data

    def _author_comment(self):
        """Extrae el comentario del autor del post en Instagram."""
        try:
            # Múltiples selectores para encontrar el comentario del autor
            author_selectors = [
                "//ul//li[descendant::h1]",
                "//article//h1",
                "//div[@role='dialog']//div[contains(@class, 'caption')]",
                "//div[contains(@class, 'comment')]//div[contains(@class, 'owner')]",
                "//div[contains(@role, 'presentation')]//h1/..",  # Nuevo selector general
                "//article//div[.//h1]"  # Otro selector general
            ]
            
            for selector in author_selectors:
                try:
                    author_comment_element = self.driver.find_element(By.XPATH, selector)
                    
                    # Extraer nombre de usuario
                    username = "unknown"
                    try:
                        username_element = author_comment_element.find_element(By.XPATH, ".//img[contains(@alt, ' profile picture')]")
                        username = username_element.get_attribute("alt").replace("'s profile picture", "")
                    except:
                        try:
                            username_element = author_comment_element.find_element(By.XPATH, ".//a")
                            username = username_element.text
                        except:
                            pass
                    
                    # Extraer texto del comentario
                    comment_text = "No disponible"
                    try:
                        comment_text = author_comment_element.find_element(By.XPATH, ".//h1").text
                    except:
                        try:
                            comment_text = author_comment_element.find_element(By.XPATH, ".//span").text
                        except:
                            pass
                    
                    # Extraer hashtags
                    hashtags = []
                    try:
                        hashtags = [tag.text for tag in author_comment_element.find_elements(By.XPATH, ".//a[contains(@href, '/explore/tags/')]")]
                    except:
                        pass
                    
                    # Extraer menciones
                    mentions = []
                    try:
                        mentions = [mention.text for mention in author_comment_element.find_elements(By.XPATH, ".//a") if '@' in mention.text]
                    except:
                        pass
                    
                    return {
                        "author": username,
                        "comment": comment_text,
                        "hashtags": hashtags,
                        "mentions": mentions
                    }
                    
                except NoSuchElementException:
                    continue
            
            print("⚠️ No se encontró comentario del autor con ningún selector.")
            return None

        except Exception as e:
            print(f"⚠️ Error al extraer comentario del autor: {e}")
            return None

    def save_to_csv(self, data, account):
        """Guarda los datos extraídos en archivos CSV y JSON."""
        if not data:
            print("⚠️ No hay datos para guardar.")
            return

        # Convertir datos a formato tabular
        processed_data = []
        for post in data:
            post_data = {
                "url_post": post.get("url_post", ""),
                "likes": post.get("likes", ""),
                "fecha_post": post.get("fecha_post", ""),
                "author": post.get("author_comment", {}).get("author", "") if post.get("author_comment") else "",
                "comment": post.get("author_comment", {}).get("comment", "") if post.get("author_comment") else "",
                "hashtags": ", ".join(post.get("author_comment", {}).get("hashtags", [])) if post.get("author_comment") else "",
                "mentions": ", ".join(post.get("author_comment", {}).get("mentions", [])) if post.get("author_comment") else "",
            }
            
            # Añadir comentarios en forma plana (como columnas adicionales)
            comentarios = post.get("comentarios", {})
            for i, (user, comment_data) in enumerate(comentarios.items(), 1):
                if i > 5:  # Limitamos a 5 comentarios por post para no tener demasiadas columnas
                    break
                post_data[f"comentario_{i}_usuario"] = user
                if isinstance(comment_data, tuple):
                    post_data[f"comentario_{i}_texto"] = comment_data[0]
                    if len(comment_data) > 1:
                        post_data[f"comentario_{i}_fecha"] = comment_data[1]
                    if len(comment_data) > 2:
                        post_data[f"comentario_{i}_likes"] = comment_data[2]
                else:
                    post_data[f"comentario_{i}_texto"] = str(comment_data)
            
            processed_data.append(post_data)

        # Crear DataFrame y guardar a CSV
        df = pd.DataFrame(processed_data)
        date_str = datetime.now().strftime("%d_%m_%Y")
        filename = f"instagram_posts_{account}_{date_str}.csv"

        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✅ [INFO] Se guardaron {len(data)} filas en {filename}.")
        
        # También guardar una copia de los datos en JSON para preservar la estructura completa
        import json
        with open(f"instagram_posts_{account}_{date_str}.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ [INFO] Se guardó una copia en formato JSON para preservar la estructura completa.")

# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("  INSTAGRAM URL SCRAPER  ".center(80, "="))
    print("  Extrae posts directamente desde URLs específicas  ".center(80, "-"))
    print("="*80 + "\n")
    
    # Mostrar configuración
    print(f"📋 Configuración:")
    print(f"   - URLs a scrapear: {len(TARGET_URLS)}")
    for i, url in enumerate(TARGET_URLS, 1):
        print(f"     {i}. {url}")
    print(f"   - Máximo posts por URL: {MAX_POSTS}")
    print(f"   - Scrolls por página: {NUM_SCROLLS}")
    print(f"   - Filtro año: {YEAR_FILTER}")
    print("\n" + "-"*80 + "\n")
    
    scraper = InstagramScraper()
    
    try:
        # 1) Login
        print("[INFO] Iniciando login...")
        scraper.login()
        print("✅ Login completado")

        # 2) Procesar cada URL
        results = {}
        total_posts = 0
        
        for i, target_url in enumerate(TARGET_URLS, 1):
            print(f"\n{'='*60}")
            print(f"  PROCESANDO URL {i}/{len(TARGET_URLS)}  ".center(60))
            print(f"{'='*60}")
            
            posts = scraper.scrape_from_url(target_url)
            results[target_url] = len(posts)
            total_posts += len(posts)

            if posts:
                print(f"[INFO] Guardando {len(posts)} posts de: {target_url}")
                scraper.save_url_results_to_csv(posts, target_url)
            else:
                print(f"⚠️ [WARNING] No se encontraron posts en: {target_url}")
            
            # Pausa entre URLs para evitar rate limits
            if i < len(TARGET_URLS):
                pause_time = random.uniform(4, 8)
                print(f"[INFO] Pausa de {pause_time:.1f} segundos antes de la siguiente URL...")
                time.sleep(pause_time)

        # 3) Mostrar resumen final
        print("\n" + "="*70)
        print("  RESUMEN FINAL  ".center(70, "="))
        for url, count in results.items():
            status = "✅" if count > 0 else "⚠️"
            url_short = url[:50] + "..." if len(url) > 50 else url
            print(f"{status} {url_short}: {count} posts")
        print(f"\n📊 TOTAL: {total_posts} posts extraídos de {len(TARGET_URLS)} URLs")
        print("="*70 + "\n")
        
        if total_posts > 0:
            print("🎉 ¡Scraping completado exitosamente!")
        else:
            print("⚠️ No se encontraron posts. Revisa las URLs y los logs.")

    except Exception as e:
        print(f"💥 [CRÍTICO] Error en la ejecución: {e}")
        traceback.print_exc()
    finally:
        try:
            input("\n⏸️  Presiona Enter para cerrar el navegador...")
        except:
            pass
        scraper.driver.quit()
        print("🔚 [INFO] Selenium cerrado correctamente.")