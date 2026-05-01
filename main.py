"""
Eve - Asistente de Voz
Punto de entrada principal. Máquina de estados que coordina
  OLED, LCD, detección de wake word, STT, TTS y el modelo IA.

Uso:
  python main.py
  python main.py --debug     (más verbose)
  python main.py --simulate  (sin hardware, para pruebas)
"""

import argparse
import signal
import sys
import time
from enum import Enum, auto

from display.oled_face import OLEDFace
from display.lcd_screen import LCDScreen
from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.stt import SpeechToText
from audio.tts import TextToSpeech
from ai.brain import Brain


# ──────────────────────────────────────────────
#  Estados de la máquina
# ──────────────────────────────────────────────
class State(Enum):
    BOOT      = auto()
    IDLE      = auto()
    LISTENING = auto()
    THINKING  = auto()
    SPEAKING  = auto()
    ERROR     = auto()


# Mapa estado → (modo_oled, título_lcd, subtítulo_lcd)
STATE_META = {
    State.BOOT:      ("idle",          "Iniciando",   "Por favor espera..."),
    State.IDLE:      ("idle",          "Eve",         "Di 'Oye Eve'"),
    State.LISTENING: ("listening",     "Escuchando",  "Habla ahora..."),
    State.THINKING:  ("thinking",      "Pensando",    "Un momento..."),
    State.SPEAKING:  ("speaking",      "Eve dice:",   ""),
    State.ERROR:     ("error",         "Error",       "Intenta de nuevo"),
}


# ──────────────────────────────────────────────
#  Asistente principal
# ──────────────────────────────────────────────
class EveAssistant:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._state = State.BOOT
        self._running = False

        self._log("Iniciando Eve...")

        # ── Pantallas ──
        self.oled = OLEDFace()
        self.lcd  = LCDScreen()
        self._set_state(State.BOOT)

        # ── Audio ──
        self.recorder = AudioRecorder()
        self.wakeword = WakeWordDetector()
        self.stt      = SpeechToText()
        self.tts      = TextToSpeech()

        # ── IA ──
        self.brain = Brain()

        self._log("Eve lista.")

    # ──────────────────────────────────────────
    #  Máquina de estados
    # ──────────────────────────────────────────
    def _set_state(self, state: State):
        self._state = state
        oled_mode, lcd_title, lcd_sub = STATE_META[state]
        self.oled.set_mode(oled_mode)
        self.lcd.show_status(lcd_title, lcd_sub)
        self._log(f"Estado: {state.name}")

    # ──────────────────────────────────────────
    #  Loop principal
    # ──────────────────────────────────────────
    def run(self):
        self._running = True
        self._set_state(State.IDLE)

        print("\n" + "─" * 50)
        print("  Eve está escuchando. Di 'Oye Eve'.")
        print("  Ctrl+C para salir.")
        print("─" * 50 + "\n")

        try:
            while self._running:
                # Escuchar wake word (no bloqueante por mucho tiempo)
                if self.wakeword.listen():
                    self._handle_conversation()

        except KeyboardInterrupt:
            print("\n[Main] Cerrando Eve...")
        finally:
            self._cleanup()

    # ──────────────────────────────────────────
    #  Flujo de conversación
    # ──────────────────────────────────────────
    def _handle_conversation(self):
        try:
            # 1. Confirmar activación
            self.oled.set_mode("wake_detected")
            self.lcd.show_status("¡Hola!", "Te escucho...")
            self.tts.speak("Dime.", block=True)

            # 2. Grabar pregunta
            self._set_state(State.LISTENING)
            wav_bytes = self.recorder.record_utterance()

            if not wav_bytes:
                self.tts.speak("No te escuché. Inténtalo de nuevo.")
                self._set_state(State.IDLE)
                return

            # 3. Transcribir
            question = self.stt.transcribe(wav_bytes)

            if not question or len(question.strip()) < 3:
                self.tts.speak("No entendí bien. ¿Puedes repetirlo?")
                self._set_state(State.IDLE)
                return

            # Mostrar lo que escuchó
            self.lcd.show_user_text(question)
            self._log(f"Pregunta: {question}")

            # 4. Consultar IA
            self._set_state(State.THINKING)
            answer = self.brain.ask(question)
            self._log(f"Respuesta: {answer[:100]}...")

            # 5. Mostrar y hablar respuesta
            self._set_state(State.SPEAKING)
            self.lcd.scroll_response(answer)   # Arranca scroll en segundo plano
            self.tts.speak(answer, block=True)  # Habla (bloquea hasta terminar)
            self.lcd.wait_scroll_done()         # Espera que el scroll termine

        except Exception as e:
            print(f"[Main] Error en conversación: {e}")
            self._set_state(State.ERROR)
            time.sleep(2)

        finally:
            self._set_state(State.IDLE)

    # ──────────────────────────────────────────
    #  Limpieza
    # ──────────────────────────────────────────
    def _cleanup(self):
        self._running = False
        self.oled.cleanup()
        self.lcd.cleanup()
        self.wakeword.cleanup()
        self.recorder.cleanup()
        print("[Main] Eve apagada. ¡Hasta pronto!")

    # ──────────────────────────────────────────
    #  Utilidades
    # ──────────────────────────────────────────
    def _log(self, msg: str):
        if self.debug:
            print(f"[DEBUG] {msg}")
        else:
            print(msg)


# ──────────────────────────────────────────────
#  Manejo de señales del sistema
# ──────────────────────────────────────────────
def _handle_signal(sig, frame):
    print("\n[Main] Señal recibida, cerrando...")
    sys.exit(0)


# ──────────────────────────────────────────────
#  Punto de entrada
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Eve — Asistente de Voz")
    parser.add_argument("--debug", action="store_true", help="Modo verbose")
    args = parser.parse_args()

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    eve = EveAssistant(debug=args.debug)
    eve.run()


if __name__ == "__main__":
    main()
