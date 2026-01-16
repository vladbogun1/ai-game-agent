from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    model: str = "llava:7b"
    ollama_url: str = "http://localhost:11434"
    screen_monitor: int = 1
    capture_width: int = 640
    capture_height: int = 360
    image_jpeg_quality: int = 80
    max_image_side: int = 960
    loop_delay_s: float = 0.2
    dry_run: bool = True
    save_debug_frames: bool = False
    debug_frame_interval_s: float = 5.0
    click_min_interval_s: float = 0.3
    key_min_interval_s: float = 0.6
