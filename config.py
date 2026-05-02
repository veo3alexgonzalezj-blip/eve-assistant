# config.py
# Configuración global del asistente Eve

# ================= HARDWARE E I2C =================
LCD_ADDRESS = 0x27
OLED_ADDRESS = 0x3C
AUDIO_RATE = 16000
CHUNK_SIZE = 4096

# ================= INTELIGENCIA ARTIFICIAL =================
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"
VOSK_MODEL_PATH = "model-es" # Asegúrate de tener la carpeta model-es aquí

# ================= LIMITES Y UMBRALES =================
MAX_CONTEXT_TOKENS = 1500  # Límite de seguridad para 8GB RAM
SILENCE_THRESHOLD = 500    # Ajustar según el ruido ambiente (Amplitud RMS)
SILENCE_DURATION = 1.8     # Segundos de silencio para dejar de grabar