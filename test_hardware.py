#!/usr/bin/env python3
"""
test_hardware.py — Diagnóstico de hardware de Eve
Ejecutar antes de iniciar Eve por primera vez para verificar
que todos los componentes están bien conectados.

Uso: python scripts/test_hardware.py
"""

import sys
import time

PASS  = "✅"
FAIL  = "❌"
WARN  = "⚠️ "
INFO  = "ℹ️ "

results = []

def ok(name, msg=""):
    results.append((True, name, msg))
    print(f"  {PASS} {name}  {msg}")

def fail(name, msg=""):
    results.append((False, name, msg))
    print(f"  {FAIL} {name}  {msg}")

def info(msg):
    print(f"  {INFO} {msg}")


print("\n━━━ Eve — Test de Hardware ━━━\n")

# ─────────────────────────────────────────────
print("1. Librerías Python")
# ─────────────────────────────────────────────
for lib, pkg in [
    ("vosk",      "vosk"),
    ("pyaudio",   "PyAudio"),
    ("numpy",     "numpy"),
    ("Pillow",    "Pillow"),
    ("luma.oled", "luma.oled"),
    ("RPLCD",     "RPLCD"),
    ("requests",  "requests"),
]:
    try:
        __import__(lib.replace("-", "_").split(".")[0])
        ok(f"Librería {pkg}")
    except ImportError:
        fail(f"Librería {pkg}", "→ pip install " + pkg)

# ─────────────────────────────────────────────
print("\n2. I2C — Dispositivos")
# ─────────────────────────────────────────────
import subprocess
try:
    result = subprocess.run(
        ["i2cdetect", "-y", "1"],
        capture_output=True, text=True, timeout=5
    )
    output = result.stdout
    print(output)

    found_addrs = []
    for line in output.splitlines():
        parts = line.split()
        if parts and parts[0].endswith(":"):
            for p in parts[1:]:
                if p != "--" and len(p) == 2:
                    found_addrs.append(int(p, 16))

    if 0x3C in found_addrs:
        ok("OLED SSD1306", f"en 0x3C")
    elif 0x3D in found_addrs:
        ok("OLED SSD1306", f"en 0x3D (actualiza OLED_I2C_ADDRESS en config.py)")
    else:
        fail("OLED SSD1306", "No detectada — verifica SDA/SCL y alimentación")

    if 0x27 in found_addrs:
        ok("LCD PCF8574", "en 0x27")
    elif 0x3F in found_addrs:
        ok("LCD PCF8574", "en 0x3F (actualiza LCD_I2C_ADDRESS en config.py)")
    else:
        fail("LCD PCF8574", "No detectada — verifica SDA/SCL y alimentación")

except FileNotFoundError:
    fail("i2cdetect", "No instalado o I2C no habilitado — ejecuta install.sh")
except Exception as e:
    fail("I2C detect", str(e))

# ─────────────────────────────────────────────
print("\n3. Audio — Micrófono USB")
# ─────────────────────────────────────────────
try:
    import pyaudio
    pa = pyaudio.PyAudio()
    usb_found = False
    print("  Dispositivos de entrada disponibles:")
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if d["maxInputChannels"] > 0:
            name = d["name"]
            print(f"    [{i}] {name}")
            if any(k in name.lower() for k in ("usb", "micro", "mic")):
                usb_found = True
                ok(f"Micrófono USB", f"[{i}] {name}")

    if not usb_found:
        warn = True
        print(f"  {WARN} No se detectó micrófono USB específico. Verifica conexión.")
    pa.terminate()
except Exception as e:
    fail("PyAudio", str(e))

# ─────────────────────────────────────────────
print("\n4. Audio — Altavoz / Salida")
# ─────────────────────────────────────────────
try:
    result = subprocess.run(
        ["aplay", "-l"],
        capture_output=True, text=True, timeout=5
    )
    if "card" in result.stdout:
        ok("ALSA audio", "Dispositivos de salida detectados")
        # Prueba de sonido (tono breve)
        try:
            subprocess.run(
                ["speaker-test", "-t", "sine", "-f", "440", "-l", "1", "-s", "1"],
                capture_output=True, timeout=5
            )
            ok("Altavoz", "Prueba de tono enviada (¿escuchaste algo?)")
        except Exception:
            info("No se pudo hacer prueba de tono con speaker-test")
    else:
        fail("ALSA audio", "Sin dispositivos de salida")
except Exception as e:
    fail("Audio salida", str(e))

# ─────────────────────────────────────────────
print("\n5. Modelo Vosk")
# ─────────────────────────────────────────────
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import VOSK_MODEL_PATH
    if os.path.exists(VOSK_MODEL_PATH):
        ok("Modelo Vosk", VOSK_MODEL_PATH)
    else:
        fail("Modelo Vosk", f"No encontrado en {VOSK_MODEL_PATH}")
        info("Ejecuta: bash scripts/install.sh")
except Exception as e:
    fail("Config", str(e))

# ─────────────────────────────────────────────
print("\n6. Ollama")
# ─────────────────────────────────────────────
try:
    import requests
    from config import OLLAMA_HOST, OLLAMA_MODEL
    r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    models = [m["name"] for m in r.json().get("models", [])]
    ok("Ollama server", f"{OLLAMA_HOST}")
    if any(OLLAMA_MODEL in m for m in models):
        ok(f"Modelo {OLLAMA_MODEL}", "disponible")
    else:
        fail(f"Modelo {OLLAMA_MODEL}", f"No descargado. Ejecuta: bash scripts/setup_model.sh")
        info(f"Modelos disponibles: {models}")
except Exception as e:
    fail("Ollama", f"No responde en {OLLAMA_HOST} — ejecuta: ollama serve")

# ─────────────────────────────────────────────
print("\n7. TTS")
# ─────────────────────────────────────────────
for tts_cmd in [("piper", "--version"), ("espeak-ng", "--version")]:
    try:
        r = subprocess.run(tts_cmd, capture_output=True, timeout=3)
        if r.returncode == 0:
            ok(tts_cmd[0], "instalado")
            break
    except FileNotFoundError:
        fail(tts_cmd[0], "no encontrado")

# ─────────────────────────────────────────────
print("\n━━━ Resumen ━━━")
passed = sum(1 for r in results if r[0])
total  = len(results)
print(f"  {passed}/{total} verificaciones pasadas\n")

if passed == total:
    print(f"  {PASS} ¡Todo listo! Ejecuta: python main.py\n")
else:
    failed = [r[1] for r in results if not r[0]]
    print(f"  {FAIL} Corrige los errores antes de continuar:")
    for f in failed:
        print(f"     · {f}")
    print()
