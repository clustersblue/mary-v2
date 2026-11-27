from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.models.shift import MShift, DtrShift, DtrUserShift, Transaction, MAttendance
from app.models.user import User
from app.models.service_user import ServiceUser
from app.schemas.shift import (
    MShiftCreate, MShiftOut,
    DtrShiftRecordCreate, DtrShiftRecordOut,
    DtrUserShiftCreate, DtrUserShiftOut,
    VueCalEvent
)
from app.services.recurrence import expand_rrule_occurrences
from app.core.security import get_current_staff_user

router = APIRouter()

# ==============================================================================
# --- 1. Master Shift Catalog (mary_api_db_new.m_shifts) ---
# ==============================================================================
@router.get("/m-shifts", response_model=List[MShiftOut])
@router.get("/care-shifts", response_model=List[MShiftOut])
async def get_m_shifts(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(MShift)
            .where(MShift.deleted_at.is_(None))
            .order_by(MShift.shift_name.asc())
        )
        return result.scalars().all()
    except Exception:
        return []

@router.post("/m-shifts", response_model=MShiftOut, status_code=status.HTTP_201_CREATED)
async def create_m_shift(
    data: MShiftCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    shift_dict = data.model_dump(exclude={"id", "shift_id", "shift", "shift_code", "created_at", "updated_at"})
    shift = MShift(**shift_dict)
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift

@router.put("/m-shifts/{shift_id}", response_model=MShiftOut)
async def update_m_shift(
    shift_id: int,
    data: MShiftCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MShift).where(MShift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        if hasattr(shift, key):
            setattr(shift, key, val)
    await db.commit()
    await db.refresh(shift)
    return shift

@router.delete("/m-shifts/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_m_shift(
    shift_id: int,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MShift).where(MShift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    shift.deleted_at = datetime.now()
    await db.commit()
    return None

# ==============================================================================
# --- 2. DTR Work Shifts Configuration (mary_api_db_new.dtr_shifts) ---
# Used by DailyTimeRecord.vue, MaryDtrPlanner.vue and MaryCarePlanner.vue
# ==============================================================================
def format_dtr_shift_dict(s: DtrShift) -> dict:
    s_time_str = s.start_time.strftime("%H:%M") if hasattr(s.start_time, "strftime") else (str(s.start_time)[:5] if s.start_time else "08:00")
    e_time_str = s.end_time.strftime("%H:%M") if hasattr(s.end_time, "strftime") else (str(s.end_time)[:5] if s.end_time else "20:00")
    return {
        "id": s.id,
        "shift_id": s.id,
        "shift_code": s.shift_code,
        "shift": s.shift_code,
        "shift_name": s.shift_code,
        "start_time": s_time_str,
        "end_time": e_time_str,
        "crosses_midnight": bool(s.crosses_midnight),
        "break_start": s.break_start.strftime("%H:%M") if hasattr(s.break_start, "strftime") else (str(s.break_start)[:5] if s.break_start else None),
        "break_end": s.break_end.strftime("%H:%M") if hasattr(s.break_end, "strftime") else (str(s.break_end)[:5] if s.break_end else None),
        "grace_period": s.grace_period or 0,
        "night_diff_from": s.night_diff_from.strftime("%H:%M") if hasattr(s.night_diff_from, "strftime") else None,
        "night_diff_to": s.night_diff_to.strftime("%H:%M") if hasattr(s.night_diff_to, "strftime") else None,
        "is_flexible": bool(s.is_flexible),
        "is_rotating": bool(s.is_rotating),
        "shift_color": s.shift_color or "#00aeff"
    }

@router.get("/shifts")
@router.get("/dtr-shifts")
async def get_dtr_shifts(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(DtrShift).order_by(DtrShift.id.asc())
        )
        shifts = result.scalars().all()
        formatted = [format_dtr_shift_dict(s) for s in shifts]
        return {
            "status": "success",
            "message": "Shift list retrieved successfully.",
            "data": formatted
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to retrieve shifts: {str(e)}", "data": []}

@router.post("/shifts", response_model=DtrShiftRecordOut, status_code=status.HTTP_201_CREATED)
@router.post("/dtr-shifts", response_model=DtrShiftRecordOut, status_code=status.HTTP_201_CREATED)
async def create_dtr_shift(
    data: DtrShiftRecordCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        shift_data = data.model_dump(exclude_unset=True)
        new_dtr_shift = DtrShift(**shift_data)
        db.add(new_dtr_shift)
        await db.commit()
        await db.refresh(new_dtr_shift)
        return new_dtr_shift
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create DTR shift: {str(e)}")

@router.put("/shifts/{id}", response_model=DtrShiftRecordOut)
@router.put("/dtr-shifts/{id}", response_model=DtrShiftRecordOut)
async def update_dtr_shift(
    id: int,
    data: DtrShiftRecordCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(DtrShift).where(DtrShift.id == id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="DTR shift record not found")
        for key, val in data.model_dump(exclude_unset=True).items():
            if hasattr(shift, key):
                setattr(shift, key, val)
        await db.commit()
        await db.refresh(shift)
        return shift
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update DTR shift: {str(e)}")

@router.delete("/shifts/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/dtr-shifts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dtr_shift(
    id: int,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(DtrShift).where(DtrShift.id == id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="DTR shift record not found")
        await db.delete(shift)
        await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete DTR shift: {str(e)}")

# ==============================================================================
# --- 3. User Shift Assignments (mary_api_db_new.dtr_user_shifts) ---
# ==============================================================================
def format_user_shift_dict(s: DtrUserShift) -> dict:
    s_date = s.start_date.strftime("%Y-%m-%d") if isinstance(s.start_date, (datetime, date)) else str(s.start_date or "")
    e_date = s.end_date.strftime("%Y-%m-%d") if isinstance(s.end_date, (datetime, date)) else (str(s.end_date) if s.end_date else None)
    rrule_val = s.recurrence_rule or s.rrule_str
    return {
        "id": s.id,
        "user_id": s.user_id,
        "su_id": s.su_id,
        "shift_id": s.shift_id,
        "branch_id": s.branch_id,
        "start_date": s_date,
        "end_date": e_date,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "rrule_str": rrule_val,
        "recurrence_rule": rrule_val,
        "recurrence_exception": getattr(s, "recurrence_exception", None),
        "recurrence_id": getattr(s, "recurrence_id", None),
        "doubleup": bool(s.doubleup),
        "status": s.status or "scheduled",
        "notes": s.notes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "carer": s.carer,
        "service_user": s.service_user,
        "shift_template": s.shift_template
    }

@router.get("/usershifts", response_model=List[DtrUserShiftOut])
async def get_user_shifts(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(DtrUserShift))
        shifts = result.scalars().all()
        return [format_user_shift_dict(s) for s in shifts]
    except Exception:
        return []

@router.post("/users/shifts", response_model=DtrUserShiftOut, status_code=status.HTTP_201_CREATED)
async def create_user_shift(
    data: DtrUserShiftCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        shift_data = data.model_dump()
        if not shift_data.get("status"):
            shift_data["status"] = "scheduled"
        rrule_val = shift_data.get("recurrence_rule") or shift_data.get("rrule_str")
        shift_data["rrule_str"] = rrule_val
        shift_data["recurrence_rule"] = rrule_val

        user_shift = DtrUserShift(**shift_data)
        db.add(user_shift)
        await db.commit()
        await db.refresh(user_shift)
        return format_user_shift_dict(user_shift)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating shift: {str(e)}")

@router.put("/users/shifts/{id}", response_model=DtrUserShiftOut)
async def update_user_shift(
    id: int,
    data: DtrUserShiftCreate,
    mode: Optional[str] = Query("all"), # "single", "future", "all"
    occurrence_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(DtrUserShift).where(DtrUserShift.id == id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift assignment not found")
        
        shift_data = data.model_dump(exclude_unset=True)
        if "recurrence_rule" in shift_data or "rrule_str" in shift_data:
            rrule_val = shift_data.get("recurrence_rule") or shift_data.get("rrule_str")
            shift_data["rrule_str"] = rrule_val
            shift_data["recurrence_rule"] = rrule_val

        if mode == "future" and occurrence_date:
            occ_dt = datetime.strptime(occurrence_date[:10], "%Y-%m-%d").date()
            prev_day = occ_dt - timedelta(days=1)
            shift.end_date = prev_day.strftime("%Y-%m-%d")
            await db.commit()

            new_data = {**shift_data, "start_date": occurrence_date[:10]}
            new_shift = DtrUserShift(**new_data)
            db.add(new_shift)
            await db.commit()
            await db.refresh(new_shift)
            return format_user_shift_dict(new_shift)
        elif mode == "single" and occurrence_date:
            occ_date_clean = occurrence_date[:10]
            existing_ex = [x.strip() for x in (shift.recurrence_exception or "").split(",") if x.strip()]
            if occ_date_clean not in existing_ex:
                existing_ex.append(occ_date_clean)
                shift.recurrence_exception = ",".join(existing_ex)
                await db.commit()

            # Create an isolated single occurrence override
            single_data = {
                **shift_data,
                "start_date": occ_date_clean,
                "end_date": occ_date_clean,
                "rrule_str": None,
                "recurrence_rule": None,
                "recurrence_id": id
            }
            single_shift = DtrUserShift(**single_data)
            db.add(single_shift)
            await db.commit()
            await db.refresh(single_shift)
            return format_user_shift_dict(single_shift)
        else:
            for key, val in shift_data.items():
                setattr(shift, key, val)
            await db.commit()
            await db.refresh(shift)
            return format_user_shift_dict(shift)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating shift: {str(e)}")

@router.delete("/users/shifts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_shift(
    id: int,
    mode: Optional[str] = Query("all"),
    occurrence_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(DtrUserShift).where(DtrUserShift.id == id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift assignment not found")

        if mode == "future" and occurrence_date:
            occ_dt = datetime.strptime(occurrence_date[:10], "%Y-%m-%d").date()
            prev_day = occ_dt - timedelta(days=1)
            shift.end_date = prev_day.strftime("%Y-%m-%d")
            await db.commit()
        elif mode == "single" and occurrence_date:
            occ_date_clean = occurrence_date[:10]
            existing_ex = [x.strip() for x in (shift.recurrence_exception or "").split(",") if x.strip()]
            if occ_date_clean not in existing_ex:
                existing_ex.append(occ_date_clean)
                shift.recurrence_exception = ",".join(existing_ex)
                await db.commit()
        else:
            await db.delete(shift)
            await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting shift: {str(e)}")

@router.post("/delete-events")
@router.post("/users/shifts/bulk-delete")
async def bulk_delete_shifts(
    payload: dict,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        su_id = payload.get("su_id")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        if not su_id:
            raise HTTPException(status_code=400, detail="Service user ID (su_id) is required")

        # Delete matching DtrUserShift
        shift_stmt = select(DtrUserShift).where(DtrUserShift.su_id == int(su_id))
        if start_date:
            shift_stmt = shift_stmt.where(DtrUserShift.start_date >= start_date[:10])
        if end_date:
            shift_stmt = shift_stmt.where(DtrUserShift.start_date <= end_date[:10])
        shift_res = await db.execute(shift_stmt)
        user_shifts = shift_res.scalars().all()
        for s in user_shifts:
            await db.delete(s)

        # Also delete matching Transaction if any
        tx_stmt = select(Transaction).where(Transaction.su_id == int(su_id))
        if start_date:
            s_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
            tx_stmt = tx_stmt.where(Transaction.start >= s_dt)
        if end_date:
            e_dt = datetime.strptime(end_date[:10], "%Y-%m-%d") + timedelta(days=1)
            tx_stmt = tx_stmt.where(Transaction.start < e_dt)
        tx_res = await db.execute(tx_stmt)
        transactions = tx_res.scalars().all()
        for t in transactions:
            await db.delete(t)

        await db.commit()
        return {"status": True, "message": f"Successfully deleted {len(user_shifts) + len(transactions)} scheduled events"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to bulk delete events: {str(e)}")

# ==============================================================================
# --- 4. Care Planner Projections Engine (m_transactions + dtr_user_shifts) ---
# Driven directly by mary_api_db_new.m_shifts
# ==============================================================================
@router.get("/get-events", response_model=List[VueCalEvent])
async def get_events(
    start_date: Optional[str] = Query(None), # YYYY-MM-DD
    end_date: Optional[str] = Query(None),   # YYYY-MM-DD
    carer_id: Optional[int] = Query(None),   # Carer filter
    branch_id: Optional[int] = Query(None),  # Branch Location filter
    search: Optional[str] = Query(None),     # Search keyword filter (Carer or Service User)
    source: Optional[str] = Query(None),     # Optional source filter: "shifts" or "transactions"
    db: AsyncSession = Depends(get_db)
):
    start_date = start_date if isinstance(start_date, str) else None
    end_date = end_date if isinstance(end_date, str) else None
    carer_id = carer_id if isinstance(carer_id, int) else None
    branch_id = branch_id if isinstance(branch_id, int) else None
    source = source if isinstance(source, str) else None
    clean_search = search.strip().lower() if isinstance(search, str) and search.strip() else None

    events: List[VueCalEvent] = []
    tx_seen_keys = set()
    now = datetime.now()

    try:
        # 1. Query m_transactions from MySQL (if source is not explicitly "shifts")
        if source != "shifts":
            tx_stmt = select(Transaction).join(User, Transaction.user_id == User.id).where(Transaction.deleted_at.is_(None))
            if carer_id:
                tx_stmt = tx_stmt.where(Transaction.user_id == carer_id)
            if start_date:
                try:
                    s_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
                    tx_stmt = tx_stmt.where(Transaction.start >= s_dt)
                except Exception:
                    pass
            if end_date:
                try:
                    e_dt = datetime.strptime(end_date[:10], "%Y-%m-%d") + timedelta(days=1)
                    tx_stmt = tx_stmt.where(Transaction.start < e_dt)
                except Exception:
                    pass

            tx_stmt = tx_stmt.order_by(User.first_name.asc(), User.surname.asc(), Transaction.start.asc())
            tx_result = await db.execute(tx_stmt)
            transactions = tx_result.scalars().all()

            for tx in transactions:
                carer_name = f"{tx.carer.first_name} {tx.carer.surname}".strip() if tx.carer else f"Carer #{tx.user_id}"
                su_name = f"{tx.service_user.first_name} {tx.service_user.surname}".strip() if tx.service_user else f"Client #{tx.su_id}"
                
                if clean_search and clean_search not in carer_name.lower() and clean_search not in su_name.lower():
                    continue

                shift_code = tx.shift_template.shift_name if tx.shift_template else "Regular Shift"
                shift_color = tx.shift_template.shift_color if (tx.shift_template and tx.shift_template.shift_color) else None
                
                start_str = tx.start.strftime("%Y-%m-%d %H:%M") if tx.start else f"{date.today()} 08:00"
                end_str = tx.end.strftime("%Y-%m-%d %H:%M") if tx.end else f"{date.today()} 17:00"
                
                s_time = tx.start.strftime("%H:%M") if tx.start else "08:00"
                e_time = tx.end.strftime("%H:%M") if tx.end else "17:00"
                
                clock_in_str = tx.attendance.time_in.strftime("%H:%M") if (tx.attendance and tx.attendance.time_in) else ""
                clock_out_str = tx.attendance.time_out.strftime("%H:%M") if (tx.attendance and tx.attendance.time_out) else ""
                
                if clock_in_str:
                    status_str = "Present"
                elif tx.start and tx.start < now:
                    status_str = "Unresolved Absence"
                else:
                    status_str = "Scheduled"
                
                title = f"{shift_code} - {su_name}"
                if tx.doubleup:
                    title = f"[2 Carers] {title}"

                occ_date = tx.start.strftime("%Y-%m-%d") if tx.start else None
                dedup_key = (tx.user_id or 1, occ_date, tx.shift_id)
                tx_seen_keys.add(dedup_key)

                events.append(
                    VueCalEvent(
                        id=tx.tx_id,
                        user_shift_id=None,
                        user_id=tx.user_id or 1,
                        carer_name=carer_name,
                        su_id=tx.su_id,
                        service_user_name=su_name,
                        shift_id=tx.shift_id,
                        shift_code=shift_code,
                        shift_color=shift_color,
                        shift_start=s_time,
                        shift_end=e_time,
                        branch_id=tx.carer.branch_id if (tx.carer and tx.carer.branch_id) else None,
                        start=start_str,
                        end=end_str,
                        clock_in=clock_in_str,
                        clock_out=clock_out_str,
                        title=title,
                        content=tx.notes or "",
                        status=status_str,
                        class_name=f"shift-{status_str.lower().replace(' ', '-')}",
                        split=tx.user_id or 1,
                        doubleup=bool(tx.doubleup),
                        rrule_str=None,
                        recurrence_rule=None,
                        is_recurring=False,
                        occurrence_date=occ_date
                    )
                )

        # 2. Query dtr_user_shifts and expand RRULE recurring schedules (if source is not explicitly "transactions")
        if source != "transactions":
            shift_stmt = select(DtrUserShift)
            if carer_id:
                shift_stmt = shift_stmt.where(DtrUserShift.user_id == carer_id)
            
            shift_result = await db.execute(shift_stmt)
            user_shifts = shift_result.scalars().all()

            view_s_date = datetime.strptime(start_date[:10], "%Y-%m-%d").date() if start_date else (date.today() - timedelta(days=30))
            view_e_date = datetime.strptime(end_date[:10], "%Y-%m-%d").date() if end_date else (date.today() + timedelta(days=90))

            seen_shift_keys = set()
            for us in user_shifts:
                carer_name = f"{us.carer.first_name} {us.carer.surname}".strip() if us.carer else f"Carer #{us.user_id}"
                su_name = f"{us.service_user.first_name} {us.service_user.surname}".strip() if us.service_user else (f"Client #{us.su_id}" if us.su_id else None)
                
                if clean_search and clean_search not in carer_name.lower() and (not su_name or clean_search not in su_name.lower()):
                    continue

                if us.shift_template:
                    shift_code_val = getattr(us.shift_template, "shift_code", None) or getattr(us.shift_template, "shift_name", "8AM - 8PM")
                    shift_color_val = getattr(us.shift_template, "shift_color", None) or "#00aeff"
                    s_t = getattr(us.shift_template, "start_time", None)
                    e_t = getattr(us.shift_template, "end_time", None)
                    s_time = us.start_time or (s_t.strftime("%H:%M") if hasattr(s_t, "strftime") else (str(s_t)[:5] if s_t else "08:00"))
                    e_time = us.end_time or (e_t.strftime("%H:%M") if hasattr(e_t, "strftime") else (str(e_t)[:5] if e_t else "20:00"))
                    crosses_mid = bool(getattr(us.shift_template, "crosses_midnight", False))
                else:
                    shift_code_val = "8AM - 8PM"
                    shift_color_val = "#00aeff"
                    s_time = us.start_time or "08:00"
                    e_time = us.end_time or "20:00"
                    crosses_mid = False

                us_start_str = us.start_date.strftime("%Y-%m-%d") if isinstance(us.start_date, (datetime, date)) else str(us.start_date or date.today().strftime("%Y-%m-%d"))
                us_end_str = us.end_date.strftime("%Y-%m-%d") if isinstance(us.end_date, (datetime, date)) else (str(us.end_date) if us.end_date else "")

                # Parse recurrence exceptions to suppress deleted/modified single occurrences
                exceptions = set()
                if us.recurrence_exception:
                    for ex in us.recurrence_exception.split(","):
                        ex_clean = ex.strip()
                        if ex_clean:
                            exceptions.add(ex_clean[:10].replace("-", ""))

                occurrences = expand_rrule_occurrences(
                    start_date_str=us_start_str,
                    end_date_str=us_end_str,
                    rrule_str=us.rrule_str or "",
                    range_start=view_s_date,
                    range_end=view_e_date
                )

                is_rec = bool(us.rrule_str and us.rrule_str.strip())

                for occ_d in occurrences:
                    occ_date_key = occ_d.strftime("%Y%m%d")
                    # Check if this occurrence is suppressed via exception
                    if occ_date_key in exceptions:
                        continue

                    occ_date_str = occ_d.strftime("%Y-%m-%d")
                    tx_key = (us.user_id or 1, occ_date_str, us.shift_id)
                    if tx_key in tx_seen_keys:
                        continue

                    # Deduplicate across multiple overlapping shift records
                    shift_key = (us.user_id or 1, us.su_id, occ_date_str, s_time, e_time)
                    if shift_key in seen_shift_keys:
                        continue
                    seen_shift_keys.add(shift_key)

                    occ_start = f"{occ_date_str} {s_time}"
                    if crosses_mid or e_time < s_time:
                        next_d = occ_d + timedelta(days=1)
                        occ_end = f"{next_d.strftime('%Y-%m-%d')} {e_time}"
                    else:
                        occ_end = f"{occ_date_str} {e_time}"

                    title = f"{carer_name}; {shift_code_val}"
                    if us.doubleup:
                        title = f"[2 Carers] {title}"

                    event_id = us.id * 100000 + int(occ_d.strftime("%Y%m%d")) % 10000

                    events.append(
                        VueCalEvent(
                            id=event_id,
                            user_shift_id=us.id,
                            user_id=us.user_id or 1,
                            carer_name=carer_name,
                            su_id=us.su_id,
                            service_user_name=su_name,
                            shift_id=us.shift_id,
                            shift_code=shift_code_val,
                            shift_color=shift_color_val,
                            shift_start=s_time,
                            shift_end=e_time,
                            branch_id=us.branch_id,
                            start=occ_start,
                            end=occ_end,
                            clock_in="",
                            clock_out="",
                            title=title,
                            content=us.notes or "",
                            status=us.status or "confirmed",
                            class_name=f"shift-{(us.status or 'confirmed').lower()}",
                            split=us.user_id or 1,
                            doubleup=bool(us.doubleup),
                            rrule_str=us.rrule_str or None,
                            recurrence_rule=None,
                            recurrence_exception=getattr(us, "recurrence_exception", None),
                            is_recurring=is_rec,
                            occurrence_date=occ_date_str,
                            series_start_date=us_start_str or None,
                            series_end_date=us_end_str or None
                        )
                    )

        return events
    except Exception as e:
        return events
