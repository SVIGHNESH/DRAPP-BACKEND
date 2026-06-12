from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.address import Address
from app.models.user import User
from app.schemas.address import AddressCreate, AddressOut, AddressUpdate

router = APIRouter(prefix="/users/me/addresses", tags=["addresses"])


async def _get_own_address(address_id: int, user: User, db: AsyncSession) -> Address:
    result = await db.execute(
        select(Address).where(Address.address_id == address_id, Address.user_id == user.user_id)
    )
    addr = result.scalar_one_or_none()
    if not addr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return addr


@router.get("", response_model=list[AddressOut])
async def list_addresses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.user_id == current_user.user_id))
    return result.scalars().all()


@router.post("", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def add_address(
    body: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.is_default:
        await db.execute(
            update(Address).where(Address.user_id == current_user.user_id).values(is_default=False)
        )
    addr = Address(**body.model_dump(), user_id=current_user.user_id)
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.patch("/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: int,
    body: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await _get_own_address(address_id, current_user, db)
    updates = body.model_dump(exclude_none=True)
    if updates.get("is_default"):
        await db.execute(
            update(Address).where(Address.user_id == current_user.user_id).values(is_default=False)
        )
    for field, value in updates.items():
        setattr(addr, field, value)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.patch("/{address_id}/set-default", response_model=AddressOut)
async def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await _get_own_address(address_id, current_user, db)
    await db.execute(
        update(Address).where(Address.user_id == current_user.user_id).values(is_default=False)
    )
    addr.is_default = True
    await db.commit()
    await db.refresh(addr)
    return addr


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await _get_own_address(address_id, current_user, db)
    await db.delete(addr)
    await db.commit()
