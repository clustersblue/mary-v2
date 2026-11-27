from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime, date
from app.schemas.master_data import BranchOut, CarerStatusOut, GenderOut


def _blank_to_none(value: Any) -> Any:
    if value == "":
        return None
    return value


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    surname: str
    username: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None
    gender_id: Optional[int] = None
    carer_status_id: Optional[int] = None
    branch_id: Optional[int] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality_id: Optional[int] = None
    marital_status_id: Optional[int] = None
    resident_status_id: Optional[int] = None
    relation_id: Optional[int] = None
    employment_type_id: Optional[int] = None
    contract_type_id: Optional[int] = None
    pension_scheme_id: Optional[int] = None
    ni_num: Optional[str] = None
    employment_start_date: Optional[date] = None
    employment_history: Optional[str] = None
    carer_notes: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_address: Optional[str] = None
    emergency_contact_number: Optional[str] = None

    @field_validator(
        "username", "email", "user_id", "mobile", "address", "ni_num",
        "employment_history", "carer_notes", "emergency_contact_name",
        "emergency_address", "emergency_contact_number",
        "date_of_birth", "employment_start_date",
        "gender_id", "carer_status_id", "branch_id", "nationality_id",
        "marital_status_id", "resident_status_id", "relation_id",
        "employment_type_id", "contract_type_id", "pension_scheme_id",
        mode="before",
    )
    @classmethod
    def blank_strings_are_null(cls, value: Any) -> Any:
        return _blank_to_none(value)


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(UserBase):
    pass


class UserLightweight(BaseModel):
    id: int
    first_name: str
    surname: str
    username: Optional[str] = None
    carer_status_id: Optional[int] = None
    branch_id: Optional[int] = None
    carer_full_name: Optional[str] = None
    branch: Optional[BranchOut] = None

    class Config:
        from_attributes = True


class UserOut(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    gender: Optional[GenderOut] = None
    branch: Optional[BranchOut] = None
    carer_status: Optional[CarerStatusOut] = None

    class Config:
        from_attributes = True
