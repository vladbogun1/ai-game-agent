import json
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class OllamaResponse:
    raw: dict

    @property
    def text(self) -> str:
        return self.raw.get("response", "").strip()


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def check_connection(self, model: str | None = None) -> tuple[bool, str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            return False, f"Ollama unreachable: {exc}"

        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if isinstance(item, dict)]
        if not model:
            return True, "Ollama reachable"
        if model in models:
            return True, f"Ollama reachable, model '{model}' available"
        return False, f"Ollama reachable, but model '{model}' not found"

    def generate(self, model: str, prompt: str) -> OllamaResponse:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        return OllamaResponse(response.json())
