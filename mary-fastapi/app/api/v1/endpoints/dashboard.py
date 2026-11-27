import re
from collections import Counter, defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, text
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional

from app.db.session import get_db
from app.core.security import get_current_admin_user
from app.models.service_user import ServiceUser
from app.models.user import User
from app.models.master_data import Branch
from app.models.shift import DtrUserShift
from app.services.recurrence import expand_rrule_occurrences
from app.api.v1.endpoints.shifts import get_events

router = APIRouter()

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    date_str: Optional[str] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Active Service Users (Clients)
        su_stmt = select(func.count()).select_from(ServiceUser).where(ServiceUser.deleted_at.is_(None))
        su_count = (await db.execute(su_stmt)).scalar() or 0

        # Carers (Staff)
        carer_stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        carer_count = (await db.execute(carer_stmt)).scalar() or 0

        # Branch lookup cache
        branches_res = await db.execute(select(Branch))
        branch_map = {b.branch_id: b.branch_name for b in branches_res.scalars().all()}

        # Shifts Today - Sourced from Care Rota Planner Engine (Single Source of Truth)
        target_d = None
        if date_str and isinstance(date_str, str) and len(date_str) >= 10:
            try:
                target_d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass
        today = target_d or date.today()
        today_str = today.strftime("%Y-%m-%d")

        today_events = await get_events(
            start_date=today_str,
            end_date=today_str,
            db=db
        )
        shifts_today_count = len(today_events)

        # Today's Shift Allocation Status (Live DB Feed)
        # Sourced directly from Care Rota Planner schedules (m_transactions + dtr_user_shifts)
        display_events = today_events
        if not display_events:
            # Fallback to upcoming scheduled shifts across next 30 days to populate live feed
            upcoming_events = await get_events(
                start_date=today_str,
                end_date=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
                db=db
            )
            if not upcoming_events:
                # Secondary fallback to monthly range around current date
                upcoming_events = await get_events(
                    start_date=(today - timedelta(days=15)).strftime("%Y-%m-%d"),
                    end_date=(today + timedelta(days=15)).strftime("%Y-%m-%d"),
                    db=db
                )
            display_events = upcoming_events
            # If displaying upcoming fallback shifts, ensure KPI reflects the active allocation count
            if not shifts_today_count and display_events:
                shifts_today_count = len(display_events)

        now = datetime.now()
        recent_shifts: List[Dict[str, Any]] = []
        for ev in display_events[:10]:
            carer_name = ev.carer_name or f"Carer #{ev.user_id}"
            su_name = ev.service_user_name or (f"Client #{ev.su_id}" if ev.su_id else "Unassigned")
            branch_name = branch_map.get(ev.branch_id, "Barnes Branch")

            s_time = ev.shift_start or "08:00"
            e_time = ev.shift_end or "17:00"
            time_range = f"{s_time} - {e_time}"

            # Format status matching Dashboard tag colors
            raw_status = (ev.status or "Scheduled").strip()
            if raw_status in ("confirmed", "Scheduled"):
                try:
                    ev_end_dt = datetime.strptime(ev.end[:16], "%Y-%m-%d %H:%M")
                    ev_start_dt = datetime.strptime(ev.start[:16], "%Y-%m-%d %H:%M")
                    if ev_end_dt < now:
                        status = "Completed"
                    elif ev_start_dt <= now <= ev_end_dt:
                        status = "In Progress"
                    else:
                        status = "Scheduled"
                except Exception:
                    status = "Scheduled"
            elif raw_status == "Present":
                status = "In Progress"
            elif raw_status == "Unresolved Absence":
                status = "Unresolved Absence"
            else:
                status = raw_status.title()

            recent_shifts.append({
                "id": ev.id,
                "carer": carer_name,
                "serviceUser": su_name,
                "time": time_range,
                "branch": branch_name,
                "status": status
            })

        return {
            "active_clients": su_count,
            "carer_staff": carer_count,
            "shifts_today": shifts_today_count,
            "monthly_payroll": None,
            "recent_shifts": recent_shifts
        }
    except Exception as e:
        return {
            "active_clients": 0,
            "carer_staff": 0,
            "shifts_today": 0,
            "monthly_payroll": None,
            "recent_shifts": []
        }


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
OCCURRENCE_HISTORY_END = date(2026, 8, 31)


