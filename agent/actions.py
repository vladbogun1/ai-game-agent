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


class ActionExecutor:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._mouse = MouseController()
        self._keyboard = KeyboardController()

    def execute(self, actions: Iterable[Action]) -> None:
        for action in actions:
            if self.dry_run:
                print(f"[DRY RUN] {action}")
                continue
            if action.type == "move_mouse" and action.x is not None and action.y is not None:
                self._mouse.position = (action.x, action.y)
            elif action.type == "click_left":
                self._mouse.click(Button.left, 1)
            elif action.type == "click_right":
                self._mouse.click(Button.right, 1)
            elif action.type == "press_key" and action.key is not None:
                self._keyboard.press(action.key)
            elif action.type == "release_key" and action.key is not None:
                self._keyboard.release(action.key)
