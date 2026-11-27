from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit import (
    ALLOWED_AUDIT_RECORD_TYPES,
    actor_name,
    client_audit_fields,
    log_audit_event,
    page_window,
)
from app.core.security import get_current_active_user, get_current_admin_user

router = APIRouter()

class ClientAuditLogRequest(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    su_id: Optional[int] = None
    patient_name: Optional[str] = None
    record_type: str = "medical_dossier"  # medical_dossier, mar_chart, care_notes
    action: str = "READ"
    details: Optional[str] = None

def _audit_row(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "su_id": log.su_id,
        "patient_name": log.patient_name,
        "record_type": log.record_type,
        "action": log.action,
        "details": log.details,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _search_clause(term: str):
    cleaned = term.replace("\\", "").replace("%", "").replace("_", "")
    like = f"%{cleaned}%"
    return or_(
        AuditLog.patient_name.like(like),
        AuditLog.username.like(like),
        AuditLog.action.like(like),
        AuditLog.record_type.like(like),
    )


@router.get("/audit/logs")
async def get_audit_logs(
    su_id: Optional[int] = Query(None),
    record_type: Optional[str] = Query(None),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Return one page of access events, plus counts for the whole trail."""
    if record_type and record_type not in ALLOWED_AUDIT_RECORD_TYPES:
        raise HTTPException(status_code=422, detail="That record type cannot be filtered.")

    clauses = []
    if su_id:
        clauses.append(AuditLog.su_id == su_id)
    if record_type:
        clauses.append(AuditLog.record_type == record_type)
    term = (q or "").strip()
    if term:
        clauses.append(_search_clause(term))

    summary_row = (await db.execute(select(
        func.count(AuditLog.id).label("total"),
        func.count(AuditLog.user_id).label("identified"),
        func.coalesce(func.sum(case((AuditLog.record_type == "medical_dossier", 1), else_=0)), 0).label("dossier"),
    ).select_from(AuditLog))).one()
    summary_total = int(summary_row.total or 0)
    identified = int(summary_row.identified or 0)
    dossier = int(summary_row.dossier or 0)

    filtered = select(func.count()).select_from(AuditLog)
    for clause in clauses:
        filtered = filtered.where(clause)
    total = int((await db.execute(filtered)).scalar() or 0)
    page, offset = page_window(page, page_size, total)

    rows = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    for clause in clauses:
        rows = rows.where(clause)
    logs = (await db.execute(rows.offset(offset).limit(page_size))).scalars().all()
    return {
        "success": True,
        "count": len(logs),
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": {
            "total": summary_total,
            "identified": identified,
            "dossier": dossier,
            "other": summary_total - dossier,
        },
        "data": [_audit_row(log) for log in logs],
    }

@router.post("/audit/log")
async def record_client_audit_log(
    req: ClientAuditLogRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record an access event. The signed-in person is taken from the session."""
    try:
        action, record_type, details, patient_name = client_audit_fields(
            req.action, req.record_type, req.details, req.patient_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    entry = await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=req.su_id,
        patient_name=patient_name,
        record_type=record_type,
        action=action,
        details=details,
        request=request
    )
    return {
        "success": True,
        "message": "Audit event recorded successfully",
        "log_id": entry.id
    }
