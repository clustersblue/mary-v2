from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Union, Any
from datetime import datetime, date, timedelta, time
from app.schemas.user import UserOut
from app.schemas.service_user import ServiceUserOut

def format_time_val(v):
    if v is None:
        return None
    if isinstance(v, timedelta):
        total_seconds = int(v.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    if isinstance(v, time):
        return v.strftime("%H:%M")
    if isinstance(v, str):
        if len(v) >= 5 and ":" in v:
            return v[:5]
        return v
    return str(v)

# --- Schemas for mary_api_db_new.m_shifts (Care Planner Master Catalog) ---
class MShiftBase(BaseModel):
    shift_name: str
    shift_code: Optional[str] = None
    shift_color: Optional[str] = None
    service: Optional[int] = 1
    shift_type: Optional[int] = 1
    start_time: Optional[str] = "08:00"
    end_time: Optional[str] = "17:00"
    hourly_rate: Optional[float] = 0.0

class MShiftCreate(MShiftBase):
    pass

class MShiftOut(MShiftBase):
    id: int
    shift_id: Optional[int] = None
    shift: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def populate_aliases(self):
        if not self.shift_id:
            self.shift_id = self.id
        if not self.shift:
            self.shift = self.shift_name
        if not self.shift_code:
            self.shift_code = self.shift_name
        return self

# Backward-compat aliases for MShift
DtrShiftBase = MShiftBase
DtrShiftCreate = MShiftCreate
DtrShiftOut = MShiftOut

# --- Schemas for mary_api_db_new.dtr_shifts (DTR Work Shifts Configuration) ---
class DtrShiftRecordBase(BaseModel):
    shift_code: str
    start_time: str
    end_time: str
    crosses_midnight: Optional[bool] = False
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    grace_period: Optional[int] = 0
    night_diff_from: Optional[str] = None
    night_diff_to: Optional[str] = None
    is_flexible: Optional[bool] = False
    is_rotating: Optional[bool] = False
    shift_color: Optional[str] = None

    @field_validator("start_time", "end_time", "break_start", "break_end", "night_diff_from", "night_diff_to", mode="before")
    def format_times(cls, v):
        return format_time_val(v)

class DtrShiftRecordCreate(DtrShiftRecordBase):
    pass

class DtrShiftRecordOut(DtrShiftRecordBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User Shift Assignment Schemas
class DtrUserShiftBase(BaseModel):
    user_id: int
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    branch_id: Optional[int] = None
    start_date: Any = None
    end_date: Any = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    rrule_str: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_exception: Optional[str] = None
    recurrence_id: Optional[int] = None
    doubleup: Optional[bool] = False
    status: Optional[str] = "scheduled"
    notes: Optional[str] = None

class DtrUserShiftCreate(DtrUserShiftBase):
    pass

class DtrUserShiftOut(BaseModel):
    id: int
    user_id: int
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    branch_id: Optional[int] = None
    start_date: Any = None
    end_date: Any = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    rrule_str: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_exception: Optional[str] = None
    recurrence_id: Optional[int] = None
    doubleup: Optional[bool] = False
    status: Optional[str] = "scheduled"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    carer: Optional[UserOut] = None
    service_user: Optional[ServiceUserOut] = None
    shift_template: Optional[Union[DtrShiftRecordOut, MShiftOut, Any]] = None

    class Config:
        from_attributes = True

    @field_validator("start_date", "end_date", mode="before")
    def convert_date_to_str(cls, v):
        if isinstance(v, (datetime, date)):
            return v.strftime("%Y-%m-%d")
        return str(v) if v is not None else None

# Vue-Cal / Syncfusion Event Projection Schema
class VueCalEvent(BaseModel):
    id: int
    user_shift_id: Optional[int] = None
    user_id: int
    carer_name: str
    su_id: Optional[int] = None
    service_user_name: Optional[str] = None
    shift_id: Optional[int] = None
    shift_code: Optional[str] = None
    shift_color: Optional[str] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    branch_id: Optional[int] = None
    start: str # YYYY-MM-DD HH:mm
    end: str   # YYYY-MM-DD HH:mm
    clock_in: Optional[str] = None # HH:mm
    clock_out: Optional[str] = None # HH:mm
    title: str
    content: Optional[str] = None
    status: str
    class_name: Optional[str] = None
    split: int # carer column split id
    doubleup: Optional[bool] = False
    rrule_str: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_exception: Optional[str] = None
    is_recurring: Optional[bool] = False
    occurrence_date: Optional[str] = None
    series_start_date: Optional[str] = None
    series_end_date: Optional[str] = None
