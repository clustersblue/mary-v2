from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime

class BaseMasterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

# Generic Item Payload for flexible master data CRUD
class MasterItemPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

# Gender
class GenderCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    gender_name: Optional[str] = None
    gender: Optional[str] = None
    name: Optional[str] = None

class GenderOut(BaseMasterSchema):
    gender_id: int
    gender_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Religion
class ReligionCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    religion_name: Optional[str] = None
    religion: Optional[str] = None
    name: Optional[str] = None

class ReligionOut(BaseMasterSchema):
    religion_id: int
    religion_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Nationality
class NationalityCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    nationality_name: Optional[str] = None
    nationality: Optional[str] = None
    name: Optional[str] = None

class NationalityOut(BaseMasterSchema):
    nationality_id: int
    nationality_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Marital Status
class MaritalStatusCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    status_name: Optional[str] = None
    marital_status: Optional[str] = None
    name: Optional[str] = None

class MaritalStatusOut(BaseMasterSchema):
    marital_status_id: int
    status_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Relation
class RelationCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    relation_name: Optional[str] = None
    relation: Optional[str] = None
    name: Optional[str] = None

class RelationOut(BaseMasterSchema):
    relation_id: int
    relation_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Carer Status
class CarerStatusCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    status_name: Optional[str] = None
    carer_status: Optional[str] = None
    name: Optional[str] = None

class CarerStatusOut(BaseMasterSchema):
    carer_status_id: int
    status_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Service Status
class ServiceStatusCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    status_name: Optional[str] = None
    service_status: Optional[str] = None
    name: Optional[str] = None

class ServiceStatusOut(BaseMasterSchema):
    service_status_id: int
    status_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Resident Status
class ResidentStatusCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    status_name: Optional[str] = None
    resident_status: Optional[str] = None
    name: Optional[str] = None

class ResidentStatusOut(BaseMasterSchema):
    resident_status_id: int
    status_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Contract Type
class ContractTypeCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    type_name: Optional[str] = None
    contract_type: Optional[str] = None
    name: Optional[str] = None

class ContractTypeOut(BaseMasterSchema):
    contract_type_id: int
    type_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Employment Type
class EmploymentTypeCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    type_name: Optional[str] = None
    employment_type: Optional[str] = None
    name: Optional[str] = None

class EmploymentTypeOut(BaseMasterSchema):
    employment_type_id: int
    type_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Branch
class BranchCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    branch_name: Optional[str] = None
    branch: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    branch_address: Optional[str] = None
    contact_number: Optional[str] = None

class BranchOut(BaseMasterSchema):
    branch_id: int
    branch_name: Optional[str] = None
    branch: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    contact_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Service
class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    service_name: Optional[str] = None
    service: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None

class ServiceOut(BaseMasterSchema):
    service_id: int
    service_name: Optional[str] = None
    service: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Pension Scheme
class PensionSchemeCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    scheme_name: Optional[str] = None
    pension_scheme: Optional[str] = None
    name: Optional[str] = None

class PensionSchemeOut(BaseMasterSchema):
    pension_scheme_id: int
    scheme_name: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Service User Rate
class ServiceUserRateCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    rate: Optional[float] = 0.0
    invoice: Optional[float] = 0.0

class ServiceUserRateUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    su_id: Optional[int] = None
    shift_id: Optional[int] = None
    rate: Optional[float] = None
    invoice: Optional[float] = None

class ServiceUserRateOut(BaseMasterSchema):
    id: Optional[int] = None
    su_id: Optional[int] = None
    su_full_name: Optional[str] = None
    shift_id: Optional[int] = None
    shift: Optional[str] = None
    rate: Optional[float] = 0.0
    invoice: Optional[float] = 0.0
