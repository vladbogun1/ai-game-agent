import argparse

from agent.agent import AgentState, GameAgent
from agent.config import AgentConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI game agent")
    parser.add_argument("--model", default="llava:7b")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--task", default="mine_ore")
    parser.add_argument("--context", default="start in mine, pickaxe equipped")
    parser.add_argument("--rules", default="avoid enemies, return when inventory full")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--monitor", type=int, default=1)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--image-quality", type=int, default=80)
    parser.add_argument("--max-image-side", type=int, default=960)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--save-debug-frames", action="store_true")
    parser.add_argument("--debug-frame-interval", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AgentConfig(
        model=args.model,
        ollama_url=args.ollama_url,
        screen_monitor=args.monitor,
        capture_width=args.width,
        capture_height=args.height,
        image_jpeg_quality=args.image_quality,
        max_image_side=args.max_image_side,
        loop_delay_s=args.delay,
        dry_run=args.dry_run,
        save_debug_frames=args.save_debug_frames,
        debug_frame_interval_s=args.debug_frame_interval,
    )
    state = AgentState(task=args.task, context=args.context, rules=args.rules)
    agent = GameAgent(config, state)
    agent.run()


if __name__ == "__main__":
    main()
