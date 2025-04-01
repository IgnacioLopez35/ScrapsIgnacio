import json
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def extract_comments_with_replies(self):
    """
    Extrae todos los comentarios del video, incluyendo sus respuestas, y los guarda en formato JSON.
    Implementa una navegación más robusta por la sección de comentarios para cargar más contenido.
    """
    comments_data = []
    try:
        print("🔍 Intentando extraer comentarios y respuestas...")
        
        # 1. Navegar hasta la sección de comentarios
        try:
            self._human_delay(1, 2)
            
            # Scroll hasta la sección de comentarios
            comments_section = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", comments_section)
            time.sleep(3)  # Esperar a que carguen los comentarios iniciales
            
            # Verificar que existan comentarios
            try:
                comments_header = self.driver.find_element(By.XPATH, '//*[@id="count"]/yt-formatted-string')
                if "Comentarios desactivados" in comments_header.text:
                    print("ℹ️ Los comentarios están desactivados en este video")
                    return json.dumps({"comments": [], "error": "comments_disabled"})
            except NoSuchElementException:
                pass
            
        except TimeoutException:
            print("⚠️ No se encontró la sección de comentarios")
            return json.dumps({"comments": [], "error": "comments_section_not_found"})
        
        # 2. Cargar más comentarios mediante scroll
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        comment_count = 0
        max_scroll_attempts = 10  # Limitar el número de scrolls para evitar bucles infinitos
        
        for scroll_attempt in range(max_scroll_attempts):
            # Hacer scroll para cargar más comentarios
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self._human_delay(1.5, 3)
            
            # Contar comentarios actuales para verificar si se cargaron más
            current_comments = self.driver.find_elements(By.XPATH, '//ytd-comment-thread-renderer')
            if len(current_comments) > comment_count:
                print(f"📊 Cargados {len(current_comments)} comentarios (antes: {comment_count})")
                comment_count = len(current_comments)
            
            # Comprobar si el scroll llegó al final
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                print("🛑 No se detectaron más comentarios al hacer scroll")
                break
            last_height = new_height
            
            # Pausa más larga cada 3 scrolls
            if scroll_attempt % 3 == 2:
                pause_time = random.uniform(3, 5)
                print(f"⏱️ Pausa de {pause_time:.1f} segundos...")
                time.sleep(pause_time)
        
        # 3. Extraer los comentarios principales
        comment_threads = self.driver.find_elements(By.XPATH, '//ytd-comment-thread-renderer')
        print(f"🔍 Procesando {len(comment_threads)} comentarios principales encontrados")
        
        for i, thread in enumerate(comment_threads):
            try:
                # Extraer datos del comentario principal
                comment_id = thread.get_attribute('id') or f"comment_{i}"
                
                # Autor del comentario
                try:
                    author = thread.find_element(By.XPATH, './/a[@id="author-text"]').text
                except NoSuchElementException:
                    author = "Usuario desconocido"
                
                # Texto del comentario
                try:
                    comment_text = thread.find_element(By.XPATH, './/yt-formatted-string[@id="content-text"]').text
                except NoSuchElementException:
                    comment_text = "[Contenido no disponible]"
                
                # Likes del comentario
                try:
                    likes_element = thread.find_element(By.XPATH, './/span[@id="vote-count-middle"]')
                    likes = likes_element.text.strip() or "0"
                except NoSuchElementException:
                    likes = "0"
                
                # Fecha del comentario
                try:
                    date = thread.find_element(By.XPATH, './/yt-formatted-string[@class="published-time-text"]').text
                except NoSuchElementException:
                    date = "Desconocido"
                
                # 4. Expandir respuestas si hay alguna
                replies_data = []
                try:
                    # Verificar si el comentario tiene respuestas por expandir
                    replies_button = thread.find_elements(By.XPATH, './/ytd-button-renderer[@id="more-replies"]/a')
                    
                    if replies_button:
                        print(f"👉 Expandiendo respuestas del comentario {i+1}")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", replies_button[0])
                        self._human_delay(0.5, 1)
                        
                        try:
                            replies_button[0].click()
                            time.sleep(2)  # Esperar a que se carguen las respuestas
                        except Exception as e:
                            print(f"⚠️ Error al hacer clic en 'Ver respuestas': {str(e)}")
                    
                    # Recopilar todas las respuestas visibles
                    try:
                        replies = thread.find_elements(By.XPATH, './/ytd-comment-renderer')
                        
                        for j, reply in enumerate(replies):
                            if j == 0:  # Saltar el primer elemento que suele ser el comentario principal
                                continue
                                
                            try:
                                # Extraer datos de la respuesta
                                reply_author = reply.find_element(By.XPATH, './/a[@id="author-text"]').text.strip()
                                reply_text = reply.find_element(By.XPATH, './/yt-formatted-string[@id="content-text"]').text.strip()
                                
                                try:
                                    reply_likes = reply.find_element(By.XPATH, './/span[@id="vote-count-middle"]').text.strip() or "0"
                                except NoSuchElementException:
                                    reply_likes = "0"
                                    
                                try:
                                    reply_date = reply.find_element(By.XPATH, './/yt-formatted-string[@class="published-time-text"]').text.strip()
                                except NoSuchElementException:
                                    reply_date = "Desconocido"
                                
                                # Agregar datos de la respuesta
                                replies_data.append({
                                    "author": reply_author,
                                    "text": reply_text,
                                    "likes": reply_likes,
                                    "date": reply_date
                                })
                            except (NoSuchElementException, StaleElementReferenceException) as e:
                                print(f"⚠️ Error extrayendo datos de una respuesta: {str(e)}")
                    
                    except Exception as e:
                        print(f"⚠️ Error procesando respuestas: {str(e)}")
                
                except Exception as e:
                    print(f"⚠️ Error expandiendo respuestas: {str(e)}")
                
                # 5. Agregar el comentario con sus respuestas
                comment_obj = {
                    "id": comment_id,
                    "author": author,
                    "text": comment_text,
                    "likes": likes,
                    "date": date,
                    "replies": replies_data
                }
                
                comments_data.append(comment_obj)
                
                # Descanso periódico
                if i % 5 == 4:
                    self._human_delay(1, 2)
                
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print(f"⚠️ Error procesando comentario {i+1}: {str(e)}")
        
        print(f"✅ Extracción completada: {len(comments_data)} comentarios principales con un total de {sum(len(c['replies']) for c in comments_data)} respuestas")
        return json.dumps({"comments": comments_data}, ensure_ascii=False, indent=2)
        
    except Exception as e:
        print(f"🚨 Error crítico extrayendo comentarios: {str(e)}")
        return json.dumps({"comments": [], "error": str(e)})

