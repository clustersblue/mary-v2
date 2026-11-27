import os
import re
import random
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, and_, or_, func
from datetime import datetime, date, time as time_type, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.db.session import get_db
from app.models.attendance import DtrAttendance
from app.models.service_user import ServiceUser
from app.models.shift import DtrShiftOccurrence, DtrShift, DtrOccurrenceServiceUser, DtrUserShift
from app.models.user import User
from app.models.master_data import MNotes, UploadedFile
from app.schemas.attendance import (
    ClockInRequest, ClockOutRequest, AttendanceOut, CareNoteGenerateRequest, ManualDtrRequest, ManualDtrServiceUser
)
from app.services.pdf_generator import generate_care_note_pdf
from app.services.excel_import import parse_dtr_excel
from app.services.ai_care_plan import call_ai_model
from app.services.visit_section_xii import resolve_visit_window
from app.services.recurrence import expand_rrule_occurrences
from app.core.security import get_current_active_user, get_current_staff_user, get_current_admin_user, is_staff_user
from app.services.audit import actor_name, log_audit_event
from app.services.audit_subject import subject_for_filename
from app.services.care_note_access import carer_owns_care_note, safe_care_note_name

router = APIRouter()

CARE_NOTES_DIR = os.path.join(os.getcwd(), "storage", "care_notes")
DOCUMENTS_DIR = os.path.join(os.getcwd(), "storage", "app", "documents")
APP_STORAGE_DIR = os.path.join(os.getcwd(), "storage", "app")

os.makedirs(CARE_NOTES_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

def find_care_note_file(su_num: str, su_id: int, date_str: str) -> Optional[str]:
    try:
        if "-" in date_str:
            formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%y")
        else:
            formatted_date = date_str
    except Exception:
        formatted_date = date_str

    su_padded = str(su_num).zfill(5)

    search_dirs = [CARE_NOTES_DIR, DOCUMENTS_DIR, APP_STORAGE_DIR]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".pdf"):
                continue
            if formatted_date in f:
                if f.startswith(f"su_{su_padded}_") or f.startswith(f"su_{su_num}_") or f"su_{su_id}_" in f:
                    return f
    return None

class DummyTimeRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    user_id: Optional[int] = None
    branch_id: Optional[int] = None

class ResetAttendanceRequest(BaseModel):
    user_id: int
    shift_id: int
    attendance_date: str
    target_type: str = "all" # main, service_user, all
    target_id: Optional[int] = None
    clear_type: str = "both" # in, out, both

class CareNoteGenerateDetailedRequest(BaseModel):
    su_id: Optional[int] = None
    user_id: Optional[int] = None
    date: str
    shift: Optional[str] = "LD"
    time_in: Optional[str] = "08:00"
    time_out: Optional[str] = "17:00"
    patient_name: Optional[str] = "Service User"
    carer_name: Optional[str] = "Carer Staff"
    clinical_notes: Optional[str] = ""
    visit_id: Optional[int] = None
    visit_clock_in: Optional[str] = None
    visit_clock_out: Optional[str] = None
    scheduled_visit_start: Optional[str] = None
    scheduled_visit_end: Optional[str] = None

def _as_time(value):
    """dtr_attendances stores clock_in and clock_out as TIME. MySQL returns timedelta."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, time_type):
        return value.replace(microsecond=0)
    if isinstance(value, timedelta):
        total = int(value.total_seconds()) % (24 * 3600)
        return time_type(total // 3600, (total % 3600) // 60, total % 60)
    return None

def _attendance_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    return date.today()

def _day_key(value) -> str:
    """Match attendance dates to shift dates as YYYY-MM-DD."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")[:10]

def _combine_clock(day, value):
    clock = _as_time(value)
    if not clock:
        return None
    return datetime.combine(_attendance_day(day), clock)

def _clock_iso(day, value):
    combined = _combine_clock(day, value)
    return combined.strftime("%Y-%m-%dT%H:%M:%S") if combined else None

def _attendance_out(att: DtrAttendance) -> dict:
    return {
        "id": att.id,
        "user_id": att.user_id,
        "su_id": None,
        "shift_id": att.shift_id,
        "clock_in": _combine_clock(att.attendance_date, att.clock_in),
        "clock_out": _combine_clock(att.attendance_date, att.clock_out),
        "clock_in_lat": None,
        "clock_in_lon": None,
        "clock_in_distance_meters": None,
        "status": "open" if att.clock_in and not att.clock_out else ("complete" if att.clock_out else None),
        "notes": None,
        "created_at": att.created_at,
        "carer": None,
        "service_user": None,
    }