def _iso(day: date) -> str:
    return day.isoformat()


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value or "")[:10]
    return datetime.strptime(text_value, "%Y-%m-%d").date()


def _number(value):
    if value is None:
        return 0
    return float(value)


def _hhmm(value) -> str:
    if value is None:
        return ""
    if isinstance(value, timedelta):
        total = int(value.total_seconds()) % 86400
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    text_value = str(value).strip()
    if "T" in text_value or " " in text_value:
        return text_value.replace("T", " ")[11:16]
    return text_value[:5]


def _plain(value, limit=80) -> str:
    text_value = re.sub(r"<[^>]+>", " ", value or "")
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if len(text_value) <= limit:
        return text_value
    return text_value[: limit - 1].rstrip() + "…"


def _label(day: date, grain: str) -> str:
    if grain == "month":
        return f"{MONTHS[day.month - 1]} {day.year}"
    return f"{day.day} {MONTHS[day.month - 1]}"


def _bucket_start(day: date, grain: str) -> date:
    if grain == "week":
        return day - timedelta(days=day.weekday())
    if grain == "month":
        return day.replace(day=1)
    return day


def _buckets(start: date, end: date, grain: str):
    cursor = _bucket_start(start, grain)
    last = _bucket_start(end, grain)
    days = []
    while cursor <= last:
        days.append(cursor)
        if grain == "month":
            cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
        elif grain == "week":
            cursor += timedelta(days=7)
        else:
            cursor += timedelta(days=1)
    return days


def _period_window(period: str, today: date):
    if period == "daily":
        return today - timedelta(days=13), today, "day"
    if period == "weekly":
        return today - timedelta(weeks=11), today, "week"
    month = today.month - 11
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1), today, "month"


def _blank():
    return defaultdict(lambda: defaultdict(float))


def _add(bucket_map, day: date, grain: str, **values):
    key = _bucket_start(day, grain)
    for name, amount in values.items():
        bucket_map[key][name] += _number(amount)


def _pack(bucket_map, buckets, grain: str, fields):
    packed = {"labels": [_label(day, grain) for day in buckets]}
    for field in fields:
        packed[field] = [round(bucket_map[day][field], 1) for day in buckets]
    return packed


def _top_pairs(counter: Counter, limit=10):
    rows = [(name, count) for name, count in counter.most_common(limit) if name and count]
    return {"labels": [name for name, _count in rows], "values": [int(_count) for _name, _count in rows]}


def _rrule_weekdays(rule: str):
    match = re.search(r"BYDAY=([A-Z0-9,\-+]+)", (rule or "").upper())
    if not match:
        return None
    days = set()
    for token in match.group(1).split(","):
        code = re.sub(r"[^A-Z]", "", token)[-2:]
        if code in WEEKDAY:
            days.add(WEEKDAY[code])
    return days or None


def _parse_day(value):
    if value is None or value == "":
        return None
    try:
        return _as_date(value)
    except ValueError:
        return None


