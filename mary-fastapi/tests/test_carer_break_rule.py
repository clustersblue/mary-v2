"""Carer breaks are written only for visits of 8 hours or more."""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("httpx", types.ModuleType("httpx"))

from app.services.ai_care_plan import _apply_break_rule, requires_carer_break, strip_carer_breaks


def minutes(start, end):
    sh, sm = [int(part) for part in start.split(":")]
    eh, em = [int(part) for part in end.split(":")]
    return (eh * 60 + em) - (sh * 60 + sm)


SAMPLES = [
    ("Margaret Morkel", "08:56", "17:04", True),
    ("Alan Hillman", "10:59", "12:02", False),
    ("Ann Jenkin", "12:59", "14:02", False),
]


def test_sample_visits():
    for name, start, end, expected in SAMPLES:
        duration = minutes(start, end)
        assert requires_carer_break(duration) is expected, f"{name} {duration}"
        print(f"{name}: {duration} minutes, carer break {'included' if expected else 'omitted'}")
    assert requires_carer_break(60) is False
    assert requires_carer_break(7 * 60 + 59) is False
    assert requires_carer_break(8 * 60) is True


def test_short_visit_drops_break_lines_only():
    notes = "\n".join([
        "10:59 am: Arrival for visit. Welcomed by Alan Hillman.",
        "11:20 am - 11:40 am: Carer break/rest period.",
        "11:40 am - 12:02 pm: Assisted Alan Hillman with lunch and breakfast fluids.",
    ])
    cleaned = strip_carer_breaks(notes)
    assert "Carer break/rest period" not in cleaned
    assert "breakfast fluids" in cleaned
    payload = _apply_break_rule({"additional_notes": notes}, 63)
    assert "rest period" not in payload["additional_notes"].lower()
    kept = _apply_break_rule({"additional_notes": notes}, 8 * 60)
    assert "Carer break/rest period" in kept["additional_notes"]


if __name__ == "__main__":
    test_sample_visits()
    test_short_visit_drops_break_lines_only()
    print("carer break rule passed")
