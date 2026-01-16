from agent.actions import CoordinateMapper


def test_coordinate_mapping() -> None:
    mapper = CoordinateMapper(
        monitor_left=100,
        monitor_top=200,
        monitor_width=1000,
        monitor_height=500,
        capture_width=500,
        capture_height=250,
    )
    assert mapper.map_to_screen(250, 125) == (600, 450)
