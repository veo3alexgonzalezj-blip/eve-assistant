"""
Eve - Asistente de Voz
Archivo de configuración central
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
#  PANTALLAS
# ─────────────────────────────────────────────
OLED_WIDTH       = 128
OLED_HEIGHT      = 64
OLED_I2C_PORT    = 1
OLED_I2C_ADDRESS = 0x3C   # Usar: sudo i2cdetect -y 1

LCD_ROWS         = 4
LCD_COLS         = 20
LCD_I2C_ADDRESS  = 0x27   # Dirección PCF8574 (verificar con i2cdetect)
LCD_I2C_PORT     = 1

# ─────────────────────────────────────────────
#  AUDIO
# ─────────────────────────────────────────────
SAMPLE_RATE    = 16000
CHUNK_SIZE     = 4000
CHANNELS       = 1

# Umbral de silencio (ajustar según el ruido ambiente; más alto = menos sensible)
SILENCE_THRESHOLD  = 400
SILENCE_DURATION   = 1.8    # segundos de silencio para cortar la grabación
MAX_RECORD_SECONDS = 12     # máximo de grabación por turno

# ─────────────────────────────────────────────
#  WAKE WORD
# ─────────────────────────────────────────────
WAKE_WORD = "oye eve"
WAKE_WORD_VARIANTS = [
    "oye eve", "oye eb", "oi eve", "oy eve",
    "hey eve", "hola eve", "oye ebe",
]

# ─────────────────────────────────────────────
#  MODELOS DE VOZ (VOSK - STT offline)
# ─────────────────────────────────────────────
VOSK_MODEL_PATH = os.path.join(BASE_DIR, "models", "vosk-model-small-es")

# ─────────────────────────────────────────────
#  TTS (Text-to-Speech)
# ─────────────────────────────────────────────
# Opción 1: Piper (alta calidad, natural)
PIPER_BINARY     = "piper"
PIPER_MODEL_PATH = os.path.join(BASE_DIR, "models", "es_ES-davefx-medium.onnx")
PIPER_CONFIG     = os.path.join(BASE_DIR, "models", "es_ES-davefx-medium.onnx.json")

# Opción 2: eSpeak-NG (fallback, robótico pero funcional)
ESPEAK_VOICE = "es"
ESPEAK_SPEED = 148
ESPEAK_PITCH = 58

# ─────────────────────────────────────────────
#  OLLAMA / IA LOCAL
# ─────────────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"

# ┌─────────────────────────────────────────────────────────────────┐
# │  MODELO RECOMENDADO para RPi 4 con 8 GB de RAM:                 │
# │                                                                   │
# │  ► llama3.2:3b  ← RECOMENDADO (2 GB, rápido, buen español)     │
# │    Velocidad: ~8-12 tok/s en RPi 4                               │
# │    Calidad: muy buena para conversación cotidiana                │
# │                                                                   │
# │  ► phi3.5:mini  (2.2 GB, excelente razonamiento, rápido)        │
# │  ► gemma2:2b    (1.5 GB, el más rápido, español decente)        │
# │  ► mistral:7b-instruct-q4_0  (4 GB, más calidad, más lento)    │
# └─────────────────────────────────────────────────────────────────┘
OLLAMA_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "Eres Eve, una asistente de voz amigable, inteligente y curiosa. "
    "Hablas exclusivamente en español, de forma natural y conversacional. "
    "Tus respuestas son concisas (máximo 3-4 oraciones) porque serán leídas "
    "en voz alta. No uses markdown, asteriscos, numeraciones ni caracteres especiales. "
    "Solo texto plano y claro. Si no sabes algo, lo dices con honestidad."
)

OLLAMA_OPTIONS = {
    "temperature": 0.75,
    "num_predict": 220,     # Limita tokens para respuestas más rápidas
    "top_p": 0.9,
    "repeat_penalty": 1.1,
}

# Máximo de turnos de conversación que se mantienen en memoria
MAX_HISTORY_TURNS = 6