def _projected_dates(user_shift, range_start: date, range_end: date):
    start_day = _parse_day(user_shift.start_date)
    end_day = _parse_day(user_shift.end_date)
    if not start_day or start_day > range_end or (end_day and end_day < range_start):
        return []
    exceptions = set()
    if user_shift.recurrence_exception:
        for item in str(user_shift.recurrence_exception).split(","):
            cleaned = item.strip()
            if cleaned:
                exceptions.add(cleaned[:10].replace("-", ""))
    rule = (user_shift.rrule_str or "").strip()
    if rule:
        dates = expand_rrule_occurrences(
            start_date_str=start_day.isoformat(),
            end_date_str=end_day.isoformat() if end_day else "",
            rrule_str=rule,
            range_start=range_start,
            range_end=range_end,
        )
        weekdays = _rrule_weekdays(rule)
        if weekdays is not None:
            dates = [day for day in dates if day.weekday() in weekdays]
    else:
        first = max(range_start, start_day)
        last = range_end if end_day is None else min(range_end, end_day)
        dates = []
        cursor = first
        while cursor <= last:
            dates.append(cursor)
            cursor += timedelta(days=1)
    return [day for day in dates if range_start <= day <= range_end and day.strftime("%Y%m%d") not in exceptions]


def _person(first, last) -> str:
    return f"{first or ''} {last or ''}".strip() or "Unknown"


def _shift_status(event, now: datetime) -> str:
    raw_status = (event.status or "Scheduled").strip()
    if raw_status in ("confirmed", "Scheduled"):
        try:
            finished = datetime.strptime(event.end[:16], "%Y-%m-%d %H:%M")
            started = datetime.strptime(event.start[:16], "%Y-%m-%d %H:%M")
            if finished < now:
                return "Completed"
            if started <= now <= finished:
                return "In Progress"
        except Exception:
            return "Scheduled"
        return "Scheduled"
    if raw_status == "Present":
        return "In Progress"
    if raw_status == "Unresolved Absence":
        return "Unresolved Absence"
    return raw_status.title()


