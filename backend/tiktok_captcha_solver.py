import cv2
import numpy as np
import base64
import re

from selenium.webdriver import Chrome, Firefox, Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from google_scrap.move_mouse import MouseMover, ActionChainsDelayed


class TikTokCAPTCHASolver():
    
    def __init__(self, driver):
        self.driver = driver
        self.action = ActionChainsDelayed(driver)
        self.mm = MouseMover(self.driver)
        self.move_mouse = self.mm.move_mouse
        self.angle = 0
        pass

# =========================================================================
# UTILIDADES
# =========================================================================
    
    def find_captcha_imgs(self, timeout = 10):
        
        # WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//img[@alt="Captcha"]')))
        # outer_circle, inner_circle = self.driver.find_elements(By.XPATH, '//img[@alt="Captcha"]')
        
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((By.XPATH, '//img[contains(@style, "transform: rotate(0deg)")]')))
            outer_circle, inner_circle = self.driver.find_elements(By.XPATH, '//img[contains(@style, "transform: rotate(0deg)")]')
        except:
            return False # Si no se encontró el captcha
        if not inner_circle.is_displayed(): return False
            
        print("Descargando imagenes")
        canvas_inner = self.driver.execute_script("""
                var img = arguments[0];
                var canvas = document.createElement('canvas');
                var ctx = canvas.getContext('2d');
                
                // Usar el tamaño real de la imagen
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                
                return canvas.toDataURL('image/png').split(',')[1];
            """, inner_circle)

        # Decodificar y guardar la imagen
        img_inner = base64.b64decode(canvas_inner)
        with open("img_inner.png", "wb") as f:
            f.write(img_inner)
        self.image_inner = img_inner

        print("Imagen extraída y guardada con éxito.")
        
        canvas_outer = self.driver.execute_script("""
                var img = arguments[0];
                var canvas = document.createElement('canvas');
                var ctx = canvas.getContext('2d');
                
                // Usar el tamaño real de la imagen
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                
                return canvas.toDataURL('image/png').split(',')[1];
            """, outer_circle)

        # Decodificar y guardar la imagen
        img_outer = base64.b64decode(canvas_outer)
        with open("img_outer.png", "wb") as f:
            f.write(img_outer)

        print("Imagen extraída y guardada con éxito.")
        
        self.read_paths('img_inner.png', 'img_outer.png')
        return True
    
    def _rotate_image(self, img, angle=0, coord=None):
       
        cy, cx = [ i/2 for i in img.shape[:-1] ] if coord is None else coord[::-1]
        # Rotar y zoom
        rot_mat = cv2.getRotationMatrix2D((cx,cy), angle, 1)
        img = cv2.warpAffine(img, rot_mat, img.shape[1::-1], flags=cv2.INTER_LINEAR, )
        
        return img
            
    def _resize_to_match(self, image, target_shape):
        resized = cv2.resize(image, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
        return resized
        
    def _overlay_images(self, background, foreground):
        h, w, _ = foreground.shape
        x_offset = (background.shape[1] - w) // 2
        y_offset = (background.shape[0] - h) // 2
        
        roi = background[y_offset:y_offset+h, x_offset:x_offset+w]
        mask = cv2.cvtColor(foreground, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        
        bg_part = cv2.bitwise_and(roi, roi, mask=mask_inv)
        fg_part = cv2.bitwise_and(foreground, foreground, mask=mask)
        background[y_offset:y_offset+h, x_offset:x_offset+w] = cv2.add(bg_part, fg_part)
        
        return background
    
    def _check_captcha_angle(self):
        # style="clip-path: circle(50%); transform: rotate(0deg); display: flex;"
        _, inner_circle = self.driver.find_elements(By.XPATH, '//img[@alt="Captcha"]')
        style = inner_circle.get_attribute('style')
        # print(f"Style: {style}")
        match = re.match(r'.+\(([\d.]+)deg.+', style)
        degrees = 0
        if match:
            degrees = match.groups()[0]
        
        print(f"Degrees: {degrees}")
        return float(degrees)
# =========================================================================
# SUPPORT
# =========================================================================
    def show_result(self):
        # self.angle=1
        print(f"Ángulo: {self.angle}")
        rotated_inner = self._rotate_image(self.image_inner, angle=-self.angle)
        rotated_outer = self._rotate_image(self.image_outer, angle=self.angle)
        result = self._overlay_images(rotated_outer, rotated_inner)
        cv2.imshow("Imagen alineada", result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    
    def read_paths(self, path_inner, path_outer):
        # Convert images to grayscale
        image_inner = cv2.imread(path_inner)
        image_outer = cv2.imread(path_outer)
        self.image_inner = image_inner
        self.image_outer = image_outer
        
        # self._coincidence(359)

        # angle = 0
        # self.angle = angle
        return 0
    
    def solve(self, angle = 359):
        img_inner = self.image_inner
        img_outer = self.image_outer
        
        # Resize inner image to overlay the images
        img_inner = cv2.resize(img_inner, np.uint8(np.array(self.image_inner.shape[:-1])*1.05))
        min_coincidence = 1e10
        best_angle = 0
        
        h, w, _ = img_inner.shape
        x_offset = (img_outer.shape[1] - w) // 2
        y_offset = (img_outer.shape[0] - h) // 2
        
        # Crop outer image to fit inner
        cropped = img_outer[y_offset:y_offset+h, x_offset:x_offset+w]
        
        for angle in range(angle):
            img_inner_rotated = self._rotate_image(img_inner, -angle)
            
            
            shared_pixels = cv2.bitwise_and(cropped, img_inner_rotated)
            # cv2.imshow('k', shared_pixels)
            
            # Calculate coincidence level
            coincidence = np.abs(img_inner_rotated - shared_pixels).mean()
            if coincidence < min_coincidence:
                min_coincidence = coincidence
                best_angle = angle
            # print(coincidence)
            # cv2.waitKey(10)
        # cv2.waitKey(0)
        cv2.destroyAllWindows()
        self.angle = best_angle/2
        print(f"Best angle found: {self.angle}")
        return self.angle

    def drag_slider(self, tolerance = 1):
        if self.angle == 0: return
        
        # Ecnonctrar slider
        print("Buscando slider")
        # slider = self.driver.find_element(By.XPATH, '//button[@id="captcha_slide_button"]')
        slider = self.driver.find_element(By.XPATH, '//div[contains(@style, "transform: translateX(0px)")]')
        
        # Calcular los pixeles a mover
        total_pxl = 284
        max_degrees = 180
        pixels_per_degree = total_pxl/max_degrees
        move_x = self.angle * pixels_per_degree
        # Funciona pero lo hace muy rápido
        self.action.drag_and_drop_by_offset(slider, move_x, 0).perform()
        
        
        # self.mm.action.click_and_hold().perform()
        # print("Click an hold slider")
        # # self.mm.action.click(slider).perform()
        # # self.mm.action.click_and_hold(slider).perform()
        # # self.mm.action.pause(np.random.uniform(1,3)).perform()
        # self.mm.action.click_and_hold()
        
        # print("Moving mouse forward")
        # self.mm.move_mouse_by_offset(offset_x=move_x+15)
        # self.mm.action.pause(np.random.uniform(1,3)).perform()
        
        # print("Moving mouse backwards")
        # self.mm.move_mouse_by_offset(offset_x=-15)
        # self.mm.action.pause(np.random.uniform(1,3)).perform()
        
        # self.mm.action.release().perform()
        
        
            

if __name__=='__main__':
    solver = TikTokCAPTCHASolver('any')
    solver.read_paths("img_inner.png",
                        "img_outer.png")
    angle = solver.solve()
    solver.show_result()
    if angle is not None:
        print(f"Las imágenes deben rotar {angle:.2f}° en sentidos opuestos para coincidir.")
        
    else:
        print("No se pudo determinar el ángulo de rotación.")
        