import json

from agent.agent import GameAgent
from agent.actions import Action


def test_parse_actions_validation() -> None:
    payload = [
        {"type": "move_mouse", "x": 10, "y": 20},
        {"type": "move_mouse", "x": 999, "y": 20},
        {"type": "press_key", "key": "1"},
        {"type": "release_key", "key": ""},
        {"type": "click_left"},
        {"type": "wait", "duration_s": 0.5},
        {"type": "unknown"},
    ]
    response_text = json.dumps(payload)
    actions = GameAgent.parse_actions(response_text, width=100, height=80)
    assert actions == [
        Action(type="move_mouse", x=10, y=20),
        Action(type="press_key", key="1"),
        Action(type="click_left"),
    ]
