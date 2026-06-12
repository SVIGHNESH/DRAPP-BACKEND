"""Smoke tests — no DB required, just validates app import and schema logic."""
import pytest
from pydantic import ValidationError

from app.schemas.booking import BookingCreate
from datetime import datetime


def test_booking_requires_exactly_one_address():
    base = dict(service_id=1, slot_start=datetime(2026, 6, 15, 8), slot_end=datetime(2026, 6, 15, 20))

    # both provided → error
    with pytest.raises(ValidationError):
        BookingCreate(**base, address_id=1, custom_address="123 Main St")

    # neither provided → error
    with pytest.raises(ValidationError):
        BookingCreate(**base)

    # only address_id → ok
    b = BookingCreate(**base, address_id=1)
    assert b.address_id == 1
    assert b.custom_address is None

    # only custom_address → ok
    b = BookingCreate(**base, custom_address="123 Main St, Delhi")
    assert b.custom_address == "123 Main St, Delhi"
    assert b.address_id is None
