from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db, require_admin
from app.models.address import Address
from app.models.booking import AssignedNurse, Booking, BookingNote
from app.models.service import Service
from app.models.user import FamilyMember, User
from app.schemas.booking import (
    AssignedNurseIn,
    BookingCreate,
    BookingNoteCreate,
    BookingOut,
    BookingStatusUpdate,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])

VALID_STATUSES = {"requested", "confirmed", "in_progress", "completed", "cancelled"}


def _booking_query():
    return select(Booking).options(
        selectinload(Booking.notes),
        selectinload(Booking.assigned_nurse),
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate service exists
    svc = await db.get(Service, body.service_id)
    if not svc or not svc.active:
        raise HTTPException(status_code=404, detail="Service not found")

    # Validate member belongs to user
    if body.member_id is not None:
        member = await db.get(FamilyMember, body.member_id)
        if not member or member.user_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="Family member not found")

    # Validate saved address belongs to user
    if body.address_id is not None:
        addr = await db.get(Address, body.address_id)
        if not addr or addr.user_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="Address not found")

    booking = Booking(
        user_id=current_user.user_id,
        member_id=body.member_id,
        service_id=body.service_id,
        address_id=body.address_id,
        custom_address=body.custom_address,
        slot_start=body.slot_start,
        slot_end=body.slot_end,
    )
    db.add(booking)
    await db.flush()

    if body.notes:
        db.add(BookingNote(booking_id=booking.booking_id, author="user", message=body.notes))

    await db.commit()

    result = await db.execute(_booking_query().where(Booking.booking_id == booking.booking_id))
    return result.scalar_one()


@router.get("", response_model=list[BookingOut])
async def list_bookings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = _booking_query()
    if current_user.role != "admin":
        q = q.where(Booking.user_id == current_user.user_id)
    result = await db.execute(q.order_by(Booking.created_at.desc()))
    return result.scalars().all()


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role != "admin" and booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return booking


@router.post("/{booking_id}/notes", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def add_note(
    booking_id: int,
    body: BookingNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role != "admin" and booking.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    author = "admin" if current_user.role == "admin" else "user"
    db.add(BookingNote(booking_id=booking_id, author=author, message=body.message))
    await db.commit()

    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    return result.scalar_one()


@router.patch("/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: int,
    body: AssignedNurseIn,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in {"requested", "confirmed"}:
        raise HTTPException(status_code=400, detail=f"Cannot confirm a booking in '{booking.status}' status")

    booking.status = "confirmed"
    if booking.assigned_nurse:
        booking.assigned_nurse.nurse_name = body.nurse_name
        booking.assigned_nurse.nurse_contact = body.nurse_contact
    else:
        db.add(AssignedNurse(booking_id=booking_id, nurse_name=body.nurse_name, nurse_contact=body.nurse_contact))

    await db.commit()
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    return result.scalar_one()


@router.patch("/{booking_id}/status", response_model=BookingOut)
async def update_status(
    booking_id: int,
    body: BookingStatusUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {VALID_STATUSES}")
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = body.status
    await db.commit()
    result = await db.execute(_booking_query().where(Booking.booking_id == booking_id))
    return result.scalar_one()
