"""Resolve the service user named by an id or by an su_ file name."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.service_user import ServiceUser
from app.services.care_note_access import service_user_file_token


def service_user_display_name(service_user) -> str | None:
    name = f"{getattr(service_user, 'first_name', '') or ''} {getattr(service_user, 'surname', '') or ''}".strip()
    return name or None


def _number_candidates(token: str) -> list[str]:
    candidates = [token]
    stripped = token.lstrip("0")
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    if token.isdigit():
        padded = str(int(token)).zfill(5)
        if padded not in candidates:
            candidates.append(padded)
    return candidates


async def _first_service_user(db: AsyncSession, statement):
    rows = (await db.execute(statement)).scalars().all()
    return rows[0] if rows else None


async def service_user_by_id(db: AsyncSession, su_id: int | None):
    if not su_id:
        return None
    return await _first_service_user(
        db,
        select(ServiceUser)
        .where(ServiceUser.su_id == int(su_id))
        .order_by(ServiceUser.deleted_at.is_(None).desc(), ServiceUser.su_id.asc()),
    )


async def service_user_by_file_token(db: AsyncSession, token: str | None):
    if not token:
        return None
    rows = (await db.execute(
        select(ServiceUser)
        .where(ServiceUser.su_number.in_(_number_candidates(token)))
        .order_by(ServiceUser.deleted_at.is_(None).desc(), ServiceUser.su_id.asc())
    )).scalars().all()
    exact = [row for row in rows if (row.su_number or "") == token]
    pool = exact or rows
    active = [row for row in pool if row.deleted_at is None]
    if active:
        return active[0]
    if pool:
        return pool[0]
    if token.isdigit():
        return await service_user_by_id(db, int(token))
    return None


async def subject_for_id(db: AsyncSession, su_id: int | None) -> tuple[int | None, str | None]:
    service_user = await service_user_by_id(db, su_id)
    if not service_user:
        return (int(su_id) if su_id else None), None
    return service_user.su_id, service_user_display_name(service_user)


async def subject_for_filename(db: AsyncSession, filename: str) -> tuple[int | None, str | None]:
    service_user = await service_user_by_file_token(db, service_user_file_token(filename))
    if not service_user:
        return None, None
    return service_user.su_id, service_user_display_name(service_user)
