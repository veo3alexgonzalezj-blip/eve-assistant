#!/usr/bin/env bash
# ============================================================
#  setup_model.sh  —  Descarga y configura el modelo IA
# ============================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; NC='\033[0m'

EVE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BOLD}"
echo "  Configuración del Modelo IA para Eve"
echo "  (Raspberry Pi 4 — 8 GB RAM)"
echo -e "${NC}"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  Modelos recomendados para 8 GB de RAM                       ║"
echo -e "╠══════════════════════════════════════════════════════════════╣"
echo -e "║  1. llama3.2:3b          ~2.0 GB  ★ RECOMENDADO             ║"
echo -e "║     Velocidad: ~10 tok/s · Español excelente · Moderno       ║"
echo -e "║                                                               ║"
echo -e "║  2. phi3.5:mini          ~2.2 GB  Muy eficiente              ║"
echo -e "║     Velocidad: ~12 tok/s · Razonamiento muy bueno            ║"
echo -e "║                                                               ║"
echo -e "║  3. gemma2:2b            ~1.5 GB  El más rápido              ║"
echo -e "║     Velocidad: ~15 tok/s · Español aceptable                  ║"
echo -e "║                                                               ║"
echo -e "║  4. mistral:7b-instruct-q4_0  ~4.0 GB  Mayor calidad        ║"
echo -e "║     Velocidad: ~5 tok/s  · Respuestas más ricas              ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

read -rp "Selecciona un modelo [1-4] (default: 1): " choice
choice="${choice:-1}"

case "$choice" in
    1) MODEL="llama3.2:3b" ;;
    2) MODEL="phi3.5:mini" ;;
    3) MODEL="gemma2:2b" ;;
    4) MODEL="mistral:7b-instruct-q4_0" ;;
    *) echo "Opción inválida, usando llama3.2:3b"; MODEL="llama3.2:3b" ;;
esac

echo ""
echo -e "Descargando ${CYAN}${MODEL}${NC}..."
echo "(Esto puede tardar varios minutos dependiendo de tu conexión)"
echo ""

# Iniciar ollama serve si no está corriendo
if ! pgrep -x ollama &>/dev/null; then
    echo "Iniciando Ollama en segundo plano..."
    ollama serve &>/dev/null &
    sleep 3
fi

ollama pull "$MODEL"

# Actualizar config.py con el modelo seleccionado
CONFIG="$EVE_DIR/config.py"
if [ -f "$CONFIG" ]; then
    sed -i "s/^OLLAMA_MODEL = .*/OLLAMA_MODEL = \"$MODEL\"/" "$CONFIG"
    echo ""
    echo -e "${GREEN}✓ config.py actualizado con modelo: ${MODEL}${NC}"
fi

# Prueba rápida
echo ""
echo "Haciendo prueba rápida del modelo..."
RESPONSE=$(ollama run "$MODEL" "Responde en una oración en español: ¿Cómo te llamas?" 2>/dev/null || echo "Error en prueba")
echo -e "Respuesta de prueba: ${CYAN}${RESPONSE}${NC}"
echo ""
echo -e "${GREEN}✓ Modelo ${MODEL} listo para Eve.${NC}"
echo ""
echo "Ahora puedes iniciar Eve:"
echo -e "  ${CYAN}source $EVE_DIR/venv/bin/activate${NC}"
echo -e "  ${CYAN}python $EVE_DIR/main.py${NC}"
