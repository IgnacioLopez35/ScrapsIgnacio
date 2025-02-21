import time
import random
import numpy as np
from selenium.webdriver import ActionChains

class MoveMouse:
    def bezier_curve(self, p0, p1, p2, n=30):
        """
        Genera puntos de una curva Bézier de segundo grado (trayectoria curvada del mouse).
        - p0: Punto inicial
        - p1: Punto de control (afecta la curvatura)
        - p2: Punto final
        - n: Número de pasos en la curva
        """
        t_values = np.linspace(0, 1, n)
        curve = np.array([(1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2) for t in t_values])
        return curve

    def smooth_mouse_move(self, driver, element):
        """
        Mueve el cursor en un patrón curvado hacia el `element`.
        """
        print("🖱️ Simulando movimiento curvado del mouse...")

        # Obtener posición del elemento
        location = element.location
        size = element.size
        target_x, target_y = location["x"] + size["width"] // 2, location["y"] + size["height"] // 2

        # Obtener posición inicial del cursor (simulada)
        start_x, start_y = random.randint(target_x - 200, target_x - 100), random.randint(target_y - 100, target_y - 50)

        # Definir punto de control para la curva (afecta la curvatura)
        control_x = (start_x + target_x) // 2 + random.randint(-50, 50)
        control_y = (start_y + target_y) // 2 + random.randint(-50, 50)

        # Generar puntos de la curva
        curve_points = self.bezier_curve((start_x, start_y), (control_x, control_y), (target_x, target_y))

        action = ActionChains(driver)

        # Mover el cursor a través de la curva
        for x, y in curve_points:
            action.move_by_offset(int(x - start_x), int(y - start_y)).perform()
            start_x, start_y = x, y
            time.sleep(random.uniform(0.01, 0.05))  # Pequeñas pausas para realismo

        action.move_to_element(element).perform()  # Asegurar que el cursor llegue al destino
        time.sleep(0.5)  # Pausa antes del clic

        print("✅ Mouse movido al primer resultado.")
