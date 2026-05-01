"""
Eve - Text To Speech
Sintetiza voz en español.
  Prioridad 1 → Piper TTS    (alta calidad, offline)
  Prioridad 2 → eSpeak-NG   (robótico pero confiable)
  Fallback    → Imprime en consola
"""

import os
import subprocess
import tempfile
import threading


class TextToSpeech:
    def __init__(self):
        self._engine = self._detect_engine()
        print(f"[TTS] Motor activo: {self._engine}")
        self._lock = threading.Lock()   # Evita hablar en paralelo

    # ──────────────────────────────────────────
    #  Detección de motor disponible
    # ──────────────────────────────────────────
    def _detect_engine(self) -> str:
        # 1. Piper
        try:
            r = subprocess.run(["piper", "--version"],
                               capture_output=True, timeout=3)
            if r.returncode == 0:
                from config import PIPER_MODEL_PATH
                if os.path.exists(PIPER_MODEL_PATH):
                    return "piper"
                else:
                    print(f"[TTS] Piper encontrado pero falta el modelo: {PIPER_MODEL_PATH}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 2. eSpeak-NG
        try:
            subprocess.run(["espeak-ng", "--version"],
                           capture_output=True, check=True, timeout=3)
            return "espeak"
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            pass

        return "none"

    # ──────────────────────────────────────────
    #  API principal
    # ──────────────────────────────────────────
    def speak(self, text: str, block: bool = True):
        """
        Sintetiza y reproduce texto.
        block=True → espera a que termine antes de retornar.
        """
        if not text or not text.strip():
            return

        text = self._sanitize(text)
        print(f"[TTS] → {text[:80]}{'...' if len(text)>80 else ''}")

        if block:
            self._say(text)
        else:
            t = threading.Thread(target=self._say, args=(text,), daemon=True)
            t.start()

    def _say(self, text: str):
        with self._lock:
            if self._engine == "piper":
                self._speak_piper(text)
            elif self._engine == "espeak":
                self._speak_espeak(text)
            else:
                # Solo consola
                print(f"[TTS CONSOLA] {text}")

    # ──────────────────────────────────────────
    #  Motores
    # ──────────────────────────────────────────
    def _speak_piper(self, text: str):
        from config import PIPER_MODEL_PATH, PIPER_CONFIG

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        try:
            cmd = [
                "piper",
                "--model",       PIPER_MODEL_PATH,
                "--config",      PIPER_CONFIG,
                "--output_file", wav_path,
                "--sentence_silence", "0.15",
            ]
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                print(f"[TTS] Piper error: {proc.stderr.decode()[:200]}")
                self._speak_espeak(text)   # Fallback
                return

            # Reproducir con aplay (ALSA)
            subprocess.run(
                ["aplay", "-q", wav_path],
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            print("[TTS] Timeout en Piper")
        except Exception as e:
            print(f"[TTS] Error Piper: {e}")
            self._speak_espeak(text)
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    def _speak_espeak(self, text: str):
        from config import ESPEAK_VOICE, ESPEAK_SPEED, ESPEAK_PITCH

        try:
            subprocess.run(
                [
                    "espeak-ng",
                    "-v", ESPEAK_VOICE,
                    "-s", str(ESPEAK_SPEED),
                    "-p", str(ESPEAK_PITCH),
                    "-a", "160",
                    "--stdout",
                    text,
                ],
                # Pasar stdout a aplay para evitar archivos temporales
                stdout=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            # En RPi, espeak-ng por defecto usa ALSA directamente
            subprocess.run(
                ["espeak-ng",
                 "-v", ESPEAK_VOICE,
                 "-s", str(ESPEAK_SPEED),
                 "-p", str(ESPEAK_PITCH),
                 "-a", "160",
                 text],
                capture_output=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("[TTS] Timeout en eSpeak")
        except Exception as e:
            print(f"[TTS] Error eSpeak: {e}")

    # ──────────────────────────────────────────
    #  Utilidades
    # ──────────────────────────────────────────
    def _sanitize(self, text: str) -> str:
        """Elimina caracteres que pueden confundir al TTS."""
        import re
        # Markdown y símbolos
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"#+\s*", "", text)
        text = re.sub(r"`+", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Múltiples espacios / saltos
        text = re.sub(r"\s+", " ", text)
        return text.strip()
