from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime, date
from app.schemas.master_data import BranchOut, ServiceStatusOut, GenderOut


def _blank_to_none(value: Any) -> Any:
    if value == "":
        return None
    return value


class ServiceUserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    surname: str
    su_number: Optional[str] = None
    preferred_name: Optional[str] = None
    gender_id: Optional[int] = None
    service_status_id: Optional[int] = None
    branch_id: Optional[int] = None
    religion_id: Optional[int] = None
    marital_status_id: Optional[int] = None
    nationality_id: Optional[int] = None
    gp_id: Optional[int] = None
    nhs_id: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[date] = None
    service_start_date: Optional[date] = None
    service_end_date: Optional[date] = None
    next_of_kin: Optional[str] = None
    nok_address: Optional[str] = None
    nok_relationship: Optional[int] = None
    nok_contact_number: Optional[str] = None
    second_contact: Optional[str] = None
    second_contact_address: Optional[str] = None
    second_contact_number: Optional[str] = None
    second_contact_relationship: Optional[int] = None
    contract: Optional[str] = None
    services_provided: Optional[str] = None
    medical_history: Optional[str] = None
    medications_json: Optional[str] = None
    care_plan_notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator(
        "su_number", "preferred_name", "address", "phone", "email",
        "next_of_kin", "nok_address", "nok_contact_number",
        "second_contact", "second_contact_address", "second_contact_number",
        "contract", "services_provided", "medical_history",
        "medications_json", "care_plan_notes",
        "date_of_birth", "service_start_date", "service_end_date",
        "gender_id", "service_status_id", "branch_id", "religion_id",
        "marital_status_id", "nationality_id", "gp_id", "nhs_id",
        "nok_relationship", "second_contact_relationship",
        "latitude", "longitude",
        mode="before",
    )
    @classmethod
    def blank_strings_are_null(cls, value: Any) -> Any:
        return _blank_to_none(value)


class ServiceUserCreate(ServiceUserBase):
    pass


class ServiceUserUpdate(ServiceUserBase):
    pass


class ServiceUserOut(ServiceUserBase):
    su_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    gender: Optional[GenderOut] = None
    service_status: Optional[ServiceStatusOut] = None
    branch: Optional[BranchOut] = None
    su_full_name: Optional[str] = None

    class Config:
        from_attributes = True
