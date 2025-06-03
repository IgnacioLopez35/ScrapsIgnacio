import re
import time
import numpy as np
import pandas as pd
from appium import webdriver
from appium.webdriver.common.touch_action import TouchAction
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from datetime import date, timedelta, datetime

import unicodedata

import json

from modules.logger import Logger

# OCR para texto
from PIL import Image
import pytesseract
import io
import base64

DEVICE_NAME = "RFCX41P744Y"
ACCOUNT = 'Plata Card'
ANDROID_VERSION = '14'
DATE_LIMIT = '2025-04-01'
POSTS_LIMIT = 50
COMMENTS_LIMIT = 20

class FacebookScraper:

    def __init__(self, version, adb_name, searchtag, comments_limit: int = 20):
        
        self.version = version
        self.adb_name = adb_name
        self.searchtag = searchtag
        self.comments_limit = comments_limit
        self.driver = self.initialize_driver()
        
        screen_size = self.driver.get_window_size()
        self.screen_width = screen_size['width']
        self.screen_height = screen_size['height']
        
        # Load xpaths
        with open('appium_scrapper/facebook_xpaths.json', 'r') as file:
            self.xpaths = json.load(file)
        

    def initialize_driver(self):
        caps = {
            "platformName": "Android",
            "deviceName": DEVICE_NAME,
            "udid": DEVICE_NAME,
            "platformVersion": ANDROID_VERSION,
            "appPackage": "com.instagram.android",
            "appActivity": ".activity.MainTabActivity",
            "automationName": "UiAutomator2",
            "noReset": True,
            "newCommandTimeout": 6000,
            "adbExecTimeout": 20000,
            "autoGrantPermissions": True,
            "disableWindowAnimation": True,
            "unicodeKeyboard": False,
            "resetKeyboard": True,
            "ensureWebviewsHavePages": True,
            "uiautomator2ServerInstallTimeout": 40_000
        }
        options = UiAutomator2Options().load_capabilities(caps)
        return webdriver.Remote(command_executor='http://127.0.0.1:4723', options=options)
    
    def _human_type(self, text: str):
        text = text.lower()
        
        def quitar_acentos(texto: str) -> str:
            """
            Elimina los acentos de un texto.
            """
            return ''.join(
                c for c in unicodedata.normalize('NFD', texto)
                if unicodedata.category(c) != 'Mn'
            )
        
        text = quitar_acentos(text)
        
        for char in text:
            # A -> 29
            key_num = ord(char) - ord('a') + 29
            if char == ' ':
                key_num = 62
            self.driver.press_keycode(key_num)
            time.sleep(np.random.uniform(0.1,0.5))


    def swipe(self, window_range: tuple = [0.7, 0.3], duration: int = 1000):
        screen_size = self.driver.get_window_size()
        screen_width = screen_size['width']
        screen_height = screen_size['height']
        # Coordenadas del swipe de abajo hacia arriba
        start_x = screen_width // 2
        start_y = int(screen_height * window_range[0])
        end_x = screen_width // 2
        end_y = int(screen_height * window_range[1])
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)
    
    def _click(self, element_name: str,
               root: webdriver.webelement.WebElement = None,
               if_error: str = 'warning'):
        
        try:
            elements = self._find(element_name, root, multiple=True)
            if not elements:
                raise ValueError()
            elements = [element for element in elements if element.get_attribute("clickable") == 'true']
            element = elements[0]
            
        except Exception as e:
            if if_error=='ignore':
                return False
            
            if if_error=='warning':
                Logger.warning(f'Element {element_name} couldn\'t be clicked')
                return False
            
            if if_error=='raise':
                Logger.error(f'Element {element_name} couldn\'t be clicked')
                raise e
            
        element.click()
        return element
    
    def _text(self, element_name: str | webdriver.webelement.WebElement = None, 
              root: webdriver.webelement.WebElement = None,
              default = None,
              filename: str = 'last_screenshot.png',
              padding: int = 0,
              bounds: tuple = None):
        # root.find_element(By.XPATH, './*/android.view.ViewGroup[6]')
        # print(len(root.find_elements(By.XPATH, './*/')))
        if bounds:
            left, right, top, bottom = bounds['left'], bounds['right'], bounds['top'], bounds['bottom']
            screenshot = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))
            image = image.crop((left, top, right, bottom))
            image.save(filename)
            
            text = pytesseract.image_to_string(image)
        
            if not text:
                Logger.warning('Pytesseract couldn\'t extract text')
                text = default
                
            return text
        
        if isinstance(element_name, str):
            try:
                element = self._find(element_name, root)
            except Exception as e:
                Logger.warning(f'Couldn\'t extract {element_name} text')
                command = 'a'
                while command:
                    command = input('What to do next? ')
                    try:
                        eval(command)
                    except Exception as e:
                        Logger.error(e)
                    
                return default
            
            if not element:
                Logger.warning('Not element')
                return default
        
        if isinstance(element_name, webdriver.webelement.WebElement):
            element = element_name
        
        # //android.view.ViewGroup[@content-desc and not(.//android.view.ViewGroup)]
        if not padding:
            element.screenshot(filename)
            image = element.screenshot_as_png
            image = Image.open(io.BytesIO(image))
        else:
            # Get screen size from Appium (viewport size)
            location = element.location_in_view
            size = element.size
            viewport_size = self.driver.get_window_size()  # {'width': ..., 'height': ...}

            # Get actual image size
            screenshot = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))
            img_width, img_height = image.size

            # Calculate scaling ratios
            scale_x = img_width / viewport_size['width']
            scale_y = img_height / viewport_size['height']

            # Calculate scaled crop box with padding
            left = int((location['x'] - padding) * scale_x)
            top = int((location['y'] - padding) * scale_y)
            right = int((location['x'] + size['width'] + padding) * scale_x)
            bottom = int((location['y'] + size['height'] + padding) * scale_y)

            # Clamp values to image bounds
            left = max(0, left)
            top = max(0, top)
            right = min(image.width, right)
            bottom = min(image.height, bottom)

            # Crop with padding
            image = image.crop((left, top, right, bottom))
            image.save(filename)
        
        text = pytesseract.image_to_string(image)
        
        if not text:
            Logger.warning('Pytesseract couldn\'t extract text')
            text = default
            
        return text
    
    def _is_visible(self, element_name, root: webdriver.webelement.WebElement = None) -> bool:
        
        try:
            element = self._find(element_name, root, if_error='ignore')
            return bool(element)
        except:
            return False
    
    def _human_delay(self, mean: float = 2, std: float = 1):
        base_time = np.random.normal(mean, std)
        noise_scale = np.random.uniform(0.9, 1.1)
        noise_loc = (np.random.chisquare(2)-1.5)/3
        delay = (base_time+noise_loc)*noise_scale
        exp = np.random.exponential(3)/5
        time.sleep(max(0.75+exp, abs(delay)))
        return True
    
    def _parse_relative_date(self, x: str, relative_date: str = '') -> datetime:
        
        months_kw = ['month', 'mes']
        weeks_kw = ['semana', 'week', 'w']
        days_kw = ['dia', 'día', 'day', 'd']
        hours_kw = ['hora', 'hour', 'min', 'segundo', 'second', 'h']
        
        if not relative_date:
            relative_date = datetime.now().strftime("%Y_%m_%d")
        
        match = re.match(r'(?P<year>\d{4})_(?P<month>\d{1,2})_(?P<day>\d{1,2})', relative_date)
        # Check relative date format
        if not match:
            print('[Error] Fecha relativa no está en el formato %Y_%m_%d')
            return None
        
        relative_year, relative_month, relative_day = match.group('year'), match.group('month'), match.group('day')
        
        # None
        if not x:
            return None
        
        # Limpiar fecha
        x = re.sub(r'[^\w\s\-\_\\]', '', x).strip()
        
        difference = timedelta(0)
        # Full date
        if match:=re.match(r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})', x):
            year, month, day = match.group('year'), match.group('month'), match.group('day')
        
        # month/day
        elif match:=re.match(r'(?P<month>\d{1,2})-(?P<day>\d{1,2})', x):
            year, month, day = relative_year, match.group('month'), match.group('day')
        
        # relative
        elif any([key_word in x for key_word in months_kw]):
            match = re.search(r'\d+', x)
            year, month, day = relative_year, relative_month, relative_day
            difference = timedelta(months=int(match.group(0)))
        
        elif any([key_word in x for key_word in weeks_kw]):
            match = re.search(r'(\d+)', x)
            year, month, day = relative_year, relative_month, relative_day
            difference = timedelta(weeks=int(match.group(0)))
        
        elif any([key_word in x for key_word in days_kw]):
            match = re.search(r'(\d+)', x)
            year, month, day = relative_year, relative_month, relative_day
            difference = timedelta(days=int(match.group(0))+1)
        
        elif any([key_word in x for key_word in hours_kw]):
            year, month, day = relative_year, relative_month, relative_day
        
        else:
            print('[WARNING] La fecha no coincide con ningún patrón')
            print(x)
            return '99'
        
        result = datetime(int(year), int(month), int(day))
        
        result = result - difference
        return result.strftime('%Y_%m_%d')

    def _parse_facebook_date(self, x: str, relative_date: str = '') -> str:
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        if any([month in x for month in months]):
            match = re.match(r'(?P<month>\w{3})\s*(?P<day>\d{1,2}),?\s?(?P<year>\d{4})?.*', x)
            if not match:
                print(x)
                return '99'
            month =months.index(match.group('month'))+1
            
            if not match:
                return '99'
            
            day = match.group('day')
            
            year = match.group('year')
            if not year:
                year = datetime.now().strftime("%Y")
                # year = 2025 #TODO: current year
        
        else:
            print(self._parse_relative_date(x))
            return self._parse_relative_date(x)
            
        print(f"{year}_{str(month).zfill(2)}_{str(day).zfill(2)}")
        return f"{year}_{str(month).zfill(2)}_{str(day).zfill(2)}"
    
    def _find(self, element_name: str, 
              root: webdriver.webelement.WebElement = None,
              multiple: bool = False,
              if_error: str = 'raise') -> webdriver.webelement.WebElement:
        
        if not root:
            root = self.driver
        
        xpaths = self.xpaths[element_name]
        xpath = ' | '.join(xpaths)
        
        # Reemplazar variables
        xpath = xpath.replace('$searchtag', self.searchtag)
        
        try:
            if multiple:
                element = root.find_elements(
                    By.XPATH,
                    xpath
                )
            else:
                element = root.find_element(
                    By.XPATH,
                    xpath
                )
        except Exception as e:
            
            if if_error=='raise':
                Logger.error(f'Element {element_name} not found using xpath {xpath}')
                raise e
            elif if_error=='warning':
                Logger.warning(f'Element {element_name} not found using xpath {xpath}')
                return None
            elif if_error=='ignore':
                return None
            elif if_error=='debug':
                command = 'a'
                while command:
                    command = input('What to do next? ')
                    try:
                        eval(command)
                    except Exception as e:
                        Logger.error(e)
            
        
        return element
    
    def _scroll_to_view(self, element: webdriver.webelement.WebElement, 
                              relative: str = 'top',
                              scroll_proportion: float = 0.2,
                              scroll_to: float = 0.5):
        last_location = 0
        
        if relative =='top':
            location = lambda : element.location['y']
        else:
            location = lambda : element.location['y'] + element.size['height']
        
        while location() < self.screen_height * scroll_to:
            start = 0.5 - scroll_proportion/2
            end = 0.5 + scroll_proportion/2
            self.swipe(window_range=(start, end))
            
            if last_location == location():
                break
            
            last_location = location()
            
        while location() > self.screen_height * scroll_to:
            start = 0.5 + scroll_proportion/2
            end = 0.5 - scroll_proportion/2
            self.swipe(window_range=(start, end))
            
            if last_location == location():
                break
            
            last_location = location()
    
    def search(self):
        """Searches certain input
        """
        
        # Buscar boton de buscar
        Logger.info('Clicking search button')
        self._click('search-button', if_error='raise')
        # search_button = self._click(
        #     '//android.widget.Button[@content-desc="Search"] | //android.view.ViewGroup[@content-desc="Search"]',
        #     if_error='raise'
        # )
        self._human_delay()
        
        # search_box = self.driver.find_element(
        #     By.XPATH,
        #     '//android.widget.EditText[@text="Search"]'
        # )
        self._human_delay()
        
        Logger.info('Typing the account')
        self._human_type(self.searchtag)
        self._human_delay()
        # search_box.send_keys(f'{self.searchtag}')
        Logger.info('Clicking best match')
        self._click('best-match')
        # self._click(f'//android.view.ViewGroup[contains(@content-desc, "{self.searchtag}")]')
        self._human_delay(3)
        
        # self.driver.press_keycode(66)
        # self._human_delay(3)
        Logger.info('Clicking account match')
        self._click('account-match')
        # self._click(f'//android.view.ViewGroup[contains(@content-desc, "{self.searchtag}")]')
        self._human_delay(3)
        # Enlace a mejor búsqueda
    
    def _area(self, element_name: str | webdriver.webelement.WebElement, 
             root: webdriver.webelement.WebElement = None):
        
        if isinstance(element_name, str):
            element = self._find(element_name, root)
        elif isinstance(element_name, webdriver.webelement.WebElement):
            element = element_name
        
        return element.size['height'] * element.size['width']
    
    def _scrape_profile(self, date_limit: str, posts_limit: int):
        
        self.scraped_posts = []
        visited = []
        
        while len(self.scraped_posts) < posts_limit:
            
            # Hacer click en el post
            while not self._is_visible('post-header'):
                self.swipe()
            
            post = self._find('post-header')
            self._scroll_to_view(post, 'top', scroll_to=0.4)
            self._click('post-header')
            # post = self._click(post_xpath)
            self._human_delay(3)
            
            post = self._find('post')
            
            date_bounds = {'left': 150,
                           'right': 400,
                           'top': 320,
                           'bottom': 400}
            date = self._text(bounds=date_bounds, filename='date_screenshot.png')
            if self.searchtag in date:
                date_bounds = {'left': 150,
                           'right': 400,
                           'top': 410,
                           'bottom': 500}
                date = self._text(bounds=date_bounds, filename='date_screenshot.png')
            
            
            # date = self._text('post-date',
            #                   root=post,
            #                   filename='date_screenshot.png',
            #                   padding=30)
            
            print(f'Date: {date}')
            
            if not date or 'Sponsored' in date:
                self.driver.back()
                self.swipe(window_range=(0.9,0.1))
                self._human_delay()
                continue
            
            if self._parse_facebook_date(date) < date_limit:
                break
            
            # Extraer información visible del post
            try:
                author = self._find('post-author').get_attribute('content-desc')[:-len(' Profile picture')]
            except:
                author = self.searchtag
            
            print(f'Author: {author}')
            
            description = self._text('post-description')
            
            likes = self._find('post-likes', post, if_error='warning')
            shares = self._find('post-shares', post, if_error='ignore')
            
            self.swipe()
            if likes:
                likes = self._text(likes, default= 0)
            else:
                likes = 0
            print(f'Likes: {likes}')
            
            if shares:
                shares = self._text(shares, default= 0)
            else:
                shares = 0
            print(f'Shares {shares}')
            
            self.swipe()
            # Comments
            visited_comments = []
            comments_data = []
            
            last_last_comments = 0
            last_comments = 0
            
            while len(comments_data) < self.comments_limit:
                
                comments = self._find('comments', multiple=True)
                
                for comment in comments:
                    
                    # Si el comentario tiene una foto
                    has_photo = False
                    if self._is_visible('comment-photo', root=comment):
                        
                        Logger.success('FOTO ENCONTRADA')
                        has_photo = True
                        
                        # Deslizar el tamaño de la imagen
                        photo = self._find('comment-photo', root=comment)
                        
                        self._scroll_to_view(photo, 'top')
                    
                    try:
                        comment_author = self._find(
                            'comment-author',
                            root= comment,
                            if_error='ignore'
                            ).get_attribute('content-desc')
                        print(f'Comment author: {comment_author}')
                    except: 
                        comment_author = ''
                    
                    try:
                        comment_text_area = self._area('comment-text', root=comment)
                        if comment_text_area > 123_456:
                            comment_text = self._click('comment-text', root=comment, if_error='warning')
                        
                        comment_text = self._text('comment-text',
                                                root=comment,
                                                default='')
                        print(f'Comment text: {comment_text}')
                    except Exception as e:
                        Logger.error(type(e))
                        Logger.error(str(e)[:100])
                        comment_text = ''
                    
                    # Bajar al final de la foto
                    if has_photo:
                        self._scroll_to_view(photo, relative='bottom')
                    
                    try:
                        comment_date = self._find('comment-date',
                                                root=comment,
                                                if_error='warning').get_attribute('content-desc')
                    except: comment_date = '99'
                    print(f'Comment date: {comment_date}')
                    
                    try:
                        comment_likes = self._find('comment-likes',
                                                   root= comment, if_error='ignore').get_attribute('content-desc')
                    except:
                        comment_likes = 0
                    print(f'Comment likes: {comment_likes}')
                    
                    
                    if not all([comment_author, comment_date, comment_text]):
                        continue
                    # Revisar si no se ha leído ese comentario antes
                    data = (comment_author, comment_date, comment_likes, comment_text)
                    if hash(data) in visited_comments:
                        continue
                    else:
                        visited_comments.append(hash(data))
                    
                    # Agregar comentario
                    comments_data.append(
                        {
                            'autor': comment_author,
                            'fecha': self._parse_facebook_date(comment_date),
                            'description': comment_text,
                            'likes': comment_likes
                        }
                    )
                if last_last_comments == len(comments_data):
                    break
                last_last_comments = last_comments
                last_comments = len(comments_data)
                
                self.swipe()
                
            
            self.scraped_posts.append({'Red': 'Facebook',
                'Mes': 'abril', #TODO: Cambiar
                'Competidor': author,
                'comentario_limpio': description,
                'fecha_post': self._parse_facebook_date(date),
                'comentarios': comments_data,
                'likes': likes,
                # 'numero_de_comentarios': comments_count,
                # 'guardados': saved,
                'compartidos': shares,
                # 'detalles': {
                #     'es_foto': is_photo,
                #     'titulo_foto': title
                #     }
                })
            self.driver.back()
            self.swipe(window_range=[0.8,0.2])
        
    
    
    
    def extractor(self, date_limit: str, posts_limit: int = 100):
        
        try:
            datetime.strptime(date_limit, '%Y_%m_%d')
        except:
            print('Date Limit is invalid, expected format %Y_%m_%d')
            raise ValueError()
        
        Logger.info(f'Searching {self.searchtag}')
        
        self.swipe(window_range=[0.3, 0.7])
        self._human_delay()
        
        self.search()
        self._human_delay()
        
        self.swipe()
             
        Logger.info('Starting to scrape videos')
        self._scrape_profile(date_limit, posts_limit)


    def save_results(self):
        df = pd.DataFrame(self.scraped_posts)
        df.to_csv(f'facebook_{self.searchtag}_{datetime.now().strftime("%Y_%m_%d")}.csv', index = False)
        self.driver.quit()

if __name__=='__main__':
    scraper = FacebookScraper(
        version="14",
        adb_name=DEVICE_NAME,
        searchtag=ACCOUNT,  # Hashtag a buscar
        comments_limit=COMMENTS_LIMIT
    )
    try:
        scraper.extractor(DATE_LIMIT, POSTS_LIMIT)
    except Exception as e:
        Logger.fatal_error('Excecution terminated')
        Logger.info('Saving results')
        scraper.save_results()
        
        raise e
        
    Logger.info('Saving results')
    scraper.save_results()