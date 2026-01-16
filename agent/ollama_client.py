import base64
import io
import json
import logging
from dataclasses import dataclass

import requests
from PIL import Image


@dataclass(frozen=True)
class OllamaResponse:
    raw: dict

    @property
    def text(self) -> str:
        return self.raw.get("response", "").strip()


class OllamaClient:
    def __init__(self, base_url: str, logger: logging.Logger | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.logger = logger or logging.getLogger(__name__)

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

    def generate(
        self,
        model: str,
        prompt: str,
        image: Image.Image | None = None,
        image_quality: int = 80,
        max_image_side: int | None = None,
    ) -> OllamaResponse:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if image is not None:
            encoded, size = self._encode_image(image, image_quality, max_image_side)
            payload["images"] = [encoded]
            self.logger.info(
                "Ollama request: model=%s prompt=%s image_size=%sx%s",
                model,
                self._truncate(prompt),
                size[0],
                size[1],
            )
        else:
            self.logger.info("Ollama request: model=%s prompt=%s", model, self._truncate(prompt))
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=90,
            )
        except requests.RequestException as exc:
            self.logger.exception("Ollama request failed: %s", exc)
            raise
        response.raise_for_status()
        result = response.json()
        self.logger.info("Ollama response: %s", self._truncate(json.dumps(result, ensure_ascii=False)))
        return OllamaResponse(result)

    def _encode_image(
        self,
        image: Image.Image,
        image_quality: int,
        max_image_side: int | None,
    ) -> tuple[str, tuple[int, int]]:
        resized = image.convert("RGB")
        if max_image_side:
            resized.thumbnail((max_image_side, max_image_side))
        buffer = io.BytesIO()
        resized.save(buffer, format="JPEG", quality=image_quality)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return encoded, (resized.width, resized.height)

    @staticmethod
    def _truncate(text: str, limit: int = 400) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "…"
