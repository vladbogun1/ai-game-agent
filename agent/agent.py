import json
import logging
import time
import re
from dataclasses import dataclass
from threading import Event

from agent.actions import Action, ActionExecutor, CoordinateMapper
from agent.config import AgentConfig
from agent.ollama_client import OllamaClient
from agent.vision import VisionAnalyzer


@dataclass(frozen=True)
class AgentState:
    task: str
    context: str
    rules: str


class GameAgent:
    def __init__(
        self,
        config: AgentConfig,
        state: AgentState,
        stop_event: Event | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.state = state
        capture_width, capture_height = self._resolve_capture_size(
            config.capture_width, config.capture_height, config.max_image_side
        )
        self.vision = VisionAnalyzer(
            monitor_index=config.screen_monitor,
            target_size=(capture_width, capture_height),
            save_debug_frames=config.save_debug_frames,
            debug_frame_interval_s=config.debug_frame_interval_s,
        )
        self.logger = logger or logging.getLogger(__name__)
        monitor = self.vision.monitor_region()
        coordinate_mapper = CoordinateMapper(
            monitor_left=monitor["left"],
            monitor_top=monitor["top"],
            monitor_width=monitor["width"],
            monitor_height=monitor["height"],
            capture_width=capture_width,
            capture_height=capture_height,
        )
        self.ollama = OllamaClient(config.ollama_url, logger=self.logger)
        self.executor = ActionExecutor(
            dry_run=config.dry_run,
            logger=self.logger,
            coordinate_mapper=coordinate_mapper,
            click_min_interval_s=config.click_min_interval_s,
            key_min_interval_s=config.key_min_interval_s,
        )
        self.stop_event = stop_event or Event()

    def build_prompt(self, frame_summary: str) -> str:
        return (
            "You are a vision-based game automation agent. You receive a screenshot image.\n"
            "You must output ONLY a JSON array of actions (max 3). No markdown, no text.\n\n"
            "Allowed action objects:\n"
            '- {"type":"move_mouse","x":int,"y":int}\n'
            '- {"type":"click_left"}\n'
            '- {"type":"click_right"}\n'
            '- {"type":"press_key","key":string}\n'
            '- {"type":"release_key","key":string}\n'
            '- {"type":"wait","duration_s":float}\n\n'
            "Rules:\n"
            "- Base decisions strictly on what is visible in the screenshot + Context/Rules.\n"
            "- Think about observations internally, but DO NOT output them.\n"
            "- If you are not confident, output [].\n"
            "- Do not click random UI. Only act when target is clearly visible or rule says safe.\n"
            "- Coordinates are in the screenshot space (width x height), top-left is (0,0).\n"
            "- NEVER output anything except the JSON array.\n\n"
            f"Task: {self.state.task}\n"
            f"Context: {self.state.context}\n"
            f"Rules: {self.state.rules}\n\n"
            f"{frame_summary}\n"
        )

    @staticmethod
    def _extract_payload(response_text: str) -> object | None:
        cleaned = GameAgent._strip_code_fence(response_text)
        try:
            return json.loads(cleaned)
        except ValueError:
            pass
        decoder = json.JSONDecoder()
        for start in range(len(cleaned)):
            if cleaned[start] not in "[{":
                continue
            try:
                payload, _ = decoder.raw_decode(cleaned[start:])
                return payload
            except ValueError:
                continue
        return None

    @staticmethod
    def _strip_code_fence(response_text: str) -> str:
        text = response_text.strip()
        if "```" not in text:
            return text
        pattern = re.compile(r"```(?:json)?\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return text


    @staticmethod
    def parse_actions(response_text: str, width: int, height: int) -> list[Action]:
        actions: list[Action] = []
        if not response_text:
            return actions
        try:
            payload = GameAgent._extract_payload(response_text)
        except ValueError:
            return actions
        if not isinstance(payload, list):
            return actions
        allowed = {"move_mouse", "click_left", "click_right", "press_key", "release_key", "wait"}
        for item in payload:
            if not isinstance(item, dict):
                continue
            action_type = item.get("type")
            if action_type not in allowed:
                continue
            if action_type == "move_mouse":
                x = item.get("x")
                y = item.get("y")
                if not isinstance(x, int) or not isinstance(y, int):
                    continue
                if x < 0 or y < 0 or x >= width or y >= height:
                    continue
                actions.append(Action(type=action_type, x=x, y=y))
                if len(actions) >= 3:
                    break
                continue
            if action_type in {"press_key", "release_key"}:
                key = item.get("key")
                if not isinstance(key, str) or not key.strip():
                    continue
                actions.append(Action(type=action_type, key=key))
                if len(actions) >= 3:
                    break
                continue
            if action_type == "wait":
                duration = item.get("duration_s")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    continue
                actions.append(Action(type=action_type, duration_s=float(duration)))
                if len(actions) >= 3:
                    break
                continue
            actions.append(
                Action(
                    type=action_type,
                )
            )
            if len(actions) >= 3:
                break
        return actions[:3]

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                image = self.vision.capture()
                summary = self.vision.summarize(image)
                prompt = self.build_prompt(summary.to_prompt())
                self.logger.info(
                    "Sending frame to Ollama: %sx%s", image.width, image.height
                )
                response = self.ollama.generate(
                    self.config.model,
                    prompt,
                    image=image,
                    image_quality=self.config.image_jpeg_quality,
                    max_image_side=None,
                )
                raw_text = response.text
                self.logger.info("Ollama raw response: %s", self._truncate(raw_text))
                actions = self.parse_actions(raw_text, image.width, image.height)
                self.logger.info("Validated actions: %s", actions)
                self.executor.execute(actions)
                time.sleep(self.config.loop_delay_s)
            except Exception:
                self.logger.exception("Agent loop error")
                time.sleep(1.0)

    @staticmethod
    def _truncate(text: str, limit: int = 400) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "…"

    @staticmethod
    def _resolve_capture_size(
        width: int, height: int, max_image_side: int | None
    ) -> tuple[int, int]:
        if not max_image_side:
            return width, height
        max_side = max(width, height)
        if max_side <= max_image_side:
            return width, height
        scale = max_image_side / max_side
        return int(round(width * scale)), int(round(height * scale))
