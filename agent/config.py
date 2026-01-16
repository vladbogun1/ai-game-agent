from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    model: str = "llava:7b"
    ollama_url: str = "http://localhost:11434"
    screen_monitor: int = 1
    capture_width: int = 384
    capture_height: int = 216
    image_jpeg_quality: int = 70
    max_image_side: int = 960
    loop_delay_s: float = 0.1
    llm_interval_s: float = 1.5
    cache_ttl_s: float = 3.0
    frame_change_threshold: int = 6
    cooldown_default_s: float = 0.6
    cooldown_key_tap_s: float = 4.0
    dry_run: bool = True
    save_debug_frames: bool = False
    debug_frame_interval_s: float = 5.0
    click_min_interval_s: float = 0.3
    key_min_interval_s: float = 0.6
