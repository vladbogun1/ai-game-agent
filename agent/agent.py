import logging
import time
from dataclasses import dataclass
from threading import Event

from agent.actions import Action, ActionExecutor
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
        self.vision = VisionAnalyzer(
            monitor_index=config.screen_monitor,
            target_size=(config.capture_width, config.capture_height),
        )
        self.logger = logger or logging.getLogger(__name__)
        self.ollama = OllamaClient(config.ollama_url, logger=self.logger)
        self.executor = ActionExecutor(dry_run=config.dry_run, logger=self.logger)
        self.stop_event = stop_event or Event()

    def build_prompt(self, frame_summary: str) -> str:
        return (
            "You are a game-playing agent. Return a JSON array of actions.\n"
            "Valid actions: move_mouse(x,y), click_left, click_right, press_key(key), release_key(key).\n"
            "Use at most 3 actions.\n\n"
            f"Task: {self.state.task}\n"
            f"Context: {self.state.context}\n"
            f"Rules: {self.state.rules}\n\n"
            f"{frame_summary}\n"
            "Respond with JSON only, no markdown."
        )

    def parse_actions(self, response_text: str) -> list[Action]:
        actions: list[Action] = []
        if not response_text:
            return actions
        try:
            payload = __import__("json").loads(response_text)
        except ValueError:
            return actions
        if not isinstance(payload, list):
            return actions
        for item in payload:
            if not isinstance(item, dict):
                continue
            action_type = item.get("type")
            actions.append(
                Action(
                    type=action_type,
                    x=item.get("x"),
                    y=item.get("y"),
                    key=item.get("key"),
                    duration_s=item.get("duration_s"),
                )
            )
        return actions

    def run(self) -> None:
        while not self.stop_event.is_set():
            image = self.vision.capture()
            summary = self.vision.summarize(image)
            prompt = self.build_prompt(summary.to_prompt())
            response = self.ollama.generate(self.config.model, prompt)
            actions = self.parse_actions(response.text)
            self.executor.execute(actions)
            time.sleep(self.config.loop_delay_s)
