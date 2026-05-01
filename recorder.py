"""
Eve - Grabador de Audio con VAD
Graba hasta que detecta silencio (Voice Activity Detection simple).
"""

import io
import time
import wave

try:
    import numpy as np
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("[Recorder] pyaudio/numpy no disponibles, modo simulado")


class AudioRecorder:
    def __init__(self):
        from config import (
            SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD,
            SILENCE_DURATION, MAX_RECORD_SECONDS
        )

        self.rate     = SAMPLE_RATE
        self.channels = CHANNELS
        self.fmt      = pyaudio.paInt16 if AUDIO_AVAILABLE else None
        self.silence_threshold = SILENCE_THRESHOLD
        self.silence_duration  = SILENCE_DURATION
        self.max_seconds       = MAX_RECORD_SECONDS

        self._pa = None
        if AUDIO_AVAILABLE:
            self._pa = pyaudio.PyAudio()
            self._device = self._find_input_device()

    def _find_input_device(self) -> int | None:
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                name = info["name"].lower()
                if any(k in name for k in ("usb", "micro", "mic", "capture")):
                    return i
        return int(self._pa.get_default_input_device_info()["index"])

    # ──────────────────────────────────────────
    #  Grabación con VAD
    # ──────────────────────────────────────────
    def record_utterance(self) -> bytes | None:
        """
        Graba audio desde el micrófono.
        Empieza a contar silencio sólo después de detectar voz.
        Retorna bytes WAV o None si no hubo voz.
        """
        if not AUDIO_AVAILABLE:
            return self._simulate_audio()

        chunk = 1024
        stream = self._pa.open(
            format=self.fmt,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self._device,
            frames_per_buffer=chunk,
        )

        frames = []
        voice_started = False
        silent_chunks = 0
        start = time.time()

        # Cuántos chunks de silencio equivalen a silence_duration segundos
        silence_limit = int(self.rate / chunk * self.silence_duration)
        max_chunks    = int(self.rate / chunk * self.max_seconds)

        print("[Recorder] Grabando...")

        try:
            while True:
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)

                # Calcular amplitud RMS del chunk
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(audio_np ** 2)))

                if rms > self.silence_threshold:
                    voice_started = True
                    silent_chunks = 0
                elif voice_started:
                    silent_chunks += 1

                # Condiciones de corte
                if voice_started and silent_chunks >= silence_limit:
                    print(f"[Recorder] Silencio detectado — fin de habla")
                    break
                if len(frames) >= max_chunks:
                    print(f"[Recorder] Tiempo máximo alcanzado")
                    break
        finally:
            stream.stop_stream()
            stream.close()

        if not voice_started:
            print("[Recorder] No se detectó voz")
            return None

        return self._to_wav(frames)

    def _to_wav(self, frames: list[bytes]) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self._pa.get_sample_size(self.fmt))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    # ──────────────────────────────────────────
    #  Simulación
    # ──────────────────────────────────────────
    def _simulate_audio(self) -> bytes | None:
        print("[Recorder SIM] Simulando grabación...")
        time.sleep(2)
        # Genera WAV silencioso de 2 s
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 16000 * 2 * 2)
        return buf.getvalue()

    # ──────────────────────────────────────────
    #  Limpieza
    # ──────────────────────────────────────────
    def cleanup(self):
        if self._pa:
            self._pa.terminate()
        print("[Recorder] Cerrado")
