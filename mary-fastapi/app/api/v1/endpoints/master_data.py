from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_, or_
from typing import List, Optional, Any, Dict
from datetime import datetime

from app.db.session import get_db
from app.models.master_data import (
    Gender, Religion, Nationality, MaritalStatus, Relation,
    CarerStatus, ServiceStatus, ResidentStatus, ContractType,
    EmploymentType, Branch, Service, PensionScheme, CareType,
    ConditionCategory, MedicalCondition, GP, NHS, Reference,
    Requirement, RequirementStatus, TrainingCourse, ServiceUserRate
)
from app.models.service_user import ServiceUser
from app.models.shift import MShift
from app.schemas.master_data import (
    GenderCreate, ReligionCreate, NationalityCreate, MaritalStatusCreate,
    RelationCreate, CarerStatusCreate, ServiceStatusCreate, ResidentStatusCreate,
    ContractTypeCreate, EmploymentTypeCreate, BranchCreate, ServiceCreate,
    PensionSchemeCreate, ServiceUserRateCreate, ServiceUserRateUpdate
)
from app.core.security import get_current_active_user, get_current_staff_user, get_current_admin_user
from app.models.user import User

router = APIRouter()

# ==============================================================================
# --- 1. SERVICE USER RATES MATRIX (m_service_users x m_shifts x m_service_user_rates) ---
# ==============================================================================

