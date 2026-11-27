"""Record workflows used by service-user and carer management.

Covers documents, clinical notes, conditions, home care, training assignments,
requirement checklists, visit rotas, and anonymised care-plan generation.
"""
import base64
import os
import re
from datetime import date as date_type, datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_current_staff_user
from app.services.audit import actor_name, log_audit_event
from app.services.audit_subject import subject_for_filename, subject_for_id
from app.db.session import get_db
from app.models.master_data import (
    CareType,
    ConditionCategory,
    MedicalCondition,
    MNotes,
    PatientCareType,
    PatientCondition,
    RequirementUserStatus,
    TrainingCourse,
    UploadedFile,
)
from app.models.service_user import ServiceUser
from app.models.user import User

router = APIRouter()

STORAGE_ROOTS = [
    Path(os.getcwd()) / "storage" / "app",
    Path(os.getcwd()) / "storage" / "app" / "documents",
    Path(os.getcwd()) / "storage" / "care_notes",
]
PRIMARY_STORAGE = STORAGE_ROOTS[0]

SU_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt", ".html"}
CARER_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt"}
SU_MAX_BYTES = 20_000_000
CARER_MAX_BYTES = 5_000_000


def _ensure_storage() -> None:
    PRIMARY_STORAGE.mkdir(parents=True, exist_ok=True)


def _basename(filename: str) -> str:
    name = os.path.basename(filename or "")
    if not name or name != filename or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return name


def _file_number(filename: str) -> str:
    parts = filename.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return parts[0]


def _decode_base64(payload: str) -> bytes:
    raw = payload.split(",", 1)[1] if "," in payload else payload
    try:
        return base64.b64decode(raw, validate=False)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to decode file data")


def _locate(filename: str) -> Optional[Path]:
    name = _basename(filename)
    for root in STORAGE_ROOTS:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


async def _store_bytes(filename: str, content: bytes, allowed: set, max_bytes: int, required_prefix: str) -> str:
    name = _basename(filename)
    if not name.lower().startswith(required_prefix):
        raise HTTPException(status_code=400, detail=f"File name must start with {required_prefix}")
    extension = Path(name).suffix.lower()
    if extension not in allowed:
        raise HTTPException(status_code=400, detail="File extension not allowed")
    if len(content) == 0 or len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="Invalid file size")
    _ensure_storage()
    target = PRIMARY_STORAGE / name
    target.write_bytes(content)
    return name


async def _upsert_uploaded(db: AsyncSession, filename: str) -> None:
    existing = await db.execute(select(UploadedFile).where(UploadedFile.filename == filename))
    row = existing.scalar_one_or_none()
    if row:
        row.file_number = _file_number(filename)
    else:
        db.add(UploadedFile(filename=filename, file_number=_file_number(filename)))
    await db.commit()


async def _list_files(db: AsyncSession, file_number: str):
    result = await db.execute(
        select(UploadedFile.filename).where(UploadedFile.file_number == file_number).order_by(UploadedFile.filename.asc())
    )
    return [row[0] for row in result.all()]


