import logging
import time
from dataclasses import dataclass
from typing import Iterable

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController


@dataclass(frozen=True)
class Action:
    type: str
    x: int | None = None
    y: int | None = None
    key: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True)
class CoordinateMapper:
    monitor_left: int
    monitor_top: int
    monitor_width: int
    monitor_height: int
    capture_width: int
    capture_height: int

    def map_to_screen(self, x: int, y: int) -> tuple[int, int]:
        abs_x = self.monitor_left + (x * self.monitor_width / self.capture_width)
        abs_y = self.monitor_top + (y * self.monitor_height / self.capture_height)
        return int(round(abs_x)), int(round(abs_y))


class ActionExecutor:
    def __init__(
        self,
        dry_run: bool = True,
        logger: logging.Logger | None = None,
        coordinate_mapper: CoordinateMapper | None = None,
        click_min_interval_s: float = 0.3,
        key_min_interval_s: float = 0.6,
    ) -> None:
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger(__name__)
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self.coordinate_mapper = coordinate_mapper
        self.click_min_interval_s = click_min_interval_s
        self.key_min_interval_s = key_min_interval_s
        self._last_action_time: dict[str, float] = {}

    def execute(self, actions: Iterable[Action]) -> None:
        for action in actions:
            if self.dry_run:
                self.logger.info("DRY RUN action: %s", action)
                continue
            if action.type == "move_mouse" and action.x is not None and action.y is not None:
                x, y = self._map_coords(action.x, action.y)
                self._mouse.position = (x, y)
            elif action.type == "click_left":
                if self._too_frequent("click_left", self.click_min_interval_s):
                    continue
                self._mouse.click(Button.left, 1)
            elif action.type == "click_right":
                if self._too_frequent("click_right", self.click_min_interval_s):
                    continue
                self._mouse.click(Button.right, 1)
            elif action.type == "press_key" and action.key is not None:
                key_id = f"press_key:{action.key}"
                if self._too_frequent(key_id, self.key_min_interval_s):
                    continue
                self._keyboard.press(action.key)
            elif action.type == "release_key" and action.key is not None:
                key_id = f"release_key:{action.key}"
                if self._too_frequent(key_id, self.key_min_interval_s):
                    continue
                self._keyboard.release(action.key)
            elif action.type == "wait" and action.duration_s:
                time.sleep(action.duration_s)

    def _map_coords(self, x: int, y: int) -> tuple[int, int]:
        if not self.coordinate_mapper:
            return x, y
        return self.coordinate_mapper.map_to_screen(x, y)

    def _too_frequent(self, key: str, min_interval_s: float) -> bool:
        now = time.monotonic()
        last_time = self._last_action_time.get(key)
        if last_time is not None and now - last_time < min_interval_s:
            self.logger.info("Skipping action %s (rate limit %.2fs)", key, min_interval_s)
            return True
        self._last_action_time[key] = now
        return False
