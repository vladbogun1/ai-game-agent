from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    model: str = "llava:7b"
    ollama_url: str = "http://localhost:11434"
    screen_monitor: int = 1
    capture_width: int = 640
    capture_height: int = 360
    loop_delay_s: float = 0.2
    dry_run: bool = True
