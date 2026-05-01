"""
Eve - OLED Face Animations
Maneja la pantalla OLED 0.96" (128x64) con animaciones de cara.
Conexión: SDA → GPIO2, SCL → GPIO3 (I2C1)
"""

import time
import threading
import math
from PIL import Image, ImageDraw, ImageFont

try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    LUMA_AVAILABLE = True
except ImportError:
    LUMA_AVAILABLE = False
    print("[OLED] luma.oled no disponible, usando modo simulado")


class OLEDFace:
    # Dimensiones OLED
    W = 128
    H = 64

    # Centro del rostro (zona superior)
    CX = 64
    CY = 30

    # Radio de la cara oval
    FACE_W = 26
    FACE_H = 26

    def __init__(self):
        from config import OLED_I2C_PORT, OLED_I2C_ADDRESS

        self.device = None
        if LUMA_AVAILABLE:
            try:
                serial = i2c(port=OLED_I2C_PORT, address=OLED_I2C_ADDRESS)
                self.device = ssd1306(serial, width=self.W, height=self.H)
                print(f"[OLED] Conectada en I2C:{OLED_I2C_ADDRESS:#x}")
            except Exception as e:
                print(f"[OLED] Error al conectar: {e}. Modo simulado.")

        self._mode = "idle"
        self._frame = 0
        self._running = True
        self._lock = threading.Lock()

        # Hilo de animación
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ──────────────────────────────────────────
    #  API pública
    # ──────────────────────────────────────────
    def set_mode(self, mode: str):
        with self._lock:
            if self._mode != mode:
                self._mode = mode
                self._frame = 0

    # ──────────────────────────────────────────
    #  Loop de animación
    # ──────────────────────────────────────────
    def _loop(self):
        fps_delay = 0.10  # 10 FPS

        while self._running:
            with self._lock:
                mode = self._mode
                frame = self._frame
                self._frame += 1

            try:
                img = Image.new("1", (self.W, self.H), 0)
                draw = ImageDraw.Draw(img)
                self._render(draw, mode, frame)
                self._push(img)
            except Exception as e:
                print(f"[OLED] Error de render: {e}")

            time.sleep(fps_delay)

    def _push(self, img):
        if self.device:
            self.device.display(img)
        # else: solo en consola si quisiéramos debug

    # ──────────────────────────────────────────
    #  Dispatcher de modos
    # ──────────────────────────────────────────
    def _render(self, draw: ImageDraw.Draw, mode: str, f: int):
        dispatch = {
            "idle":          self._idle,
            "wake_detected": self._happy,
            "listening":     self._listening,
            "thinking":      self._thinking,
            "speaking":      self._speaking,
            "error":         self._error,
        }
        fn = dispatch.get(mode, self._idle)
        fn(draw, f)

    # ──────────────────────────────────────────
    #  Primitivas de dibujo
    # ──────────────────────────────────────────
    def _face_oval(self, draw):
        cx, cy = self.CX, self.CY
        fw, fh = self.FACE_W, self.FACE_H
        draw.ellipse(
            [cx - fw, cy - fh, cx + fw, cy + fh],
            outline=1, fill=0
        )

    def _eyes(self, draw, f,
              blink=False, wide=False,
              dx=0, dy=0,
              style="normal"):
        cx, cy = self.CX, self.CY
        # Posición base de cada ojo
        lx, ly = cx - 9, cy - 6
        rx, ry = cx + 9, cy - 6

        ew = 5          # radio horizontal del ojo
        eh = 7 if wide else 5   # radio vertical

        if blink:
            # Línea de parpadeo
            draw.line([lx - ew, ly, lx + ew, ly], fill=1, width=2)
            draw.line([rx - ew, ry, rx + ew, ry], fill=1, width=2)
            return

        if style == "happy":
            # Ojos curvados hacia arriba (feliz)
            draw.arc([lx - ew, ly - 4, lx + ew, ly + 4], 200, 340, fill=1, width=2)
            draw.arc([rx - ew, ry - 4, rx + ew, ry + 4], 200, 340, fill=1, width=2)
            return

        if style == "sad":
            draw.arc([lx - ew, ly - 3, lx + ew, ly + 3], 20, 160, fill=1, width=2)
            draw.arc([rx - ew, ry - 3, rx + ew, ry + 3], 20, 160, fill=1, width=2)
            return

        if style == "x":
            for ox, oy in [(lx, ly), (rx, ry)]:
                draw.line([ox - 4, oy - 4, ox + 4, oy + 4], fill=1, width=2)
                draw.line([ox + 4, oy - 4, ox - 4, oy + 4], fill=1, width=2)
            return

        # Ojos normales con iris, pupila y brillo
        for ox, oy in [(lx + dx, ly + dy), (rx + dx, ry + dy)]:
            # Iris (círculo blanco)
            draw.ellipse([ox - ew, oy - eh, ox + ew, oy + eh], outline=1, fill=0)
            # Pupila (relleno negro)
            draw.ellipse([ox - 2, oy - 3, ox + 2, oy + 3], fill=1)
            # Brillo
            draw.point([ox + 1, oy - 2], fill=0)

    def _mouth(self, draw, shape="smile", f=0):
        mx, my = self.CX, self.CY + 14

        if shape == "smile":
            draw.arc([mx - 9, my - 5, mx + 9, my + 5], 5, 175, fill=1, width=2)

        elif shape == "neutral":
            draw.line([mx - 7, my, mx + 7, my], fill=1, width=2)

        elif shape == "sad":
            draw.arc([mx - 9, my - 5, mx + 9, my + 5], 185, 355, fill=1, width=2)

        elif shape == "open":
            draw.ellipse([mx - 7, my - 4, mx + 7, my + 5], outline=1, fill=0)

        elif shape == "talk":
            # Alterna entre dos tamaños cada 2 frames
            if (f // 2) % 2 == 0:
                draw.ellipse([mx - 7, my - 3, mx + 7, my + 3], outline=1, fill=0)
            else:
                draw.ellipse([mx - 6, my - 5, mx + 6, my + 5], outline=1, fill=0)
                # Dientes (pequeña línea blanca)
                draw.line([mx - 4, my, mx + 4, my], fill=0, width=1)

        elif shape == "ooo":
            draw.ellipse([mx - 4, my - 6, mx + 4, my + 5], outline=1, fill=0)

    def _label(self, draw, text: str, y: int = 57):
        """Texto pequeño centrado en la parte inferior"""
        try:
            font = ImageFont.load_default()
            bbox = font.getbbox(text)
            w = bbox[2] - bbox[0]
            draw.text(((self.W - w) // 2, y), text, font=font, fill=1)
        except Exception:
            draw.text((self.W // 2 - len(text) * 3, y), text, fill=1)

    def _sound_waves(self, draw, f):
        """Ondas de sonido a los lados del rostro"""
        cx, cy = self.CX, self.CY
        beat = (f % 6)
        amps = [2, 4, 6, 4, 2]
        for i, base_amp in enumerate(amps):
            y = cy - 8 + i * 5
            a = base_amp + (2 if beat in [0, 3] else 0)
            # Derecha
            draw.line([cx + 28, y, cx + 28 + a, y], fill=1, width=1)
            # Izquierda
            draw.line([cx - 28, y, cx - 28 - a, y], fill=1, width=1)

    def _think_dots(self, draw, f):
        """Puntos de pensamiento arriba a la derecha"""
        cx, cy = self.CX, self.CY
        visible = (f // 8) % 4   # 0-3 puntos visibles
        for i in range(3):
            r = 2
            x = cx + 20 + i * 7
            y = cy - 24
            if i < visible:
                draw.ellipse([x - r, y - r, x + r, y + r], fill=1)
            else:
                draw.ellipse([x - r, y - r, x + r, y + r], outline=1)

    def _stars(self, draw, f):
        """Pequeñas estrellas parpadeantes para happy"""
        positions = [(cx, cy) for cx, cy in [(15, 10), (105, 8), (20, 50), (110, 48)]]
        for i, (x, y) in enumerate(positions):
            if (f + i * 5) % 15 < 10:
                draw.point([x, y], fill=1)
                draw.point([x + 1, y], fill=1)
                draw.point([x, y + 1], fill=1)

    # ──────────────────────────────────────────
    #  Modos de animación
    # ──────────────────────────────────────────

    def _idle(self, draw, f):
        """Cara en reposo: parpadeo cada 3 s"""
        self._face_oval(draw)
        blink = (f % 35) >= 33
        self._eyes(draw, f, blink=blink)
        self._mouth(draw, "smile", f)
        self._label(draw, "Eve")

    def _happy(self, draw, f):
        """Wake word detectado: cara feliz"""
        self._stars(draw, f)
        self._face_oval(draw)
        self._eyes(draw, f, style="happy")
        self._mouth(draw, "smile" if f % 10 < 5 else "open", f)
        self._label(draw, "Hola! :)")

    def _listening(self, draw, f):
        """Grabando voz: ojos abiertos, ondas de sonido"""
        self._face_oval(draw)
        wide = (f % 20) < 15
        self._eyes(draw, f, wide=wide)
        self._mouth(draw, "neutral", f)
        self._sound_waves(draw, f)
        self._label(draw, "Escuchando")

    def _thinking(self, draw, f):
        """Procesando: ojos mirando al costado, puntos"""
        self._face_oval(draw)
        # Mirada alternante
        phase = (f // 15) % 4
        offsets = [(2, -2), (0, -3), (-2, -2), (0, -1)]
        dx, dy = offsets[phase]
        self._eyes(draw, f, dx=dx, dy=dy)
        self._mouth(draw, "neutral", f)
        self._think_dots(draw, f)
        dots = "." * ((f // 8) % 4)
        self._label(draw, "Pensando" + dots)

    def _speaking(self, draw, f):
        """TTS activo: boca en movimiento"""
        self._face_oval(draw)
        self._eyes(draw, f)
        self._mouth(draw, "talk", f)
        # Pequeñas notas de audio
        for ox, oy in [(self.CX + 30, self.CY - 12), (self.CX - 30, self.CY - 12)]:
            if (f + ox) % 12 < 8:
                draw.text((ox - 3, oy), "♪" if hasattr(str, "encode") else "~", fill=1)
        self._label(draw, "Hablando")

    def _error(self, draw, f):
        """Error: X en los ojos, boca triste"""
        self._face_oval(draw)
        self._eyes(draw, f, style="x")
        self._mouth(draw, "sad", f)
        self._label(draw, "Error :(")

    # ──────────────────────────────────────────
    #  Limpieza
    # ──────────────────────────────────────────
    def cleanup(self):
        self._running = False
        time.sleep(0.25)
        if self.device:
            try:
                self.device.cleanup()
            except Exception:
                pass
        print("[OLED] Apagada")
