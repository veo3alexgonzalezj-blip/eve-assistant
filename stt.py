"""
Eve - Speech To Text (Vosk offline)
Transcribe audio WAV a texto usando el modelo español de Vosk.
"""

import io
import json
import os
import wave

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("[STT] Vosk no disponible, modo simulado")


class SpeechToText:
    def __init__(self):
        from config import VOSK_MODEL_PATH, SAMPLE_RATE

        self.sample_rate = SAMPLE_RATE
        self._recognizer = None

        if not VOSK_AVAILABLE:
            print("[STT] Modo simulado activo")
            return

        if not os.path.exists(VOSK_MODEL_PATH):
            raise FileNotFoundError(
                f"\n[STT] Modelo Vosk no encontrado en:\n  {VOSK_MODEL_PATH}\n"
                "Ejecuta:  bash scripts/install.sh"
            )

        vosk.SetLogLevel(-1)
        model = vosk.Model(VOSK_MODEL_PATH)
        self._recognizer = vosk.KaldiRecognizer(model, self.sample_rate)
        self._recognizer.SetWords(True)
        print("[STT] Listo con modelo español")

    # ──────────────────────────────────────────
    #  API principal
    # ──────────────────────────────────────────
    def transcribe(self, wav_bytes: bytes) -> str:
        """
        Transcribe audio WAV (bytes) a texto.
        Retorna string vacío si no se reconoció nada.
        """
        if not VOSK_AVAILABLE or not self._recognizer:
            return self._simulate()

        self._recognizer.Reset()

        wav_io = io.BytesIO(wav_bytes)
        try:
            with wave.open(wav_io, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                    print("[STT] Advertencia: formato de audio inesperado")

                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    self._recognizer.AcceptWaveform(data)

            result = json.loads(self._recognizer.FinalResult())
            text = result.get("text", "").strip()

        except Exception as e:
            print(f"[STT] Error al transcribir: {e}")
            return ""

        print(f"[STT] '{text}'")
        return text

    def _simulate(self) -> str:
        import time
        time.sleep(0.5)
        demo = "¿cuál es la capital de Colombia?"
        print(f"[STT SIM] '{demo}'")
        return demo
