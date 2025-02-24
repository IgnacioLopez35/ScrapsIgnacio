import os
import time
import random
import json
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScrapingInsta:
    def __init__(self, driver):
        self.driver = driver
        self.action = ActionChains(self.driver)
        self.timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        self.output_folder = f"instagram_data/{self.timestamp}"
        os.makedirs(self.output_folder, exist_ok=True)
    
    def _scroll_human(self):
        body = self.driver.find_element(By.TAG_NAME, "body")
        for _ in range(random.randint(3, 6)):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(1.5, 3.0))
    
    def _extract_text(self, xpath):
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text if element else "No disponible"
        except:
            return "No disponible"
    
    def _take_screenshot(self, post_element, image_id):
        filename = os.path.join(self.output_folder, f"{image_id}.png")
        post_element.screenshot(filename)
        return filename
    
    def _extract_comments(self):
        comments = {}
        comment_elements = self.driver.find_elements(By.XPATH, "//ul[@class='_a9z6 _a9za']//span")
        user_elements = self.driver.find_elements(By.XPATH, "//ul[@class='_a9z6 _a9za']//h3")
        
        for i, (user, comment) in enumerate(zip(user_elements[:10], comment_elements[:10])):
            comments[user.text] = comment.text if comment.text else "image"
        return json.dumps(comments, ensure_ascii=False)
    
    def scrape_posts(self, max_posts=20):
        posts_data = []
        posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
        
        for index, post in enumerate(posts[:max_posts]):
            try:
                self.action.move_to_element(post).perform()
                time.sleep(2)
                
                screenshot_path = self._take_screenshot(post, index+1)
                post_url = post.get_attribute("href")
                post.click()
                time.sleep(3)
                
                likes = self._extract_text("//section//span[contains(text(), 'Me gusta')]/preceding-sibling::span")
                fecha_post = self._extract_text("//time")
                comments = self._extract_comments()
                
                posts_data.append({
                    "url_post": post_url,
                    "fecha_ejecucion": self.timestamp,
                    "nombre_image": screenshot_path,
                    "likes": likes,
                    "fecha_post": fecha_post,
                    "comentarios": comments
                })
                
                close_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='dialog']//button"))
                )
                close_btn.click()
                time.sleep(2)
            except Exception as e:
                print(f"❌ Error extrayendo post: {e}")
                continue
        
        df = pd.DataFrame(posts_data)
        print(df.head())
        df.to_csv("instagram.csv", index=False, encoding="utf-8")
        print("✅ Datos guardados en instagram.csv")
