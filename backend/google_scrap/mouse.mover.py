import numpy as np
import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
import time

sqrt3 = np.sqrt(3)
sqrt5 = np.sqrt(5)

# Source: https://ben.land/post/2021/04/25/windmouse-human-mouse-movement/

# =========================================================================
# Mouse
# =========================================================================
class MouseMover:
    def __init__(self, driver: uc.Chrome, start_x: int = 0, start_y: int = 0):
        self.driver = driver
        self.start_x = start_x
        self.start_y = start_y
        
        self.action = ActionChains(driver)

    def wind_mouse(self, dest_x, dest_y, G_0=9, W_0=3, M_0=15, D_0=12, move_mouse=lambda x,y: None):
        '''
        WindMouse algorithm. Calls the move_mouse kwarg with each new step.
        Released under the terms of the GPLv3 license.
        G_0 - magnitude of the gravitational fornce
        W_0 - magnitude of the wind force fluctuations
        M_0 - maximum step size (velocity clip threshold)
        D_0 - distance where wind behavior changes from random to damped
        '''
        
        start_x, start_y = self.start_x, self.start_y
        
        current_x,current_y = start_x, start_y
        v_x = v_y = W_x = W_y = 0
        while (dist:=np.hypot(dest_x-start_x,dest_y-start_y)) >= 1:
            W_mag = min(W_0, dist)
            if dist >= D_0:
                W_x = W_x/sqrt3 + (2*np.random.random()-1)*W_mag/sqrt5
                W_y = W_y/sqrt3 + (2*np.random.random()-1)*W_mag/sqrt5
            else:
                W_x /= sqrt3
                W_y /= sqrt3
                if M_0 < 3:
                    M_0 = np.random.random()*3 + 3
                else:
                    M_0 /= sqrt5
            v_x += W_x + G_0*(dest_x-start_x)/dist
            v_y += W_y + G_0*(dest_y-start_y)/dist
            v_mag = np.hypot(v_x, v_y)
            if v_mag > M_0:
                v_clip = M_0/2 + np.random.random()*M_0/2
                v_x = (v_x/v_mag) * v_clip
                v_y = (v_y/v_mag) * v_clip
            start_x += v_x
            start_y += v_y
            move_x = int(np.round(start_x))
            move_y = int(np.round(start_y))
            if current_x != move_x or current_y != move_y:
                #This should wait for the mouse polling interval
                # move_mouse(current_x:=move_x,current_y:=move_y)
                move_mouse(int(move_x-current_x), int(move_y - current_y ))
                current_x, current_y = move_x, move_y
        
        self.start_x, self.start_y = current_x, current_y
        return current_x,current_y
    
    def move_mouse(self, element: uc.WebElement):
        location = element.location
        size = element.size
        target_x = location["x"] + size["width"] * np.random.uniform()
        target_y = location["y"] + size["height"] * np.random.uniform()
        
        def lambda_mover(x, y):
            self.action.move_by_offset(x, y).perform()
            time.sleep(np.random.uniform(0.001, 0.01))
        
        
        self.wind_mouse(dest_x=target_x, dest_y=target_y,
                        move_mouse= lambda x, y: lambda_mover(x, y))
        self.start_x, self.start_y = target_x, target_y