@router.post("/attendances/timein", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
async def time_in(
    data: ClockInRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # This portal always records the signed-in user. A supplied user_id is ignored.
    today = date.today()
    res = await db.execute(
        select(DtrAttendance).where(
            DtrAttendance.user_id == current_user.id,
            DtrAttendance.attendance_date == today,
        )
    )
    att = res.scalars().first()
    if att and att.clock_in and not att.clock_out:
        raise HTTPException(status_code=409, detail="You are already clocked in.")
    if att and att.clock_in and att.clock_out:
        raise HTTPException(status_code=409, detail="Today's attendance is already complete.")
    shift_id = None
    if data.shift_id:
        shift_ok = await db.execute(select(DtrShift.id).where(DtrShift.id == data.shift_id))
        if shift_ok.scalar_one_or_none() is not None:
            shift_id = data.shift_id
    if not att:
        att = DtrAttendance(
            user_id=current_user.id,
            shift_id=shift_id,
            attendance_date=date.today(),
            clock_in=_as_time(datetime.now()),
        )
        db.add(att)
    else:
        att.clock_in = _as_time(datetime.now())
        if shift_id:
            att.shift_id = shift_id
    await db.commit()
    await db.refresh(att)
    return _attendance_out(att)

@router.post("/attendances/timeout", response_model=AttendanceOut)
async def time_out(
    data: ClockOutRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(DtrAttendance).where(DtrAttendance.id == data.attendance_id))
    att = res.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if att.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only clock out of your own attendance record.")
    if not att.clock_in or att.clock_out:
        raise HTTPException(status_code=409, detail="There is no open attendance session to clock out.")

    started = _combine_clock(att.attendance_date, att.clock_in)
    finished = datetime.now().replace(microsecond=0)
    if started and finished < started:
        finished = finished + timedelta(days=1)
    att.clock_out = _as_time(finished)
    if started:
        diff_mins = (finished - started).total_seconds() / 60.0
        att.total_hours = round(max(0, diff_mins / 60.0), 2)
    await db.commit()
    await db.refresh(att)
    return _attendance_out(att)

@router.get("/attendances/session")
async def current_attendance_session(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()
    res = await db.execute(
        select(DtrAttendance).where(
            DtrAttendance.user_id == current_user.id,
            DtrAttendance.attendance_date == today,
        )
    )
    att = res.scalars().first()
    if not att:
        return {"attendance_id": None, "clock_in": None, "clock_out": None, "attendance_date": today.isoformat()}
    return {
        "attendance_id": att.id,
        "clock_in": _clock_iso(att.attendance_date, att.clock_in),
        "clock_out": _clock_iso(att.attendance_date, att.clock_out),
        "attendance_date": today.isoformat(),
    }

class VisitLogRequest(BaseModel):
    su_id: Optional[int] = None
    notes: str

def _note_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None).isoformat(timespec="seconds")
    if isinstance(value, date):
        return datetime.combine(value, time_type.min).isoformat(timespec="seconds")
    text = str(value).strip()
    if not text or text.startswith("0000-00-00"):
        return None
    return text.replace(" ", "T", 1)

NO_ACTIVE_SHIFT_DETAIL = (
    "Unable to save Care Note.\n"
    "No active shift or assigned Service User was found.\n"
    "Please Clock In before creating Care Notes."
)

def _note_row(note: MNotes, author: Optional[User], service_user: Optional[ServiceUser] = None) -> dict:
    created_at = _note_iso(note.created_at) or _note_iso(note.updated_at)
    service_name = ""
    if service_user:
        service_name = f"{service_user.first_name or ''} {service_user.surname or ''}".strip()
    return {
        "id": note.id,
        "user_id": note.user_id,
        "su_id": note.su_id,
        "notes": note.notes,
        "created_at": created_at,
        "updated_at": _note_iso(note.updated_at),
        "user": {
            "id": note.user_id,
            "first_name": author.first_name if author else "",
            "surname": author.surname if author else "",
        },
        "service_user": {
            "su_id": note.su_id,
            "full_name": service_name,
        },
    }

async def _active_shift_su(db: AsyncSession, user_id: int) -> Optional[int]:
    """Service user on today's shift. Older assignments are not treated as active."""
    today = date.today().isoformat()
    occ = await db.execute(
        select(DtrOccurrenceServiceUser.su_id)
        .join(DtrShiftOccurrence, DtrOccurrenceServiceUser.shift_occurrence_id == DtrShiftOccurrence.id)
        .where(
            DtrShiftOccurrence.user_id == user_id,
            DtrShiftOccurrence.occurrence_date == today,
        )
        .order_by(DtrOccurrenceServiceUser.id.asc())
        .limit(1)
    )
    su_id = occ.scalar_one_or_none()
    if su_id:
        return su_id
    current_shift = await db.execute(
        select(DtrUserShift.su_id)
        .where(
            DtrUserShift.user_id == user_id,
            DtrUserShift.su_id.is_not(None),
            func.date(DtrUserShift.start_date) <= today,
            or_(DtrUserShift.end_date.is_(None), func.date(DtrUserShift.end_date) >= today),
        )
        .order_by(DtrUserShift.start_date.desc(), DtrUserShift.id.asc())
        .limit(1)
    )
    return current_shift.scalar_one_or_none()

async def _open_attendance(db: AsyncSession, user_id: int) -> Optional[DtrAttendance]:
    res = await db.execute(
        select(DtrAttendance).where(
            DtrAttendance.user_id == user_id,
            DtrAttendance.attendance_date == date.today(),
        )
    )
    att = res.scalars().first()
    if att and att.clock_in and not att.clock_out:
        return att
    return None

def _notes_query(su_id: int):
    return (
        select(MNotes, User, ServiceUser)
        .join(User, User.id == MNotes.user_id, isouter=True)
        .join(ServiceUser, ServiceUser.su_id == MNotes.su_id, isouter=True)
        .where(MNotes.su_id == su_id)
        .order_by(func.coalesce(MNotes.created_at, MNotes.updated_at).desc(), MNotes.id.desc())
    )

@router.get("/attendances/visit-notes")
async def list_visit_notes(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    su_id = await _active_shift_su(db, current_user.id)
    if not su_id:
        return []
    result = await db.execute(_notes_query(su_id))
    return [_note_row(note, author, service_user) for note, author, service_user in result.all()]

@router.post("/attendances/visit-log")
async def save_visit_log(
    data: VisitLogRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    notes = (data.notes or "").strip()
    if not notes:
        raise HTTPException(status_code=422, detail="Care notes are required")
    if not await _open_attendance(db, current_user.id):
        raise HTTPException(status_code=422, detail=NO_ACTIVE_SHIFT_DETAIL)
    su_id = await _active_shift_su(db, current_user.id)
    if not su_id:
        raise HTTPException(status_code=422, detail=NO_ACTIVE_SHIFT_DETAIL)
    item = MNotes(user_id=current_user.id, su_id=su_id, notes=notes)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    service_user = await db.get(ServiceUser, su_id)
    row = _note_row(item, current_user, service_user)
    row["success"] = True
    return row

class VisitNoteUpdate(BaseModel):
    notes: str

@router.post("/attendances/visit-notes/{note_id}")
async def update_visit_note(
    note_id: int,
    data: VisitNoteUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    notes = (data.notes or "").strip()
    if not notes:
        raise HTTPException(status_code=422, detail="Note cannot be empty")
    result = await db.execute(select(MNotes).where(MNotes.id == note_id, MNotes.user_id == current_user.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Note not found")
    item.notes = notes
    await db.commit()
    return {"success": True}

@router.delete("/attendances/visit-notes/{note_id}")
async def delete_visit_note(
    note_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MNotes).where(MNotes.id == note_id, MNotes.user_id == current_user.id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}

def _hhmm_text(value, fallback=""):
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        return text[:5] if len(text) >= 5 and text[2] == ":" else text
    clock = _as_time(value)
    return clock.strftime("%H:%M") if clock else fallback

def _month_bounds(day: date):
    start = day.replace(day=1)
    if start.month == 12:
        next_month = date(start.year + 1, 1, 1)
    else:
        next_month = date(start.year, start.month + 1, 1)
    return start, next_month - timedelta(days=1)

def _history_start(month_start: date) -> date:
    month = month_start.month - 3
    year = month_start.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)

def _parse_shift_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None

def _clock_hhmm(value) -> str:
    clock = _as_time(value)
    return clock.strftime("%H:%M") if clock else ""

def _worked_status(clock_in: str, clock_out: str, fallback: str = "Scheduled") -> str:
    if clock_in and clock_out:
        return "Completed"
    if clock_in:
        return "Clocked in"
    return fallback

def _shift_window(user_shift: DtrUserShift):
    """Employee schedule from the shift template, for example 8AM - 8PM is 08:00-20:00.

    Assignment start_time/end_time can be a short visit window. Those must not
    replace the scheduled shift shown on the Daily Time Record.
    """
    template = user_shift.shift_template if user_shift is not None else None
    start = _hhmm_text(getattr(template, "start_time", None)) if template is not None else ""
    end = _hhmm_text(getattr(template, "end_time", None)) if template is not None else ""
    if not start:
        start = _hhmm_text(user_shift.start_time)
    if not end:
        end = _hhmm_text(user_shift.end_time)
    return start or "08:00", end or "17:00"

def _template_shift_code(user_shift: DtrUserShift) -> str:
    template = user_shift.shift_template if user_shift is not None else None
    if template is None:
        return ""
    return getattr(template, "shift_code", None) or getattr(template, "shift_name", None) or ""

# Employee clocks stay inside this many minutes of the scheduled shift.
# Visit clocks stay inside this many minutes of the scheduled visit.
# Clock in is early or on time. Clock out is on time or later.
EMPLOYEE_CLOCK_VARIANCE_MINUTES = 8
VISIT_CLOCK_VARIANCE_MINUTES = 5

def _combine_hhmm(day: date, hhmm: str) -> datetime:
    text = _hhmm_text(hhmm, "00:00")
    hour = int(text[:2])
    minute = int(text[3:5]) if len(text) >= 5 else 0
    return datetime(day.year, day.month, day.day, hour, minute)

def _schedule_span(day: date, start_hhmm: str, end_hhmm: str):
    start = _combine_hhmm(day, start_hhmm)
    end = _combine_hhmm(day, end_hhmm)
    if end <= start:
        end += timedelta(days=1)
    return start, end

def _vary_clock(moment: datetime, variance_minutes: int, edge: str) -> datetime:
    """edge 'in' is at or before the schedule. edge 'out' is at or after it."""
    if edge == "in":
        delta = random.randint(-variance_minutes, 0)
    else:
        delta = random.randint(0, variance_minutes)
    return (moment + timedelta(minutes=delta)).replace(second=0, microsecond=0)

def _stored_moment(value, day: date, fallback_hhmm: str):
    if isinstance(value, datetime):
        return value.replace(second=0, microsecond=0)
    if fallback_hhmm:
        return _combine_hhmm(day, fallback_hhmm)
    return None

def _duration_hours(started: datetime, finished: datetime) -> float:
    if finished <= started:
        finished += timedelta(days=1)
    return round(max(0, (finished - started).total_seconds() / 3600.0), 2)

def _user_shift_dates(user_shift: DtrUserShift, range_start: date, range_end: date):
    """Dates the DTR projection shows for one series. Matches expand_rrule_occurrences."""
    start_day = _parse_shift_day(user_shift.start_date)
    end_day = _parse_shift_day(user_shift.end_date)
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
    else:
        dates = expand_rrule_occurrences(
            start_date_str=start_day.isoformat(),
            end_date_str=end_day.isoformat() if end_day else "",
            rrule_str="",
            range_start=range_start,
            range_end=range_end,
        )
    return [day for day in dates if range_start <= day <= range_end and day.strftime("%Y%m%d") not in exceptions]

async def _resolve_user_shift(db: AsyncSession, user_id: int, day_str: str, shift_id: Optional[int], explicit_id: Optional[int]):
    """Series row that produces this DTR day. The occurrence table requires it."""
    day = datetime.strptime(day_str[:10], "%Y-%m-%d").date()

    def covers(row: DtrUserShift) -> bool:
        if (row.status or "").lower() == "cancelled":
            return False
        return day in _user_shift_dates(row, day, day)

    if explicit_id:
        chosen_result = await db.execute(
            select(DtrUserShift).where(
                DtrUserShift.id == explicit_id,
                DtrUserShift.user_id == user_id,
            )
        )
        chosen = chosen_result.scalars().first()
        if chosen is not None and covers(chosen):
            return chosen

    result = await db.execute(select(DtrUserShift).where(DtrUserShift.user_id == user_id))
    matches = [row for row in result.scalars().unique().all() if covers(row)]
    if shift_id:
        for row in matches:
            if row.shift_id == shift_id:
                return row
    return matches[0] if matches else None

def _assigned_service_user(user_shift: DtrUserShift) -> str:
    service_user = user_shift.service_user
    if service_user:
        name = f"{service_user.first_name or ''} {service_user.surname or ''}".strip()
        if name:
            return name
    if user_shift.su_id:
        return f"Service user {user_shift.su_id}"
    return "No service user assigned"

def _rrule_weekdays(rule: str):
    match = re.search(r"BYDAY=([A-Z0-9,\-+]+)", rule.upper())
    if not match:
        return None
    names = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
    days = set()
    for token in match.group(1).split(","):
        code = re.sub(r"[^A-Z]", "", token)[-2:]
        if code in names:
            days.add(names[code])
    return days or None

def _schedule_dates(user_shift: DtrUserShift, month_start: date, month_end: date):
    start_day = _parse_shift_day(user_shift.start_date)
    end_day = _parse_shift_day(user_shift.end_date)
    if not start_day or start_day > month_end:
        return []
    if end_day and end_day < month_start:
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
            range_start=month_start,
            range_end=month_end,
        )
        weekdays = _rrule_weekdays(rule)
        if weekdays is not None:
            dates = [day for day in dates if day.weekday() in weekdays]
    else:
        first = max(month_start, start_day)
        last = month_end if end_day is None else min(month_end, end_day)
        dates = []
        cursor = first
        while cursor <= last:
            dates.append(cursor)
            cursor += timedelta(days=1)
    return [day for day in dates if month_start <= day <= month_end and day.strftime("%Y%m%d") not in exceptions]

@router.get("/attendances/my-history")
async def my_attendance_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Attendance clocks and this month's rota for the signed-in user only."""
    today = date.today()
    month_start, month_end = _month_bounds(today)
    attendance_start = _history_start(month_start)

    attendance_result = await db.execute(
        select(DtrAttendance)
        .where(
            DtrAttendance.user_id == current_user.id,
            DtrAttendance.attendance_date >= attendance_start,
            DtrAttendance.attendance_date <= today,
        )
        .order_by(DtrAttendance.attendance_date.desc(), DtrAttendance.id.desc())
    )
    attendance_rows = []
    clocks_by_day = {}
    for att in attendance_result.scalars().unique().all():
        day = _day_key(att.attendance_date)
        clock_in = _clock_hhmm(att.clock_in)
        clock_out = _clock_hhmm(att.clock_out)
        hours = None if att.total_hours is None else round(float(att.total_hours), 2)
        row = {
            "date": day,
            "clock_in": clock_in,
            "clock_out": clock_out,
            "total_hours": hours,
            "status": _worked_status(clock_in, clock_out, "Recorded"),
        }
        attendance_rows.append(row)
        clocks_by_day.setdefault(day, row)

    shift_result = await db.execute(
        select(DtrUserShift)
        .where(DtrUserShift.user_id == current_user.id)
        .order_by(DtrUserShift.start_date.asc(), DtrUserShift.id.asc())
    )
    schedules = []
    seen = set()
    for user_shift in shift_result.scalars().unique().all():
        start_time, end_time = _shift_window(user_shift)
        service_user = _assigned_service_user(user_shift)
        shift_status = (user_shift.status or "").strip().lower()
        fallback = "Cancelled" if shift_status == "cancelled" else "Scheduled"
        for day in _schedule_dates(user_shift, month_start, month_end):
            key = (day.isoformat(), user_shift.su_id, start_time, end_time)
            if key in seen:
                continue
            seen.add(key)
            clocks = clocks_by_day.get(day.isoformat(), {})
            schedules.append({
                "date": day.isoformat(),
                "service_user": service_user,
                "scheduled_start": start_time,
                "scheduled_end": end_time,
                "clock_in": clocks.get("clock_in", ""),
                "clock_out": clocks.get("clock_out", ""),
                "status": _worked_status(clocks.get("clock_in", ""), clocks.get("clock_out", ""), fallback),
            })
    schedules.sort(key=lambda row: (row["date"], row["scheduled_start"], row["scheduled_end"], row["service_user"]))
    return {
        "month": month_start.strftime("%Y-%m"),
        "attendance": attendance_rows,
        "schedules": schedules,
    }

class AttendanceReportRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    branch_id: Optional[int] = None
    search: Optional[str] = None
    service_user_id: Optional[int] = None
    user_id: Optional[int] = None

@router.post("/attendances/report")
async def get_attendance_report(
    req: AttendanceReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    start_date = req.start or "2026-07-01"
    end_date = req.end or "2026-07-31"

    # Enforce field carer scoping: Carers can only retrieve their own attendance report
    target_user_id = current_user.id if getattr(current_user, "role", None) == 3 else req.user_id

    from sqlalchemy.orm import selectinload
    stmt = (
        select(DtrShiftOccurrence)
        .options(
            selectinload(DtrShiftOccurrence.carer),
            selectinload(DtrShiftOccurrence.shift),
            selectinload(DtrShiftOccurrence.service_users_assoc).selectinload(DtrOccurrenceServiceUser.service_user)
        )
        .join(User, DtrShiftOccurrence.user_id == User.id)
        .where(DtrShiftOccurrence.occurrence_date >= start_date)
        .where(DtrShiftOccurrence.occurrence_date <= end_date)
    )

    if target_user_id:
        stmt = stmt.where(DtrShiftOccurrence.user_id == target_user_id)

    stmt = stmt.order_by(DtrShiftOccurrence.occurrence_date.asc(), User.first_name.asc())
    
    result = await db.execute(stmt)
    occurrences = result.scalars().unique().all()

    linked_shift_ids = {occ.user_shift_id for occ in occurrences if occ.user_shift_id}
    linked_user_shifts = {}
    if linked_shift_ids:
        linked_result = await db.execute(select(DtrUserShift).where(DtrUserShift.id.in_(linked_shift_ids)))
        linked_user_shifts = {row.id: row for row in linked_result.scalars().unique().all()}

    # Legacy DTR joins dtr_shifts on the occurrence shift id. Those rows are the
    # schedule labels (8AM - 8PM) and their colors. m_shifts holds planner names.
    catalog_result = await db.execute(select(DtrShift))
    dtr_shift_catalog = {row.id: row for row in catalog_result.scalars().all()}

    # Fetch DtrAttendance records in range to populate persistent main clock times
    att_stmt = (
        select(DtrAttendance)
        .where(DtrAttendance.attendance_date >= start_date)
        .where(DtrAttendance.attendance_date <= end_date)
    )
    if target_user_id:
        att_stmt = att_stmt.where(DtrAttendance.user_id == target_user_id)
    att_result = await db.execute(att_stmt)
    attendances = att_result.scalars().all()
    
    att_map = {}
    for att in attendances:
        key = f"{att.user_id}_{_day_key(att.attendance_date)}"
        att_map[key] = att

    # Pre-scan PDF file names ONCE to eliminate N+1 disk listdir I/O bottleneck
    all_pdf_files = []
    for d in [CARE_NOTES_DIR, DOCUMENTS_DIR, APP_STORAGE_DIR]:
        if os.path.exists(d):
            try:
                all_pdf_files.extend([f for f in os.listdir(d) if f.endswith(".pdf")])
            except Exception:
                pass

    def find_care_note_fast(su_num: str, su_id: int, date_str: str) -> Optional[str]:
        try:
            if "-" in date_str:
                formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%y")
            else:
                formatted_date = date_str
        except Exception:
            formatted_date = date_str
        su_padded = str(su_num).zfill(5)
        for f in all_pdf_files:
            if formatted_date in f:
                if f.startswith(f"su_{su_padded}_") or f.startswith(f"su_{su_num}_") or f"su_{su_id}_" in f:
                    return f
        return None

    report_list = []
    for occ in occurrences:
        carer_name = f"{occ.carer.first_name} {occ.carer.surname}".strip() if occ.carer else f"User #{occ.user_id}"
        first_name = occ.carer.first_name if occ.carer else ""
        surname = occ.carer.surname if occ.carer else ""
        linked_shift = linked_user_shifts.get(occ.user_shift_id) if occ.user_shift_id else None
        template = linked_shift.shift_template if linked_shift is not None else None
        if template is None:
            template = dtr_shift_catalog.get(occ.shift_id)
        shift_code = getattr(template, "shift_code", None) or ""
        shift_color = getattr(template, "shift_color", None) or ""
        scheduled_start = _hhmm_text(getattr(template, "start_time", None)) if template is not None else ""
        scheduled_end = _hhmm_text(getattr(template, "end_time", None)) if template is not None else ""
        if linked_shift is not None and (not scheduled_start or not scheduled_end):
            scheduled_start, scheduled_end = _shift_window(linked_shift)
        if not scheduled_start:
            scheduled_start = "08:00"
        if not scheduled_end:
            scheduled_end = "17:00"
        if not shift_code:
            shift_code = _template_shift_code(linked_shift) if linked_shift is not None else ""
        if not shift_color and linked_shift is not None and linked_shift.shift_template is not None:
            shift_color = getattr(linked_shift.shift_template, "shift_color", None) or ""

        att_key = f"{occ.user_id}_{_day_key(occ.occurrence_date)}"
        att = att_map.get(att_key)
        
        main_clock_in = None
        main_clock_out = None
        if att and att.clock_in:
            main_clock_in = _clock_iso(att.attendance_date, att.clock_in)
        if att and att.clock_out:
            main_clock_out = _clock_iso(att.attendance_date, att.clock_out)
            
        leave_type_id = att.leave_type_id if att else occ.leave_type_id
        leave_type = att.leave_type if att else occ.leave_type

        # Load associated service users
        su_list = []
        
        for assoc in (occ.service_users_assoc or []):
            if assoc.service_user:
                su_full_name = f"{assoc.service_user.first_name} {assoc.service_user.surname}".strip()
                su_num = getattr(assoc.service_user, 'su_number', f"{assoc.su_id}")
            else:
                su_full_name = f"Client #{assoc.su_id}"
                su_num = f"{assoc.su_id}"
            
            # Fast in-memory lookup
            found_file = find_care_note_fast(str(su_num), assoc.su_id, str(occ.occurrence_date))
            is_generated = bool(found_file)

            su_list.append({
                "id": assoc.id,
                "su_id": assoc.su_id,
                "su_full_name": su_full_name,
                "start_date": assoc.start_date.isoformat() if assoc.start_date else None,
                "end_date": assoc.end_date.isoformat() if assoc.end_date else None,
                "clock_in": assoc.clock_in.isoformat() if assoc.clock_in else None,
                "clock_out": assoc.clock_out.isoformat() if assoc.clock_out else None,
                "is_care_note_generated": is_generated,
                "care_note_filename": found_file if is_generated else None
            })
            
        status_label = "Scheduled"
        if leave_type:
            status_label = leave_type
        elif main_clock_in:
            status_label = "Present"
            
        report_list.append({
            "id": occ.id,
            "occurrence_id": occ.id,
            "occurrence_date": str(occ.occurrence_date),
            "branch_id": occ.branch_id or 1,
            "branch_name": "Barnes Branch",
            "user_id": occ.user_id,
            "first_name": first_name,
            "surname": surname,
            "full_name": carer_name,
            "shift_id": occ.shift_id,
            "user_shift_id": occ.user_shift_id,
            "shift_code": shift_code,
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "shift_color": shift_color,
            "attendance_id": att.id if att else None,
            "clock_in": main_clock_in,
            "clock_out": main_clock_out,
            "late_minutes": 0,
            "is_absent": 0,
            "leave_type_id": leave_type_id,
            "leave_type": leave_type,
            "total_hours": str(att.total_hours) if (att and att.total_hours) else "09:00",
            "status_label": status_label,
            "service_users": su_list
        })

    # Ensure 100% parity with Care Rota Planner by dynamically projecting schedules from dtr_user_shifts
    existing_pair_keys = {(occ.user_id, str(occ.occurrence_date)) for occ in occurrences}

    user_shift_stmt = select(DtrUserShift)
    if target_user_id:
        user_shift_stmt = user_shift_stmt.where(DtrUserShift.user_id == target_user_id)

    us_res = await db.execute(user_shift_stmt)
    user_shifts = us_res.scalars().all()

    try:
        req_s_date = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        req_e_date = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        req_s_date = date.today() - timedelta(days=30)
        req_e_date = date.today() + timedelta(days=30)

    projected_dtr: Dict[tuple, Dict[str, Any]] = {}

    for us in user_shifts:
        us_start_str = us.start_date.strftime("%Y-%m-%d") if isinstance(us.start_date, (datetime, date)) else str(us.start_date or "")
        us_end_str = us.end_date.strftime("%Y-%m-%d") if isinstance(us.end_date, (datetime, date)) else (str(us.end_date) if us.end_date else "")

        exceptions = set()
        if us.recurrence_exception:
            for ex in us.recurrence_exception.split(","):
                ex_clean = ex.strip()
                if ex_clean:
                    exceptions.add(ex_clean[:10].replace("-", ""))

        occurrences_dates = expand_rrule_occurrences(
            start_date_str=us_start_str,
            end_date_str=us_end_str,
            rrule_str=us.rrule_str or "",
            range_start=req_s_date,
            range_end=req_e_date
        )

        template = us.shift_template
        shift_code = getattr(template, "shift_code", None) or "8AM - 8PM"
        shift_color = getattr(template, "shift_color", None) or ""
        s_time = _hhmm_text(getattr(template, "start_time", None)) if template is not None else ""
        e_time = _hhmm_text(getattr(template, "end_time", None)) if template is not None else ""
        if not s_time or not e_time:
            s_time, e_time = _shift_window(us)

        carer_name = f"{us.carer.first_name} {us.carer.surname}".strip() if us.carer else f"Carer #{us.user_id}"
        first_name = us.carer.first_name if us.carer else ""
        surname = us.carer.surname if us.carer else ""

        for occ_d in occurrences_dates:
            occ_date_key = occ_d.strftime("%Y%m%d")
            if occ_date_key in exceptions:
                continue

            occ_date_str = occ_d.strftime("%Y-%m-%d")
            pair_key = (us.user_id, occ_date_str)
            if pair_key in existing_pair_keys:
                continue

            if pair_key not in projected_dtr:
                att_key = f"{us.user_id}_{_day_key(occ_date_str)}"
                att = att_map.get(att_key)

                main_clock_in = None
                main_clock_out = None
                if att and att.clock_in:
                    main_clock_in = _clock_iso(att.attendance_date, att.clock_in)
                if att and att.clock_out:
                    main_clock_out = _clock_iso(att.attendance_date, att.clock_out)

                leave_type_id = att.leave_type_id if att else None
                leave_type = att.leave_type if att else None

                status_label = "Scheduled"
                if leave_type:
                    status_label = leave_type
                elif main_clock_in:
                    status_label = "Present"

                calc_id = us.id * 100000 + int(occ_d.strftime("%Y%m%d")) % 10000
                projected_dtr[pair_key] = {
                    "id": calc_id,
                    "occurrence_id": calc_id,
                    "occurrence_date": occ_date_str,
                    "branch_id": us.branch_id or 1,
                    "branch_name": "Barnes Branch",
                    "user_id": us.user_id,
                    "first_name": first_name,
                    "surname": surname,
                    "full_name": carer_name,
                    "shift_id": us.shift_id or 1,
                    "user_shift_id": us.id,
                    "shift_code": shift_code,
                    "scheduled_start": s_time,
                    "scheduled_end": e_time,
                    "shift_color": shift_color,
                    "attendance_id": att.id if att else None,
                    "clock_in": main_clock_in,
                    "clock_out": main_clock_out,
                    "late_minutes": 0,
                    "is_absent": 0,
                    "leave_type_id": leave_type_id,
                    "leave_type": leave_type,
                    "total_hours": str(att.total_hours) if (att and att.total_hours) else "09:00",
                    "status_label": status_label,
                    "service_users": []
                }

            # Attach assigned service user visit
            if us.su_id:
                su_name = f"{us.service_user.first_name} {us.service_user.surname}".strip() if us.service_user else f"Client #{us.su_id}"
                su_num = getattr(us.service_user, 'su_number', f"{us.su_id}") if us.service_user else f"{us.su_id}"
                found_file = find_care_note_fast(str(su_num), us.su_id, occ_date_str)
                is_generated = bool(found_file)

                existing_su_ids = [su_item["su_id"] for su_item in projected_dtr[pair_key]["service_users"]]
                if us.su_id not in existing_su_ids:
                    projected_dtr[pair_key]["service_users"].append({
                        "id": us.id,
                        "su_id": us.su_id,
                        "su_full_name": su_name,
                        "start_date": f"{occ_date_str}T{s_time}:00",
                        "end_date": f"{occ_date_str}T{e_time}:00",
                        "clock_in": None,
                        "clock_out": None,
                        "is_care_note_generated": is_generated,
                        "care_note_filename": found_file if is_generated else None
                    })

    for proj in projected_dtr.values():
        report_list.append(proj)

    report_list.sort(key=lambda r: (r.get("occurrence_date", ""), r.get("full_name", "")))
    return report_list

@router.post("/attendances/inputManualDTR")
async def input_manual_dtr(
    data: ManualDtrRequest,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    occ_date_str = str(data.occurrence_date).split(' ')[0].split('T')[0]
    
    # 1. Update/Create DtrAttendance (Main Clock In/Out)
    att_res = await db.execute(
        select(DtrAttendance).where(
            DtrAttendance.user_id == data.user_id,
            DtrAttendance.attendance_date == occ_date_str
        )
    )
    att = att_res.scalars().first()
    if not att:
        att = DtrAttendance(
            user_id=data.user_id,
            shift_id=data.shift_id,
            attendance_date=occ_date_str
        )
        db.add(att)

    def parse_dt(t_str: Optional[str]) -> Optional[datetime]:
        if not t_str:
            return None
        t_clean = str(t_str).strip()
        if not t_clean or t_clean in ["00:00", "00:00:00", "None", "null", "undefined"]:
            return None

        if "T" in t_clean:
            try:
                return datetime.fromisoformat(t_clean.replace("Z", "+00:00").replace("+00:00", ""))
            except Exception:
                t_clean = t_clean.split("T")[1].replace("Z", "")

        if " " in t_clean:
            parts = t_clean.split(" ")
            if len(parts) == 2 and "-" in parts[0]:
                try:
                    return datetime.strptime(t_clean.split(".")[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    t_clean = parts[1]
            else:
                t_clean = parts[0]

        t_clean = t_clean.strip(":")
        parts = t_clean.split(":")
        if len(parts) >= 2:
            try:
                hh = int(parts[0])
                mm = int(parts[1])
                ss = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                return datetime.strptime(f"{occ_date_str} {hh:02d}:{mm:02d}:{ss:02d}", "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return None

    c_in_dt = parse_dt(data.clock_in)
    c_out_dt = parse_dt(data.clock_out)
    # Legacy inputManualDTR drops every clock when a leave status is saved.
    on_leave = bool(data.leave_type_id)
    if on_leave:
        c_in_dt = None
        c_out_dt = None

    att.clock_in = _as_time(c_in_dt)
    att.clock_out = _as_time(c_out_dt)
    att.leave_type_id = data.leave_type_id
    att.leave_type = data.leave_type
    
    if c_in_dt and c_out_dt:
        if c_out_dt <= c_in_dt:
            c_out_dt = c_out_dt + timedelta(days=1)
        diff_mins = (c_out_dt - c_in_dt).total_seconds() / 60.0
        att.total_hours = round(max(0, diff_mins / 60.0), 2)
    else:
        att.total_hours = 0.0

    # 2. Update/Create DtrShiftOccurrence
    # Legacy matches the row by user, date, and shift. Fall back to the day
    # when this record was projected and the stored shift id differs.
    occ = None
    if data.shift_id:
        occ_res = await db.execute(
            select(DtrShiftOccurrence).where(
                DtrShiftOccurrence.user_id == data.user_id,
                DtrShiftOccurrence.occurrence_date == occ_date_str,
                DtrShiftOccurrence.shift_id == data.shift_id,
            )
        )
        occ = occ_res.scalars().first()
    if occ is None:
        occ_res = await db.execute(
            select(DtrShiftOccurrence).where(
                DtrShiftOccurrence.user_id == data.user_id,
                DtrShiftOccurrence.occurrence_date == occ_date_str,
            )
        )
        occ = occ_res.scalars().first()
    if not occ:
        primary = await _resolve_user_shift(
            db,
            data.user_id,
            occ_date_str,
            data.shift_id,
            data.user_shift_id,
        )
        if primary is None:
            raise HTTPException(
                status_code=400,
                detail="No scheduled shift covers this employee on this date.",
            )
        occ = DtrShiftOccurrence(
            user_shift_id=primary.id,
            user_id=data.user_id,
            shift_id=data.shift_id or primary.shift_id or 1,
            branch_id=primary.branch_id,
            occurrence_date=occ_date_str,
            leave_type_id=data.leave_type_id,
            leave_type=data.leave_type,
        )
        db.add(occ)
        await db.flush()
    else:
        occ.leave_type_id = data.leave_type_id
        occ.leave_type = data.leave_type
        
    # 3. Update/Insert/Delete Service User Visits
    existing_vis_res = await db.execute(
        select(DtrOccurrenceServiceUser).where(DtrOccurrenceServiceUser.shift_occurrence_id == occ.id)
    )
    existing_visits = existing_vis_res.scalars().all()
    existing_visit_map = {v.id: v for v in existing_visits}
    
    keep_ids = set()
    for su_req in (data.service_users or []):
        su_in_dt = None if on_leave else parse_dt(su_req.clock_in)
        su_out_dt = None if on_leave else parse_dt(su_req.clock_out)
        su_start_dt = parse_dt(su_req.start_time) or datetime.strptime(f"{occ_date_str} 08:00:00", "%Y-%m-%d %H:%M:%S")
        su_end_dt = parse_dt(su_req.end_time) or datetime.strptime(f"{occ_date_str} 17:00:00", "%Y-%m-%d %H:%M:%S")
        
        if su_req.id and su_req.id in existing_visit_map:
            v = existing_visit_map[su_req.id]
            v.clock_in = su_in_dt
            v.clock_out = su_out_dt
            if su_req.su_id:
                v.su_id = su_req.su_id
            keep_ids.add(v.id)
        elif su_req.su_id:
            new_v = DtrOccurrenceServiceUser(
                shift_occurrence_id=occ.id,
                su_id=su_req.su_id,
                start_date=su_start_dt,
                end_date=su_end_dt,
                clock_in=su_in_dt,
                clock_out=su_out_dt
            )
            db.add(new_v)

    # Delete visits removed in edit form
    for v_id, v_obj in existing_visit_map.items():
        if v_id not in keep_ids:
            await db.delete(v_obj)

    await db.commit()

    # Re-query occurrence service users with names for instant reactive UI response
    refreshed_vis_res = await db.execute(
        select(DtrOccurrenceServiceUser, ServiceUser)
        .outerjoin(ServiceUser, DtrOccurrenceServiceUser.su_id == ServiceUser.su_id)
        .where(DtrOccurrenceServiceUser.shift_occurrence_id == occ.id)
    )
    saved_visits = []
    for vis, su_obj in refreshed_vis_res.all():
        su_name = f"{su_obj.first_name} {su_obj.surname}".strip() if su_obj else f"Service User #{vis.su_id}"
        su_num = getattr(su_obj, 'su_number', f"{vis.su_id}") if su_obj else str(vis.su_id)
        c_note_file = find_care_note_file(su_num, vis.su_id, occ_date_str)
        
        s_time = vis.start_date.strftime("%H:%M") if vis.start_date else "08:00"
        e_time = vis.end_date.strftime("%H:%M") if vis.end_date else "17:00"
        c_in = vis.clock_in.strftime("%H:%M") if vis.clock_in else ""
        c_out = vis.clock_out.strftime("%H:%M") if vis.clock_out else ""
        
        saved_visits.append({
            "id": vis.id,
            "su_id": vis.su_id,
            "su_full_name": su_name,
            "scheduled_visit": f"{s_time} - {e_time}",
            "start_time": s_time,
            "end_time": e_time,
            "clock_in": c_in,
            "clock_out": c_out,
            "is_care_note_generated": bool(c_note_file),
            "care_note_filename": c_note_file
        })

    return {
        "status": "success",
        "success": True,
        "message": "Attendance saved successfully to database.",
        "service_users": saved_visits
    }

@router.post("/attendances/reset")
async def reset_attendance(
    req: ResetAttendanceRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    occ_date_str = str(req.attendance_date).split(' ')[0].split('T')[0]
    
    # 1. Main Clock reset
    if req.target_type in ["main", "all"]:
        att_res = await db.execute(
            select(DtrAttendance).where(
                DtrAttendance.user_id == req.user_id,
                DtrAttendance.attendance_date == occ_date_str
            )
        )
        att = att_res.scalars().first()
        if att:
            if req.clear_type in ["in", "both"]:
                att.clock_in = None
            if req.clear_type in ["out", "both"]:
                att.clock_out = None
            if not att.clock_in and not att.clock_out:
                att.total_hours = 0.0

    # 2. Visit Clock reset
    occ_res = await db.execute(
        select(DtrShiftOccurrence).where(
            DtrShiftOccurrence.user_id == req.user_id,
            DtrShiftOccurrence.occurrence_date == occ_date_str
        )
    )
    occ = occ_res.scalars().first()
    if occ and req.target_type in ["service_user", "all"]:
        stmt = select(DtrOccurrenceServiceUser).where(DtrOccurrenceServiceUser.shift_occurrence_id == occ.id)
        if req.target_type == "service_user" and req.target_id:
            stmt = stmt.where(DtrOccurrenceServiceUser.id == req.target_id)
        visits_res = await db.execute(stmt)
        visits = visits_res.scalars().all()
        for v in visits:
            if req.clear_type in ["in", "both"]:
                v.clock_in = None
            if req.clear_type in ["out", "both"]:
                v.clock_out = None

    await db.commit()
    return {
        "status": "success",
        "success": True,
        "message": "Clock times reset successfully."
    }

def _visit_span(day: date, start_value, end_value, start_hhmm: str = "", end_hhmm: str = ""):
    """Scheduled visit bounds. Stored visit times win. Shift times are not a substitute."""
    start = _stored_moment(start_value, day, start_hhmm)
    end = _stored_moment(end_value, day, end_hhmm)
    if start is None or end is None:
        return None
    if end <= start:
        end += timedelta(days=1)
    return start, end

def _clock_matches_edge(clock_value, moment: datetime, edge: str) -> bool:
    clock = _as_time(clock_value)
    if clock is None:
        return False
    scheduled = moment.time().replace(second=0, microsecond=0)
    clock = clock.replace(second=0, microsecond=0)
    if edge == "in":
        return clock <= scheduled
    return clock >= scheduled

def _fill_employee_clocks(att: DtrAttendance, start_dt: datetime, end_dt: datetime) -> bool:
    changed = False
    if not _clock_matches_edge(att.clock_in, start_dt, "in"):
        att.clock_in = _as_time(_vary_clock(start_dt, EMPLOYEE_CLOCK_VARIANCE_MINUTES, "in"))
        changed = True
    if not _clock_matches_edge(att.clock_out, end_dt, "out"):
        att.clock_out = _as_time(_vary_clock(end_dt, EMPLOYEE_CLOCK_VARIANCE_MINUTES, "out"))
        changed = True
    if changed and att.clock_in and att.clock_out:
        started = _combine_clock(att.attendance_date, att.clock_in)
        finished = _combine_clock(att.attendance_date, att.clock_out)
        if started and finished:
            att.total_hours = _duration_hours(started, finished)
    return changed

def _fill_visit_clocks(visit: DtrOccurrenceServiceUser, start_dt: datetime, end_dt: datetime) -> int:
    filled = 0
    if not visit.clock_in:
        visit.clock_in = _vary_clock(start_dt, VISIT_CLOCK_VARIANCE_MINUTES, "in")
        filled += 1
    if not visit.clock_out:
        visit.clock_out = _vary_clock(end_dt, VISIT_CLOCK_VARIANCE_MINUTES, "out")
        filled += 1
    return filled

@router.post("/attendances/generate-dummy-times")
async def generate_dummy_times(
    req: DummyTimeRequest = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    start_str = req.start or "2026-07-01" if req else "2026-07-01"
    end_str = req.end or today_str if req else today_str
    if end_str > today_str:
        end_str = today_str
    range_start = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
    range_end = datetime.strptime(end_str[:10], "%Y-%m-%d").date()

    shift_stmt = select(DtrUserShift).order_by(DtrUserShift.id.asc())
    if req and req.user_id:
        shift_stmt = shift_stmt.where(DtrUserShift.user_id == req.user_id)
    shift_result = await db.execute(shift_stmt)
    user_shifts = [row for row in shift_result.scalars().unique().all() if (row.status or "").strip().lower() != "cancelled"]
    user_shift_by_id = {row.id: row for row in user_shifts}

    shifts_by_day = {}
    for user_shift in user_shifts:
        for day in _user_shift_dates(user_shift, range_start, range_end):
            shifts_by_day.setdefault((user_shift.user_id, day.isoformat()), []).append(user_shift)

    occ_stmt = (
        select(DtrShiftOccurrence)
        .options(selectinload(DtrShiftOccurrence.service_users_assoc))
        .where(DtrShiftOccurrence.occurrence_date >= start_str)
        .where(DtrShiftOccurrence.occurrence_date <= end_str)
    )
    if req and req.user_id:
        occ_stmt = occ_stmt.where(DtrShiftOccurrence.user_id == req.user_id)
    occ_result = await db.execute(occ_stmt)
    occurrences = occ_result.scalars().unique().all()
    occurrence_by_day = {}
    for occ in occurrences:
        occurrence_by_day.setdefault((occ.user_id, _day_key(occ.occurrence_date)), occ)

    att_stmt = (
        select(DtrAttendance)
        .where(DtrAttendance.attendance_date >= range_start)
        .where(DtrAttendance.attendance_date <= range_end)
    )
    if req and req.user_id:
        att_stmt = att_stmt.where(DtrAttendance.user_id == req.user_id)
    att_result = await db.execute(att_stmt)
    attendance_by_day = {(att.user_id, _day_key(att.attendance_date)): att for att in att_result.scalars().all()}

    generated_shift_count = 0
    generated_visit_count = 0

    def remember_attendance(user_id: int, day: date, shift_id: int, start_dt: datetime, end_dt: datetime):
        nonlocal generated_shift_count
        key = (user_id, day.isoformat())
        att = attendance_by_day.get(key)
        if att is None:
            att = DtrAttendance(
                user_id=user_id,
                shift_id=shift_id,
                attendance_date=day,
            )
            db.add(att)
            attendance_by_day[key] = att
        if _fill_employee_clocks(att, start_dt, end_dt):
            generated_shift_count += 1

    for key, occ in occurrence_by_day.items():
        if occ.leave_type_id or occ.leave_type:
            continue
        day = datetime.strptime(key[1], "%Y-%m-%d").date()
        day_shifts = shifts_by_day.get(key, [])
        primary = user_shift_by_id.get(occ.user_shift_id) if occ.user_shift_id else None
        if primary is None and day_shifts:
            primary = day_shifts[0]
        if primary is not None:
            shift_start, shift_end = _schedule_span(day, *_shift_window(primary))
        else:
            shift_start, shift_end = _schedule_span(day, "08:00", "17:00")
        remember_attendance(occ.user_id, day, occ.shift_id or 1, shift_start, shift_end)

        for visit in (occ.service_users_assoc or []):
            match = next((item for item in day_shifts if item.su_id == visit.su_id), None)
            visit_start_hhmm = _hhmm_text(match.start_time) if match else ""
            visit_end_hhmm = _hhmm_text(match.end_time) if match else ""
            span = _visit_span(day, visit.start_date, visit.end_date, visit_start_hhmm, visit_end_hhmm)
            if span is None:
                continue
            generated_visit_count += _fill_visit_clocks(visit, span[0], span[1])

    for key, day_shifts in shifts_by_day.items():
        if key in occurrence_by_day:
            continue
        day = datetime.strptime(key[1], "%Y-%m-%d").date()
        primary = day_shifts[0]
        shift_start, shift_end = _schedule_span(day, *_shift_window(primary))
        occ = DtrShiftOccurrence(
            user_shift_id=primary.id,
            user_id=primary.user_id,
            shift_id=1,
            branch_id=primary.branch_id,
            occurrence_date=key[1],
        )
        db.add(occ)
        occurrence_by_day[key] = occ
        seen_service_users = set()
        for user_shift in day_shifts:
            if not user_shift.su_id or user_shift.su_id in seen_service_users:
                continue
            seen_service_users.add(user_shift.su_id)
            start_hhmm = _hhmm_text(user_shift.start_time) or "08:00"
            end_hhmm = _hhmm_text(user_shift.end_time) or "17:00"
            visit_start, visit_end = _schedule_span(day, start_hhmm, end_hhmm)
            occ.service_users_assoc.append(DtrOccurrenceServiceUser(
                su_id=user_shift.su_id,
                start_date=visit_start,
                end_date=visit_end,
                clock_in=_vary_clock(visit_start, VISIT_CLOCK_VARIANCE_MINUTES, "in"),
                clock_out=_vary_clock(visit_end, VISIT_CLOCK_VARIANCE_MINUTES, "out"),
            ))
            generated_visit_count += 2
        remember_attendance(primary.user_id, day, occ.shift_id, shift_start, shift_end)

    await db.commit()
    return {
        "status": "success",
        "success": True,
        "message": f"Generated clock times for {generated_shift_count} shifts and {generated_visit_count} Service User visits up to {end_str}.",
        "generated_shift_count": generated_shift_count,
        "generated_visit_count": generated_visit_count
    }

@router.post("/attendances/importDTR")
async def import_dtr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_staff_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
        
    contents = await file.read()
    records = parse_dtr_excel(contents)
    return {
        "status": "success",
        "imported_count": len(records),
        "records": records
    }

async def _scheduled_visit_for_care_note(db: AsyncSession, su_id, user_id, day, visit_id):
    """The service-user visit row. This is not the carer's shift attendance."""
    if visit_id:
        stmt = (
            select(DtrOccurrenceServiceUser)
            .join(DtrShiftOccurrence, DtrOccurrenceServiceUser.shift_occurrence_id == DtrShiftOccurrence.id)
            .where(DtrOccurrenceServiceUser.id == visit_id)
        )
        if su_id:
            stmt = stmt.where(DtrOccurrenceServiceUser.su_id == su_id)
        if user_id:
            stmt = stmt.where(DtrShiftOccurrence.user_id == user_id)
        row = (await db.execute(stmt)).scalars().first()
        if row:
            return row
    if not su_id:
        return None
    day_text = str(day or "")[:10]
    stmt = (
        select(DtrOccurrenceServiceUser)
        .join(DtrShiftOccurrence, DtrOccurrenceServiceUser.shift_occurrence_id == DtrShiftOccurrence.id)
        .where(DtrOccurrenceServiceUser.su_id == su_id)
        .where(or_(
            DtrShiftOccurrence.occurrence_date == day_text,
            DtrShiftOccurrence.occurrence_date.like(f"{day_text}%"),
        ))
        .order_by(DtrOccurrenceServiceUser.id.asc())
    )
    if user_id:
        stmt = stmt.where(DtrShiftOccurrence.user_id == user_id)
    return (await db.execute(stmt)).scalars().first()


@router.post("/care-notes/generate")
async def generate_care_note(
    data: CareNoteGenerateDetailedRequest,
    request: Request,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    p_name = data.patient_name or "Service User"
    c_name = data.carer_name or "Carer Staff"
    shift_dt = data.date
    visit_row = await _scheduled_visit_for_care_note(db, data.su_id, data.user_id, shift_dt, data.visit_id)
    if visit_row is not None:
        window = resolve_visit_window(
            clock_in=visit_row.clock_in,
            clock_out=visit_row.clock_out,
            scheduled_start=visit_row.start_date,
            scheduled_end=visit_row.end_date,
            fallback_in=data.time_in,
            fallback_out=data.time_out,
        )
    else:
        # A payload that omits the visit clock fields is the legacy shape:
        # time_in and time_out are already the visit clocks.
        request_clock_in = data.time_in if data.visit_clock_in is None else data.visit_clock_in
        request_clock_out = data.time_out if data.visit_clock_out is None else data.visit_clock_out
        window = resolve_visit_window(
            clock_in=request_clock_in,
            clock_out=request_clock_out,
            scheduled_start=data.scheduled_visit_start,
            scheduled_end=data.scheduled_visit_end,
            fallback_in=data.time_in,
            fallback_out=data.time_out,
        )
    t_in = window["time_in"]
    t_out = window["time_out"]
    shift_tm = f"{t_in} - {t_out}"
    
    su_num = str(data.su_id or "1")
    med_history = "No major medical history recorded"
    medications = "No active prescription medications recorded"
    su_notes = "Standard domiciliary care routine"

    if data.su_id:
        su_res = await db.execute(select(ServiceUser).where(ServiceUser.su_id == data.su_id))
        su_obj = su_res.scalar_one_or_none()
        if su_obj:
            p_name = f"{su_obj.first_name} {su_obj.surname}".strip()
            su_num = (su_obj.su_number or str(su_obj.su_id)).strip()
            if su_obj.medical_history:
                med_history = str(su_obj.medical_history).strip()
            if su_obj.medications_json:
                medications = str(su_obj.medications_json).strip()
            if su_obj.care_plan_notes:
                su_notes = str(su_obj.care_plan_notes).strip()

    su_num_padded = str(su_num).zfill(5)

    if data.user_id:
        user_res = await db.execute(select(User).where(User.id == data.user_id))
        u_obj = user_res.scalar_one_or_none()
        if u_obj:
            c_name = f"{u_obj.first_name} {u_obj.surname}".strip()

    carer_name_sanitized = "".join(c for c in c_name.upper() if c.isalnum())
    t_in_str = "".join(c for c in t_in if c.isdigit())
    t_out_str = "".join(c for c in t_out if c.isdigit())
    
    try:
        formatted_date = datetime.strptime(shift_dt, "%Y-%m-%d").strftime("%d.%m.%y")
    except Exception:
        formatted_date = shift_dt.replace("-", ".")

    filename = f"su_{su_num_padded}_{carer_name_sanitized}_CARE_NOTE_{t_in_str}-{t_out_str}_{formatted_date}.pdf"
    
    # GDPR Compliance & PII Anonymization for AI Model Context Payload:
    # Strip all real names, exact addresses, and contact numbers before sending to AI model payload.
    anon_patient = f"Service User (SU-{su_num_padded})"
    anon_carer = f"Carer Staff (ID-{data.user_id or 1})"
    
    # Sanitize optional user-provided notes to remove any accidentally typed PII (e.g. phone numbers, postcodes, emails)
    raw_user_obs = (data.clinical_notes or "").strip()
    sanitized_obs = re.sub(r'\b[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}\b', '[POSTCODE]', raw_user_obs, flags=re.IGNORECASE)
    sanitized_obs = re.sub(r'\b0\d{9,10}\b', '[PHONE REDACTED]', sanitized_obs)
    sanitized_obs = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL REDACTED]', sanitized_obs)

    ai_prompt_payload = {
        "anonymized_patient": anon_patient,
        "anonymized_carer": anon_carer,
        "shift_date": shift_dt,
        "visit_window": shift_tm,
        "supplementary_medical_history": med_history,
        "supplementary_medications": medications,
        "supplementary_su_notes": su_notes,
        "user_observations": sanitized_obs or "Routine care visit completed per care plan standards."
    }

    # Execute legacy AI model logic (prompt building, break rules, Care Center detection, 12-hour timestamps)
    ai_json = await call_ai_model(
        su_name=p_name,
        preferred_name=getattr(su_obj, 'preferred_name', None) if data.su_id and 'su_obj' in locals() and su_obj else None,
        carer_name=c_name,
        date_str=shift_dt,
        time_in=t_in,
        time_out=t_out,
        care_plan=su_notes,
        clinical_notes=data.clinical_notes
    )

    # Section XII is the AI timetable, same as the legacy care note.
    # time_in and time_out above are the scheduled visit clocks, so the model
    # writes those notes inside the visit rather than the carer's shift.
    timeline_notes = ai_json.get("additional_notes", "")

    pdf_data = {
        "patient_name": p_name,
        "carer_name": c_name,
        "shift_date": shift_dt,
        "shift_time": shift_tm,
        "time_in": t_in,
        "time_out": t_out,
        "care_notes": timeline_notes,
        "ai_json": ai_json,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    pdf_bytes = generate_care_note_pdf(pdf_data)
    
    # Save exclusively to storage/care_notes
    file_path = os.path.join(CARE_NOTES_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    # Database Persistence: uploaded_files
    uf_res = await db.execute(select(UploadedFile).where(UploadedFile.filename == filename))
    uf = uf_res.scalars().first()
    if not uf:
        uf = UploadedFile(file_number=f"su_{su_num_padded}", filename=filename)
        db.add(uf)

    # Database Persistence: m_notes
    if data.user_id and data.su_id:
        m_note = MNotes(
            user_id=data.user_id,
            su_id=data.su_id,
            notes=timeline_notes
        )
        db.add(m_note)

    await db.commit()

    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=data.su_id,
        patient_name=p_name,
        record_type="care_notes",
        action="UPDATE",
        details=f"Generated care note file {filename}",
        request=request,
    )

    return {
        "status": "success",
        "success": True,
        "filename": filename,
        "message": "AI Person-Centred Care Note generated and saved successfully to database."
    }

def _care_note_file(filename: str) -> str | None:
    name = safe_care_note_name(filename)
    if not name:
        return None
    for directory in (CARE_NOTES_DIR, DOCUMENTS_DIR, APP_STORAGE_DIR):
        root = os.path.realpath(directory)
        candidate = os.path.realpath(os.path.join(root, name))
        if candidate.startswith(root + os.sep) and os.path.isfile(candidate):
            return candidate
    return None

@router.get("/care-notes/view/{filename}")
async def view_care_note(
    filename: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    name = safe_care_note_name(filename)
    if not name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    if not is_staff_user(current_user) and not carer_owns_care_note(name, current_user.first_name, current_user.surname):
        raise HTTPException(status_code=403, detail="You can only open a care note assigned to you.")
    file_path = _care_note_file(name)
    if not file_path:
        raise HTTPException(status_code=404, detail="Care Note file not found on server.")

    su_id, patient_name = await subject_for_filename(db, name)
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="care_notes",
        action="VIEW",
        details=f"Viewed care note file {name}",
        request=request,
    )
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=name,
        headers={"Content-Disposition": f"inline; filename={name}"},
    )

@router.delete("/care-notes/revert/{filename}")
async def revert_care_note(
    filename: str,
    request: Request,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    name = safe_care_note_name(filename)
    if not name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    file_path = _care_note_file(name)
    if file_path:
        os.remove(file_path)

    uf_res = await db.execute(select(UploadedFile).where(UploadedFile.filename == name))
    uf = uf_res.scalars().first()
    if uf:
        await db.delete(uf)
    if not file_path and not uf:
        raise HTTPException(status_code=404, detail="Care Note file not found on server.")

    await db.commit()
    su_id, patient_name = await subject_for_filename(db, name)
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="care_notes",
        action="DELETE",
        details=f"Deleted care note file {name}",
        request=request,
    )
    return {
        "status": "success",
        "success": True,
        "message": "Care Note deleted and reverted successfully."
    }
