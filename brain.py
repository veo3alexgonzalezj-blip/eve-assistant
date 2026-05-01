"""
Eve - AI Brain (Ollama)
Cliente para el modelo de lenguaje local servido por Ollama.
Mantiene el historial de conversación en memoria.
"""

import re
import time

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[Brain] requests no disponible, modo simulado")


class Brain:
    def __init__(self):
        from config import (
            OLLAMA_HOST, OLLAMA_MODEL,
            SYSTEM_PROMPT, OLLAMA_OPTIONS, MAX_HISTORY_TURNS
        )

        self.host            = OLLAMA_HOST
        self.model           = OLLAMA_MODEL
        self.system_prompt   = SYSTEM_PROMPT
        self.options         = OLLAMA_OPTIONS
        self.max_turns       = MAX_HISTORY_TURNS

        self.history: list[dict] = []   # [{"role": ..., "content": ...}]

        # Verificar conexión con Ollama al arrancar
        self._check_connection()
        print(f"[Brain] Listo — modelo: {self.model}")

    # ──────────────────────────────────────────
    #  Verificación
    # ──────────────────────────────────────────
    def _check_connection(self):
        if not REQUESTS_AVAILABLE:
            return
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"[Brain] Ollama online. Modelos: {models}")
            if self.model not in models and not any(self.model in m for m in models):
                print(
                    f"[Brain] ⚠  Modelo '{self.model}' no encontrado.\n"
                    f"         Ejecuta: ollama pull {self.model}"
                )
        except Exception as e:
            print(f"[Brain] ⚠  No se pudo conectar a Ollama: {e}")
            print(f"         Asegúrate de que Ollama esté corriendo: ollama serve")

    # ──────────────────────────────────────────
    #  Consulta principal
    # ──────────────────────────────────────────
    def ask(self, question: str) -> str:
        """
        Envía una pregunta al modelo y retorna la respuesta limpia.
        Mantiene el historial de conversación automáticamente.
        """
        if not REQUESTS_AVAILABLE:
            return self._simulate(question)

        # Agregar pregunta al historial
        self.history.append({"role": "user", "content": question})

        # Solo enviar los últimos N turnos (ahorra memoria/tiempo)
        recent = self.history[-(self.max_turns * 2):]

        payload = {
            "model":   self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + recent,
            "stream":  False,
            "options": self.options,
        }

        t0 = time.time()
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=90,     # RPi puede ser lento con modelos grandes
            )
            resp.raise_for_status()
            data = resp.json()

        except requests.exceptions.Timeout:
            self._pop_last()
            return (
                "Lo siento, tardé demasiado. "
                "¿Puedes hacer una pregunta más corta?"
            )
        except requests.exceptions.ConnectionError:
            self._pop_last()
            return "No puedo conectarme al servicio de inteligencia artificial."
        except Exception as e:
            self._pop_last()
            print(f"[Brain] Error inesperado: {e}")
            return "Tuve un problema interno. Por favor inténtalo de nuevo."

        elapsed = time.time() - t0
        answer = data.get("message", {}).get("content", "").strip()

        if not answer:
            self._pop_last()
            return "No obtuve una respuesta. ¿Puedes repetir tu pregunta?"

        # Limpiar y guardar
        answer = self._clean(answer)
        self.history.append({"role": "assistant", "content": answer})

        tokens = data.get("eval_count", 0)
        speed  = tokens / elapsed if elapsed > 0 else 0
        print(f"[Brain] {tokens} tokens en {elapsed:.1f}s ({speed:.1f} tok/s)")

        return answer

    # ──────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────
    def _pop_last(self):
        """Elimina el último mensaje de usuario si no hubo respuesta."""
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()

    def _clean(self, text: str) -> str:
        """Elimina markdown y artefactos no aptos para TTS."""
        # Negritas, cursivas
        text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
        # Encabezados
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Código
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        # URLs en markdown
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Saltos múltiples → espacio
        text = re.sub(r"\s*\n\s*", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    def clear_history(self):
        self.history.clear()
        print("[Brain] Historial borrado")

    # ──────────────────────────────────────────
    #  Simulación
    # ──────────────────────────────────────────
    def _simulate(self, question: str) -> str:
        time.sleep(1.5)
        return (
            f"Estoy en modo simulado sin Ollama. "
            f"Tu pregunta fue: {question[:40]}. "
            "Cuando configures Ollama, recibirás respuestas reales."
        )