@router.get("/getsurates")
@router.get("/service-user-rates")
async def get_service_user_rates(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    """
    Returns full cross-product matrix of Active Service Users x Master Shifts
    joined with existing m_service_user_rates, exactly mirroring legacy getsurates.
    """
    query = text("""
        SELECT 
            su.su_id,
            CONCAT(su.su_first_name, ' ', su.su_last_name) AS su_full_name,
            s.shift_id,
            s.shift,
            r.id,
            CAST(COALESCE(r.rate, 0) AS DECIMAL(10,2)) AS rate,
            CAST(COALESCE(r.invoice, 0) AS DECIMAL(10,2)) AS invoice
        FROM m_service_users su
        CROSS JOIN m_shifts s
        LEFT JOIN m_service_user_rates r 
            ON su.su_id = r.su_id 
            AND s.shift_id = r.shift_id 
            AND r.deleted_at IS NULL
        WHERE su.deleted_at IS NULL
            AND su.service_status_id = 1
            AND s.deleted_at IS NULL
        ORDER BY su.su_id ASC, s.shift_id ASC
    """)
    result = await db.execute(query)
    rows = result.fetchall()
    
    data = []
    for row in rows:
        data.append({
            "su_id": row[0],
            "su_full_name": row[1] or "",
            "shift_id": row[2],
            "shift": row[3] or "",
            "id": row[4],
            "rate": float(row[5] or 0),
            "invoice": float(row[6] or 0)
        })
    return data

@router.post("/savesurate", status_code=status.HTTP_201_CREATED)
@router.post("/service-user-rates", status_code=status.HTTP_201_CREATED)
async def create_service_user_rate(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    su_id = payload.get("su_id")
    shift_id = payload.get("shift_id")
    rate = float(payload.get("rate") or 0.0)
    invoice = float(payload.get("invoice") or 0.0)

    # Upsert check: if rate record already exists for this (su_id, shift_id), update it
    if su_id and shift_id:
        existing = await db.execute(
            select(ServiceUserRate).where(
                ServiceUserRate.su_id == su_id,
                ServiceUserRate.shift_id == shift_id,
                ServiceUserRate.deleted_at.is_(None)
            )
        )
        rate_record = existing.scalar_one_or_none()
        if rate_record:
            rate_record.rate = rate
            rate_record.invoice = invoice
            await db.commit()
            await db.refresh(rate_record)
            return {"success": True, "data": rate_record}

    rate_record = ServiceUserRate(
        su_id=su_id,
        shift_id=shift_id,
        rate=rate,
        invoice=invoice
    )
    db.add(rate_record)
    await db.commit()
    await db.refresh(rate_record)
    return {"success": True, "data": rate_record}

@router.post("/updatesurate/{rate_id}")
@router.put("/updatesurate/{rate_id}")
@router.put("/service-user-rates/{rate_id}")
async def update_service_user_rate(rate_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    result = await db.execute(select(ServiceUserRate).where(ServiceUserRate.id == rate_id))
    rate_record = result.scalar_one_or_none()
    if not rate_record:
        raise HTTPException(status_code=404, detail="Service user rate record not found")
    
    if "rate" in payload and payload["rate"] is not None:
        rate_record.rate = float(payload["rate"])
    if "invoice" in payload and payload["invoice"] is not None:
        rate_record.invoice = float(payload["invoice"])
    if "su_id" in payload and payload["su_id"] is not None:
        rate_record.su_id = int(payload["su_id"])
    if "shift_id" in payload and payload["shift_id"] is not None:
        rate_record.shift_id = int(payload["shift_id"])

    await db.commit()
    await db.refresh(rate_record)
    return {"success": True, "data": rate_record}

@router.delete("/surate/{rate_id}")
@router.delete("/service-user-rates/{rate_id}")
async def delete_service_user_rate(rate_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    result = await db.execute(select(ServiceUserRate).where(ServiceUserRate.id == rate_id))
    rate_record = result.scalar_one_or_none()
    if not rate_record:
        raise HTTPException(status_code=404, detail="Service user rate record not found")
    rate_record.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}

@router.post("/checkServiceUserRate")
async def check_service_user_rate(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    su_id = payload.get("su_id")
    shift_id = payload.get("shift_id")
    result = await db.execute(
        select(ServiceUserRate).where(
            ServiceUserRate.su_id == su_id,
            ServiceUserRate.shift_id == shift_id,
            ServiceUserRate.deleted_at.is_(None)
        )
    )
    rate_record = result.scalar_one_or_none()
    if rate_record and (rate_record.rate or rate_record.invoice):
        return {"success": True, "data": rate_record}
    return {"success": False, "data": False}


# ==============================================================================
# --- 2. MASTER DATA CRUD ENDPOINTS (Both Legacy & Standard REST Aliases) ---
# ==============================================================================

# Helper for standard JSON formatting
def format_entity(item, pk_name, name_col, code_val="", desc_val="", status_val="Active"):
    pk_val = getattr(item, pk_name)
    raw_name = getattr(item, name_col, "")
    return {
        "id": pk_val,
        pk_name: pk_val,
        "name": raw_name,
        name_col: raw_name,
        "code": code_val,
        "description": desc_val,
        "status": status_val
    }

# --- 2.1 Branches (m_branches) ---
@router.get("/getbranches")
@router.get("/branches")
async def get_branches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Branch).where(Branch.deleted_at.is_(None)).order_by(Branch.branch_id.asc()))
    branches = result.scalars().all()
    return [{
        "id": b.branch_id,
        "branch_id": b.branch_id,
        "name": b.branch_name,
        "branch": b.branch_name,
        "branch_name": b.branch_name,
        "address": b.address or "",
        "branch_address": b.address or "",
        "description": b.address or "",
        "contact_number": b.contact_number or "",
        "code": f"BR-{b.branch_id}",
        "status": "Active"
    } for b in branches]

@router.post("/savebranch", status_code=status.HTTP_201_CREATED)
@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    name = payload.get("branch") or payload.get("branch_name") or payload.get("name") or "New Branch"
    addr = payload.get("branch_address") or payload.get("address") or payload.get("description") or ""
    contact = payload.get("contact_number") or ""
    b = Branch(branch_name=name, address=addr, contact_number=contact)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return {"success": True, "data": b, "id": b.branch_id, "name": b.branch_name}

@router.post("/updatebranch/{branch_id}")
@router.put("/updatebranch/{branch_id}")
@router.put("/branches/{branch_id}")
async def update_branch(branch_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    res = await db.execute(select(Branch).where(Branch.branch_id == branch_id))
    b = res.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Branch not found")
    if "branch" in payload or "branch_name" in payload or "name" in payload:
        b.branch_name = payload.get("branch") or payload.get("branch_name") or payload.get("name")
    if "branch_address" in payload or "address" in payload or "description" in payload:
        b.address = payload.get("branch_address") or payload.get("address") or payload.get("description")
    if "contact_number" in payload:
        b.contact_number = payload.get("contact_number")
    await db.commit()
    await db.refresh(b)
    return {"success": True, "data": b}

@router.delete("/branch/{branch_id}")
@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    res = await db.execute(select(Branch).where(Branch.branch_id == branch_id))
    b = res.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Branch not found")
    b.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.2 Carer Statuses (m_carer_statuses) ---
@router.get("/getcarerstatuses")
@router.get("/carer-statuses")
async def get_carer_statuses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(CarerStatus).where(CarerStatus.deleted_at.is_(None)).order_by(CarerStatus.carer_status_id.asc()))
    items = res.scalars().all()
    return [{
        "id": c.carer_status_id,
        "carer_status_id": c.carer_status_id,
        "name": c.status_name,
        "carer_status": c.status_name,
        "code": f"CS-{c.carer_status_id}",
        "description": c.status_name,
        "status": "Active"
    } for c in items]

@router.post("/savecarerstatuses", status_code=status.HTTP_201_CREATED)
@router.post("/carer-statuses", status_code=status.HTTP_201_CREATED)
async def create_carer_status(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("carer_status") or payload.get("status_name") or payload.get("name") or "New Status"
    item = CarerStatus(status_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.carer_status_id, "name": item.status_name}

@router.post("/updatecarerstatuses/{id}")
@router.put("/updatecarerstatuses/{id}")
@router.put("/carer-statuses/{id}")
async def update_carer_status(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(CarerStatus).where(CarerStatus.carer_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Carer status not found")
    name = payload.get("carer_status") or payload.get("status_name") or payload.get("name")
    if name:
        item.status_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/carerstatuses/{id}")
@router.delete("/carer-statuses/{id}")
async def delete_carer_status(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(CarerStatus).where(CarerStatus.carer_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Carer status not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.3 Care Types (m_care_types) ---
@router.get("/care-types")
async def get_care_types(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(CareType).order_by(CareType.care_type_id.asc()))
    items = res.scalars().all()
    return [{
        "id": c.care_type_id,
        "care_type_id": c.care_type_id,
        "name": c.name,
        "code": f"CARE-{c.care_type_id}",
        "description": c.description or "",
        "status": "Active"
    } for c in items]

@router.post("/care-types", status_code=status.HTTP_201_CREATED)
async def create_care_type(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("name") or "New Care Type"
    desc = payload.get("description") or ""
    item = CareType(name=name, description=desc)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.care_type_id, "name": item.name}

@router.put("/care-types/{id}")
@router.post("/care-types/{id}")
async def update_care_type(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(CareType).where(CareType.care_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Care type not found")
    if "name" in payload:
        item.name = payload["name"]
    if "description" in payload:
        item.description = payload["description"]
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/care-types/{id}")
async def delete_care_type(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(CareType).where(CareType.care_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Care type not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


# --- 2.4 Condition Categories (m_condition_categories) ---
@router.get("/condition-categories")
async def get_condition_categories(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ConditionCategory).order_by(ConditionCategory.category_id.asc()))
    items = res.scalars().all()
    return [{
        "id": c.category_id,
        "category_id": c.category_id,
        "name": c.name,
        "code": f"CAT-{c.category_id}",
        "description": c.description or "",
        "status": "Active"
    } for c in items]

@router.post("/condition-categories", status_code=status.HTTP_201_CREATED)
async def create_condition_category(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("name") or "New Category"
    desc = payload.get("description") or ""
    item = ConditionCategory(name=name, description=desc)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.category_id, "name": item.name}

@router.put("/condition-categories/{id}")
@router.post("/condition-categories/{id}")
async def update_condition_category(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ConditionCategory).where(ConditionCategory.category_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    if "name" in payload:
        item.name = payload["name"]
    if "description" in payload:
        item.description = payload["description"]
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/condition-categories/{id}")
async def delete_condition_category(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ConditionCategory).where(ConditionCategory.category_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


# --- 2.5 Contract Types (m_contract_types) ---
@router.get("/getcontracttypes")
@router.get("/contract-types")
async def get_contract_types(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContractType).where(ContractType.deleted_at.is_(None)).order_by(ContractType.contract_type_id.asc()))
    items = res.scalars().all()
    return [{
        "id": c.contract_type_id,
        "contract_type_id": c.contract_type_id,
        "name": c.type_name,
        "contract_type": c.type_name,
        "code": f"CT-{c.contract_type_id}",
        "description": c.type_name,
        "status": "Active"
    } for c in items]

@router.post("/savecontracttypes", status_code=status.HTTP_201_CREATED)
@router.post("/contract-types", status_code=status.HTTP_201_CREATED)
async def create_contract_type(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("contract_type") or payload.get("type_name") or payload.get("name") or "New Contract Type"
    item = ContractType(type_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.contract_type_id, "name": item.type_name}

@router.post("/updatecontracttypes/{id}")
@router.put("/updatecontracttypes/{id}")
@router.put("/contract-types/{id}")
async def update_contract_type(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ContractType).where(ContractType.contract_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Contract type not found")
    name = payload.get("contract_type") or payload.get("type_name") or payload.get("name")
    if name:
        item.type_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/contracttypes/{id}")
@router.delete("/contract-types/{id}")
async def delete_contract_type(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ContractType).where(ContractType.contract_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Contract type not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.6 Employment Types (m_employment_types) ---
@router.get("/getemploymenttypes")
@router.get("/employment-types")
async def get_employment_types(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EmploymentType).where(EmploymentType.deleted_at.is_(None)).order_by(EmploymentType.employment_type_id.asc()))
    items = res.scalars().all()
    return [{
        "id": e.employment_type_id,
        "employment_type_id": e.employment_type_id,
        "name": e.type_name,
        "employment_type": e.type_name,
        "code": f"ET-{e.employment_type_id}",
        "description": e.type_name,
        "status": "Active"
    } for e in items]

@router.post("/saveemploymenttypes", status_code=status.HTTP_201_CREATED)
@router.post("/employment-types", status_code=status.HTTP_201_CREATED)
async def create_employment_type(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("employment_type") or payload.get("type_name") or payload.get("name") or "New Employment Type"
    item = EmploymentType(type_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.employment_type_id, "name": item.type_name}

@router.post("/updateemploymenttypes/{id}")
@router.put("/updateemploymenttypes/{id}")
@router.put("/employment-types/{id}")
async def update_employment_type(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(EmploymentType).where(EmploymentType.employment_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Employment type not found")
    name = payload.get("employment_type") or payload.get("type_name") or payload.get("name")
    if name:
        item.type_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/employmenttypes/{id}")
@router.delete("/employment-types/{id}")
async def delete_employment_type(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(EmploymentType).where(EmploymentType.employment_type_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Employment type not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.7 Genders (m_genders) ---
@router.get("/getgenders")
@router.get("/genders")
async def get_genders(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Gender).where(Gender.deleted_at.is_(None)).order_by(Gender.gender_id.asc()))
    items = res.scalars().all()
    return [{
        "id": g.gender_id,
        "gender_id": g.gender_id,
        "name": g.gender_name,
        "gender": g.gender_name,
        "code": f"G-{g.gender_id}",
        "description": g.gender_name,
        "status": "Active"
    } for g in items]

@router.post("/savegenders", status_code=status.HTTP_201_CREATED)
@router.post("/genders", status_code=status.HTTP_201_CREATED)
async def create_gender(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("gender") or payload.get("gender_name") or payload.get("name") or "New Gender"
    item = Gender(gender_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.gender_id, "name": item.gender_name}

@router.post("/updategenders/{gender_id}")
@router.put("/updategenders/{gender_id}")
@router.put("/genders/{gender_id}")
async def update_gender(gender_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Gender).where(Gender.gender_id == gender_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Gender not found")
    name = payload.get("gender") or payload.get("gender_name") or payload.get("name")
    if name:
        item.gender_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/genders/{gender_id}")
async def delete_gender(gender_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Gender).where(Gender.gender_id == gender_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Gender not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.8 GP Practices (m_gps) ---
@router.get("/getgps")
@router.get("/gps")
async def get_gps(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(GP).where(GP.deleted_at.is_(None)).order_by(GP.gp_id.asc()))
    items = res.scalars().all()
    return [{
        "id": g.gp_id,
        "gp_id": g.gp_id,
        "name": f"Dr. {g.gp_first_name or ''} {g.gp_last_name or ''}".strip(),
        "gp_first_name": g.gp_first_name or "",
        "gp_last_name": g.gp_last_name or "",
        "address": g.gp_address or "",
        "description": g.gp_address or g.gp_notes or "",
        "email": g.gp_email or "",
        "contact_number": g.gp_contact_number or "",
        "code": f"GP-{g.gp_id}",
        "status": "Active"
    } for g in items]

@router.post("/savegp", status_code=status.HTTP_201_CREATED)
@router.post("/gps", status_code=status.HTTP_201_CREATED)
async def create_gp(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    first_name = payload.get("gp_first_name") or payload.get("name", "").split(" ")[0] or "Dr."
    last_name = payload.get("gp_last_name") or (" ".join(payload.get("name", "").split(" ")[1:]) if len(payload.get("name", "").split(" ")) > 1 else "")
    addr = payload.get("gp_address") or payload.get("address") or payload.get("description") or ""
    email = payload.get("gp_email") or payload.get("email") or ""
    contact = payload.get("gp_contact_number") or payload.get("contact_number") or ""
    notes = payload.get("gp_notes") or payload.get("notes") or ""
    item = GP(
        gp_first_name=first_name,
        gp_last_name=last_name,
        gp_address=addr,
        gp_email=email,
        gp_contact_number=contact,
        gp_notes=notes
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.gp_id, "name": f"{first_name} {last_name}".strip()}

@router.post("/updategp/{id}")
@router.put("/updategp/{id}")
@router.put("/gps/{id}")
async def update_gp(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(GP).where(GP.gp_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="GP not found")
    if "gp_first_name" in payload or "name" in payload:
        item.gp_first_name = payload.get("gp_first_name") or payload.get("name", "").split(" ")[0]
    if "gp_last_name" in payload:
        item.gp_last_name = payload.get("gp_last_name")
    if "gp_address" in payload or "address" in payload or "description" in payload:
        item.gp_address = payload.get("gp_address") or payload.get("address") or payload.get("description")
    if "gp_email" in payload or "email" in payload:
        item.gp_email = payload.get("gp_email") or payload.get("email")
    if "gp_contact_number" in payload or "contact_number" in payload:
        item.gp_contact_number = payload.get("gp_contact_number") or payload.get("contact_number")
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/gps/{id}")
async def delete_gp(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(GP).where(GP.gp_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="GP not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.9 Marital Statuses (m_marital_statuses) ---
@router.get("/getmaritalstatuses")
@router.get("/marital-statuses")
async def get_marital_statuses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MaritalStatus).where(MaritalStatus.deleted_at.is_(None)).order_by(MaritalStatus.marital_status_id.asc()))
    items = res.scalars().all()
    return [{
        "id": m.marital_status_id,
        "marital_status_id": m.marital_status_id,
        "name": m.status_name,
        "marital_status": m.status_name,
        "code": f"MS-{m.marital_status_id}",
        "description": m.status_name,
        "status": "Active"
    } for m in items]

@router.post("/savemaritalstatuses", status_code=status.HTTP_201_CREATED)
@router.post("/marital-statuses", status_code=status.HTTP_201_CREATED)
async def create_marital_status(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("marital_status") or payload.get("status_name") or payload.get("name") or "New Marital Status"
    item = MaritalStatus(status_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.marital_status_id, "name": item.status_name}

@router.post("/updatemaritalstatuses/{id}")
@router.put("/updatemaritalstatuses/{id}")
@router.put("/marital-statuses/{id}")
async def update_marital_status(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(MaritalStatus).where(MaritalStatus.marital_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Marital status not found")
    name = payload.get("marital_status") or payload.get("status_name") or payload.get("name")
    if name:
        item.status_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/maritalstatuses/{id}")
@router.delete("/marital-statuses/{id}")
async def delete_marital_status(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(MaritalStatus).where(MaritalStatus.marital_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Marital status not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.10 Medical Conditions (m_medical_conditions) ---
@router.get("/medical-conditions")
async def get_medical_conditions(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MedicalCondition).order_by(MedicalCondition.condition_id.asc()))
    items = res.scalars().all()
    return [{
        "id": m.condition_id,
        "condition_id": m.condition_id,
        "name": m.name,
        "code": f"MED-{m.condition_id}",
        "description": m.description or "",
        "status": "Active"
    } for m in items]

@router.post("/medical-conditions", status_code=status.HTTP_201_CREATED)
async def create_medical_condition(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("name") or "New Condition"
    desc = payload.get("description") or ""
    item = MedicalCondition(name=name, description=desc)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.condition_id, "name": item.name}

@router.put("/medical-conditions/{id}")
@router.post("/medical-conditions/{id}")
async def update_medical_condition(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(MedicalCondition).where(MedicalCondition.condition_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    if "name" in payload:
        item.name = payload["name"]
    if "description" in payload:
        item.description = payload["description"]
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/medical-conditions/{id}")
async def delete_medical_condition(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(MedicalCondition).where(MedicalCondition.condition_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


# --- 2.11 Nationalities (m_nationalities) ---
@router.get("/getnationalities")
@router.get("/nationalities")
async def get_nationalities(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Nationality).where(Nationality.deleted_at.is_(None)).order_by(Nationality.nationality_id.asc()))
    items = res.scalars().all()
    return [{
        "id": n.nationality_id,
        "nationality_id": n.nationality_id,
        "name": n.nationality_name,
        "nationality": n.nationality_name,
        "code": f"NAT-{n.nationality_id}",
        "description": n.nationality_name,
        "status": "Active"
    } for n in items]

@router.post("/savenationalities", status_code=status.HTTP_201_CREATED)
@router.post("/nationalities", status_code=status.HTTP_201_CREATED)
async def create_nationality(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("nationality") or payload.get("nationality_name") or payload.get("name") or "New Nationality"
    item = Nationality(nationality_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.nationality_id, "name": item.nationality_name}

@router.post("/updatenationalities/{id}")
@router.put("/updatenationalities/{id}")
@router.put("/nationalities/{id}")
async def update_nationality(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Nationality).where(Nationality.nationality_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Nationality not found")
    name = payload.get("nationality") or payload.get("nationality_name") or payload.get("name")
    if name:
        item.nationality_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/nationalities/{id}")
async def delete_nationality(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Nationality).where(Nationality.nationality_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Nationality not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.12 NHS Commissioners (m_nhsses) ---
@router.get("/getnhs")
@router.get("/nhs")
async def get_nhs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(NHS).where(NHS.deleted_at.is_(None)).order_by(NHS.nhs_id.asc()))
    items = res.scalars().all()
    return [{
        "id": n.nhs_id,
        "nhs_id": n.nhs_id,
        "name": f"{n.nhs_first_name or ''} {n.nhs_last_name or ''}".strip(),
        "nhs_first_name": n.nhs_first_name or "",
        "nhs_last_name": n.nhs_last_name or "",
        "address": n.nhs_address or "",
        "description": n.nhs_address or n.nhs_notes or "",
        "email": n.nhs_email or "",
        "contact_number": n.nhs_contact_number or "",
        "code": f"NHS-{n.nhs_id}",
        "status": "Active"
    } for n in items]

@router.post("/savenhs", status_code=status.HTTP_201_CREATED)
@router.post("/nhs", status_code=status.HTTP_201_CREATED)
async def create_nhs(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    first_name = payload.get("nhs_first_name") or payload.get("name", "").split(" ")[0] or "NHS"
    last_name = payload.get("nhs_last_name") or (" ".join(payload.get("name", "").split(" ")[1:]) if len(payload.get("name", "").split(" ")) > 1 else "Trust")
    addr = payload.get("nhs_address") or payload.get("address") or payload.get("description") or ""
    email = payload.get("nhs_email") or payload.get("email") or ""
    contact = payload.get("nhs_contact_number") or payload.get("contact_number") or ""
    notes = payload.get("nhs_notes") or payload.get("notes") or ""
    item = NHS(
        nhs_first_name=first_name,
        nhs_last_name=last_name,
        nhs_address=addr,
        nhs_email=email,
        nhs_contact_number=contact,
        nhs_notes=notes
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.nhs_id, "name": f"{first_name} {last_name}".strip()}

@router.post("/updatenhs/{id}")
@router.put("/updatenhs/{id}")
@router.put("/nhs/{id}")
async def update_nhs(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(NHS).where(NHS.nhs_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="NHS Commissioner not found")
    if "nhs_first_name" in payload or "name" in payload:
        item.nhs_first_name = payload.get("nhs_first_name") or payload.get("name", "").split(" ")[0]
    if "nhs_last_name" in payload:
        item.nhs_last_name = payload.get("nhs_last_name")
    if "nhs_address" in payload or "address" in payload or "description" in payload:
        item.nhs_address = payload.get("nhs_address") or payload.get("address") or payload.get("description")
    if "nhs_email" in payload or "email" in payload:
        item.nhs_email = payload.get("nhs_email") or payload.get("email")
    if "nhs_contact_number" in payload or "contact_number" in payload:
        item.nhs_contact_number = payload.get("nhs_contact_number") or payload.get("contact_number")
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/nhs/{id}")
async def delete_nhs(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(NHS).where(NHS.nhs_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="NHS not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.13 Pension Schemes (m_pension_schemes) ---
@router.get("/getpensionscheme")
@router.get("/pension-schemes")
async def get_pension_schemes(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PensionScheme).where(PensionScheme.deleted_at.is_(None)).order_by(PensionScheme.pension_scheme_id.asc()))
    items = res.scalars().all()
    return [{
        "id": p.pension_scheme_id,
        "pension_scheme_id": p.pension_scheme_id,
        "name": p.scheme_name,
        "pension_scheme": p.scheme_name,
        "code": f"PEN-{p.pension_scheme_id}",
        "description": p.scheme_name,
        "status": "Active"
    } for p in items]

@router.post("/savepensionscheme", status_code=status.HTTP_201_CREATED)
@router.post("/pension-schemes", status_code=status.HTTP_201_CREATED)
async def create_pension_scheme(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("pension_scheme") or payload.get("scheme_name") or payload.get("name") or "New Pension Scheme"
    item = PensionScheme(scheme_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.pension_scheme_id, "name": item.scheme_name}

@router.post("/updatepensionscheme/{id}")
@router.put("/updatepensionscheme/{id}")
@router.put("/pension-schemes/{id}")
async def update_pension_scheme(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(PensionScheme).where(PensionScheme.pension_scheme_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Pension scheme not found")
    name = payload.get("pension_scheme") or payload.get("scheme_name") or payload.get("name")
    if name:
        item.scheme_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/pensionscheme/{id}")
@router.delete("/pension-schemes/{id}")
async def delete_pension_scheme(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(PensionScheme).where(PensionScheme.pension_scheme_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Pension scheme not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.14 References (m_references) ---
@router.get("/getreference")
@router.get("/references")
async def get_references(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Reference).where(Reference.deleted_at.is_(None)).order_by(Reference.reference_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.reference_id,
        "reference_id": r.reference_id,
        "name": f"{r.reference_first_name or ''} {r.reference_surname or ''}".strip() or (r.reference_relation or f"Reference #{r.reference_id}"),
        "reference_first_name": r.reference_first_name or "",
        "reference_surname": r.reference_surname or "",
        "code": f"REF-{r.reference_id}",
        "description": r.reference_address or r.reference_relation or "",
        "reference_address": r.reference_address or "",
        "reference_contact": r.reference_contact or "",
        "reference_relation": r.reference_relation or "",
        "status": "Active"
    } for r in items]

@router.post("/savereference", status_code=status.HTTP_201_CREATED)
@router.post("/references", status_code=status.HTTP_201_CREATED)
async def create_reference(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    first_name = payload.get("reference_first_name") or payload.get("name", "").split(" ")[0] or "Reference"
    surname = payload.get("reference_surname") or (" ".join(payload.get("name", "").split(" ")[1:]) if len(payload.get("name", "").split(" ")) > 1 else "")
    contact = payload.get("reference_contact") or payload.get("contact") or ""
    addr = payload.get("reference_address") or payload.get("address") or payload.get("description") or ""
    rel = payload.get("reference_relation") or payload.get("code") or "Professional"
    item = Reference(
        reference_first_name=first_name,
        reference_surname=surname,
        reference_contact=contact,
        reference_address=addr,
        reference_relation=rel
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.reference_id, "name": f"{first_name} {surname}".strip()}

@router.post("/updatereference/{id}")
@router.put("/updatereference/{id}")
@router.put("/references/{id}")
async def update_reference(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Reference).where(Reference.reference_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Reference not found")
    if "reference_first_name" in payload or "name" in payload:
        item.reference_first_name = payload.get("reference_first_name") or payload.get("name", "").split(" ")[0]
    if "reference_surname" in payload:
        item.reference_surname = payload.get("reference_surname")
    if "reference_address" in payload or "address" in payload or "description" in payload:
        item.reference_address = payload.get("reference_address") or payload.get("address") or payload.get("description")
    if "reference_contact" in payload or "contact" in payload:
        item.reference_contact = payload.get("reference_contact") or payload.get("contact")
    if "reference_relation" in payload:
        item.reference_relation = payload.get("reference_relation")
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/reference/{id}")
@router.delete("/references/{id}")
async def delete_reference(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Reference).where(Reference.reference_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Reference not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.15 Relations (m_relations) ---
@router.get("/getrelations")
@router.get("/relations")
async def get_relations(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Relation).where(Relation.deleted_at.is_(None)).order_by(Relation.relation_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.relation_id,
        "relation_id": r.relation_id,
        "name": r.relation_name,
        "relation": r.relation_name,
        "code": f"REL-{r.relation_id}",
        "description": r.relation_name,
        "status": "Active"
    } for r in items]

@router.post("/saverelations", status_code=status.HTTP_201_CREATED)
@router.post("/relations", status_code=status.HTTP_201_CREATED)
async def create_relation(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("relation") or payload.get("relation_name") or payload.get("name") or "New Relation"
    item = Relation(relation_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.relation_id, "name": item.relation_name}

@router.post("/updaterelations/{id}")
@router.put("/updaterelations/{id}")
@router.put("/relations/{id}")
async def update_relation(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Relation).where(Relation.relation_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Relation not found")
    name = payload.get("relation") or payload.get("relation_name") or payload.get("name")
    if name:
        item.relation_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/relations/{id}")
async def delete_relation(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Relation).where(Relation.relation_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Relation not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.16 Religions (m_religions) ---
@router.get("/get-religions")
@router.get("/religions")
async def get_religions(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Religion).order_by(Religion.religion_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.religion_id,
        "religion_id": r.religion_id,
        "name": r.religion_name,
        "religion": r.religion_name,
        "code": f"RELIG-{r.religion_id}",
        "description": r.religion_name,
        "status": "Active"
    } for r in items]

@router.post("/save-religions", status_code=status.HTTP_201_CREATED)
@router.post("/religions", status_code=status.HTTP_201_CREATED)
async def create_religion(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("religion") or payload.get("religion_name") or payload.get("name") or "New Religion"
    item = Religion(religion_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.religion_id, "name": item.religion_name}

@router.post("/update-religions/{id}")
@router.put("/update-religions/{id}")
@router.put("/religions/{id}")
async def update_religion(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Religion).where(Religion.religion_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Religion not found")
    name = payload.get("religion") or payload.get("religion_name") or payload.get("name")
    if name:
        item.religion_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/religions/{id}")
async def delete_religion(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Religion).where(Religion.religion_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Religion not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


# --- 2.17 Requirements (m_requirements) ---
@router.get("/getrequirements")
@router.get("/requirements")
async def get_requirements(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Requirement).where(Requirement.deleted_at.is_(None)).order_by(Requirement.requirement_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.requirement_id,
        "requirement_id": r.requirement_id,
        "name": r.requirement,
        "requirement": r.requirement,
        "code": f"REQ-{r.requirement_id}",
        "description": r.requirement,
        "status": "Active"
    } for r in items]

@router.post("/saverequirements", status_code=status.HTTP_201_CREATED)
@router.post("/requirements", status_code=status.HTTP_201_CREATED)
async def create_requirement(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("requirement") or payload.get("name") or "New Requirement"
    item = Requirement(requirement=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.requirement_id, "name": item.requirement}

@router.post("/updaterequirements/{id}")
@router.put("/updaterequirements/{id}")
@router.put("/requirements/{id}")
async def update_requirement(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Requirement).where(Requirement.requirement_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Requirement not found")
    name = payload.get("requirement") or payload.get("name")
    if name:
        item.requirement = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/requirements/{id}")
async def delete_requirement(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Requirement).where(Requirement.requirement_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Requirement not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.18 Requirement Statuses (m_requirement_statuses) ---
@router.get("/getrequirementstatuses")
@router.get("/requirement-statuses")
async def get_requirement_statuses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(RequirementStatus).where(RequirementStatus.deleted_at.is_(None)).order_by(RequirementStatus.requirement_status_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.requirement_status_id,
        "requirement_status_id": r.requirement_status_id,
        "name": r.requirement_status,
        "requirement_status": r.requirement_status,
        "code": f"RS-{r.requirement_status_id}",
        "description": r.requirement_status,
        "status": "Active"
    } for r in items]

@router.post("/saverequirementstatuses", status_code=status.HTTP_201_CREATED)
@router.post("/requirement-statuses", status_code=status.HTTP_201_CREATED)
async def create_requirement_status(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("requirement_status") or payload.get("name") or "New Status"
    item = RequirementStatus(requirement_status=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.requirement_status_id, "name": item.requirement_status}

@router.post("/updaterequirementstatuses/{id}")
@router.put("/updaterequirementstatuses/{id}")
@router.put("/requirement-statuses/{id}")
async def update_requirement_status(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(RequirementStatus).where(RequirementStatus.requirement_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Requirement status not found")
    name = payload.get("requirement_status") or payload.get("name")
    if name:
        item.requirement_status = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/requirementstatuses/{id}")
@router.delete("/requirement-statuses/{id}")
async def delete_requirement_status(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(RequirementStatus).where(RequirementStatus.requirement_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Requirement status not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.19 Resident Statuses (m_resident_statuses) ---
@router.get("/getresidentstatuses")
@router.get("/resident-statuses")
async def get_resident_statuses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ResidentStatus).where(ResidentStatus.deleted_at.is_(None)).order_by(ResidentStatus.resident_status_id.asc()))
    items = res.scalars().all()
    return [{
        "id": r.resident_status_id,
        "resident_status_id": r.resident_status_id,
        "name": r.status_name,
        "resident_status": r.status_name,
        "code": f"RES-{r.resident_status_id}",
        "description": r.status_name,
        "status": "Active"
    } for r in items]

@router.post("/saveresidentstatuses", status_code=status.HTTP_201_CREATED)
@router.post("/resident-statuses", status_code=status.HTTP_201_CREATED)
async def create_resident_status(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("resident_status") or payload.get("status_name") or payload.get("name") or "New Resident Status"
    item = ResidentStatus(status_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.resident_status_id, "name": item.status_name}

@router.post("/updateresidentstatuses/{id}")
@router.put("/updateresidentstatuses/{id}")
@router.put("/resident-statuses/{id}")
async def update_resident_status(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ResidentStatus).where(ResidentStatus.resident_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Resident status not found")
    name = payload.get("resident_status") or payload.get("status_name") or payload.get("name")
    if name:
        item.status_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/residentstatuses/{id}")
@router.delete("/resident-statuses/{id}")
async def delete_resident_status(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ResidentStatus).where(ResidentStatus.resident_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Resident status not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.20 Care Services (m_services) ---
@router.get("/getservices")
@router.get("/services")
async def get_services(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Service).where(Service.deleted_at.is_(None)).order_by(Service.service_id.asc()))
    items = res.scalars().all()
    return [{
        "id": s.service_id,
        "service_id": s.service_id,
        "name": s.service_name,
        "service": s.service_name,
        "code": f"SRV-{s.service_id}",
        "description": s.service_name,
        "status": "Active"
    } for s in items]

@router.post("/saveservice", status_code=status.HTTP_201_CREATED)
@router.post("/services", status_code=status.HTTP_201_CREATED)
async def create_service(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("service") or payload.get("service_name") or payload.get("name") or "New Service"
    item = Service(service_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.service_id, "name": item.service_name}

@router.post("/updateservice/{id}")
@router.put("/updateservice/{id}")
@router.put("/services/{id}")
async def update_service(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Service).where(Service.service_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    name = payload.get("service") or payload.get("service_name") or payload.get("name")
    if name:
        item.service_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/service/{id}")
@router.delete("/services/{id}")
async def delete_service(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(Service).where(Service.service_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.21 Service Statuses (m_service_statuses) ---
@router.get("/getservicestatuses")
@router.get("/service-statuses")
async def get_service_statuses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ServiceStatus).where(ServiceStatus.deleted_at.is_(None)).order_by(ServiceStatus.service_status_id.asc()))
    items = res.scalars().all()
    return [{
        "id": s.service_status_id,
        "service_status_id": s.service_status_id,
        "name": s.status_name,
        "service_status": s.status_name,
        "code": f"SS-{s.service_status_id}",
        "description": s.status_name,
        "status": "Active"
    } for s in items]

@router.post("/saveservicestatuses", status_code=status.HTTP_201_CREATED)
@router.post("/service-statuses", status_code=status.HTTP_201_CREATED)
async def create_service_status(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("service_status") or payload.get("status_name") or payload.get("name") or "New Status"
    item = ServiceStatus(status_name=name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.service_status_id, "name": item.status_name}

@router.post("/updateservicestatuses/{id}")
@router.put("/updateservicestatuses/{id}")
@router.put("/service-statuses/{id}")
async def update_service_status(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ServiceStatus).where(ServiceStatus.service_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service status not found")
    name = payload.get("service_status") or payload.get("status_name") or payload.get("name")
    if name:
        item.status_name = name
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/servicestatuses/{id}")
@router.delete("/service-statuses/{id}")
async def delete_service_status(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(ServiceStatus).where(ServiceStatus.service_status_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service status not found")
    item.deleted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


# --- 2.22 Training Courses (m_training_courses) ---
@router.get("/trainings")
@router.get("/training-courses")
async def get_trainings(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrainingCourse).order_by(TrainingCourse.training_course_id.asc()))
    items = res.scalars().all()
    return [{
        "id": t.training_course_id,
        "training_course_id": t.training_course_id,
        "name": t.name,
        "code": f"TRN-{t.training_course_id}",
        "description": t.description or (f"{t.duration_hours or ''} hrs - {t.validity_months or ''} months validity" if t.duration_hours else ""),
        "duration_hours": t.duration_hours or "",
        "validity_months": t.validity_months or 12,
        "status": "Active"
    } for t in items]

@router.post("/trainings", status_code=status.HTTP_201_CREATED)
@router.post("/training-courses", status_code=status.HTTP_201_CREATED)
async def create_training(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    name = payload.get("name") or "New Course"
    desc = payload.get("description") or ""
    dur = str(payload.get("duration_hours") or "4")
    val = int(payload.get("validity_months") or 12)
    item = TrainingCourse(name=name, description=desc, duration_hours=dur, validity_months=val)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item, "id": item.training_course_id, "name": item.name}

@router.put("/trainings/{id}")
@router.post("/trainings/{id}")
@router.put("/training-courses/{id}")
async def update_training(id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(TrainingCourse).where(TrainingCourse.training_course_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Training course not found")
    if "name" in payload:
        item.name = payload["name"]
    if "description" in payload:
        item.description = payload["description"]
    if "duration_hours" in payload:
        item.duration_hours = str(payload["duration_hours"])
    if "validity_months" in payload:
        item.validity_months = int(payload["validity_months"])
    await db.commit()
    await db.refresh(item)
    return {"success": True, "data": item}

@router.delete("/trainings/{id}")
@router.delete("/training-courses/{id}")
async def delete_training(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    res = await db.execute(select(TrainingCourse).where(TrainingCourse.training_course_id == id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Training course not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}
