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
