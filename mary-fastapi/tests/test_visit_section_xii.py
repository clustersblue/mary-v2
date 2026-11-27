"""The AI visit window comes from the scheduled visit clocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.visit_section_xii import resolve_visit_window


SAMPLES = [
    ("Margaret Morkel", "", "17:00", "08:56", "17:04"),
    ("Alan Hillman", "", "12:00", "10:59", "12:02"),
    ("Ann Jenkin", "", "14:00", "12:59", "14:02"),
]


def test_ai_window_uses_visit_clocks():
    for name, start, end, clock_in, clock_out in SAMPLES:
        window = resolve_visit_window(
            clock_in=clock_in,
            clock_out=clock_out,
            scheduled_start=start,
            scheduled_end=end,
            fallback_in="08:00",
            fallback_out="17:00",
        )
        assert window["time_in"] == clock_in, name
        assert window["time_out"] == clock_out, name
        assert window["scheduled_start"] == ""
        assert window["scheduled_end"] == end
        assert window["time_in"] != "08:00" or clock_in == "08:00"
        print(f"{name}: AI visit window {window['time_in']}-{window['time_out']}")


if __name__ == "__main__":
    test_ai_window_uses_visit_clocks()
    print("visit window samples passed")
