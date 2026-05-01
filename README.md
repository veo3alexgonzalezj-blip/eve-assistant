# Eve — Asistente de Voz para Raspberry Pi 4

> Di **"Oye Eve"** y conversa con una IA local. Sin internet. Sin nube.

---

## Hardware necesario

| Componente | Conexión |
|---|---|
| Raspberry Pi 4 (8 GB) | — |
| OLED 0.96" SSD1306 | I2C: SDA→GPIO2, SCL→GPIO3 |
| LCD 4×20 con PCF8574 | I2C: SDA→GPIO2, SCL→GPIO3 |
| Micrófono USB | Puerto USB cualquiera |
| Altavoz pequeño | Jack 3.5mm o USB audio |

> La OLED y la LCD comparten el bus I2C. Asegúrate de que tengan **direcciones distintas**:
> - OLED: `0x3C` (por defecto)
> - LCD: `0x27` o `0x3F` (según tu módulo PCF8574)

---

## Diagrama de conexión I2C

```
RPi GPIO2 (SDA) ──┬──── OLED SDA
                  └──── LCD SDA

RPi GPIO3 (SCL) ──┬──── OLED SCL
                  └──── LCD SCL

RPi 3.3V ─────── OLED VCC
RPi 5V ────────── LCD VCC  ← La LCD necesita 5V
RPi GND ──────── OLED GND + LCD GND
```

---

## Modelo de IA recomendado

Para una **Raspberry Pi 4 con 8 GB de RAM**, la mejor opción es:

### ★ `llama3.2:3b` (Recomendado)

| Característica | Valor |
|---|---|
| Tamaño en RAM | ~2.0 GB (Q4) |
| Velocidad en RPi 4 | ~8-12 tokens/segundo |
| Calidad en español | ⭐⭐⭐⭐ |
| Tiempo de respuesta | 3-8 segundos |

**¿Por qué este modelo?**
- Lanza Meta en 2024, entrenado con datos multilingüe de alta calidad
- El cuantizado Q4 cabe holgado en 8 GB (sobran ~5 GB para el OS y los modelos de voz)
- Excelente comprensión del español latinoamericano
- Respuestas coherentes y naturales para conversación cotidiana

**Alternativas:**
- `phi3.5:mini` → si quieres algo más rápido y tienes preguntas técnicas
- `gemma2:2b` → si necesitas la mayor velocidad posible
- `mistral:7b-instruct-q4_0` → si prefieres más calidad aunque tarde más

---

## Instalación paso a paso

### 1. Clonar el proyecto
```bash
git clone https://github.com/tu-usuario/eve-assistant.git
cd eve-assistant
```

### 2. Ejecutar instalador
```bash
chmod +x scripts/install.sh
bash scripts/install.sh
```
Esto instala: dependencias del sistema, Python venv, Vosk (STT), Piper TTS y Ollama.

### 3. Descargar modelo IA
```bash
bash scripts/setup_model.sh
```
Selecciona el modelo. Se descarga y configura automáticamente.

### 4. Verificar hardware
```bash
source venv/bin/activate
python scripts/test_hardware.py
```

### 5. Iniciar Eve
```bash
# Terminal 1: iniciar Ollama
ollama serve

# Terminal 2: iniciar Eve
source venv/bin/activate
python main.py
```

---

## Estructura del proyecto

```
eve/
├── main.py               ← Punto de entrada, máquina de estados
├── config.py             ← Toda la configuración (editar aquí)
│
├── display/
│   ├── oled_face.py      ← Animaciones de cara en OLED 128×64
│   └── lcd_screen.py     ← Mensajes y scroll en LCD 4×20
│
├── audio/
│   ├── wakeword.py       ← Detección de "Oye Eve" (Vosk)
│   ├── recorder.py       ← Grabación con VAD (detección de silencio)
│   ├── stt.py            ← Transcripción de voz a texto
│   └── tts.py            ← Síntesis de voz (Piper / eSpeak)
│
├── ai/
│   └── brain.py          ← Cliente Ollama con historial
│
├── models/               ← Se crean al instalar
│   ├── vosk-model-small-es/
│   ├── es_ES-davefx-medium.onnx
│   └── piper/
│
└── scripts/
    ├── install.sh         ← Instalador completo
    ├── setup_model.sh     ← Descarga modelo Ollama
    ├── create_service.sh  ← Servicio systemd (arranque automático)
    └── test_hardware.py   ← Diagnóstico de hardware
```

---

## Estados de Eve

| Estado | OLED | LCD |
|---|---|---|
| **Reposo** | Cara con parpadeo suave | "Eve — Di 'Oye Eve'" |
| **Activada** | Cara feliz con estrellas | "¡Hola! — Te escucho..." |
| **Escuchando** | Ojos abiertos + ondas de sonido | "Escuchando — Habla ahora..." |
| **Pensando** | Ojos moviéndose + puntos animados | "Pensando..." |
| **Hablando** | Boca moviéndose | Respuesta en scroll 2 filas |
| **Error** | X en ojos, boca triste | "Error — Intenta de nuevo" |

---

## Configuración avanzada (config.py)

```python
# Cambiar modelo IA
OLLAMA_MODEL = "llama3.2:3b"

# Ajustar sensibilidad del micrófono
SILENCE_THRESHOLD = 400    # Subir si hay mucho ruido ambiente

# Cambiar wake word (variantes que acepta)
WAKE_WORD_VARIANTS = ["oye eve", "hey eve", "hola eve"]

# Personalidad de Eve
SYSTEM_PROMPT = "Eres Eve, una asistente..."
```

---

## Solución de problemas

**Eve no detecta la wake word**
- Verifica el micrófono: `arecord -l`
- Ajusta `SILENCE_THRESHOLD` en config.py (más alto = menos sensible)
- Habla más cerca y claro: "**Oye Eve**"

**La OLED no muestra nada**
- `sudo i2cdetect -y 1` — ¿aparece `3c`?
- Revisa conexiones SDA/SCL/VCC/GND
- Verifica `OLED_I2C_ADDRESS` en config.py

**La LCD no muestra nada**
- `sudo i2cdetect -y 1` — ¿aparece `27` o `3f`?
- Ajusta el contraste con el potenciómetro del módulo PCF8574
- Verifica `LCD_I2C_ADDRESS` en config.py

**Ollama responde muy lento**
- Usa un modelo más pequeño: `gemma2:2b`
- Asegúrate de usar la SD más rápida posible o un SSD USB

**No hay sonido**
- `aplay -l` — lista dispositivos de salida
- `alsamixer` — sube el volumen
- Prueba: `espeak-ng -v es "Hola mundo"`

---

## Autoarranque al encender

```bash
bash scripts/create_service.sh

# Controlar el servicio:
sudo systemctl start eve
sudo systemctl stop eve
sudo journalctl -u eve -f    # Ver logs en vivo
```

---

## Créditos de componentes

- **STT:** [Vosk](https://alphacephei.com/vosk/) con modelo español (~50 MB)
- **LLM:** [Ollama](https://ollama.ai) + LLaMA 3.2 / Phi 3.5
- **TTS:** [Piper](https://github.com/rhasspy/piper) con voz `es_ES-davefx`
- **OLED:** [luma.oled](https://luma-oled.readthedocs.io/)
- **LCD:** [RPLCD](https://rplcd.readthedocs.io/)
