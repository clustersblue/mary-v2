from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import UserOut
from app.schemas.service_user import ServiceUserOut

class ClockInRequest(BaseModel):
    user_id: Optional[int] = None
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ClockOutRequest(BaseModel):
    attendance_id: int
    notes: Optional[str] = None

class AttendanceOut(BaseModel):
    id: int
    user_id: int
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    clock_in_lat: Optional[float] = None
    clock_in_lon: Optional[float] = None
    clock_in_distance_meters: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    carer: Optional[UserOut] = None
    service_user: Optional[ServiceUserOut] = None

    class Config:
        from_attributes = True

class CareNoteGenerateRequest(BaseModel):
    patient_name: str
    carer_name: str
    shift_date: str
    shift_time: str
    care_notes: str

class ManualDtrServiceUser(BaseModel):
    id: Optional[int] = None
    su_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None

class ManualDtrRequest(BaseModel):
    user_id: int
    shift_id: Optional[int] = None
    user_shift_id: Optional[int] = None
    occurrence_date: str
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    full_attendance: Optional[bool] = False
    leave_type_id: Optional[int] = None
    leave_type: Optional[str] = None
    service_users: Optional[list[ManualDtrServiceUser]] = []

