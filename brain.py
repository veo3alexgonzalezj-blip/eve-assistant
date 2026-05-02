# brain.py
import requests
import json
from config import OLLAMA_MODEL, OLLAMA_URL, MAX_CONTEXT_TOKENS

class Brain:
    def __init__(self):
        self.system_prompt = "Eres Eve, un asistente virtual profesional, conciso y amable. Responde siempre en español en menos de 3 oraciones."
        self.history = []

    def _estimate_tokens(self, text: str) -> int:
        """Estimación rápida: ~1.3 tokens por palabra en español."""
        return int(len(text.split()) * 1.3)

    def _trim_history(self):
        """Poda el historial dinámicamente para no desbordar la RAM."""
        tokens_totales = self._estimate_tokens(self.system_prompt)
        
        for msg in self.history:
            tokens_totales += self._estimate_tokens(msg["content"])
            
        while tokens_totales > MAX_CONTEXT_TOKENS and len(self.history) >= 2:
            rem_user = self.history.pop(0)
            rem_asst = self.history.pop(0)
            tokens_totales -= self._estimate_tokens(rem_user["content"])
            tokens_totales -= self._estimate_tokens(rem_asst["content"])
            print(f"[Brain] Historial podado. Tokens restantes: {tokens_totales}")

    def ask(self, question: str) -> str:
        self.history.append({"role": "user", "content": question})
        self._trim_history()

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": self.system_prompt}] + self.history,
            "stream": False
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            answer = response.json().get("message", {}).get("content", "")
            if answer:
                self.history.append({"role": "assistant", "content": answer})
                return answer
            return "Lo siento, mis circuitos cognitivos no respondieron."
        except Exception as e:
            self.history.pop() # Eliminar la pregunta si hubo error
            print(f"[Brain Error]: {e}")
            return "Hubo un problema de conexión con mi núcleo local."