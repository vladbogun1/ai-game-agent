import os
import threading
import time
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
    def __init__(
        self,
        monitor_index: int,
        target_size: Tuple[int, int],
        save_debug_frames: bool = False,
        debug_frame_interval_s: float = 5.0,
        debug_dir: str = "debug_frames",
    ) -> None:
        self.monitor_index = monitor_index
        self.target_size = target_size
        self.save_debug_frames = save_debug_frames
        self.debug_frame_interval_s = debug_frame_interval_s
        self.debug_dir = debug_dir
        self._sct_local = threading.local()
        self._last_debug_ts: float = 0.0

    def capture(self) -> Image.Image:
        sct = self._get_sct()
        monitor = sct.monitors[self.monitor_index]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        resized = image.resize(self.target_size)
        self._maybe_save_debug(resized)
        return resized

    def summarize(self, image: Image.Image) -> FrameSummary:
        stats = ImageStat.Stat(image)
        mean = tuple(int(value) for value in stats.mean[:3])
        return FrameSummary(width=image.width, height=image.height, mean_rgb=mean)

    def signature(self, image: Image.Image, hash_size: int = 8) -> int:
        grayscale = image.convert("L").resize((hash_size + 1, hash_size), Image.BILINEAR)
        pixels = list(grayscale.getdata())
        signature = 0
        bit_index = 0
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                if left > right:
                    signature |= 1 << bit_index
                bit_index += 1
        return signature

    def monitor_region(self) -> dict[str, int]:
        sct = self._get_sct()
        monitor = sct.monitors[self.monitor_index]
        return {
            "left": int(monitor["left"]),
            "top": int(monitor["top"]),
            "width": int(monitor["width"]),
            "height": int(monitor["height"]),
        }

    def _get_sct(self) -> mss.mss:
        sct = getattr(self._sct_local, "instance", None)
        if sct is None:
            sct = mss.mss()
            self._sct_local.instance = sct
        return sct

    def _maybe_save_debug(self, image: Image.Image) -> None:
        if not self.save_debug_frames:
            return
        now = time.monotonic()
        if now - self._last_debug_ts < self.debug_frame_interval_s:
            return
        os.makedirs(self.debug_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.debug_dir, f"frame_{timestamp}.jpg")
        image.save(filename, format="JPEG", quality=85)
        self._last_debug_ts = now