@router.get("/files/{file_number}")
async def list_service_user_files(file_number: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _list_files(db, file_number)


@router.get("/carerfiles/{file_number}")
async def list_carer_files(file_number: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _list_files(db, file_number)


async def _upload_payload(body: dict, allowed: set, max_bytes: int, prefix: str, db: AsyncSession):
    encoded = body.get("base64data")
    filename = body.get("filename")
    if not encoded or not filename:
        raise HTTPException(status_code=400, detail="File data and file name are required")
    content = _decode_base64(encoded)
    stored = await _store_bytes(filename, content, allowed, max_bytes, prefix)
    await _upsert_uploaded(db, stored)
    return {"success": True, "msg": stored, "path": stored}


@router.post("/upload")
async def upload_service_user_file(body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _upload_payload(body, SU_EXTENSIONS, SU_MAX_BYTES, "su_", db)


@router.post("/carerupload")
async def upload_carer_file(body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _upload_payload(body, CARER_EXTENSIONS, CARER_MAX_BYTES, "id_", db)


def _download_response(filename: str) -> Response:
    path = _locate(filename)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    content = path.read_bytes()
    media = "application/octet-stream"
    ext = path.suffix.lower()
    media_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".html": "text/html",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media = media_map.get(ext, media)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@router.get("/download/{filename}")
@router.post("/download/{filename}")
@router.get("/carerdownload/{filename}")
@router.post("/carerdownload/{filename}")
async def download_file(
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    safe_name = _basename(filename)
    response = _download_response(safe_name)
    su_id, patient_name = await subject_for_filename(db, safe_name)
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="documents",
        action="VIEW",
        details=f"Downloaded file {safe_name}",
        request=request,
    )
    return response


async def _delete_file(filename: str, db: AsyncSession):
    name = _basename(filename)
    result = await db.execute(select(UploadedFile).where(UploadedFile.filename == name))
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    path = _locate(name)
    if path:
        path.unlink(missing_ok=True)
    if not row and not path:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True, "message": "File deleted successfully"}


@router.delete("/deleteFile/{filename}")
@router.delete("/carerDeleteFile/{filename}")
async def delete_managed_file(filename: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _delete_file(filename, db)


def _note_stamp(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None).isoformat(timespec="seconds")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text_value = str(value).strip()
    if not text_value or text_value.startswith("0000-00-00"):
        return None
    return text_value.replace(" ", "T", 1)

@router.get("/get-notes")
async def list_notes(su_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(text("""
        SELECT n.id, n.user_id, n.su_id, n.notes, n.created_at, n.updated_at,
               u.first_name, u.surname,
               su.su_first_name, su.su_last_name
        FROM m_notes n
        LEFT JOIN users u ON u.id = n.user_id
        LEFT JOIN m_service_users su ON su.su_id = n.su_id
        WHERE n.su_id = :su_id
        ORDER BY COALESCE(n.created_at, n.updated_at) DESC, n.id DESC
    """), {"su_id": su_id})
    rows = []
    for row in result.mappings():
        created_at = _note_stamp(row["created_at"]) or _note_stamp(row["updated_at"])
        service_name = f"{row['su_first_name'] or ''} {row['su_last_name'] or ''}".strip()
        rows.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "su_id": row["su_id"],
            "notes": row["notes"],
            "created_at": created_at,
            "updated_at": _note_stamp(row["updated_at"]),
            "user": {
                "id": row["user_id"],
                "first_name": row["first_name"] or "",
                "surname": row["surname"] or "",
            },
            "service_user": {
                "su_id": row["su_id"],
                "full_name": service_name,
            },
        })
    return rows


@router.post("/notes")
async def create_note(body: dict, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    notes = (body.get("notes") or "").strip()
    su_id = body.get("su_id")
    if not notes or not su_id:
        raise HTTPException(status_code=422, detail="A note and service user are required")
    linked_id, patient_name = await subject_for_id(db, int(su_id))
    item = MNotes(user_id=current_user.id, su_id=linked_id or int(su_id), notes=notes)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=linked_id or int(su_id),
        patient_name=patient_name,
        record_type="care_notes",
        action="UPDATE",
        details=f"Added care note {item.id}",
        request=request,
    )
    return {"success": True, "id": item.id}


@router.post("/update-notes/{note_id}")
async def update_note(note_id: int, body: dict, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(MNotes).where(MNotes.id == note_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Note not found")
    notes = (body.get("notes") or "").strip()
    if not notes:
        raise HTTPException(status_code=422, detail="Note cannot be empty")
    item.notes = notes
    su_id, patient_name = await subject_for_id(db, item.su_id)
    await db.commit()
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="care_notes",
        action="UPDATE",
        details=f"Updated care note {note_id}",
        request=request,
    )
    return {"success": True, "message": "Note updated successfully"}


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(MNotes).where(MNotes.id == note_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Note not found")
    su_id, patient_name = await subject_for_id(db, item.su_id)
    await db.delete(item)
    await db.commit()
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="care_notes",
        action="DELETE",
        details=f"Deleted care note {note_id}",
        request=request,
    )
    return {"success": True}


def _condition_payload(row, condition, category) -> dict:
    return {
        "patient_condition_id": row.patient_condition_id,
        "su_id": row.su_id,
        "condition_id": row.condition_id,
        "category_id": row.category_id,
        "diagnosis_date": row.diagnosis_date.isoformat() if row.diagnosis_date else None,
        "is_primary": int(row.is_primary or 0),
        "condition": {
            "name": condition.name if condition else None,
            "description": condition.description if condition else None,
        },
        "category": {"name": category.name if category else None},
    }


@router.get("/patient-conditions/by-user/{su_id}")
async def conditions_for_user(su_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(PatientCondition).where(PatientCondition.su_id == su_id).order_by(PatientCondition.patient_condition_id.asc()))
    items = result.scalars().all()
    payload = []
    for row in items:
        condition = None
        category = None
        if row.condition_id:
            condition = (await db.execute(select(MedicalCondition).where(MedicalCondition.condition_id == row.condition_id))).scalar_one_or_none()
        if row.category_id:
            category = (await db.execute(select(ConditionCategory).where(ConditionCategory.category_id == row.category_id))).scalar_one_or_none()
        payload.append(_condition_payload(row, condition, category))
    return {"success": True, "data": payload}


@router.post("/patient-conditions")
async def create_condition(body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    if not body.get("su_id") or not body.get("condition_id") or not body.get("category_id"):
        raise HTTPException(status_code=422, detail="Service user, condition, and category are required")
    item = PatientCondition(
        su_id=int(body["su_id"]),
        condition_id=int(body["condition_id"]),
        category_id=int(body["category_id"]),
        diagnosis_date=_as_date(body.get("diagnosis_date")),
        is_primary=1 if body.get("is_primary") in (1, True, "1") else 0,
    )
    db.add(item)
    await db.commit()
    return {"success": True, "id": item.patient_condition_id}


@router.put("/patient-conditions/{patient_condition_id}")
@router.post("/patient-conditions/{patient_condition_id}")
async def update_condition(patient_condition_id: int, body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(PatientCondition).where(PatientCondition.patient_condition_id == patient_condition_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    if not body.get("condition_id") or not body.get("category_id"):
        raise HTTPException(status_code=422, detail="Condition and category are required")
    item.condition_id = int(body["condition_id"])
    item.category_id = int(body["category_id"])
    item.diagnosis_date = _as_date(body.get("diagnosis_date"))
    item.is_primary = 1 if body.get("is_primary") in (1, True, "1") else 0
    await db.commit()
    return {"success": True}


@router.delete("/patient-conditions/{patient_condition_id}")
async def delete_condition(patient_condition_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(PatientCondition).where(PatientCondition.patient_condition_id == patient_condition_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Medical condition not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


async def _care_rows(db: AsyncSession, su_id: int):
    result = await db.execute(select(PatientCareType).where(PatientCareType.su_id == su_id).order_by(PatientCareType.patient_care_type_id.asc()))
    rows = []
    for item in result.scalars().all():
        care = None
        if item.care_type_id:
            care = (await db.execute(select(CareType).where(CareType.care_type_id == item.care_type_id))).scalar_one_or_none()
        rows.append({
            "patient_care_type_id": item.patient_care_type_id,
            "su_id": item.su_id,
            "care_type_id": item.care_type_id,
            "care_type": {
                "name": care.name if care else None,
                "description": care.description if care else None,
            },
        })
    return rows


async def _daily_cares(db: AsyncSession, su_id: int):
    try:
        result = await db.execute(text("""
            SELECT DATE(s.created_at) AS created_date, ct.name AS care_name
            FROM m_patient_care_type_selections s
            JOIN m_care_types ct ON ct.care_type_id = s.care_type_id
            WHERE s.su_id = :su_id
            ORDER BY created_date DESC, ct.name ASC
        """), {"su_id": su_id})
    except Exception:
        return []
    grouped = {}
    for row in result.mappings():
        day = str(row["created_date"])
        grouped.setdefault(day, [])
        if row["care_name"] and row["care_name"] not in grouped[day]:
            grouped[day].append(row["care_name"])
    return [{"created_date": day, "care_types": ", ".join(names)} for day, names in grouped.items()]


@router.get("/patient-care-types/by-user/{su_id}")
async def care_types_for_user(su_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return {
        "success": True,
        "data": {
            "patientCareTypes": await _care_rows(db, su_id),
            "patientdailyhomecares": await _daily_cares(db, su_id),
        },
    }


async def _care_type_already_assigned(db: AsyncSession, su_id: int, care_type_id: int, exclude_id: int | None = None) -> bool:
    statement = select(PatientCareType).where(
        PatientCareType.su_id == su_id,
        PatientCareType.care_type_id == care_type_id,
    )
    if exclude_id is not None:
        statement = statement.where(PatientCareType.patient_care_type_id != exclude_id)
    existing = (await db.execute(statement)).scalars().first()
    return existing is not None


@router.post("/patient-care-types")
async def create_care_type_link(body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    if not body.get("su_id") or not body.get("care_type_id"):
        raise HTTPException(status_code=422, detail="Service user and care type are required")
    su_id = int(body["su_id"])
    care_type_id = int(body["care_type_id"])
    if await _care_type_already_assigned(db, su_id, care_type_id):
        raise HTTPException(status_code=409, detail="This home care type is already assigned")
    item = PatientCareType(su_id=su_id, care_type_id=care_type_id)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This home care type is already assigned") from None
    return {"success": True, "id": item.patient_care_type_id}


@router.put("/patient-care-types/{patient_care_type_id}")
@router.post("/patient-care-types/{patient_care_type_id}")
async def update_care_type_link(patient_care_type_id: int, body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(PatientCareType).where(PatientCareType.patient_care_type_id == patient_care_type_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Home care record not found")
    if not body.get("care_type_id"):
        raise HTTPException(status_code=422, detail="Care type is required")
    care_type_id = int(body["care_type_id"])
    if await _care_type_already_assigned(db, item.su_id, care_type_id, exclude_id=item.patient_care_type_id):
        raise HTTPException(status_code=409, detail="This home care type is already assigned")
    item.care_type_id = care_type_id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This home care type is already assigned") from None
    return {"success": True}


@router.delete("/patient-care-types/{patient_care_type_id}")
async def delete_care_type_link(patient_care_type_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(select(PatientCareType).where(PatientCareType.patient_care_type_id == patient_care_type_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Home care record not found")
    await db.delete(item)
    await db.commit()
    return {"success": True}


@router.get("/users/{user_id}/training-courses")
async def list_user_training(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(text("""
        SELECT tc.training_course_id, tc.name, tc.description, tc.duration_hours, tc.validity_months,
               p.completion_date, p.status
        FROM training_course_user p
        JOIN m_training_courses tc ON tc.training_course_id = p.training_course_id
        WHERE p.user_id = :user_id
        ORDER BY tc.name ASC
    """), {"user_id": user_id})
    data = []
    for row in result.mappings():
        completed = row["completion_date"]
        data.append({
            "training_course_id": row["training_course_id"],
            "name": row["name"],
            "description": row["description"],
            "duration_hours": row["duration_hours"],
            "validity_months": row["validity_months"],
            "pivot": {
                "completion_date": completed.isoformat() if hasattr(completed, "isoformat") else completed,
                "status": row["status"],
            },
        })
    return {"success": True, "data": data}


@router.post("/users/{user_id}/training-courses")
async def assign_training(user_id: int, body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    course_id = body.get("training_course_id")
    status_value = body.get("status")
    completed = body.get("completion_date")
    if not course_id or not completed or not status_value:
        raise HTTPException(status_code=422, detail="Training course, completion date, and status are required")
    course = (await db.execute(select(TrainingCourse).where(TrainingCourse.training_course_id == int(course_id)))).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Training course not found")
    existing = await db.execute(text("""
        SELECT training_course_id FROM training_course_user
        WHERE user_id = :user_id AND training_course_id = :course_id
    """), {"user_id": user_id, "course_id": int(course_id)})
    params = {"user_id": user_id, "course_id": int(course_id), "completed": completed, "status": status_value}
    if existing.first():
        await db.execute(text("""
            UPDATE training_course_user
            SET completion_date = :completed, status = :status, updated_at = NOW()
            WHERE user_id = :user_id AND training_course_id = :course_id
        """), params)
    else:
        await db.execute(text("""
            INSERT INTO training_course_user
                (user_id, training_course_id, completion_date, status, created_at, updated_at)
            VALUES (:user_id, :course_id, :completed, :status, NOW(), NOW())
        """), params)
    await db.commit()
    return await list_user_training(user_id, db, current_user)


@router.put("/users/{user_id}/training-courses/{course_id}")
async def update_training_assignment(user_id: int, course_id: int, body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    body = {**body, "training_course_id": course_id}
    return await assign_training(user_id, body, db, current_user)


@router.delete("/users/{user_id}/training-courses/{course_id}")
async def delete_training_assignment(user_id: int, course_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    await db.execute(text("""
        DELETE FROM training_course_user
        WHERE user_id = :user_id AND training_course_id = :course_id
    """), {"user_id": user_id, "course_id": course_id})
    await db.commit()
    return {"success": True}


@router.get("/getuserrequirements/{user_id}")
async def user_requirements(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(text("""
        SELECT r.requirement_id, r.requirement, s.id, s.user_id,
               COALESCE(s.status, 0) AS status
        FROM m_requirements r
        LEFT JOIN m_requirements_status s
          ON s.requirement_id = r.requirement_id
         AND s.user_id = :user_id
         AND s.deleted_at IS NULL
        WHERE r.deleted_at IS NULL
        ORDER BY r.requirement ASC
    """), {"user_id": user_id})
    return [dict(row) for row in result.mappings()]


async def _save_requirement_status(body: dict, db: AsyncSession, status_id: Optional[int] = None):
    user_id = body.get("user_id")
    requirement_id = body.get("requirement_id")
    if not user_id or not requirement_id:
        raise HTTPException(status_code=422, detail="User and requirement are required")
    status_value = 1 if body.get("status") in (1, True, "1", "true") else 0
    if status_id:
        result = await db.execute(select(RequirementUserStatus).where(RequirementUserStatus.id == status_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Requirement status not found")
        item.status = status_value
    else:
        item = RequirementUserStatus(user_id=int(user_id), requirement_id=int(requirement_id), status=status_value)
        db.add(item)
    await db.commit()
    return {"success": True}


@router.post("/saverequirementsstatus")
async def create_requirement_status(body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _save_requirement_status(body, db)


@router.post("/updaterequirementsstatus/{status_id}")
async def update_requirement_status(status_id: int, body: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    return await _save_requirement_status(body, db, status_id)


def _as_date(value):
    if not value:
        return None
    if isinstance(value, date_type):
        return value
    return date_type.fromisoformat(str(value)[:10])


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@router.get("/getdtr")
async def carer_rota(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(text("""
        SELECT t.tx_id, t.start, t.rate, t.payroll,
               u.first_name, u.surname,
               CONCAT(su.su_first_name, ' ', su.su_last_name) AS su_full_name,
               sh.shift AS shift_name,
               a.time_in, a.time_out
        FROM m_transactions t
        JOIN users u ON u.id = t.id
        JOIN m_service_users su ON su.su_id = t.su_id
        LEFT JOIN m_shifts sh ON sh.shift_id = t.shift_id
        JOIN m_attendances a ON a.tx_id = t.tx_id AND a.deleted_at IS NULL
        WHERE t.id = :user_id AND t.deleted_at IS NULL
        ORDER BY t.start ASC
        LIMIT 90
    """), {"user_id": user_id})
    rows = []
    for row in result.mappings():
        rows.append({
            "tx_id": row["tx_id"],
            "first_name": row["first_name"],
            "surname": row["surname"],
            "rate": row["rate"],
            "start": _iso(row["start"]),
            "service_user": {"su_full_name": row["su_full_name"]},
            "shift": {"shift": row["shift_name"]},
            "attendance": {
                "time_in": _iso(row["time_in"]),
                "time_out": _iso(row["time_out"]),
                "paid": row["payroll"],
            },
        })
    return rows


@router.get("/getserviceuserdtrs")
async def service_user_rota(suId: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_staff_user)):
    result = await db.execute(text("""
        SELECT t.tx_id, t.start, t.end,
               COALESCE(t.rate, r.rate) AS rate,
               sh.shift AS shift_name,
               CONCAT(u.first_name, ' ', u.surname) AS carer_full_name,
               a.time_in, a.time_out
        FROM m_transactions t
        JOIN users u ON u.id = t.id
        JOIN m_service_users su ON su.su_id = t.su_id
        JOIN m_shifts sh ON sh.shift_id = t.shift_id AND sh.deleted_at IS NULL
        LEFT JOIN m_service_user_rates r
          ON r.su_id = su.su_id AND r.shift_id = sh.shift_id AND r.deleted_at IS NULL
        LEFT JOIN m_attendances a ON a.tx_id = t.tx_id
        WHERE su.deleted_at IS NULL
          AND su.service_status_id = 1
          AND su.su_id = :su_id
          AND t.deleted_at IS NULL
          AND (t.payroll IS NULL OR t.invoice IS NULL)
        ORDER BY t.start ASC
    """), {"su_id": suId})
    return [{
        "tx_id": row["tx_id"],
        "start": _iso(row["start"]),
        "end": _iso(row["end"]),
        "rate": row["rate"],
        "shift": row["shift_name"],
        "carer_full_name": row["carer_full_name"],
        "time_in": _iso(row["time_in"]),
        "time_out": _iso(row["time_out"]),
    } for row in result.mappings()]


def _scrub(value: Optional[str]) -> str:
    if not value:
        return ""
    text_value = re.sub(r"<[^>]+>", " ", value)
    text_value = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[REDACTED EMAIL]", text_value, flags=re.I)
    text_value = re.sub(r"(?:\+?\d[\d\s().-]{7,}\d)", "[REDACTED PHONE]", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _mock_care_plan(age: Any, gender: str, summary: str) -> str:
    return f"""
<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #111;">
  <h2 style="color: #0b4b88;">Person-centred care plan</h2>
  <p>This plan was prepared from anonymised clinical information. A care coordinator must review it before it is used.</p>
  <h3 style="color: #0b4b88;">1. Profile and communication</h3>
  <p>Age {age}. Gender: {gender}. Refer to the person as the service user. Record communication needs before the first visit.</p>
  <h3 style="color: #0b4b88;">2. Health status</h3>
  <p>{summary or "No additional clinical summary was supplied."}</p>
  <h3 style="color: #0b4b88;">3. Medication</h3>
  <p>Follow the current MAR chart. Do not add medicines that are not already prescribed. Report refusals and side effects.</p>
  <h3 style="color: #0b4b88;">4. Daily care</h3>
  <p>Support washing, dressing, nutrition, hydration, and mobility in the way the service user prefers. Keep the routine consistent.</p>
  <h3 style="color: #0b4b88;">5. Risks</h3>
  <p>Review falls, skin integrity, moving and handling, and the home environment at each visit. Escalate changes the same day.</p>
  <h3 style="color: #0b4b88;">6. Consent and emergencies</h3>
  <p>Confirm consent. If capacity is in doubt, follow the recorded best-interest decision. Contact the GP, NHS 111, or 999 when the situation requires it.</p>
</div>
""".strip()


@router.post("/service-users/generate-ai-care-plan")
async def generate_ai_care_plan(body: dict, current_user: User = Depends(get_current_staff_user)):
    age = body.get("age")
    if age is None or age == "":
        raise HTTPException(status_code=422, detail="Age is required")
    gender = body.get("gender") or "Not specified"
    conditions = body.get("medical_conditions") or []
    summary_parts = [
        _scrub(body.get("medical_history")),
        _scrub(body.get("current_medications")),
        _scrub(body.get("su_notes")),
        _scrub(body.get("services_provided")),
    ]
    if conditions:
        summary_parts.insert(0, "Conditions: " + _scrub(str(conditions)))
    summary = " ".join(part for part in summary_parts if part)
    prompt = (
        "Write a UK domiciliary care plan as HTML. Do not include names, addresses, or telephone numbers. "
        f"Age {age}. Gender {gender}. Clinical summary: {summary}"
    )
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY1")
    if api_key:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )
            response.raise_for_status()
            text_out = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "care_plan": text_out, "is_mock": False}
        except Exception:
            pass
    return {"success": True, "care_plan": _mock_care_plan(age, gender, summary), "is_mock": True}


@router.post("/updatesu-medications/{su_id}")
async def update_medications(
    su_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(ServiceUser).where(ServiceUser.su_id == su_id, ServiceUser.deleted_at.is_(None)))
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(status_code=404, detail="Service user not found")
    medications = body.get("medications") or ""
    su.medications_json = medications
    patient_name = f"{su.first_name or ''} {su.surname or ''}".strip()
    db.add(MNotes(
        user_id=current_user.id,
        su_id=su_id,
        notes="Medications and care services field updated from the care plan review.",
    ))
    await db.commit()
    await log_audit_event(
        db=db,
        user_id=current_user.id,
        username=actor_name(current_user),
        su_id=su_id,
        patient_name=patient_name,
        record_type="mar_chart",
        action="UPDATE",
        details=f"Updated medication record for service user {su_id}",
        request=request,
    )
    return {"success": True, "message": "Medications field updated"}


@router.post("/service-users/upload-care-plan-document")
async def upload_care_plan_document(
    su_id: int = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    result = await db.execute(select(ServiceUser).where(ServiceUser.su_id == su_id, ServiceUser.deleted_at.is_(None)))
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(status_code=404, detail="Service user not found")
    content = await file.read()
    stored = await _store_bytes(filename, content, SU_EXTENSIONS, SU_MAX_BYTES, "su_")
    await _upsert_uploaded(db, stored)
    return {"success": True, "filename": stored}
