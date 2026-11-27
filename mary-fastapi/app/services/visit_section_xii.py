"""Visit clock window passed to the care-note AI.

Section XII itself is the model's additional_notes text. This module only
chooses the visit times that bound that text. It does not write the notes.
"""

from datetime import datetime, time as time_type


def hhmm(value) -> str:
    """Return HH:MM from a time, datetime, or clock string. Blank stays blank."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, time_type):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return ""
    if "T" in text:
        text = text.split("T", 1)[1]
    elif " " in text:
        text = text.split(" ", 1)[1]
    if len(text) >= 5 and text[2] == ":":
        hour, minute = text[:2], text[3:5]
        if hour.isdigit() and minute.isdigit():
            return f"{int(hour):02d}:{int(minute):02d}"
    return ""


def resolve_visit_window(
    *,
    clock_in=None,
    clock_out=None,
    scheduled_start=None,
    scheduled_end=None,
    fallback_in=None,
    fallback_out=None,
) -> dict:
    """Times given to the AI as the actual visit.

    Visit clock-in and clock-out come first, then the scheduled visit.
    fallback_in and fallback_out are only used when the visit has neither,
    and they are not treated as the scheduled visit.
    """
    arrival = hhmm(clock_in)
    departure = hhmm(clock_out)
    visit_start = hhmm(scheduled_start)
    visit_end = hhmm(scheduled_end)
    time_in = arrival or visit_start or hhmm(fallback_in) or "08:00"
    time_out = departure or visit_end or hhmm(fallback_out) or "17:00"
    return {
        "time_in": time_in,
        "time_out": time_out,
        "clock_in": arrival,
        "clock_out": departure,
        "scheduled_start": visit_start,
        "scheduled_end": visit_end,
    }
