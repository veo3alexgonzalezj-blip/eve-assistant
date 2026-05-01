"""
Eve - LCD 4×20 Display
Maneja la pantalla LCD 20 columnas × 4 filas via I2C (módulo PCF8574).
Conexión: SDA → GPIO2, SCL → GPIO3 — misma línea I2C que la OLED
         (dirección diferente: comúnmente 0x27 o 0x3F)
"""

import time
import threading
import textwrap

try:
    from RPLCD.i2c import CharLCD
    RPLCD_AVAILABLE = True
except ImportError:
    RPLCD_AVAILABLE = False
    print("[LCD] RPLCD no disponible, usando modo simulado")


class LCDScreen:
    COLS = 20
    ROWS = 4

    # Filas con roles fijos
    ROW_TITLE    = 0   # Título / estado
    ROW_DIVIDER  = 1   # Separador o subtítulo
    ROW_TEXT1    = 2   # Línea de texto / respuesta 1
    ROW_TEXT2    = 3   # Línea de texto / respuesta 2

    def __init__(self):
        from config import LCD_I2C_ADDRESS, LCD_I2C_PORT

        self.lcd = None
        if RPLCD_AVAILABLE:
            try:
                self.lcd = CharLCD(
                    i2c_expander="PCF8574",
                    address=LCD_I2C_ADDRESS,
                    port=LCD_I2C_PORT,
                    cols=self.COLS,
                    rows=self.ROWS,
                    charmap="A02",
                    auto_linebreaks=False,
                )
                self._define_custom_chars()
                self.lcd.clear()
                print(f"[LCD] Conectada en I2C:{LCD_I2C_ADDRESS:#x}")
            except Exception as e:
                print(f"[LCD] Error al conectar: {e}. Modo simulado.")

        # Control del scroll en segundo plano
        self._scroll_thread: threading.Thread | None = None
        self._scroll_stop = threading.Event()

        # Mutex para acceso a la pantalla
        self._lock = threading.Lock()

    # ──────────────────────────────────────────
    #  Caracteres personalizados
    # ──────────────────────────────────────────
    def _define_custom_chars(self):
        if not self.lcd:
            return
        # Char 0: flecha derecha ►
        self.lcd.create_char(0, [
            0b00000, 0b01000, 0b01100, 0b01110,
            0b01100, 0b01000, 0b00000, 0b00000
        ])
        # Char 1: barra llena █
        self.lcd.create_char(1, [
            0b11111, 0b11111, 0b11111, 0b11111,
            0b11111, 0b11111, 0b11111, 0b11111
        ])
        # Char 2: nota musical ♪
        self.lcd.create_char(2, [
            0b00100, 0b00110, 0b00101, 0b00100,
            0b01100, 0b11100, 0b11000, 0b00000
        ])

    # ──────────────────────────────────────────
    #  Helpers de escritura
    # ──────────────────────────────────────────
    def _pad(self, text: str, width: int | None = None) -> str:
        w = width or self.COLS
        return text[:w].ljust(w)

    def _write_row(self, row: int, text: str):
        """Escribe una línea en la LCD con acceso controlado."""
        if not self.lcd:
            print(f"[LCD SIM] [{row}] {self._pad(text)}")
            return
        with self._lock:
            self.lcd.cursor_pos = (row, 0)
            self.lcd.write_string(self._pad(text))

    def _center(self, text: str) -> str:
        return text[:self.COLS].center(self.COLS)

    # ──────────────────────────────────────────
    #  API pública
    # ──────────────────────────────────────────
    def show_status(self, title: str, subtitle: str = "", detail: str = ""):
        """
        Muestra un estado en la pantalla.
        Fila 0: título  |  Fila 1: ─── separador ───
        Fila 2: subtitle|  Fila 3: detail
        """
        self._stop_scroll()

        # Construir línea divisora con título incrustado
        if len(title) <= 16:
            divider = f"--[ {title[:14]} ]--".center(self.COLS, "-")[:self.COLS]
        else:
            divider = "-" * self.COLS

        self._write_row(self.ROW_TITLE,   self._center(f"* Eve *"))
        self._write_row(self.ROW_DIVIDER, divider)
        self._write_row(self.ROW_TEXT1,   self._pad(subtitle))
        self._write_row(self.ROW_TEXT2,   self._pad(detail))

    def show_user_text(self, text: str):
        """Muestra el texto reconocido del usuario en la LCD."""
        self._stop_scroll()
        tu = "Tu: " + text
        lines = textwrap.wrap(tu, self.COLS)
        self._write_row(self.ROW_TITLE,   self._center("* Eve *"))
        self._write_row(self.ROW_DIVIDER, self._pad("--[ Tu pregunta ]---"))
        self._write_row(self.ROW_TEXT1,   self._pad(lines[0] if len(lines) > 0 else ""))
        self._write_row(self.ROW_TEXT2,   self._pad(lines[1] if len(lines) > 1 else ""))

    def scroll_response(self, text: str, words_per_screen: float = 2.8):
        """
        Muestra la respuesta completa en scroll paginado.
        Filas 0-1 fijas como cabecera; filas 2-3 para el texto.
        words_per_screen: segundos entre páginas (ajustar para lectura cómoda).
        """
        self._stop_scroll()

        # Cabecera fija
        self._write_row(self.ROW_TITLE,   self._center("* Eve dice *"))
        self._write_row(self.ROW_DIVIDER, "-" * self.COLS)

        # Construir páginas: cada página = 2 filas de COLS chars
        pages = self._build_pages(text)

        self._scroll_stop.clear()
        self._scroll_thread = threading.Thread(
            target=self._scroll_worker,
            args=(pages, words_per_screen),
            daemon=True,
        )
        self._scroll_thread.start()

    def wait_scroll_done(self):
        """Bloquea hasta que el scroll termine."""
        if self._scroll_thread and self._scroll_thread.is_alive():
            self._scroll_thread.join()

    # ──────────────────────────────────────────
    #  Scroll interno
    # ──────────────────────────────────────────
    def _build_pages(self, text: str) -> list[tuple[str, str]]:
        """Divide el texto en páginas de 2 filas × 20 columnas."""
        # Word-wrap a 20 caracteres
        wrapped_lines = []
        for raw_line in text.replace("\n", " ").split("  "):
            for wl in textwrap.wrap(raw_line.strip(), self.COLS) or [""]:
                wrapped_lines.append(wl)

        if not wrapped_lines:
            wrapped_lines = [""]

        # Agrupar de 2 en 2
        pages = []
        for i in range(0, len(wrapped_lines), 2):
            l1 = wrapped_lines[i]     if i     < len(wrapped_lines) else ""
            l2 = wrapped_lines[i + 1] if i + 1 < len(wrapped_lines) else ""
            pages.append((l1, l2))

        return pages

    def _scroll_worker(self, pages: list[tuple[str, str]], delay: float):
        total = len(pages)
        for idx, (l1, l2) in enumerate(pages):
            if self._scroll_stop.is_set():
                break

            # Indicador de página
            page_info = f"{idx + 1}/{total}"
            l1_display = l1[:self.COLS - len(page_info) - 1] + " " + page_info \
                         if idx == 0 and total > 1 else l1

            self._write_row(self.ROW_TEXT1, self._pad(l1_display))
            self._write_row(self.ROW_TEXT2, self._pad(l2))

            # Calcular demora basada en palabras en la página
            words = len((l1 + " " + l2).split())
            wait = max(1.8, words * delay * 0.6)

            self._scroll_stop.wait(timeout=wait)

        if not self._scroll_stop.is_set():
            # Fin del mensaje
            self._write_row(self.ROW_TEXT1, self._center(""))
            self._write_row(self.ROW_TEXT2, self._pad("[ Fin ]".center(self.COLS)))

    def _stop_scroll(self):
        self._scroll_stop.set()
        if self._scroll_thread and self._scroll_thread.is_alive():
            self._scroll_thread.join(timeout=1.5)
        self._scroll_thread = None

    # ──────────────────────────────────────────
    #  Animación de carga (progreso)
    # ──────────────────────────────────────────
    def show_progress(self, label: str, pct: int):
        """
        Muestra una barra de progreso.
        pct: 0-100
        """
        self._stop_scroll()
        filled = int(self.COLS * pct / 100)
        bar = "\xff" * filled + " " * (self.COLS - filled)   # chr(0xFF) = bloque lleno
        self._write_row(self.ROW_TITLE,   self._center(label))
        self._write_row(self.ROW_DIVIDER, bar)
        self._write_row(self.ROW_TEXT1,   self._center(f"{pct}%"))
        self._write_row(self.ROW_TEXT2,   "")

    # ──────────────────────────────────────────
    #  Limpieza
    # ──────────────────────────────────────────
    def cleanup(self):
        self._stop_scroll()
        if self.lcd:
            try:
                self.lcd.clear()
                self.lcd.close(clear=True)
            except Exception:
                pass
        print("[LCD] Apagada")
