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
        self._last_llm_ts = 0.0
        self._last_frame_sig: int | None = None
        self._cache: dict[int, tuple[float, list[Action]]] = {}
        self._cooldown_until_ts = 0.0
        self._empty_response_count = 0

    def build_prompt(self, frame_summary: str) -> str:
        return (
            "You are a vision-based game automation agent.\n"
            "Return ONLY a JSON array of actions (max 3). No markdown.\n"
            "If unsure, return [].\n\n"
            "Actions:\n"
            '- {"type":"move_mouse","x":int,"y":int}\n'
            '- {"type":"click_left"}\n'
            '- {"type":"click_right"}\n'
            '- {"type":"tap_key","key":string}\n'
            '- {"type":"press_key","key":string}\n'
            '- {"type":"release_key","key":string}\n'
            '- {"type":"wait","duration_s":float}\n\n'
            "Use only what is visible + Context/Rules. Coordinates are screenshot pixels.\n\n"
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
        allowed = {
            "move_mouse",
            "click_left",
            "click_right",
            "tap_key",
            "press_key",
            "release_key",
            "wait",
        }
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
            if action_type in {"press_key", "release_key", "tap_key"}:
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
                loop_start = time.monotonic()
                capture_start = time.monotonic()
                image = self.vision.capture()
                capture_ms = (time.monotonic() - capture_start) * 1000

                sig_start = time.monotonic()
                frame_sig = self.vision.signature(image)
                sig_ms = (time.monotonic() - sig_start) * 1000

                now = time.monotonic()
                cached_actions = self._cached_actions(frame_sig, now)
                if cached_actions is not None:
                    exec_start = time.monotonic()
                    self.executor.execute(cached_actions)
                    exec_ms = (time.monotonic() - exec_start) * 1000
                    self._apply_cooldown(cached_actions, now)
                    self.logger.info(
                        "Cache hit. timings capture=%.1fms sig=%.1fms exec=%.1fms",
                        capture_ms,
                        sig_ms,
                        exec_ms,
                    )
                    self._sleep_remaining(loop_start)
                    continue

                if not self.should_call_llm(now, frame_sig):
                    self.logger.debug(
                        "Skipping LLM. cooldown=%.2fs",
                        max(0.0, self._cooldown_until_ts - now),
                    )
                    self._sleep_remaining(loop_start)
                    continue

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
                    max_image_side=self.config.max_image_side,
                )
                llm_ms = response.request_ms or 0.0
                encode_ms = response.encode_ms or 0.0
                raw_text = response.text
                self.logger.info("Ollama raw response: %s", self._truncate(raw_text))
                parse_start = time.monotonic()
                actions = self.parse_actions(raw_text, image.width, image.height)
                parse_ms = (time.monotonic() - parse_start) * 1000
                self.logger.info("Validated actions: %s", actions)
                exec_start = time.monotonic()
                self.executor.execute(actions)
                exec_ms = (time.monotonic() - exec_start) * 1000
                self._cache[frame_sig] = (now, actions)
                self._last_llm_ts = now
                self._last_frame_sig = frame_sig
                if actions:
                    self._empty_response_count = 0
                    self._apply_cooldown(actions, now)
                else:
                    self._empty_response_count += 1
                self.logger.info(
                    "timings capture=%.1fms sig=%.1fms encode=%.1fms llm=%.1fms parse=%.1fms exec=%.1fms",
                    capture_ms,
                    sig_ms,
                    encode_ms,
                    llm_ms,
                    parse_ms,
                    exec_ms,
                )
                self._sleep_remaining(loop_start)
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

    def should_call_llm(self, now: float, frame_sig: int) -> bool:
        if now < self._cooldown_until_ts:
            return False
        if self._last_frame_sig is None:
            return True
        if now - self._last_llm_ts < self.config.llm_interval_s:
            return self._frame_changed_significantly(frame_sig)
        if self._empty_response_count >= 3 and self._frame_changed_significantly(frame_sig):
            return True
        return self._frame_changed_significantly(frame_sig)

    def _frame_changed_significantly(self, frame_sig: int) -> bool:
        if self._last_frame_sig is None:
            return True
        distance = (frame_sig ^ self._last_frame_sig).bit_count()
        return distance >= self.config.frame_change_threshold

    def _cached_actions(self, frame_sig: int, now: float) -> list[Action] | None:
        self._prune_cache(now)
        entry = self._cache.get(frame_sig)
        if entry:
            cached_ts, actions = entry
            if now - cached_ts <= self.config.cache_ttl_s:
                return actions
        for sig, (cached_ts, actions) in self._cache.items():
            if now - cached_ts > self.config.cache_ttl_s:
                continue
            if (frame_sig ^ sig).bit_count() <= self.config.frame_change_threshold:
                return actions
        return None

    def _prune_cache(self, now: float) -> None:
        expired = [
            sig
            for sig, (cached_ts, _) in self._cache.items()
            if now - cached_ts > self.config.cache_ttl_s
        ]
        for sig in expired:
            self._cache.pop(sig, None)

    def _apply_cooldown(self, actions: list[Action], now: float) -> None:
        cooldown = 0.0
        if actions:
            cooldown = self.config.cooldown_default_s
        if any(action.type in {"tap_key", "press_key", "release_key"} for action in actions):
            cooldown = max(cooldown, self.config.cooldown_key_tap_s)
        if cooldown > 0:
            self._cooldown_until_ts = max(self._cooldown_until_ts, now + cooldown)

    def _sleep_remaining(self, loop_start: float) -> None:
        elapsed = time.monotonic() - loop_start
        remaining = self.config.loop_delay_s - elapsed
        if remaining > 0:
            time.sleep(remaining)
