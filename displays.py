# displays.py
import time
import threading
import queue
from RPLCD.i2c import CharLCD
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw
from config import LCD_ADDRESS, OLED_ADDRESS

class DisplayManager:
    def __init__(self):
        self.state_queue = queue.Queue()
        self.is_running = True
        self.lcd_scroll_event = threading.Event()
        
        # Iniciar Hardware
        try:
            self.lcd = CharLCD(i2c_expander='PCF8574', address=LCD_ADDRESS, port=1, cols=20, rows=4, dotsize=8)
            self.lcd.clear()
        except Exception as e:
            print(f"[LCD Error] {e}")
            self.lcd = None

        try:
            serial = i2c(port=1, address=OLED_ADDRESS)
            self.oled = ssd1306(serial)
        except Exception as e:
            print(f"[OLED Error] {e}")
            self.oled = None

        # Iniciar Hilo
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def update_state(self, state_name: str, text_data: str = ""):
        self.state_queue.put((state_name, text_data))

    def stop_scroll(self):
        self.lcd_scroll_event.clear()

    def _draw_face(self, state):
        if not self.oled: return
        img = Image.new('1', (self.oled.width, self.oled.height))
        draw = ImageDraw.Draw(img)
        
        if state == "DURMIENDO":
            draw.line((30, 32, 50, 32), fill="white", width=2)
            draw.line((78, 32, 98, 32), fill="white", width=2)
        elif state == "ESCUCHANDO":
            draw.ellipse((30, 22, 50, 42), outline="white", fill="white")
            draw.ellipse((78, 22, 98, 42), outline="white", fill="white")
        elif state == "PENSANDO":
            draw.ellipse((30, 22, 50, 42), outline="white")
            draw.ellipse((78, 22, 98, 42), outline="white")
            draw.ellipse((38, 22, 46, 30), fill="white")
            draw.ellipse((86, 22, 94, 30), fill="white")
        elif state == "HABLANDO":
            draw.ellipse((30, 22, 50, 42), outline="white", fill="white")
            draw.ellipse((78, 22, 98, 42), outline="white", fill="white")
            draw.ellipse((54, 48, 74, 58), outline="white", fill="white")
            
        self.oled.display(img)

    def _worker(self):
        current_state = "DURMIENDO"
        text_to_scroll = ""
        
        while self.is_running:
            try:
                new_state, text_data = self.state_queue.get(timeout=0.1)
                current_state = new_state
                self._draw_face(current_state)
                
                if current_state in ["ESCUCHANDO", "PENSANDO"]:
                    if self.lcd:
                        self.lcd.clear()
                        self.lcd.cursor_pos = (1, 4)
                        self.lcd.write_string(current_state)
                        
                elif current_state == "HABLANDO":
                    text_to_scroll = text_data
                    self.lcd_scroll_event.set()
                    
            except queue.Empty:
                pass

            # Lógica de Scroll bloqueante manejada dentro del hilo
            if current_state == "HABLANDO" and self.lcd_scroll_event.is_set() and self.lcd:
                self._do_scroll(text_to_scroll)
                self.lcd_scroll_event.clear()
                self._draw_face("DURMIENDO") # Vuelve a dormir visualmente al terminar

    def _do_scroll(self, text):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 20:
                current_line += (word + " ")
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip())

        for i in range(0, len(lines), 4):
            if not self.lcd_scroll_event.is_set():
                break # Interrupción de Barge-in detectada
            self.lcd.clear()
            for j in range(4):
                if i + j < len(lines):
                    self.lcd.cursor_pos = (j, 0)
                    self.lcd.write_string(lines[i + j])
            
            # Pausa verificando interrupciones
            for _ in range(30): 
                if not self.lcd_scroll_event.is_set(): break
                time.sleep(0.1)