from datetime import datetime, date
from dateutil.rrule import rrulestr
from typing import List

def expand_rrule_occurrences(
    start_date_str: str,
    end_date_str: str,
    rrule_str: str,
    range_start: date,
    range_end: date
) -> List[date]:
    """
    Expands an RRULE string into flat date occurrences between range_start and range_end.
    Ensures naive datetimes are used throughout to prevent TypeError with offset-aware datetimes.
    """
    try:
        dt_start = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
        
        # If the series starts after the requested range, no occurrences can fall in range
        if dt_start.date() > range_end:
            return []

        # Determine actual projection end limit
        until_dt = range_end
        if end_date_str:
            try:
                dt_end = datetime.strptime(end_date_str[:10], "%Y-%m-%d").date()
                if dt_end < range_start:
                    return []
                if dt_end >= dt_start.date():
                    until_dt = min(until_dt, dt_end)
            except Exception:
                pass
        
        calc_end = min(until_dt, range_end)
        calc_start = max(range_start, dt_start.date())
        if calc_start > calc_end:
            return []

        if not rrule_str or rrule_str.strip() == "":
            if range_start <= dt_start.date() <= range_end:
                return [dt_start.date()]
            return []

        # Strip any existing 'Z' or timezone markers to enforce naive UTC comparison
        clean_rrule = rrule_str.strip().replace("Z", "")
        if "UNTIL" not in clean_rrule.upper() and "COUNT" not in clean_rrule.upper():
            until_str = calc_end.strftime("%Y%m%dT235959")
            clean_rrule += f";UNTIL={until_str}"

        if "DTSTART" not in clean_rrule.upper():
            full_rrule = f"DTSTART:{dt_start.strftime('%Y%m%dT000000')}\nRRULE:{clean_rrule}"
        else:
            full_rrule = clean_rrule

        rule = rrulestr(full_rrule, dtstart=dt_start)
        
        start_dt = datetime.combine(calc_start, datetime.min.time())
        end_dt = datetime.combine(calc_end, datetime.max.time())
        
        occurrences = rule.between(start_dt, end_dt, inc=True)
        # Keep only dates the rule actually generates. The series start date is
        # often outside BYDAY (a Sunday start for a Monday-Friday rota) and is
        # not itself a visit.
        return sorted({item.date() for item in occurrences})
    except Exception as e:
        try:
            dt_start = datetime.strptime(start_date_str[:10], "%Y-%m-%d").date()
            if range_start <= dt_start <= range_end:
                return [dt_start]
        except Exception:
            pass
        return []