# Modificar la función process_channel para almacenar los comentarios en formato JSON
def process_channel_modified(channel_url, service):
    print(f"\n📢 Procesando canal: {channel_url}")
    data = []
    
    # Configurar opciones del navegador
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") #---------------
    chrome_options.add_argument(f"user-agent={random.choice(agents)}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Crear driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    scraper = YouTubeScraper(driver)
    
    # Agregar el nuevo método al objeto scraper
    scraper.extract_comments_with_replies = extract_comments_with_replies.__get__(scraper, YouTubeScraper)
    
    try:
        for attempt in range(MAX_RETRIES):
            try:
                # [Resto del código se mantiene igual hasta el procesamiento de videos]
                
                driver.get(channel_url)
                scraper._wait_for_page_load()
                scraper._human_delay(2, 4)
                
                # Hacer scroll para cargar videos
                scraper._scroll_to_bottom(times=SCROLL_ATTEMPTS, pause_every=PAUSE_EVERY)
                
                # Extraer enlaces de videos
                videos = scraper.wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@href, "/watch?v=")]')))
                links = list({video.get_attribute('href') for video in videos if video.get_attribute('href')})
                
                print(f"✅ {len(links)} videos únicos encontrados (buscando {VIDEOS_TO_SCRAPE} que cumplan el filtro)")
                
                videos_processed = 0
                matching_videos = 0
                
                # Procesar videos hasta encontrar los que cumplen el filtro
                for link in links:
                    if not link or matching_videos >= VIDEOS_TO_SCRAPE or videos_processed >= MAX_VIDEOS_TO_CHECK:
                        break
                        
                    videos_processed += 1
                    print(f"\n🔎 Procesando video {videos_processed}: {link}")
                    
                    for video_attempt in range(MAX_RETRIES):
                        try:
                            driver.get(link)
                            scraper._wait_for_page_load()
                            scraper._human_delay(2, 4)
                            
                            # Extraer y verificar fecha
                            publish_date = scraper.extract_publish_date(as_datetime=True)
                            date_text = scraper.extract_publish_date(as_datetime=False)
                            
                            if not scraper._date_matches_filter(publish_date):
                                print(f"⏩ Video no cumple el filtro ({date_text}), saltando...")
                                break
                                
                            matching_videos += 1
                            print(f"🎯 Video cumple el filtro ({date_text}), extrayendo datos...")
                            
                            # Extraer metadatos
                            try:
                                title = driver.find_element(By.XPATH, '//meta[@name="title"]').get_attribute('content')
                                description = driver.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
                            except NoSuchElementException:
                                title, description = "N/A", "N/A"
                            
                            # Extraer otros datos
                            likes = scraper.extract_likes()
                            views = scraper.extract_views()
                            
                            # Extraer comentarios con el nuevo método
                            comments_json = scraper.extract_comments_with_replies()
                            
                            # Guardar datos
                            data.append([
                                channel_url, 
                                title, 
                                views, 
                                likes, 
                                description, 
                                comments_json,  # Comentarios en formato JSON 
                                date_text, 
                                link
                            ])
                            break
                            
                        except Exception as e:
                            print(f"⚠️ Intento {video_attempt + 1} fallido: {str(e)}")
                            if video_attempt == MAX_RETRIES - 1:
                                print("❌ No se pudo procesar el video")
                            time.sleep(random.uniform(2, 5))
                
                print(f"\n🎯 {matching_videos} videos encontrados que cumplen con el filtro '{DATE_FILTER}'")
                break
                
            except Exception as e:
                print(f"⚠️ Intento {attempt + 1} fallido para canal: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    print("❌ No se pudo procesar el canal")
                time.sleep(random.uniform(5, 10))
                
    except Exception as e:
        print(f"🚨 Error crítico: {str(e)}")
    finally:
        driver.quit()
        return data