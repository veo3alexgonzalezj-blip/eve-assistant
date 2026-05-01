"""
Eve - Wake Word Detector
Detecta "Oye Eve" en tiempo real usando Vosk (STT offline).
Corre continuamente en el hilo principal sin bloquear la UI.
"""

import json
import os
import queue
import threading
import time

try:
    import pyaudio
    import vosk
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("[WakeWord] pyaudio/vosk no disponibles, modo simulado")


class WakeWordDetector:
    def __init__(self):
        from config import VOSK_MODEL_PATH, SAMPLE_RATE, CHUNK_SIZE, WAKE_WORD_VARIANTS

        self.wake_variants = WAKE_WORD_VARIANTS
        self.sample_rate = SAMPLE_RATE
        self.chunk = CHUNK_SIZE

        self._pa = None
        self._stream = None
        self._recognizer = None
        self._detected = threading.Event()
        self._running = False

        if not AUDIO_AVAILABLE:
            print("[WakeWord] Modo simulado activo")
            return

        # Verificar modelo
        if not os.path.exists(VOSK_MODEL_PATH):
            raise FileNotFoundError(
                f"\n[WakeWord] Modelo Vosk no encontrado en:\n  {VOSK_MODEL_PATH}\n"
                "Ejecuta:  bash scripts/install.sh  para descargarlo."
            )

        vosk.SetLogLevel(-1)    # Silenciar logs de Kaldi
        model = vosk.Model(VOSK_MODEL_PATH)
        self._recognizer = vosk.KaldiRecognizer(model, self.sample_rate)

        # Abrir micrófono en modo siempre-activo (pequeñas lecturas)
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=self._find_input_device(),
            frames_per_buffer=self.chunk,
        )
        print("[WakeWord] Listo — escuchando 'Oye Eve'...")

    # ──────────────────────────────────────────
    #  Búsqueda de micrófono USB
    # ──────────────────────────────────────────
    def _find_input_device(self) -> int | None:
        if not self._pa:
            return None
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                name = info["name"].lower()
                if any(k in name for k in ("usb", "micro", "mic", "capture")):
                    print(f"[WakeWord] Micrófono USB: [{i}] {info['name']}")
                    return i
        default = self._pa.get_default_input_device_info()
        print(f"[WakeWord] Usando micrófono por defecto: {default['name']}")
        return int(default["index"])

    # ──────────────────────────────────────────
    #  API principal: llamar en loop
    # ──────────────────────────────────────────
    def listen(self) -> bool:
        """
        Lee un chunk de audio y retorna True si se detectó la wake word.
        Diseñado para llamarse en un loop continuo (no bloqueante largo).
        """
        if not AUDIO_AVAILABLE or not self._stream:
            return self._simulate()

        try:
            data = self._stream.read(self.chunk, exception_on_overflow=False)
        except OSError:
            return False

        text = self._decode(data)
        if text:
            return self._match(text)
        return False

    def _decode(self, data: bytes) -> str:
        """Decodifica el chunk; retorna texto parcial o final."""
        if self._recognizer.AcceptWaveform(data):
            result = json.loads(self._recognizer.Result())
            return result.get("text", "").lower()
        else:
            partial = json.loads(self._recognizer.PartialResult())
            return partial.get("partial", "").lower()

    def _match(self, text: str) -> bool:
        for variant in self.wake_variants:
            if variant in text:
                print(f"[WakeWord] ✓ Detectado: '{text}'")
                self._recognizer.Reset()
                return True
        return False

    # ──────────────────────────────────────────
    #  Modo simulado (sin hardware)
    # ──────────────────────────────────────────
    _sim_counter = 0

    def _simulate(self) -> bool:
        self._sim_counter += 1
        if self._sim_counter % 200 == 0:   # Cada ~2 s si delay=0.01
            print("[WakeWord SIM] Wake word simulada")
            return True
        time.sleep(0.01)
        return False

    # ──────────────────────────────────────────
    #  Limpieza
    # ──────────────────────────────────────────
    def cleanup(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._pa:
            self._pa.terminate()
        print("[WakeWord] Cerrado")
