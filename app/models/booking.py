from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    booking_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    member_id: Mapped[int | None] = mapped_column(ForeignKey("family_members.member_id", ondelete="SET NULL"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.service_id"))
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.address_id", ondelete="SET NULL"))
    custom_address: Mapped[str | None] = mapped_column(String(1000))
    slot_start: Mapped[datetime] = mapped_column(DateTime)
    slot_end: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="bookings")
    member: Mapped["FamilyMember | None"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship(back_populates="bookings")
    address: Mapped["Address | None"] = relationship(back_populates="bookings")
    notes: Mapped[list["BookingNote"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    assigned_nurse: Mapped["AssignedNurse | None"] = relationship(back_populates="booking", cascade="all, delete-orphan", uselist=False)


class BookingNote(Base):
    __tablename__ = "booking_notes"

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.booking_id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    booking: Mapped["Booking"] = relationship(back_populates="notes")


class AssignedNurse(Base):
    __tablename__ = "assigned_nurses"

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.booking_id", ondelete="CASCADE"), unique=True)
    nurse_name: Mapped[str] = mapped_column(String(255))
    nurse_contact: Mapped[str | None] = mapped_column(String(100))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    booking: Mapped["Booking"] = relationship(back_populates="assigned_nurse")
