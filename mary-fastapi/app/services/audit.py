from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models.audit import AuditLog

async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    su_id: Optional[int] = None,
    patient_name: Optional[str] = None,
    record_type: str = "medical_dossier",
    action: str = "READ",
    details: Optional[str] = None,
    request: Optional[Request] = None
):
    """Record who opened or changed a care record.

    The row stores the signed-in person, the service user when known, the record
    kind, and the action. It does not store clinical text.
    """
    ip_addr = None
    ua = None
    if request:
        # Nginx sets X-Real-IP from the connection it accepted. Do not trust a
        # client-supplied forwarded list when that header is present.
        real_ip = (request.headers.get("X-Real-IP") or "").split(",")[0].strip()
        if real_ip:
            ip_addr = real_ip[:100]
        elif request.client:
            ip_addr = request.client.host
        ua = request.headers.get("user-agent")

    audit_entry = AuditLog(
        user_id=user_id,
        username=username or "Authenticated User",
        su_id=su_id,
        patient_name=(patient_name or "").strip() or None,
        record_type=record_type,
        action=action,
        details=details,
        ip_address=ip_addr,
        user_agent=ua
    )
    db.add(audit_entry)
    await db.commit()
    return audit_entry


def actor_name(user) -> str:
    name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'surname', '') or ''}".strip()
    return name or getattr(user, "username", None) or f"user {getattr(user, 'id', '')}"


ALLOWED_AUDIT_ACTIONS = {"READ", "VIEW", "EXPORT", "UPDATE", "DELETE"}
ALLOWED_AUDIT_RECORD_TYPES = {
    "medical_dossier",
    "mar_chart",
    "care_notes",
    "documents",
    "sar_preview",
    "sar_export",
    "attendance_notes",
}


def page_window(page: int, page_size: int, total: int) -> tuple[int, int]:
    """Return the page number and row offset that stay inside the result set."""
    if total <= 0:
        return 1, 0
    last_page = (total + page_size - 1) // page_size
    current = min(max(page, 1), last_page)
    return current, (current - 1) * page_size


def client_audit_fields(action: str, record_type: str, details: Optional[str], patient_name: Optional[str]):
    """Accept only known actions. Ignore any identity the browser tried to send."""
    action_name = (action or "").strip().upper()
    if action_name not in ALLOWED_AUDIT_ACTIONS:
        raise ValueError("That action cannot be recorded.")
    record = (record_type or "").strip()
    if record not in ALLOWED_AUDIT_RECORD_TYPES:
        raise ValueError("That record type cannot be recorded.")
    text = (details or "").replace("\x00", "").strip()
    if len(text) > 500:
        text = text[:500]
    name = (patient_name or "").strip()
    if len(name) > 255:
        name = name[:255]
    return action_name, record, text or None, name or None
