#!/usr/bin/env bash
# ============================================================
#  install.sh  —  Eve Asistente de Voz
#  Instala todas las dependencias en Raspberry Pi OS (64-bit)
#  Ejecutar: bash scripts/install.sh
# ============================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

EVE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${BOLD}━━━ $* ━━━${NC}"; }

echo -e "${BOLD}"
cat << 'BANNER'
  ███████╗██╗   ██╗███████╗
  ██╔════╝██║   ██║██╔════╝
  █████╗  ██║   ██║█████╗
  ██╔══╝  ╚██╗ ██╔╝██╔══╝
  ███████╗ ╚████╔╝ ███████╗
  ╚══════╝  ╚═══╝  ╚══════╝
  Asistente de Voz — Instalador
BANNER
echo -e "${NC}"

# ─────────────────────────────────────────────
step "1/7  Actualizando sistema"
# ─────────────────────────────────────────────
sudo apt-get update -qq
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    portaudio19-dev libportaudio2 \
    espeak-ng espeak-ng-data libespeak-ng1 \
    ffmpeg alsa-utils alsa-tools \
    i2c-tools libi2c-dev python3-smbus \
    git wget unzip curl \
    libatlas-base-dev libopenblas-dev \
    libjpeg-dev zlib1g-dev libfreetype6-dev \
    2>/dev/null
success "Paquetes del sistema instalados"

# ─────────────────────────────────────────────
step "2/7  Habilitando I2C y configurando audio"
# ─────────────────────────────────────────────
# Habilitar I2C
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    warn "Habilitando I2C en /boot/config.txt..."
    sudo raspi-config nonint do_i2c 0 || \
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

# Añadir usuario al grupo audio e i2c
sudo usermod -aG audio,i2c "$USER" 2>/dev/null || true

# Verificar dispositivos I2C
info "Dispositivos I2C detectados:"
sudo i2cdetect -y 1 2>/dev/null || warn "No se pudo ejecutar i2cdetect (normal si aún no hay hardware)"

success "I2C configurado"

# ─────────────────────────────────────────────
step "3/7  Entorno virtual Python"
# ─────────────────────────────────────────────
cd "$EVE_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    info "Entorno virtual creado en $EVE_DIR/venv"
fi

source venv/bin/activate
pip install --upgrade pip wheel setuptools -q
success "Entorno virtual listo"

# ─────────────────────────────────────────────
step "4/7  Instalando dependencias Python"
# ─────────────────────────────────────────────
pip install -r requirements.txt
success "Dependencias Python instaladas"

# ─────────────────────────────────────────────
step "5/7  Descargando modelo Vosk (español)"
# ─────────────────────────────────────────────
VOSK_DIR="$EVE_DIR/models/vosk-model-small-es"
VOSK_URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"

if [ ! -d "$VOSK_DIR" ]; then
    mkdir -p "$EVE_DIR/models"
    info "Descargando modelo Vosk (~50 MB)..."
    wget -q --show-progress -O /tmp/vosk-es.zip "$VOSK_URL"
    info "Descomprimiendo..."
    unzip -q /tmp/vosk-es.zip -d "$EVE_DIR/models/"
    mv "$EVE_DIR/models/vosk-model-small-es-0.42" "$VOSK_DIR"
    rm /tmp/vosk-es.zip
    success "Modelo Vosk descargado en $VOSK_DIR"
else
    success "Modelo Vosk ya existe — omitiendo descarga"
fi

# ─────────────────────────────────────────────
step "6/7  Instalando Ollama"
# ─────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    info "Instalando Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    success "Ollama instalado"
else
    success "Ollama ya está instalado ($(ollama --version))"
fi

# ─────────────────────────────────────────────
step "7/7  (Opcional) Instalar Piper TTS"
# ─────────────────────────────────────────────
PIPER_DIR="$EVE_DIR/models/piper"

if [ ! -f "$PIPER_DIR/piper" ]; then
    echo ""
    read -rp "¿Instalar Piper TTS (voz natural en español, ~200MB)? [S/n]: " resp
    resp="${resp:-S}"
    if [[ "$resp" =~ ^[Ss] ]]; then
        mkdir -p "$PIPER_DIR"
        # Detectar arquitectura
        ARCH=$(uname -m)
        if [ "$ARCH" = "aarch64" ]; then
            PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
        else
            PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
        fi

        wget -q --show-progress -O /tmp/piper.tar.gz "$PIPER_URL"
        tar -xzf /tmp/piper.tar.gz -C "$PIPER_DIR" --strip-components=1
        rm /tmp/piper.tar.gz

        # Crear enlace simbólico para acceso global
        sudo ln -sf "$PIPER_DIR/piper" /usr/local/bin/piper 2>/dev/null || true

        # Descargar voz española
        VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
        VOICE_CFG="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"

        info "Descargando voz española para Piper..."
        wget -q --show-progress -O "$EVE_DIR/models/es_ES-davefx-medium.onnx" "$VOICE_URL"
        wget -q --show-progress -O "$EVE_DIR/models/es_ES-davefx-medium.onnx.json" "$VOICE_CFG"
        success "Piper TTS instalado con voz española"
    else
        warn "Piper omitido. Eve usará eSpeak-NG (voz más robótica)."
    fi
else
    success "Piper ya está instalado"
fi

# ─────────────────────────────────────────────
#  Crear servicio systemd (opcional)
# ─────────────────────────────────────────────
echo ""
read -rp "¿Crear servicio systemd para que Eve arranque al iniciar? [S/n]: " resp2
resp2="${resp2:-S}"
if [[ "$resp2" =~ ^[Ss] ]]; then
    bash "$(dirname "$0")/create_service.sh"
fi

# ─────────────────────────────────────────────
#  Resumen final
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════╗"
echo -e "║    ¡Instalación completada con éxito!    ║"
echo -e "╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "Próximos pasos:"
echo -e "  1. Descarga el modelo IA:  ${CYAN}bash scripts/setup_model.sh${NC}"
echo -e "  2. Inicia Ollama:          ${CYAN}ollama serve${NC}"
echo -e "  3. Ejecuta Eve:            ${CYAN}cd $EVE_DIR && source venv/bin/activate && python main.py${NC}"
echo ""
warn "Reinicia la Raspberry Pi si habilitaste I2C por primera vez."
echo ""
