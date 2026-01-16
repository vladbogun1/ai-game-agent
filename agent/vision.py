from dataclasses import dataclass
from typing import Tuple

import mss
from PIL import Image, ImageStat


@dataclass(frozen=True)
class FrameSummary:
    width: int
    height: int
    mean_rgb: Tuple[int, int, int]

    def to_prompt(self) -> str:
        return (
            "Frame summary:\n"
            f"- resolution: {self.width}x{self.height}\n"
            f"- mean_rgb: {self.mean_rgb}\n"
        )


class VisionAnalyzer:
    def __init__(self, monitor_index: int, target_size: Tuple[int, int]) -> None:
        self.monitor_index = monitor_index
        self.target_size = target_size
        self._sct = mss.mss()

    def capture(self) -> Image.Image:
        monitor = self._sct.monitors[self.monitor_index]
        screenshot = self._sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return image.resize(self.target_size)

    def summarize(self, image: Image.Image) -> FrameSummary:
        stats = ImageStat.Stat(image)
        mean = tuple(int(value) for value in stats.mean[:3])
        return FrameSummary(width=image.width, height=image.height, mean_rgb=mean)
