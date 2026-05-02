# audio_handler.py
import json
import time
import math
import struct
import pyaudio
import subprocess
from vosk import Model, KaldiRecognizer
from config import VOSK_MODEL_PATH, AUDIO_RATE, CHUNK_SIZE, SILENCE_THRESHOLD, SILENCE_DURATION

class AudioIO:
    def __init__(self):
        self.model = Model(VOSK_MODEL_PATH)
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=AUDIO_RATE, input=True, frames_per_buffer=CHUNK_SIZE)
        self.stream.start_stream()
        
        # Variables TTS
        self._tts_process = None
        self.is_speaking = False

    def _rms(self, data):
        """Calcula la amplitud RMS para detectar silencios."""
        count = len(data) / 2
        format = "%dh" % (count)
        shorts = struct.unpack(format, data)
        sum_squares = 0.0
        for sample in shorts:
            n = sample * (1.0/32768.0)
            sum_squares += n * n
        return math.sqrt(sum_squares / count) * 32768

    def listen_wakeword(self) -> bool:
        """Escucha de forma continua hasta detectar 'oye eve'."""
        rec = KaldiRecognizer(self.model, AUDIO_RATE)
        while True:
            data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                if "oye eve" in res.get("text", "").lower():
                    return True

    def record_command(self) -> str:
        """Graba hasta detectar un silencio prolongado y devuelve el texto."""
        rec = KaldiRecognizer(self.model, AUDIO_RATE)
        silence_start = None
        
        while True:
            data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
            rms_value = self._rms(data)
            
            if rec.AcceptWaveform(data):
                # Si reconoció algo completo, cortamos
                break
                
            if rms_value < SILENCE_THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    break # Silencio detectado, dejamos de escuchar
            else:
                silence_start = None # Reinicia el contador si hay ruido

        res = json.loads(rec.FinalResult())
        return res.get("text", "")

    def speak(self, text: str):
        """Reproduce voz usando espeak de forma no bloqueante."""
        self.is_speaking = True
        # Usamos espeak de Linux, puedes cambiar "es" por tu variante
        self._tts_process = subprocess.Popen(
            ["espeak", "-ves", text],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )

    def stop_speaking(self):
        """Mata el proceso de audio (Barge-in)."""
        if self._tts_process and self._tts_process.poll() is None:
            self._tts_process.terminate()
        self.is_speaking = False