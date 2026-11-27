from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.service_user import ServiceUser
from app.schemas.service_user import ServiceUserCreate, ServiceUserUpdate, ServiceUserOut
from app.core.security import get_current_active_user, get_current_staff_user, get_current_admin_user
from app.services.audit import actor_name, log_audit_event
from app.services.sar_controls import prepare_sar_disclosure, validate_sar_request
from app.services.sar_export import fetch_sar_dataset, generate_sar_pdf, generate_sar_excel

router = APIRouter()


class SarExportRequest(BaseModel):
    format: str = "pdf"
    reason: str
    request_date: datetime.date
    include_third_parties: bool = False


def _actor_name(user: User) -> str:
    name = f"{user.first_name or ''} {user.surname or ''}".strip()
    return name or user.username or f"user {user.id}"

@router.get("/getsu", response_model=List[ServiceUserOut])
async def get_service_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ServiceUser)
        .where(ServiceUser.deleted_at.is_(None))
        .order_by(ServiceUser.first_name.asc())
    )
    return result.scalars().all()

@router.get("/getactivesu", response_model=List[ServiceUserOut])
async def get_active_service_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ServiceUser)
        .where(ServiceUser.deleted_at.is_(None))
        .order_by(ServiceUser.first_name.asc())
    )
    return result.scalars().all()

@router.get("/service_users/{su_id}/dossier")
@router.get("/getsu/{su_id}")
async def get_service_user_dossier(
    su_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Return one service-user dossier and record who opened it."""
    result = await db.execute(
        select(ServiceUser).where(ServiceUser.su_id == su_id, ServiceUser.deleted_at.is_(None))
    )
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(status_code=404, detail="Service user not found")

    patient_name = f"{su.first_name} {su.surname}".strip()

    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su.su_id,
        patient_name=patient_name,
        record_type="medical_dossier",
        action="READ",
        details=f"Opened medical dossier {su.su_id}",
        request=request
    )

    return {
        "success": True,
        "data": {
            "su_id": su.su_id,
            "su_number": su.su_number,
            "full_name": patient_name,
            "first_name": su.first_name,
            "surname": su.surname,
            "date_of_birth": su.date_of_birth.isoformat() if su.date_of_birth else None,
            "address": su.address,
            "phone": su.phone,
            "email": su.email,
            "medical_history": su.medical_history,
            "medications": su.medications_json,
            "care_plan_notes": su.care_plan_notes,
            "services_provided": su.services_provided,
            "next_of_kin": su.next_of_kin,
            "nok_contact_number": su.nok_contact_number
        }
    }

@router.get("/service_users/{su_id}/sar-data")
async def get_service_user_sar_data(
    su_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    sar_data = await fetch_sar_dataset(db, su_id)
    if not sar_data:
        raise HTTPException(status_code=404, detail="Service user not found")

    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=_actor_name(current_user),
        su_id=su_id,
        patient_name=sar_data["full_name"],
        record_type="sar_preview",
        action="VIEW",
        details="Opened the Article 15 count summary. No file was downloaded.",
        request=request
    )
    return {
        "success": True,
        "data": {
            "su_id": su_id,
            "patient_name": sar_data["full_name"],
            "su_number": sar_data["patient"].get("su_number"),
            "notes_count": len(sar_data["notes"]),
            "transactions_count": len(sar_data["transactions"]),
            "invoices_count": len(sar_data["invoices"]),
            "audit_logs_count": len(sar_data["audit_logs"]),
            "generated_at": sar_data["generated_at"]
        }
    }

@router.post("/service_users/{su_id}/sar-export")
async def export_service_user_sar(
    su_id: int,
    body: SarExportRequest,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Download an Article 15 copy. Administrators only. The reason stays on the audit row."""
    try:
        reason = validate_sar_request(body.reason, body.request_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    sar_data = await fetch_sar_dataset(db, su_id)
    if not sar_data:
        raise HTTPException(status_code=404, detail="Service user not found")

    fmt = body.format.lower().strip()
    if fmt not in {"pdf", "excel", "xlsx"}:
        raise HTTPException(status_code=422, detail="Choose a PDF dossier or a spreadsheet copy.")
    disclosure = prepare_sar_disclosure(sar_data, body.include_third_parties, body.request_date)
    patient_name = disclosure["full_name"]
    su_num = disclosure["patient"].get("su_number") or f"SU_{su_id:05d}"
    today_str = datetime.date.today().strftime("%Y%m%d")
    third_party_state = "included" if body.include_third_parties else "withheld"

    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=_actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="sar_export",
        action="EXPORT",
        details=(
            f"Article 15 copy ({fmt}). Request date {body.request_date.isoformat()}. "
            f"Third-party contacts {third_party_state}. Reason: {reason}"
        ),
        request=request
    )

    if fmt in {"excel", "xlsx"}:
        content = generate_sar_excel(disclosure)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"UK_GDPR_Art15_SAR_{su_num}_{today_str}.xlsx"
    else:
        content = generate_sar_pdf(disclosure)
        media_type = "application/pdf"
        filename = f"UK_GDPR_Art15_SAR_{su_num}_{today_str}.pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.post("/savesu", response_model=ServiceUserOut, status_code=status.HTTP_201_CREATED)
@router.post("/service-users", response_model=ServiceUserOut, status_code=status.HTTP_201_CREATED)
async def create_service_user(
    data: ServiceUserCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    payload = data.model_dump()
    if not payload.get("service_status_id"):
        payload["service_status_id"] = 1
    su = ServiceUser(**payload)
    db.add(su)
    await db.commit()
    await db.refresh(su)
    return su

@router.post("/updatesu/{su_id}", response_model=ServiceUserOut)
@router.put("/updatesu/{su_id}", response_model=ServiceUserOut)
@router.put("/service-users/{su_id}", response_model=ServiceUserOut)
async def update_service_user(
    su_id: int,
    data: ServiceUserUpdate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ServiceUser).where(ServiceUser.su_id == su_id, ServiceUser.deleted_at.is_(None))
    )
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(status_code=404, detail="Service user not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(su, key, val)

    await db.commit()
    await db.refresh(su)
    return su

@router.delete("/su/{su_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/service-users/{su_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_user(
    su_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ServiceUser).where(ServiceUser.su_id == su_id))
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(status_code=404, detail="Service user not found")

    await db.delete(su)
    await db.commit()
    return None