@router.get("/dashboard-analytics")
async def get_dashboard_analytics(
    period: str = Query("monthly"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Organisation analytics for administrators. Carers and staff receive 403."""
    if period not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=422, detail="Period must be daily, weekly, or monthly")
    today = date.today()
    start, end, grain = _period_window(period, today)
    params = {"start": _iso(start), "end": _iso(end), "today": _iso(today), "end_next": _iso(end + timedelta(days=1))}

    service_users = (await db.execute(select(func.count()).select_from(ServiceUser).where(ServiceUser.deleted_at.is_(None)))).scalar() or 0
    carers = (await db.execute(select(func.count()).select_from(User).where(User.deleted_at.is_(None), User.role == 3))).scalar() or 0
    attendance_today = (await db.execute(text("""
        SELECT COUNT(*) FROM dtr_attendances
        WHERE attendance_date = :today AND clock_in IS NOT NULL
    """), params)).scalar() or 0
    care_split = (await db.execute(text("""
        SELECT
          SUM(LOWER(COALESCE(sh.shift, '')) LIKE '%live in%' OR LOWER(COALESCE(sh.shift, '')) LIKE '%live out%') AS care_visits,
          SUM(NOT (LOWER(COALESCE(sh.shift, '')) LIKE '%live in%' OR LOWER(COALESCE(sh.shift, '')) LIKE '%live out%')) AS other_visits
        FROM m_transactions t
        LEFT JOIN m_shifts sh ON sh.shift_id = t.shift_id AND sh.deleted_at IS NULL
        WHERE t.deleted_at IS NULL
    """))).mappings().one()
    note_count = (await db.execute(text("SELECT COUNT(*) FROM m_notes"))).scalar() or 0
    requirements = (await db.execute(text("""
        SELECT COUNT(*) AS recorded, SUM(status = 1) AS complete
        FROM m_requirements_status
        WHERE deleted_at IS NULL
    """))).mappings().one()

    attendance_rows = (await db.execute(text("""
        SELECT attendance_date AS d,
               SUM(clock_in IS NOT NULL) AS clock_ins,
               SUM(clock_out IS NOT NULL) AS clock_outs,
               SUM(COALESCE(total_hours, 0)) AS hours,
               SUM(COALESCE(overtime_minutes, 0)) AS overtime_minutes
        FROM dtr_attendances
        WHERE attendance_date BETWEEN :start AND :end
        GROUP BY attendance_date
    """), params)).mappings().all()
    attendance_map = _blank()
    for row in attendance_rows:
        _add(
            attendance_map, _as_date(row["d"]), grain,
            clock_ins=row["clock_ins"], clock_outs=row["clock_outs"],
            hours=row["hours"], overtime_hours=_number(row["overtime_minutes"]) / 60,
        )

    charge_rows = (await db.execute(text("""
        SELECT DATE(start) AS d, COUNT(*) AS visits,
               SUM(CASE WHEN end IS NOT NULL AND end > start THEN TIMESTAMPDIFF(MINUTE, start, end) ELSE 0 END) AS minutes,
               SUM(payroll IS NOT NULL AND payroll <> '') AS payrolls,
               SUM(invoice IS NOT NULL AND invoice <> '') AS invoices
        FROM m_transactions
        WHERE deleted_at IS NULL AND start >= :start AND start < :end_next
        GROUP BY DATE(start)
    """), params)).mappings().all()
    charge_map = _blank()
    for row in charge_rows:
        _add(
            charge_map, _as_date(row["d"]), grain,
            visits=row["visits"], scheduled_hours=_number(row["minutes"]) / 60,
            payrolls=row["payrolls"], invoices=row["invoices"],
        )

    quality_rows = (await db.execute(text("""
        SELECT o.occurrence_date AS d, COUNT(*) AS scheduled,
               SUM(COALESCE(a.has_in, 0)) AS attended
        FROM dtr_shift_occurrences o
        LEFT JOIN (
            SELECT user_id, attendance_date,
                   MAX(clock_in IS NOT NULL) AS has_in,
                   MAX(clock_out IS NOT NULL) AS has_out
            FROM dtr_attendances
            WHERE attendance_date BETWEEN :start AND :end
            GROUP BY user_id, attendance_date
        ) a ON a.user_id = o.user_id AND DATE_FORMAT(a.attendance_date, '%Y-%m-%d') = LEFT(o.occurrence_date, 10)
        WHERE LEFT(o.occurrence_date, 10) BETWEEN :start AND :end
          AND COALESCE(o.is_deleted, 0) = 0
        GROUP BY o.occurrence_date
    """), params)).mappings().all()
    quality_map = _blank()
    for row in quality_rows:
        day = _as_date(row["d"])
        scheduled = _number(row["scheduled"])
        attended = _number(row["attended"])
        missed = max(scheduled - attended, 0) if day < today else 0
        _add(quality_map, day, grain, attended=attended, missed=missed)

    late_rows = (await db.execute(text("""
        SELECT o.occurrence_date AS d, COUNT(DISTINCT o.id) AS late
        FROM dtr_shift_occurrences o
        JOIN dtr_attendances a ON a.user_id = o.user_id AND DATE_FORMAT(a.attendance_date, '%Y-%m-%d') = LEFT(o.occurrence_date, 10)
        JOIN dtr_occurrence_service_users osu ON osu.shift_occurrence_id = o.id
        WHERE LEFT(o.occurrence_date, 10) BETWEEN :start AND :end
          AND COALESCE(o.is_deleted, 0) = 0
          AND a.clock_in IS NOT NULL
          AND osu.start_date IS NOT NULL
          AND TIME(a.clock_in) > TIME(osu.start_date)
        GROUP BY o.occurrence_date
    """), params)).mappings().all()
    for row in late_rows:
        _add(quality_map, _as_date(row["d"]), grain, late=row["late"])

    status_row = (await db.execute(text("""
        SELECT
          SUM(COALESCE(a.has_out, 0) = 1) AS completed,
          SUM(COALESCE(a.has_in, 0) = 1 AND COALESCE(a.has_out, 0) = 0) AS active,
          SUM(COALESCE(a.has_in, 0) = 0 AND LEFT(o.occurrence_date, 10) < :today) AS missed,
          SUM(COALESCE(a.has_in, 0) = 0 AND LEFT(o.occurrence_date, 10) >= :today) AS scheduled
        FROM dtr_shift_occurrences o
        LEFT JOIN (
            SELECT user_id, attendance_date,
                   MAX(clock_in IS NOT NULL) AS has_in,
                   MAX(clock_out IS NOT NULL) AS has_out
            FROM dtr_attendances
            WHERE attendance_date BETWEEN :start AND :end
            GROUP BY user_id, attendance_date
        ) a ON a.user_id = o.user_id AND DATE_FORMAT(a.attendance_date, '%Y-%m-%d') = LEFT(o.occurrence_date, 10)
        WHERE LEFT(o.occurrence_date, 10) BETWEEN :start AND :end
          AND COALESCE(o.is_deleted, 0) = 0
    """), params)).mappings().one()
    visit_status = {key: int(_number(status_row[key])) for key in ("scheduled", "active", "completed", "missed")}

    visit_counter = Counter()
    for row in (await db.execute(text("""
        SELECT TRIM(CONCAT(COALESCE(su.su_first_name, ''), ' ', COALESCE(su.su_last_name, ''))) AS name, COUNT(*) AS visits
        FROM dtr_shift_occurrences o
        JOIN dtr_occurrence_service_users osu ON osu.shift_occurrence_id = o.id
        JOIN m_service_users su ON su.su_id = osu.su_id
        WHERE LEFT(o.occurrence_date, 10) BETWEEN :start AND :end
          AND COALESCE(o.is_deleted, 0) = 0
        GROUP BY su.su_id, su.su_first_name, su.su_last_name
    """), params)).mappings().all():
        visit_counter[row["name"] or "Unassigned"] += int(_number(row["visits"]))

    workload_hours = {}
    for row in (await db.execute(text("""
        SELECT u.id AS user_id,
               TRIM(CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.surname, ''))) AS name,
               SUM(COALESCE(a.total_hours, 0)) AS hours
        FROM dtr_attendances a
        JOIN users u ON u.id = a.user_id
        WHERE a.attendance_date BETWEEN :start AND :end
        GROUP BY u.id, u.first_name, u.surname
    """), params)).mappings().all():
        workload_hours[row["user_id"]] = {"name": row["name"] or "Unknown", "hours": _number(row["hours"]), "visits": 0}
    for row in (await db.execute(text("""
        SELECT o.user_id AS user_id, COUNT(*) AS visits
        FROM dtr_shift_occurrences o
        WHERE LEFT(o.occurrence_date, 10) BETWEEN :start AND :end
          AND COALESCE(o.is_deleted, 0) = 0
        GROUP BY o.user_id
    """), params)).mappings().all():
        entry = workload_hours.setdefault(row["user_id"], {"name": f"Carer {row['user_id']}", "hours": 0, "visits": 0})
        entry["visits"] += int(_number(row["visits"]))

    gap_start = max(start, OCCURRENCE_HISTORY_END + timedelta(days=1))
    if gap_start <= end:
        clocks = {}
        for row in (await db.execute(text("""
            SELECT user_id, attendance_date,
                   MAX(clock_in IS NOT NULL) AS has_in,
                   MAX(clock_out IS NOT NULL) AS has_out
            FROM dtr_attendances
            WHERE attendance_date BETWEEN :gap_start AND :end
            GROUP BY user_id, attendance_date
        """), {**params, "gap_start": _iso(gap_start)})).mappings().all():
            clocks[(row["user_id"], _as_date(row["attendance_date"]))] = (int(row["has_in"] or 0), int(row["has_out"] or 0))
        shift_result = await db.execute(
            select(DtrUserShift).where(
                func.date(DtrUserShift.start_date) <= end,
                or_(DtrUserShift.end_date.is_(None), func.date(DtrUserShift.end_date) >= gap_start),
            )
        )
        seen_projected = set()
        for user_shift in shift_result.scalars().unique().all():
            service_name = _person(
                getattr(user_shift.service_user, "first_name", None),
                getattr(user_shift.service_user, "surname", None),
            ) if user_shift.service_user else ("Unassigned" if not user_shift.su_id else f"Service user {user_shift.su_id}")
            carer_name = _person(
                getattr(user_shift.carer, "first_name", None),
                getattr(user_shift.carer, "surname", None),
            ) if user_shift.carer else f"Carer {user_shift.user_id}"
            for day in _projected_dates(user_shift, gap_start, end):
                key = (user_shift.user_id, user_shift.su_id, day.isoformat(), user_shift.start_time, user_shift.end_time)
                if key in seen_projected:
                    continue
                seen_projected.add(key)
                has_in, has_out = clocks.get((user_shift.user_id, day), (0, 0))
                if has_out:
                    visit_status["completed"] += 1
                    _add(quality_map, day, grain, attended=1)
                elif has_in:
                    visit_status["active"] += 1
                    _add(quality_map, day, grain, attended=1)
                elif day < today:
                    visit_status["missed"] += 1
                    _add(quality_map, day, grain, missed=1)
                else:
                    visit_status["scheduled"] += 1
                visit_counter[service_name] += 1
                entry = workload_hours.setdefault(user_shift.user_id, {"name": carer_name, "hours": 0, "visits": 0})
                entry["visits"] += 1

    buckets = _buckets(start, end, grain)
    delivery_map = _blank()
    for day in buckets:
        scheduled_hours = charge_map[day]["scheduled_hours"]
        completed_hours = attendance_map[day]["hours"]
        _add(
            delivery_map, day, grain,
            scheduled_hours=scheduled_hours,
            completed_hours=completed_hours,
            missed_hours=max(scheduled_hours - completed_hours, 0),
            overtime_hours=attendance_map[day]["overtime_hours"],
        )

    note_map = _blank()
    for row in (await db.execute(text("""
        SELECT DATE(COALESCE(created_at, updated_at)) AS d, COUNT(*) AS notes
        FROM m_notes
        WHERE COALESCE(created_at, updated_at) >= :start
          AND COALESCE(created_at, updated_at) < :end_next
        GROUP BY DATE(COALESCE(created_at, updated_at))
    """), params)).mappings().all():
        if row["d"]:
            _add(note_map, _as_date(row["d"]), grain, notes=row["notes"])
    notes_by_carer = Counter()
    for row in (await db.execute(text("""
        SELECT TRIM(CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.surname, ''))) AS name, COUNT(*) AS notes
        FROM m_notes n
        LEFT JOIN users u ON u.id = n.user_id
        WHERE COALESCE(n.created_at, n.updated_at) >= :start
          AND COALESCE(n.created_at, n.updated_at) < :end_next
        GROUP BY n.user_id, u.first_name, u.surname
        ORDER BY notes DESC
        LIMIT 10
    """), params)).mappings().all():
        notes_by_carer[row["name"] or "Unknown"] = int(_number(row["notes"]))
    notes_by_service_user = Counter()
    for row in (await db.execute(text("""
        SELECT TRIM(CONCAT(COALESCE(su.su_first_name, ''), ' ', COALESCE(su.su_last_name, ''))) AS name, COUNT(*) AS notes
        FROM m_notes n
        LEFT JOIN m_service_users su ON su.su_id = n.su_id
        WHERE COALESCE(n.created_at, n.updated_at) >= :start
          AND COALESCE(n.created_at, n.updated_at) < :end_next
        GROUP BY n.su_id, su.su_first_name, su.su_last_name
        ORDER BY notes DESC
        LIMIT 10
    """), params)).mappings().all():
        notes_by_service_user[row["name"] or "Unknown"] = int(_number(row["notes"]))

    workload = sorted(workload_hours.values(), key=lambda item: (item["hours"], item["visits"]), reverse=True)[:10]
    recent_attendance = []
    for row in (await db.execute(text("""
        SELECT a.attendance_date, a.clock_in, a.clock_out, a.total_hours, u.first_name, u.surname
        FROM dtr_attendances a
        JOIN users u ON u.id = a.user_id
        ORDER BY a.attendance_date DESC, a.id DESC
        LIMIT 8
    """))).mappings().all():
        clock_in = _hhmm(row["clock_in"])
        clock_out = _hhmm(row["clock_out"])
        recent_attendance.append({
            "date": _iso(_as_date(row["attendance_date"])),
            "carer": _person(row["first_name"], row["surname"]),
            "clock_in": clock_in,
            "clock_out": clock_out,
            "total_hours": None if row["total_hours"] is None else round(_number(row["total_hours"]), 2),
            "status": "Completed" if clock_in and clock_out else ("Clocked in" if clock_in else "Recorded"),
        })
    recent_notes = []
    for row in (await db.execute(text("""
        SELECT COALESCE(n.created_at, n.updated_at) AS stamp, n.notes,
               u.first_name, u.surname, su.su_first_name, su.su_last_name
        FROM m_notes n
        LEFT JOIN users u ON u.id = n.user_id
        LEFT JOIN m_service_users su ON su.su_id = n.su_id
        WHERE COALESCE(n.created_at, n.updated_at) IS NOT NULL
        ORDER BY COALESCE(n.created_at, n.updated_at) DESC, n.id DESC
        LIMIT 8
    """))).mappings().all():
        recent_notes.append({
            "when": row["stamp"].replace(tzinfo=None).isoformat(timespec="seconds") if isinstance(row["stamp"], datetime) else str(row["stamp"]),
            "author": _person(row["first_name"], row["surname"]),
            "service_user": _person(row["su_first_name"], row["su_last_name"]),
            "excerpt": _plain(row["notes"]),
        })

    branches = {branch.branch_id: branch.branch_name for branch in (await db.execute(select(Branch))).scalars().all()}
    today_events = await get_events(start_date=_iso(today), end_date=_iso(today), db=db)
    now = datetime.now()
    recent_shifts = []
    for event in today_events[:30]:
        recent_shifts.append({
            "id": event.id,
            "carer": event.carer_name or f"Carer {event.user_id}",
            "serviceUser": event.service_user_name or "Unassigned",
            "time": f"{event.shift_start or '08:00'} - {event.shift_end or '17:00'}",
            "branch": branches.get(event.branch_id, "Unassigned branch"),
            "status": _shift_status(event, now),
        })

    return {
        "period": period,
        "start": _iso(start),
        "end": _iso(end),
        "kpis": {
            "service_users": int(service_users),
            "carers": int(carers),
            "active_shifts": len(today_events),
            "attendance_today": int(attendance_today),
            "care_visits": int(_number(care_split["care_visits"])),
            "other_visits": int(_number(care_split["other_visits"])),
            "care_notes": int(note_count),
            "requirements_complete": int(_number(requirements["complete"])),
            "requirements_recorded": int(_number(requirements["recorded"])),
        },
        "attendance": _pack(attendance_map, buckets, grain, ["clock_ins", "clock_outs", "hours"]),
        "attendance_quality": _pack(quality_map, buckets, grain, ["attended", "missed", "late"]),
        "visits_by_service_user": _top_pairs(visit_counter),
        "visit_status": visit_status,
        "notes_by_day": _pack(note_map, buckets, grain, ["notes"]),
        "notes_by_carer": _top_pairs(notes_by_carer),
        "notes_by_service_user": _top_pairs(notes_by_service_user),
        "workload": {
            "labels": [item["name"] for item in workload],
            "hours": [round(item["hours"], 1) for item in workload],
            "visits": [int(item["visits"]) for item in workload],
        },
        "delivery": _pack(delivery_map, buckets, grain, ["scheduled_hours", "completed_hours", "missed_hours", "overtime_hours"]),
        "charges": _pack(charge_map, buckets, grain, ["visits", "payrolls", "invoices"]),
        "recent_attendance": recent_attendance,
        "recent_notes": recent_notes,
        "recent_shifts": recent_shifts,
    }
