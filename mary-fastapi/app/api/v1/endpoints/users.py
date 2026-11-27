from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List, Union, Optional

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserLightweight
from app.core.security import get_current_staff_user, get_current_admin_user
from app.api.v1.endpoints.auth import hash_password

router = APIRouter()

@router.get("/getcarers", response_model=List[Union[UserOut, UserLightweight]])
async def get_carers(
    lightweight: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.deleted_at.is_(None)).order_by(User.first_name.asc())
    result = await db.execute(query)
    carers = result.scalars().all()
    
    if lightweight:
        out = []
        for c in carers:
            d = UserLightweight.model_validate(c)
            d.carer_full_name = f"{c.first_name} {c.surname}".strip()
            out.append(d)
        return out

    return carers

@router.post("/savecarer", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@router.post("/carers", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_carer(
    data: UserCreate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    payload = data.model_dump(exclude={"password"})
    if not payload.get("carer_status_id"):
        payload["carer_status_id"] = 1
    user = User(**payload)
    if data.password:
        user.password = hash_password(data.password)
    db.add(user)
    try:
        await db.flush()
        if not user.user_id:
            user.user_id = f"{user.id:05d}"
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username or email is already in use.")
    await db.refresh(user)
    return user

@router.post("/updatecarer/{carer_id}", response_model=UserOut)
@router.put("/updatecarer/{carer_id}", response_model=UserOut)
@router.put("/carers/{carer_id}", response_model=UserOut)
async def update_carer(
    carer_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == carer_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Carer not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(user, key, val)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username or email is already in use.")
    await db.refresh(user)
    return user

@router.delete("/carer/{carer_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/carers/{carer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_carer(
    carer_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == carer_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Carer not found")

    await db.delete(user)
    await db.commit()
    return None
